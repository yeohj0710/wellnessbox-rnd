from __future__ import annotations

import math
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from wellnessbox_rnd.models import (
    EfficacyModelArtifact,
    load_efficacy_model_artifact,
    predict_effect_proxy,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    NextAction,
    RecommendationRequest,
    RecommendationStatus,
)
from wellnessbox_rnd.synthetic import (
    SyntheticCohortRecord,
    SyntheticLabels,
    advance_synthetic_request_for_step,
    build_synthetic_step_signals,
)
from wellnessbox_rnd.training import load_synthetic_records


class SimulationPolicyAction(StrEnum):
    PRESENT_RECOMMENDATION = "present_recommendation"
    REQUEST_BASELINE_QUESTIONNAIRE = "request_baseline_questionnaire"
    REQUEST_SAFETY_REVIEW = "request_safety_review"
    SEND_FOLLOWUP_REMINDER = "send_followup_reminder"
    CONTINUE_PLAN = "continue_plan"
    RE_OPTIMIZE_COMBINATION = "re_optimize_combination"
    STOP_AND_ESCALATE = "stop_and_escalate"


class EffectSource(StrEnum):
    LEARNED_MODEL = "learned_model"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class SimulationTraceStep(BaseModel):
    cycle_index: int = Field(ge=0)
    day_index: int = Field(ge=0)
    state_before: str
    reminder_sent: bool = False
    policy_action: SimulationPolicyAction
    state_after: str
    request_id: str
    engine_status: RecommendationStatus
    engine_next_action: NextAction
    reason_code: str
    recommendation_keys: list[str] = Field(default_factory=list)
    follow_up_window_days: int = Field(ge=1, le=90)
    predicted_effect_proxy: float = Field(ge=-1.0, le=1.0)
    predicted_effect_source: EffectSource
    adherence_proxy: float = Field(ge=0.0, le=1.0)
    risk_tier: str
    adverse_event: bool
    fallback_closed_loop_state: str


class ClosedLoopSimulationReport(BaseModel):
    scenario_id: str
    user_id: str
    cohort_version: str
    dataset_path: str
    user_rng_seed: int
    model_artifact_path: str | None = None
    model_loaded: bool = False
    learned_reranking_enabled: bool = False
    trace: list[SimulationTraceStep] = Field(default_factory=list)
    final_state: str
    final_policy_action: SimulationPolicyAction
    terminated_early: bool


