from __future__ import annotations

import math
from collections import Counter
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from wellnessbox_rnd.models import (
    EfficacyModelArtifact,
    PolicyModelArtifact,
    load_efficacy_model_artifact,
    load_policy_model_artifact,
    predict_effect_proxy,
    predict_policy_action,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.policy import apply_policy_guard
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
    BLOCKED = "blocked"
    START_PLAN = "start_plan"
    ASK_TARGETED_FOLLOWUP = "ask_targeted_followup"
    TRIGGER_SAFETY_RECHECK = "trigger_safety_recheck"
    CONTINUE_PLAN = "continue_plan"
    RE_OPTIMIZE = "re_optimize"
    REDUCE_OR_STOP = "reduce_or_stop"
    MONITOR_ONLY = "monitor_only"


class EffectSource(StrEnum):
    LEARNED_MODEL = "learned_model"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class PolicyActionSource(StrEnum):
    DETERMINISTIC_POLICY = "deterministic_policy"
    LEARNED_POLICY_GUARDED = "learned_policy_guarded"


class SimulationTraceStep(BaseModel):
    cycle_index: int = Field(ge=0)
    day_index: int = Field(ge=0)
    state_before: str
    reminder_sent: bool = False
    policy_action: SimulationPolicyAction
    policy_action_source: PolicyActionSource
    state_after: str
    request_id: str
    engine_status: RecommendationStatus
    engine_next_action: NextAction
    selected_policy_next_action: NextAction
    raw_policy_next_action: NextAction | None = None
    policy_guard_applied: bool = False
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
    policy_model_artifact_path: str | None = None
    policy_model_loaded: bool = False
    learned_policy_enabled: bool = False
    learned_reranking_enabled: bool = False
    trace: list[SimulationTraceStep] = Field(default_factory=list)
    final_state: str
    final_policy_action: SimulationPolicyAction
    terminated_early: bool


class ClosedLoopBatchModeReport(BaseModel):
    mode_name: str
    dataset_path: str
    scenario_count: int
    user_ids: list[str] = Field(default_factory=list)
    max_cycles: int = Field(ge=1)
    model_artifact_path: str | None = None
    model_loaded: bool = False
    policy_model_artifact_path: str | None = None
    policy_model_loaded: bool = False
    learned_policy_enabled: bool = False
    learned_reranking_enabled: bool = False
    scenario_reports: list[ClosedLoopSimulationReport] = Field(default_factory=list)
    total_trace_steps: int = Field(ge=0)
    average_trace_length: float = Field(ge=0.0)
    terminated_early_count: int = Field(ge=0)
    adverse_event_count: int = Field(ge=0)
    average_predicted_effect_proxy: float
    final_state_counts: dict[str, int]
    final_policy_action_counts: dict[str, int]
    policy_action_source_counts: dict[str, int]
    engine_next_action_counts: dict[str, int]
    selected_policy_next_action_counts: dict[str, int]
    state_transition_counts: dict[str, int]
    policy_guard_applied_count: int = Field(ge=0)
    learned_policy_disagreement_count: int = Field(ge=0)


class ClosedLoopBatchComparisonReport(BaseModel):
    scenario_set_id: str
    dataset_path: str
    compared_modes: list[ClosedLoopBatchModeReport]
    differing_final_state_user_ids: list[str] = Field(default_factory=list)
    differing_final_policy_user_ids: list[str] = Field(default_factory=list)
    differing_policy_path_user_ids: list[str] = Field(default_factory=list)


def simulate_closed_loop_scenario(
    *,
    dataset_path: str | Path,
    user_id: str,
    max_cycles: int = 3,
    model_artifact_path: str | Path | None = None,
    policy_model_artifact_path: str | Path | None = None,
    enable_learned_policy: bool = False,
    enable_learned_reranking: bool = False,
) -> ClosedLoopSimulationReport:
    records = load_synthetic_records(dataset_path)
    baseline_record = _load_baseline_record(records, user_id=user_id)
    artifact = _load_optional_artifact(model_artifact_path)
    policy_artifact = _load_optional_policy_artifact(policy_model_artifact_path)
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
        (
            selected_policy_next_action,
            raw_policy_next_action,
            policy_action_source,
            policy_guard_applied,
        ) = _resolve_policy_next_action(
            artifact=policy_artifact,
            request=request,
            response=response,
            cycle_index=cycle_index,
            user_rng_seed=baseline_record.rng_seed,
            adherence_proxy=signals.adherence_proxy,
            risk_tier=signals.risk_tier,
            fallback_effect_proxy=signals.fallback_effect_proxy,
            fallback_closed_loop_state=signals.fallback_closed_loop_state,
            enable_learned_policy=enable_learned_policy,
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
            next_action=selected_policy_next_action,
            response_status=response.status,
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
                policy_action_source=policy_action_source,
                state_after=state_after,
                request_id=request.request_id,
                engine_status=response.status,
                engine_next_action=response.next_action,
                selected_policy_next_action=selected_policy_next_action,
                raw_policy_next_action=raw_policy_next_action,
                policy_guard_applied=policy_guard_applied,
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
            "blocked",
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
        policy_model_artifact_path=(
            str(Path(policy_model_artifact_path))
            if policy_model_artifact_path is not None
            else None
        ),
        policy_model_loaded=policy_artifact is not None,
        learned_policy_enabled=enable_learned_policy,
        learned_reranking_enabled=enable_learned_reranking,
        trace=trace,
        final_state=final_step.state_after,
        final_policy_action=final_step.policy_action,
        terminated_early=terminated_early,
    )


def simulate_closed_loop_batch(
    *,
    dataset_path: str | Path,
    max_cycles: int = 3,
    max_users: int | None = None,
    model_artifact_path: str | Path | None = None,
    policy_model_artifact_path: str | Path | None = None,
    enable_learned_policy: bool = False,
    enable_learned_reranking: bool = False,
    mode_name: str,
) -> ClosedLoopBatchModeReport:
    records = load_synthetic_records(dataset_path)
    user_ids = sorted(
        {
            record.user_id
            for record in records
            if record.follow_up_step == 0
        }
    )
    if max_users is not None:
        user_ids = user_ids[:max_users]

    scenario_reports = [
        simulate_closed_loop_scenario(
            dataset_path=dataset_path,
            user_id=user_id,
            max_cycles=max_cycles,
            model_artifact_path=model_artifact_path,
            policy_model_artifact_path=policy_model_artifact_path,
            enable_learned_policy=enable_learned_policy,
            enable_learned_reranking=enable_learned_reranking,
        )
        for user_id in user_ids
    ]
    total_trace_steps = sum(len(report.trace) for report in scenario_reports)
    average_trace_length = (
        round(total_trace_steps / len(scenario_reports), 6) if scenario_reports else 0.0
    )
    predicted_effect_values = [
        step.predicted_effect_proxy
        for report in scenario_reports
        for step in report.trace
    ]
    average_predicted_effect_proxy = (
        round(sum(predicted_effect_values) / len(predicted_effect_values), 6)
        if predicted_effect_values
        else 0.0
    )
    final_state_counts = Counter(report.final_state for report in scenario_reports)
    final_policy_action_counts = Counter(
        report.final_policy_action.value for report in scenario_reports
    )
    policy_action_source_counts = Counter(
        step.policy_action_source.value
        for report in scenario_reports
        for step in report.trace
    )
    engine_next_action_counts = Counter(
        step.engine_next_action.value
        for report in scenario_reports
        for step in report.trace
    )
    selected_policy_next_action_counts = Counter(
        step.selected_policy_next_action.value
        for report in scenario_reports
        for step in report.trace
    )
    state_transition_counts = Counter(
        f"{step.state_before}->{step.state_after}"
        for report in scenario_reports
        for step in report.trace
    )
    policy_guard_applied_count = sum(
        1
        for report in scenario_reports
        for step in report.trace
        if step.policy_guard_applied
    )
    learned_policy_disagreement_count = sum(
        1
        for report in scenario_reports
        for step in report.trace
        if step.raw_policy_next_action is not None
        and step.raw_policy_next_action != step.engine_next_action
    )
    adverse_event_count = sum(
        1
        for report in scenario_reports
        for step in report.trace
        if step.adverse_event
    )
    terminated_early_count = sum(
        1 for report in scenario_reports if report.terminated_early
    )

    return ClosedLoopBatchModeReport(
        mode_name=mode_name,
        dataset_path=str(Path(dataset_path)),
        scenario_count=len(scenario_reports),
        user_ids=user_ids,
        max_cycles=max_cycles,
        model_artifact_path=(
            str(Path(model_artifact_path)) if model_artifact_path is not None else None
        ),
        model_loaded=bool(model_artifact_path and Path(model_artifact_path).exists()),
        policy_model_artifact_path=(
            str(Path(policy_model_artifact_path))
            if policy_model_artifact_path is not None
            else None
        ),
        policy_model_loaded=bool(
            policy_model_artifact_path and Path(policy_model_artifact_path).exists()
        ),
        learned_policy_enabled=enable_learned_policy,
        learned_reranking_enabled=enable_learned_reranking,
        scenario_reports=scenario_reports,
        total_trace_steps=total_trace_steps,
        average_trace_length=average_trace_length,
        terminated_early_count=terminated_early_count,
        adverse_event_count=adverse_event_count,
        average_predicted_effect_proxy=average_predicted_effect_proxy,
        final_state_counts=dict(sorted(final_state_counts.items())),
        final_policy_action_counts=dict(sorted(final_policy_action_counts.items())),
        policy_action_source_counts=dict(sorted(policy_action_source_counts.items())),
        engine_next_action_counts=dict(sorted(engine_next_action_counts.items())),
        selected_policy_next_action_counts=dict(
            sorted(selected_policy_next_action_counts.items())
        ),
        state_transition_counts=dict(sorted(state_transition_counts.items())),
        policy_guard_applied_count=policy_guard_applied_count,
        learned_policy_disagreement_count=learned_policy_disagreement_count,
    )


def compare_batch_simulation_modes(
    *,
    dataset_path: str | Path,
    max_cycles: int = 3,
    max_users: int | None = None,
    model_artifact_path: str | Path | None = None,
    policy_model_artifact_path: str | Path | None = None,
) -> ClosedLoopBatchComparisonReport:
    deterministic_report = simulate_closed_loop_batch(
        dataset_path=dataset_path,
        max_cycles=max_cycles,
        max_users=max_users,
        model_artifact_path=model_artifact_path,
        policy_model_artifact_path=policy_model_artifact_path,
        enable_learned_policy=False,
        enable_learned_reranking=False,
        mode_name="deterministic_only",
    )
    learned_policy_report = simulate_closed_loop_batch(
        dataset_path=dataset_path,
        max_cycles=max_cycles,
        max_users=max_users,
        model_artifact_path=model_artifact_path,
        policy_model_artifact_path=policy_model_artifact_path,
        enable_learned_policy=True,
        enable_learned_reranking=False,
        mode_name="learned_policy_guarded",
    )
    baseline_by_user = {
        report.user_id: report for report in deterministic_report.scenario_reports
    }
    learned_by_user = {
        report.user_id: report for report in learned_policy_report.scenario_reports
    }
    differing_final_state_user_ids: list[str] = []
    differing_final_policy_user_ids: list[str] = []
    differing_policy_path_user_ids: list[str] = []
    for user_id in sorted(set(baseline_by_user) & set(learned_by_user)):
        baseline = baseline_by_user[user_id]
        learned = learned_by_user[user_id]
        if baseline.final_state != learned.final_state:
            differing_final_state_user_ids.append(user_id)
        if baseline.final_policy_action != learned.final_policy_action:
            differing_final_policy_user_ids.append(user_id)
        if [
            step.selected_policy_next_action for step in baseline.trace
        ] != [
            step.selected_policy_next_action for step in learned.trace
        ]:
            differing_policy_path_user_ids.append(user_id)

    return ClosedLoopBatchComparisonReport(
        scenario_set_id="closed-loop-batch-v0",
        dataset_path=str(Path(dataset_path)),
        compared_modes=[deterministic_report, learned_policy_report],
        differing_final_state_user_ids=differing_final_state_user_ids,
        differing_final_policy_user_ids=differing_final_policy_user_ids,
        differing_policy_path_user_ids=differing_policy_path_user_ids,
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
        f"- policy_model_loaded: `{report.policy_model_loaded}`",
        f"- learned_policy_enabled: `{report.learned_policy_enabled}`",
        f"- learned_reranking_enabled: `{report.learned_reranking_enabled}`",
        f"- final_state: `{report.final_state}`",
        f"- final_policy_action: `{report.final_policy_action.value}`",
        f"- terminated_early: `{report.terminated_early}`",
        "",
        "## Trace",
        "",
        (
            "| cycle | day | before | reminder | engine_action | selected_action | "
            "policy_action | source | guard | after | effect | effect_source | "
            "adverse_event | recommendations |"
        ),
        (
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
            "--- | --- | --- |"
        ),
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
            f"{step.selected_policy_next_action.value} | "
            f"{step.policy_action.value} | "
            f"{step.policy_action_source.value} | "
            f"{'yes' if step.policy_guard_applied else 'no'} | "
            f"{step.state_after} | "
            f"{step.predicted_effect_proxy} | "
            f"{step.predicted_effect_source.value} | "
            f"{'yes' if step.adverse_event else 'no'} | "
            f"{recommendation_keys} |"
        )
    return "\n".join(lines) + "\n"


def render_batch_simulation_markdown(report: ClosedLoopBatchComparisonReport) -> str:
    lines = [
        "# closed loop batch simulation v0",
        "",
        f"- scenario_set_id: `{report.scenario_set_id}`",
        f"- dataset_path: `{report.dataset_path}`",
        f"- differing_final_state_user_ids: `{len(report.differing_final_state_user_ids)}`",
        f"- differing_final_policy_user_ids: `{len(report.differing_final_policy_user_ids)}`",
        f"- differing_policy_path_user_ids: `{len(report.differing_policy_path_user_ids)}`",
        "",
    ]
    for mode in report.compared_modes:
        lines.extend(
            [
                f"## {mode.mode_name}",
                "",
                f"- scenario_count: `{mode.scenario_count}`",
                f"- total_trace_steps: `{mode.total_trace_steps}`",
                f"- average_trace_length: `{mode.average_trace_length}`",
                f"- terminated_early_count: `{mode.terminated_early_count}`",
                f"- adverse_event_count: `{mode.adverse_event_count}`",
                f"- average_predicted_effect_proxy: `{mode.average_predicted_effect_proxy}`",
                f"- learned_policy_enabled: `{mode.learned_policy_enabled}`",
                f"- policy_model_loaded: `{mode.policy_model_loaded}`",
                f"- policy_guard_applied_count: `{mode.policy_guard_applied_count}`",
                f"- learned_policy_disagreement_count: `{mode.learned_policy_disagreement_count}`",
                "",
                "### Final States",
            ]
        )
        for key, value in mode.final_state_counts.items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend(["", "### Final Policy Actions"])
        for key, value in mode.final_policy_action_counts.items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend(["", "### Policy Action Sources"])
        for key, value in mode.policy_action_source_counts.items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend(["", "### State Transitions"])
        for key, value in mode.state_transition_counts.items():
            lines.append(f"- `{key}`: `{value}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


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


def write_batch_simulation_outputs(
    *,
    report: ClosedLoopBatchComparisonReport,
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
        render_batch_simulation_markdown(report),
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


def _load_optional_policy_artifact(
    path: str | Path | None,
) -> PolicyModelArtifact | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return load_policy_model_artifact(target)


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


def _resolve_policy_next_action(
    *,
    artifact: PolicyModelArtifact | None,
    request: RecommendationRequest,
    response,
    cycle_index: int,
    user_rng_seed: int,
    adherence_proxy: float,
    risk_tier: str,
    fallback_effect_proxy: float,
    fallback_closed_loop_state: str,
    enable_learned_policy: bool,
) -> tuple[NextAction, NextAction | None, PolicyActionSource, bool]:
    deterministic_action = response.next_action
    if artifact is None or not enable_learned_policy:
        return (
            deterministic_action,
            None,
            PolicyActionSource.DETERMINISTIC_POLICY,
            False,
        )
    transient_record = SyntheticCohortRecord(
        record_id=f"{request.request_id}-policy-step-{cycle_index}",
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
            next_action=deterministic_action,
            reason_code=response.next_action_rationale.reason_code,
            safety_status=response.status,
            risk_tier=risk_tier,
            adverse_event=False,
            closed_loop_state=fallback_closed_loop_state,
        ),
    )
    raw_predicted_action = predict_policy_action(artifact, transient_record)
    guarded_action = apply_policy_guard(
        predicted_action=raw_predicted_action,
        deterministic_action=deterministic_action,
    )
    return (
        guarded_action,
        raw_predicted_action,
        PolicyActionSource.LEARNED_POLICY_GUARDED,
        guarded_action != raw_predicted_action,
    )


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
    next_action: NextAction,
    response_status: RecommendationStatus,
    predicted_effect_proxy: float,
    adverse_event: bool,
) -> tuple[SimulationPolicyAction, str]:
    if cycle_index == 0:
        if next_action == NextAction.BLOCKED:
            return (
                SimulationPolicyAction.BLOCKED,
                "blocked",
            )
        if next_action == NextAction.START_PLAN:
            return (
                SimulationPolicyAction.START_PLAN,
                "recommendation_ready",
            )
        if next_action == NextAction.COLLECT_MORE_INPUT:
            return (
                SimulationPolicyAction.ASK_TARGETED_FOLLOWUP,
                "baseline_questionnaire_due",
            )
        return (SimulationPolicyAction.TRIGGER_SAFETY_RECHECK, "safety_review")

    if adverse_event:
        return (SimulationPolicyAction.REDUCE_OR_STOP, "stop_or_escalate")
    if next_action == NextAction.BLOCKED:
        return (SimulationPolicyAction.BLOCKED, "blocked")
    if next_action == NextAction.TRIGGER_SAFETY_RECHECK:
        return (SimulationPolicyAction.TRIGGER_SAFETY_RECHECK, "safety_review")
    if next_action == NextAction.COLLECT_MORE_INPUT:
        return (SimulationPolicyAction.ASK_TARGETED_FOLLOWUP, "re_evaluation")
    if response_status == RecommendationStatus.NEEDS_REVIEW:
        return (SimulationPolicyAction.TRIGGER_SAFETY_RECHECK, "safety_review")
    if predicted_effect_proxy > 0:
        return (SimulationPolicyAction.CONTINUE_PLAN, "intake_active")
    return (SimulationPolicyAction.RE_OPTIMIZE, "adjust_plan")