def simulate_closed_loop_scenario(
    *,
    dataset_path: str | Path,
    user_id: str,
    max_cycles: int = 3,
    model_artifact_path: str | Path | None = None,
    enable_learned_reranking: bool = False,
) -> ClosedLoopSimulationReport:
    records = load_synthetic_records(dataset_path)
    baseline_record = _load_baseline_record(records, user_id=user_id)
    artifact = _load_optional_artifact(model_artifact_path)
    trace: list[SimulationTraceStep] = []
    request = baseline_record.request
    terminated_early = False

    for cycle_index in range(max_cycles):
        response = recommend(
            request,
            enable_learned_reranking=enable_learned_reranking,
            learned_efficacy_artifact_path=(
                str(model_artifact_path) if model_artifact_path is not None else None
            ),
        )
        signals = build_synthetic_step_signals(
            request=request,
            step=cycle_index,
            response=response,
        )
        predicted_effect_proxy, predicted_effect_source = _resolve_effect_proxy(
            artifact=artifact,
            request=request,
            response=response,
            cycle_index=cycle_index,
            user_rng_seed=baseline_record.rng_seed,
            adherence_proxy=signals.adherence_proxy,
            risk_tier=signals.risk_tier,
            fallback_effect_proxy=signals.fallback_effect_proxy,
            fallback_closed_loop_state=signals.fallback_closed_loop_state,
        )
        adverse_event = _resolve_adverse_event(
            cycle_index=cycle_index,
            response=response,
            predicted_effect_proxy=predicted_effect_proxy,
            risk_tier=signals.risk_tier,
        )
        state_before = "baseline_intake" if cycle_index == 0 else "followup_received"
        reminder_sent = cycle_index > 0 and bool(trace)
        policy_action, state_after = _policy_transition(
            cycle_index=cycle_index,
            response=response,
            predicted_effect_proxy=predicted_effect_proxy,
            adverse_event=adverse_event,
        )
        trace.append(
            SimulationTraceStep(
                cycle_index=cycle_index,
                day_index=cycle_index * 14,
                state_before=state_before,
                reminder_sent=reminder_sent,
                policy_action=policy_action,
                state_after=state_after,
                request_id=request.request_id,
                engine_status=response.status,
                engine_next_action=response.next_action,
                reason_code=response.next_action_rationale.reason_code,
                recommendation_keys=[
                    item.ingredient_key for item in response.recommendations
                ],
                follow_up_window_days=response.follow_up_window_days,
                predicted_effect_proxy=predicted_effect_proxy,
                predicted_effect_source=predicted_effect_source,
                adherence_proxy=signals.adherence_proxy,
                risk_tier=signals.risk_tier,
                adverse_event=adverse_event,
                fallback_closed_loop_state=signals.fallback_closed_loop_state,
            )
        )

        if state_after in {
            "baseline_questionnaire_due",
            "safety_review",
            "stop_or_escalate",
        }:
            terminated_early = cycle_index < max_cycles - 1
            break
        if cycle_index == max_cycles - 1:
            break
        request = advance_synthetic_request_for_step(
            request=request,
            response=response,
            step=cycle_index + 1,
        )

    final_step = trace[-1]
    return ClosedLoopSimulationReport(
        scenario_id=f"closed-loop-{user_id}",
        user_id=user_id,
        cohort_version=baseline_record.cohort_version,
        dataset_path=str(Path(dataset_path)),
        user_rng_seed=baseline_record.rng_seed,
        model_artifact_path=(
            str(Path(model_artifact_path)) if model_artifact_path is not None else None
        ),
        model_loaded=artifact is not None,
        learned_reranking_enabled=enable_learned_reranking,
        trace=trace,
        final_state=final_step.state_after,
        final_policy_action=final_step.policy_action,
        terminated_early=terminated_early,
    )


def render_simulation_markdown(report: ClosedLoopSimulationReport) -> str:
    lines = [
        "# closed loop simulation v0",
        "",
        f"- scenario_id: `{report.scenario_id}`",
        f"- user_id: `{report.user_id}`",
        f"- cohort_version: `{report.cohort_version}`",
        f"- dataset_path: `{report.dataset_path}`",
        f"- model_loaded: `{report.model_loaded}`",
        f"- learned_reranking_enabled: `{report.learned_reranking_enabled}`",
        f"- final_state: `{report.final_state}`",
        f"- final_policy_action: `{report.final_policy_action.value}`",
        f"- terminated_early: `{report.terminated_early}`",
        "",
        "## Trace",
        "",
        (
            "| cycle | day | before | reminder | engine_action | policy_action | "
            "after | effect | source | adverse_event | recommendations |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for step in report.trace:
        recommendation_keys = ", ".join(step.recommendation_keys) or "-"
        lines.append(
            "| "
            f"{step.cycle_index} | "
            f"{step.day_index} | "
            f"{step.state_before} | "
            f"{'yes' if step.reminder_sent else 'no'} | "
            f"{step.engine_next_action.value} | "
            f"{step.policy_action.value} | "
            f"{step.state_after} | "
            f"{step.predicted_effect_proxy} | "
            f"{step.predicted_effect_source.value} | "
            f"{'yes' if step.adverse_event else 'no'} | "
            f"{recommendation_keys} |"
        )
    return "\n".join(lines) + "\n"


def write_simulation_outputs(
    *,
    report: ClosedLoopSimulationReport,
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    report_json_target = Path(report_json_path)
    report_md_target = Path(report_md_path)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(
        render_simulation_markdown(report),
        encoding="utf-8",
    )


def _load_baseline_record(
    records: list[SyntheticCohortRecord],
    *,
    user_id: str,
) -> SyntheticCohortRecord:
    for record in records:
        if record.user_id == user_id and record.follow_up_step == 0:
            return record
    raise ValueError(f"step-0 synthetic record not found for user_id={user_id}")


def _load_optional_artifact(
    path: str | Path | None,
) -> EfficacyModelArtifact | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return load_efficacy_model_artifact(target)


def _resolve_effect_proxy(
    *,
    artifact: EfficacyModelArtifact | None,
    request: RecommendationRequest,
    response,
    cycle_index: int,
    user_rng_seed: int,
    adherence_proxy: float,
    risk_tier: str,
    fallback_effect_proxy: float,
    fallback_closed_loop_state: str,
) -> tuple[float, EffectSource]:
    if artifact is None:
        return fallback_effect_proxy, EffectSource.DETERMINISTIC_FALLBACK

    transient_record = SyntheticCohortRecord(
        record_id=f"{request.request_id}-sim-step-{cycle_index}",
        user_id=request.request_id,
        rng_seed=user_rng_seed,
        follow_up_step=cycle_index,
        day_index=cycle_index * 14,
        request=request,
        expected_effect_proxy=fallback_effect_proxy,
        adherence_proxy=adherence_proxy,
        baseline_recommendations=[
            item.ingredient_key for item in response.recommendations
        ],
        labels=SyntheticLabels(
            next_action=response.next_action,
            reason_code=response.next_action_rationale.reason_code,
            safety_status=response.status,
            risk_tier=risk_tier,
            adverse_event=False,
            closed_loop_state=fallback_closed_loop_state,
        ),
    )
    predicted = predict_effect_proxy(artifact, transient_record)
    if not math.isfinite(predicted) or predicted < -1.0 or predicted > 1.0:
        return fallback_effect_proxy, EffectSource.DETERMINISTIC_FALLBACK
    return predicted, EffectSource.LEARNED_MODEL


def _resolve_adverse_event(
    *,
    cycle_index: int,
    response,
    predicted_effect_proxy: float,
    risk_tier: str,
) -> bool:
    if cycle_index == 0:
        return False
    if risk_tier == "high" and response.next_action != NextAction.START_PLAN:
        return True
    return predicted_effect_proxy < -0.05 and risk_tier != "low"


def _policy_transition(
    *,
    cycle_index: int,
    response,
    predicted_effect_proxy: float,
    adverse_event: bool,
) -> tuple[SimulationPolicyAction, str]:
    if cycle_index == 0:
        if response.next_action == NextAction.START_PLAN:
            return (
                SimulationPolicyAction.PRESENT_RECOMMENDATION,
                "recommendation_ready",
            )
        if response.next_action == NextAction.COLLECT_MORE_INPUT:
            return (
                SimulationPolicyAction.REQUEST_BASELINE_QUESTIONNAIRE,
                "baseline_questionnaire_due",
            )
        return (SimulationPolicyAction.REQUEST_SAFETY_REVIEW, "safety_review")

    if adverse_event:
        return (SimulationPolicyAction.STOP_AND_ESCALATE, "stop_or_escalate")
    if response.next_action == NextAction.NEEDS_HUMAN_REVIEW:
        return (SimulationPolicyAction.REQUEST_SAFETY_REVIEW, "safety_review")
    if response.next_action == NextAction.COLLECT_MORE_INPUT:
        return (SimulationPolicyAction.RE_OPTIMIZE_COMBINATION, "re_evaluation")
    if response.status == RecommendationStatus.NEEDS_REVIEW:
        return (SimulationPolicyAction.REQUEST_SAFETY_REVIEW, "safety_review")
    if predicted_effect_proxy > 0:
        return (SimulationPolicyAction.CONTINUE_PLAN, "intake_active")
    return (SimulationPolicyAction.RE_OPTIMIZE_COMBINATION, "adjust_plan")
