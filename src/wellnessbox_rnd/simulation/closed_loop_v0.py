from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from wellnessbox_rnd.models import (
    EffectModelV1Artifact,
    PolicyModelV1Artifact,
    build_policy_feature_dict_v1,
    load_effect_model_v1_artifact,
    load_policy_model_v1_artifact,
    predict_policy_action_v1,
    predict_policy_effect_proxy_v1,
    predict_policy_scores_from_feature_dict_v1,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.policy import apply_policy_guard
from wellnessbox_rnd.schemas.recommendation import NextAction, RecommendationStatus
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import (
    DOSE_TEMPLATES,
    RichRegimenItem,
    RichSyntheticCohortRecord,
)

SIMULATION_VERSION = "closed_loop_batch_simulation_v3_compare"
TRACE_SAMPLE_LIMIT = 4
LEARNED_EFFECT_NEAR_TIE_GAP = 1.0
CONTINUE_PLAN_EFFECT_PRIOR_BONUS = 0.8
MONITOR_ONLY_EFFECT_PRIOR_BONUS = 0.65
RE_OPTIMIZE_EFFECT_PRIOR_BONUS = 1.1
RE_OPTIMIZE_REVIVAL_PROXY_MIN = 0.18
RE_OPTIMIZE_REVIVAL_PROXY_MAX = 0.205
RE_OPTIMIZE_CGM_REVIVAL_PROXY_MAX = 0.222
RE_OPTIMIZE_REVIVAL_BONUS = 0.95
RE_OPTIMIZE_REVIVAL_MONITOR_PENALTY = 0.2
RE_OPTIMIZE_REVIVAL_CONTINUE_PENALTY = 0.25
CONTINUE_PLAN_TRIGGER_PENALTY = 0.15
MONITOR_ONLY_TRIGGER_PENALTY = 0.3
RE_OPTIMIZE_TRIGGER_PENALTY = 0.4
TERMINAL_STATES = {
    "baseline_questionnaire_due",
    "blocked",
    "safety_review",
    "stop_or_escalate",
}
REPLAY_SLICES: dict[str, Callable[[RichSyntheticCohortRecord], bool]] = {
    "cgm_users": lambda record: record.request.input_availability.cgm,
    "genetic_users": lambda record: record.request.input_availability.genetic,
    "low_risk_users": lambda record: record.labels.risk_tier == "low",
    "high_risk_users": lambda record: record.labels.risk_tier == "high",
    "single_goal_users": lambda record: len(record.request.goals) == 1,
    "multi_goal_users": lambda record: len(record.request.goals) > 1,
}


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
    LEARNED_MODEL_V1 = "learned_model_v1"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"


class PolicyActionSource(StrEnum):
    DETERMINISTIC_POLICY = "deterministic_policy"
    LEARNED_POLICY_GUARDED = "learned_policy_guarded"


class RankingSource(StrEnum):
    DETERMINISTIC_RANKING = "deterministic_ranking"
    LEARNED_EFFECT_GUARDED = "learned_effect_guarded"


class SimulationTraceStep(BaseModel):
    cycle_index: int = Field(ge=0)
    day_index: int = Field(ge=0)
    state_before: str
    state_after: str
    request_id: str
    engine_status: RecommendationStatus
    engine_next_action: NextAction
    deterministic_action: SimulationPolicyAction
    raw_learned_policy_action: SimulationPolicyAction | None = None
    selected_policy_action: SimulationPolicyAction
    policy_guard_applied: bool = False
    policy_guard_reason: str | None = None
    deterministic_top_candidate: str | None = None
    raw_learned_top_candidate: str | None = None
    selected_candidate: str | None = None
    effect_guard_applied: bool = False
    effect_guard_reason: str | None = None
    action_source: PolicyActionSource
    ranking_source: RankingSource
    reason_code: str
    recommendation_keys: list[str] = Field(default_factory=list)
    follow_up_window_days: int = Field(ge=1, le=90)
    predicted_effect_proxy: float
    predicted_effect_source: EffectSource
    policy_effect_proxy_used: float
    policy_effect_proxy_override_applied: bool = False
    adherence_proxy: float = Field(ge=0.0, le=1.0)
    side_effect_proxy: float = Field(ge=0.0, le=1.0)
    risk_tier: str
    adverse_event: bool


class ClosedLoopSimulationReport(BaseModel):
    scenario_id: str
    mode_name: str
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
    final_candidate: str | None = None
    terminated_early: bool


class CohortSliceSummary(BaseModel):
    slice_name: str
    user_count: int = Field(ge=0)
    avg_trace_length: float = Field(ge=0.0)
    final_state_distribution: dict[str, int] = Field(default_factory=dict)
    final_action_distribution: dict[str, int] = Field(default_factory=dict)
    avg_effect: float = 0.0
    adverse_event_count: int = Field(ge=0)
    deterministic_vs_learned_disagreement_count: int = Field(default=0, ge=0)
    policy_guard_applied_count: int = Field(ge=0)
    effect_guard_applied_count: int = Field(ge=0)


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
    average_predicted_effect_proxy: float = 0.0
    final_state_counts: dict[str, int] = Field(default_factory=dict)
    final_policy_action_counts: dict[str, int] = Field(default_factory=dict)
    action_source_counts: dict[str, int] = Field(default_factory=dict)
    ranking_source_counts: dict[str, int] = Field(default_factory=dict)
    engine_next_action_counts: dict[str, int] = Field(default_factory=dict)
    state_transition_counts: dict[str, int] = Field(default_factory=dict)
    policy_guard_applied_count: int = Field(ge=0)
    effect_guard_applied_count: int = Field(ge=0)
    policy_effect_override_applied_count: int = Field(ge=0)
    raw_policy_disagreement_count: int = Field(ge=0)
    raw_ranking_disagreement_count: int = Field(ge=0)
    deterministic_vs_learned_disagreement_count: int = Field(default=0, ge=0)
    cohort_slice_metrics: dict[str, CohortSliceSummary] = Field(default_factory=dict)


class TraceSample(BaseModel):
    user_id: str
    mode_name: str
    trace: list[SimulationTraceStep] = Field(default_factory=list)


class ClosedLoopBatchComparisonReport(BaseModel):
    scenario_set_id: str
    dataset_path: str
    compared_modes: list[ClosedLoopBatchModeReport] = Field(default_factory=list)
    differing_final_state_user_ids: dict[str, list[str]] = Field(default_factory=dict)
    differing_final_policy_user_ids: dict[str, list[str]] = Field(default_factory=dict)
    differing_ranking_user_ids: dict[str, list[str]] = Field(default_factory=dict)
    differing_trace_user_ids: dict[str, list[str]] = Field(default_factory=dict)
    comparison_notes: dict[str, str] = Field(default_factory=dict)
    trace_samples: list[TraceSample] = Field(default_factory=list)


class _CandidateResolution(BaseModel):
    deterministic_top_candidate: str | None = None
    raw_learned_top_candidate: str | None = None
    selected_candidate: str | None = None
    predicted_effect_proxy: float
    predicted_effect_source: EffectSource
    ranking_source: RankingSource
    effect_guard_applied: bool = False
    effect_guard_reason: str | None = None


class _PolicyResolution(BaseModel):
    deterministic_action: SimulationPolicyAction
    raw_learned_policy_action: SimulationPolicyAction | None = None
    selected_policy_action: SimulationPolicyAction
    action_source: PolicyActionSource
    policy_effect_proxy_used: float
    policy_effect_proxy_override_applied: bool = False
    policy_guard_applied: bool = False
    policy_guard_reason: str | None = None


def simulate_closed_loop_scenario(
    *,
    dataset_path: str | Path,
    user_id: str,
    max_cycles: int = 5,
    model_artifact_path: str | Path | None = None,
    policy_model_artifact_path: str | Path | None = None,
    enable_learned_policy: bool = False,
    enable_learned_reranking: bool = False,
    enable_policy_effect_proxy_override: bool = True,
    mode_name: str | None = None,
) -> ClosedLoopSimulationReport:
    records_by_user = _load_records_by_user(dataset_path)
    scenario_records = records_by_user.get(user_id)
    if not scenario_records:
        raise ValueError(f"synthetic user not found: {user_id}")

    effect_artifact = _load_optional_effect_artifact(model_artifact_path)
    policy_artifact = _load_optional_policy_artifact(policy_model_artifact_path)
    trace: list[SimulationTraceStep] = []
    terminated_early = False
    selected_mode_name = mode_name or _mode_name(
        enable_learned_policy=enable_learned_policy,
        enable_learned_reranking=enable_learned_reranking,
    )

    for cycle_index, record in enumerate(scenario_records[:max_cycles]):
        response = recommend(record.request)
        candidate_resolution = _resolve_candidate_selection(
            record=record,
            response=response,
            artifact=effect_artifact,
            enable_learned_reranking=enable_learned_reranking,
        )
        policy_resolution = _resolve_policy_selection(
            record=record,
            response=response,
            predicted_effect_proxy=candidate_resolution.predicted_effect_proxy,
            predicted_effect_source=candidate_resolution.predicted_effect_source,
            artifact=policy_artifact,
            enable_learned_policy=enable_learned_policy,
            enable_policy_effect_proxy_override=enable_policy_effect_proxy_override,
        )
        state_before = "baseline_intake" if cycle_index == 0 else trace[-1].state_after
        state_after = _state_after_action(
            cycle_index=cycle_index,
            action=policy_resolution.selected_policy_action,
        )
        trace.append(
            SimulationTraceStep(
                cycle_index=cycle_index,
                day_index=record.day_index,
                state_before=state_before,
                state_after=state_after,
                request_id=record.request.request_id,
                engine_status=response.status,
                engine_next_action=response.next_action,
                deterministic_action=policy_resolution.deterministic_action,
                raw_learned_policy_action=policy_resolution.raw_learned_policy_action,
                selected_policy_action=policy_resolution.selected_policy_action,
                policy_guard_applied=policy_resolution.policy_guard_applied,
                policy_guard_reason=policy_resolution.policy_guard_reason,
                deterministic_top_candidate=candidate_resolution.deterministic_top_candidate,
                raw_learned_top_candidate=candidate_resolution.raw_learned_top_candidate,
                selected_candidate=candidate_resolution.selected_candidate,
                effect_guard_applied=candidate_resolution.effect_guard_applied,
                effect_guard_reason=candidate_resolution.effect_guard_reason,
                action_source=policy_resolution.action_source,
                ranking_source=candidate_resolution.ranking_source,
                reason_code=response.next_action_rationale.reason_code,
                recommendation_keys=[
                    item.ingredient_key for item in response.recommendations
                ],
                follow_up_window_days=response.follow_up_window_days,
                predicted_effect_proxy=candidate_resolution.predicted_effect_proxy,
                predicted_effect_source=candidate_resolution.predicted_effect_source,
                policy_effect_proxy_used=policy_resolution.policy_effect_proxy_used,
                policy_effect_proxy_override_applied=policy_resolution.policy_effect_proxy_override_applied,
                adherence_proxy=record.adherence_proxy,
                side_effect_proxy=record.side_effect_proxy,
                risk_tier=record.labels.risk_tier,
                adverse_event=record.labels.adverse_event,
            )
        )
        if state_after in TERMINAL_STATES:
            terminated_early = cycle_index < min(max_cycles, len(scenario_records)) - 1
            break

    final_step = trace[-1]
    return ClosedLoopSimulationReport(
        scenario_id=f"{SIMULATION_VERSION}-{user_id}",
        mode_name=selected_mode_name,
        user_id=user_id,
        cohort_version=scenario_records[0].cohort_version,
        dataset_path=str(Path(dataset_path)),
        user_rng_seed=scenario_records[0].rng_seed,
        model_artifact_path=(
            str(Path(model_artifact_path)) if model_artifact_path is not None else None
        ),
        model_loaded=effect_artifact is not None,
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
        final_policy_action=final_step.selected_policy_action,
        final_candidate=final_step.selected_candidate,
        terminated_early=terminated_early,
    )


def simulate_closed_loop_batch(
    *,
    dataset_path: str | Path,
    max_cycles: int = 5,
    max_users: int | None = None,
    model_artifact_path: str | Path | None = None,
    policy_model_artifact_path: str | Path | None = None,
    enable_learned_policy: bool = False,
    enable_learned_reranking: bool = False,
    enable_policy_effect_proxy_override: bool = True,
    mode_name: str,
) -> ClosedLoopBatchModeReport:
    records_by_user = _load_records_by_user(dataset_path)
    user_ids = sorted(records_by_user)
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
            enable_policy_effect_proxy_override=enable_policy_effect_proxy_override,
            mode_name=mode_name,
        )
        for user_id in user_ids
    ]
    total_trace_steps = sum(len(report.trace) for report in scenario_reports)
    trace_lengths = [len(report.trace) for report in scenario_reports]
    effect_values = [
        step.predicted_effect_proxy
        for report in scenario_reports
        for step in report.trace
    ]
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
        average_trace_length=round(sum(trace_lengths) / len(trace_lengths), 6)
        if trace_lengths
        else 0.0,
        terminated_early_count=sum(
            1 for report in scenario_reports if report.terminated_early
        ),
        adverse_event_count=sum(
            1
            for report in scenario_reports
            for step in report.trace
            if step.adverse_event
        ),
        average_predicted_effect_proxy=round(sum(effect_values) / len(effect_values), 6)
        if effect_values
        else 0.0,
        final_state_counts=dict(
            sorted(Counter(report.final_state for report in scenario_reports).items())
        ),
        final_policy_action_counts=dict(
            sorted(
                Counter(report.final_policy_action.value for report in scenario_reports).items()
            )
        ),
        action_source_counts=dict(
            sorted(
                Counter(
                    step.action_source.value
                    for report in scenario_reports
                    for step in report.trace
                ).items()
            )
        ),
        ranking_source_counts=dict(
            sorted(
                Counter(
                    step.ranking_source.value
                    for report in scenario_reports
                    for step in report.trace
                ).items()
            )
        ),
        engine_next_action_counts=dict(
            sorted(
                Counter(
                    step.engine_next_action.value
                    for report in scenario_reports
                    for step in report.trace
                ).items()
            )
        ),
        state_transition_counts=dict(
            sorted(
                Counter(
                    f"{step.state_before}->{step.state_after}"
                    for report in scenario_reports
                    for step in report.trace
                ).items()
            )
        ),
        policy_guard_applied_count=sum(
            1
            for report in scenario_reports
            for step in report.trace
            if step.policy_guard_applied
        ),
        effect_guard_applied_count=sum(
            1
            for report in scenario_reports
            for step in report.trace
            if step.effect_guard_applied
        ),
        policy_effect_override_applied_count=sum(
            1
            for report in scenario_reports
            for step in report.trace
            if step.policy_effect_proxy_override_applied
        ),
        raw_policy_disagreement_count=sum(
            1
            for report in scenario_reports
            for step in report.trace
            if step.raw_learned_policy_action is not None
            and step.raw_learned_policy_action != step.deterministic_action
        ),
        raw_ranking_disagreement_count=sum(
            1
            for report in scenario_reports
            for step in report.trace
            if step.raw_learned_top_candidate is not None
            and step.raw_learned_top_candidate != step.deterministic_top_candidate
        ),
    )


def compare_batch_simulation_modes(
    *,
    dataset_path: str | Path,
    max_cycles: int = 5,
    max_users: int | None = None,
    model_artifact_path: str | Path | None = None,
    policy_model_artifact_path: str | Path | None = None,
    enable_policy_effect_proxy_override: bool = True,
) -> ClosedLoopBatchComparisonReport:
    mode_reports = [
        simulate_closed_loop_batch(
            dataset_path=dataset_path,
            max_cycles=max_cycles,
            max_users=max_users,
            model_artifact_path=model_artifact_path,
            policy_model_artifact_path=policy_model_artifact_path,
            enable_learned_policy=False,
            enable_learned_reranking=False,
            enable_policy_effect_proxy_override=enable_policy_effect_proxy_override,
            mode_name="deterministic_only",
        ),
        simulate_closed_loop_batch(
            dataset_path=dataset_path,
            max_cycles=max_cycles,
            max_users=max_users,
            model_artifact_path=model_artifact_path,
            policy_model_artifact_path=policy_model_artifact_path,
            enable_learned_policy=False,
            enable_learned_reranking=True,
            enable_policy_effect_proxy_override=enable_policy_effect_proxy_override,
            mode_name="learned_effect_guarded",
        ),
        simulate_closed_loop_batch(
            dataset_path=dataset_path,
            max_cycles=max_cycles,
            max_users=max_users,
            model_artifact_path=model_artifact_path,
            policy_model_artifact_path=policy_model_artifact_path,
            enable_learned_policy=True,
            enable_learned_reranking=False,
            enable_policy_effect_proxy_override=enable_policy_effect_proxy_override,
            mode_name="learned_policy_guarded",
        ),
        simulate_closed_loop_batch(
            dataset_path=dataset_path,
            max_cycles=max_cycles,
            max_users=max_users,
            model_artifact_path=model_artifact_path,
            policy_model_artifact_path=policy_model_artifact_path,
            enable_learned_policy=True,
            enable_learned_reranking=True,
            enable_policy_effect_proxy_override=enable_policy_effect_proxy_override,
            mode_name="learned_effect_and_policy_guarded",
        ),
    ]
    baseline_report = mode_reports[0]
    baseline_by_user = {
        report.user_id: report for report in baseline_report.scenario_reports
    }
    baseline_records = {
        report.user_id: _load_baseline_record(dataset_path=dataset_path, user_id=report.user_id)
        for report in baseline_report.scenario_reports
    }

    differing_final_state_user_ids: dict[str, list[str]] = {}
    differing_final_policy_user_ids: dict[str, list[str]] = {}
    differing_ranking_user_ids: dict[str, list[str]] = {}
    differing_trace_user_ids: dict[str, list[str]] = {}
    comparison_notes: dict[str, str] = {}

    updated_reports: list[ClosedLoopBatchModeReport] = []
    for mode_report in mode_reports:
        if mode_report.mode_name == "deterministic_only":
            updated_reports.append(
                mode_report.model_copy(
                    update={
                        "deterministic_vs_learned_disagreement_count": 0,
                        "cohort_slice_metrics": _build_slice_summaries(
                            mode_report=mode_report,
                            baseline_by_user=baseline_by_user,
                            baseline_records=baseline_records,
                        ),
                    }
                )
            )
            continue

        final_state_diff: list[str] = []
        final_policy_diff: list[str] = []
        ranking_diff: list[str] = []
        trace_diff: list[str] = []
        step_disagreement_count = 0
        for scenario_report in mode_report.scenario_reports:
            baseline = baseline_by_user[scenario_report.user_id]
            if scenario_report.final_state != baseline.final_state:
                final_state_diff.append(scenario_report.user_id)
            if scenario_report.final_policy_action != baseline.final_policy_action:
                final_policy_diff.append(scenario_report.user_id)
            if _candidate_path_differs(scenario_report, baseline):
                ranking_diff.append(scenario_report.user_id)
            if _trace_signature(scenario_report) != _trace_signature(baseline):
                trace_diff.append(scenario_report.user_id)
            step_disagreement_count += _trace_step_disagreement_count(
                scenario_report, baseline
            )

        differing_final_state_user_ids[mode_report.mode_name] = final_state_diff
        differing_final_policy_user_ids[mode_report.mode_name] = final_policy_diff
        differing_ranking_user_ids[mode_report.mode_name] = ranking_diff
        differing_trace_user_ids[mode_report.mode_name] = trace_diff
        comparison_notes[mode_report.mode_name] = _build_comparison_note(
            mode_report=mode_report,
            differing_final_state_count=len(final_state_diff),
            differing_final_policy_count=len(final_policy_diff),
            differing_ranking_count=len(ranking_diff),
            differing_trace_count=len(trace_diff),
        )
        updated_reports.append(
            mode_report.model_copy(
                update={
                    "deterministic_vs_learned_disagreement_count": step_disagreement_count,
                    "cohort_slice_metrics": _build_slice_summaries(
                        mode_report=mode_report,
                        baseline_by_user=baseline_by_user,
                        baseline_records=baseline_records,
                    ),
                }
            )
        )

    return ClosedLoopBatchComparisonReport(
        scenario_set_id=SIMULATION_VERSION,
        dataset_path=str(Path(dataset_path)),
        compared_modes=updated_reports,
        differing_final_state_user_ids=differing_final_state_user_ids,
        differing_final_policy_user_ids=differing_final_policy_user_ids,
        differing_ranking_user_ids=differing_ranking_user_ids,
        differing_trace_user_ids=differing_trace_user_ids,
        comparison_notes=comparison_notes,
        trace_samples=_select_trace_samples(
            mode_reports=updated_reports,
            differing_trace_user_ids=differing_trace_user_ids,
        ),
    )


def render_simulation_markdown(report: ClosedLoopSimulationReport) -> str:
    lines = [
        "# closed loop simulation v1",
        "",
        f"- scenario_id: `{report.scenario_id}`",
        f"- mode_name: `{report.mode_name}`",
        f"- user_id: `{report.user_id}`",
        f"- cohort_version: `{report.cohort_version}`",
        f"- dataset_path: `{report.dataset_path}`",
        f"- model_loaded: `{report.model_loaded}`",
        f"- policy_model_loaded: `{report.policy_model_loaded}`",
        f"- learned_policy_enabled: `{report.learned_policy_enabled}`",
        f"- learned_reranking_enabled: `{report.learned_reranking_enabled}`",
        f"- final_state: `{report.final_state}`",
        f"- final_policy_action: `{report.final_policy_action.value}`",
        f"- final_candidate: `{report.final_candidate or '-'}`",
        "",
        "## Trace",
        "",
        (
            "| cycle | before | deterministic_action | raw_policy | selected_action | "
            "det_candidate | raw_candidate | selected_candidate | action_source | "
            "ranking_source | policy_guard | effect_guard | effect | policy_effect | state_after |"
        ),
        (
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
            "--- | --- | --- | --- |"
        ),
    ]
    for step in report.trace:
        lines.append(
            "| "
            f"{step.cycle_index} | "
            f"{step.state_before} | "
            f"{step.deterministic_action.value} | "
            f"{step.raw_learned_policy_action.value if step.raw_learned_policy_action else '-'} | "
            f"{step.selected_policy_action.value} | "
            f"{step.deterministic_top_candidate or '-'} | "
            f"{step.raw_learned_top_candidate or '-'} | "
            f"{step.selected_candidate or '-'} | "
            f"{step.action_source.value} | "
            f"{step.ranking_source.value} | "
            f"{'yes' if step.policy_guard_applied else 'no'} | "
            f"{'yes' if step.effect_guard_applied else 'no'} | "
            f"{step.predicted_effect_proxy} | "
            f"{step.policy_effect_proxy_used} | "
            f"{step.state_after} |"
        )
    return "\n".join(lines) + "\n"


def render_batch_simulation_markdown(report: ClosedLoopBatchComparisonReport) -> str:
    lines = [
        "# closed loop batch simulation v1 compare",
        "",
        f"- scenario_set_id: `{report.scenario_set_id}`",
        f"- dataset_path: `{report.dataset_path}`",
        "",
        "## Mode Differences",
        "",
        (
            "| mode | final_state_diff_users | final_policy_diff_users | "
            "ranking_diff_users | trace_diff_users |"
        ),
        "| --- | --- | --- | --- | --- |",
    ]
    for mode_name in (
        "learned_effect_guarded",
        "learned_policy_guarded",
        "learned_effect_and_policy_guarded",
    ):
        lines.append(
            "| "
            f"{mode_name} | "
            f"{len(report.differing_final_state_user_ids.get(mode_name, []))} | "
            f"{len(report.differing_final_policy_user_ids.get(mode_name, []))} | "
            f"{len(report.differing_ranking_user_ids.get(mode_name, []))} | "
            f"{len(report.differing_trace_user_ids.get(mode_name, []))} |"
        )
    for mode in report.compared_modes:
        lines.extend(
            [
                "",
                f"## {mode.mode_name}",
                "",
                f"- scenario_count: `{mode.scenario_count}`",
                f"- total_trace_steps: `{mode.total_trace_steps}`",
                f"- average_trace_length: `{mode.average_trace_length}`",
                f"- average_predicted_effect_proxy: `{mode.average_predicted_effect_proxy}`",
                f"- adverse_event_count: `{mode.adverse_event_count}`",
                f"- policy_guard_applied_count: `{mode.policy_guard_applied_count}`",
                f"- effect_guard_applied_count: `{mode.effect_guard_applied_count}`",
                (
                    "- policy_effect_override_applied_count: "
                    f"`{mode.policy_effect_override_applied_count}`"
                ),
                f"- raw_policy_disagreement_count: `{mode.raw_policy_disagreement_count}`",
                f"- raw_ranking_disagreement_count: `{mode.raw_ranking_disagreement_count}`",
                (
                    "- deterministic_vs_learned_disagreement_count: "
                    f"`{mode.deterministic_vs_learned_disagreement_count}`"
                ),
            ]
        )
        note = report.comparison_notes.get(mode.mode_name)
        if note:
            lines.append(f"- note: {note}")
        lines.extend(["", "### Final States"])
        for key, value in mode.final_state_counts.items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend(["", "### Final Actions"])
        for key, value in mode.final_policy_action_counts.items():
            lines.append(f"- `{key}`: `{value}`")
        lines.extend(["", "### Cohort Slices", ""])
        lines.append(
            
                "| slice | users | avg_trace_length | avg_effect | adverse_events | "
                "disagreement | policy_guard | effect_guard |"
            
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for slice_name, slice_summary in mode.cohort_slice_metrics.items():
            lines.append(
                "| "
                f"{slice_name} | "
                f"{slice_summary.user_count} | "
                f"{slice_summary.avg_trace_length} | "
                f"{slice_summary.avg_effect} | "
                f"{slice_summary.adverse_event_count} | "
                f"{slice_summary.deterministic_vs_learned_disagreement_count} | "
                f"{slice_summary.policy_guard_applied_count} | "
                f"{slice_summary.effect_guard_applied_count} |"
            )
    if report.trace_samples:
        lines.extend(["", "## Trace Samples"])
        for sample in report.trace_samples:
            lines.append(
                f"- `{sample.mode_name}` / `{sample.user_id}`: `{len(sample.trace)}` steps"
            )
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
    report_json_target.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    report_md_target.write_text(render_simulation_markdown(report), encoding="utf-8")


def write_batch_simulation_outputs(
    *,
    report: ClosedLoopBatchComparisonReport,
    report_json_path: str | Path,
    report_md_path: str | Path,
    trace_samples_json_path: str | Path | None = None,
) -> None:
    report_json_target = Path(report_json_path)
    report_md_target = Path(report_md_path)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    report_md_target.write_text(
        render_batch_simulation_markdown(report),
        encoding="utf-8",
    )
    if trace_samples_json_path is not None:
        trace_samples_target = Path(trace_samples_json_path)
        trace_samples_target.parent.mkdir(parents=True, exist_ok=True)
        trace_samples_target.write_text(
            "[\n"
            + ",\n".join(sample.model_dump_json(indent=2) for sample in report.trace_samples)
            + "\n]\n",
            encoding="utf-8",
        )


@lru_cache(maxsize=8)
def _load_records_by_user(
    dataset_path: str | Path,
) -> dict[str, list[RichSyntheticCohortRecord]]:
    records_by_user: dict[str, list[RichSyntheticCohortRecord]] = {}
    for line in Path(dataset_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = RichSyntheticCohortRecord.model_validate_json(line)
        records_by_user.setdefault(record.user_id, []).append(record)
    for user_id in records_by_user:
        records_by_user[user_id].sort(key=lambda item: item.trajectory_step)
    return records_by_user


def _load_baseline_record(
    *,
    dataset_path: str | Path,
    user_id: str,
) -> RichSyntheticCohortRecord:
    records = _load_records_by_user(dataset_path)
    if user_id not in records:
        raise ValueError(f"baseline synthetic record not found for {user_id}")
    return records[user_id][0]


def _load_optional_effect_artifact(
    path: str | Path | None,
) -> EffectModelV1Artifact | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return load_effect_model_v1_artifact(target)


def _load_optional_policy_artifact(
    path: str | Path | None,
) -> PolicyModelV1Artifact | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return load_policy_model_v1_artifact(target)


def _resolve_candidate_selection(
    *,
    record: RichSyntheticCohortRecord,
    response,
    artifact: EffectModelV1Artifact | None,
    enable_learned_reranking: bool,
) -> _CandidateResolution:
    recommendation_keys = [item.ingredient_key for item in response.recommendations]
    deterministic_top_candidate = recommendation_keys[0] if recommendation_keys else None
    default_resolution = _CandidateResolution(
        deterministic_top_candidate=deterministic_top_candidate,
        raw_learned_top_candidate=None,
        selected_candidate=deterministic_top_candidate,
        predicted_effect_proxy=record.expected_effect_proxy,
        predicted_effect_source=EffectSource.DETERMINISTIC_FALLBACK,
        ranking_source=RankingSource.DETERMINISTIC_RANKING,
    )
    if artifact is None or not enable_learned_reranking or not response.recommendations:
        return default_resolution

    eligible, reason = _can_apply_learned_effect_guard(record=record, response=response)
    near_tied_keys = _near_tied_candidate_keys(response=response)
    candidate_scores = _predict_candidate_effect_scores(
        artifact=artifact,
        record=record,
        response=response,
        candidate_keys=near_tied_keys if eligible else None,
    )
    raw_learned_top_candidate = _best_candidate_key(candidate_scores)
    if not eligible:
        return default_resolution.model_copy(
            update={
                "raw_learned_top_candidate": raw_learned_top_candidate,
                "effect_guard_applied": raw_learned_top_candidate
                not in {None, deterministic_top_candidate},
                "effect_guard_reason": reason,
            }
        )

    if raw_learned_top_candidate not in near_tied_keys:
        return default_resolution.model_copy(
            update={
                "raw_learned_top_candidate": raw_learned_top_candidate,
                "effect_guard_applied": raw_learned_top_candidate
                not in {None, deterministic_top_candidate},
                "effect_guard_reason": "candidate_outside_low_risk_near_tie_window",
            }
        )

    selected_candidate = raw_learned_top_candidate or deterministic_top_candidate
    selected_effect_proxy = candidate_scores.get(
        selected_candidate,
        record.expected_effect_proxy,
    )
    return _CandidateResolution(
        deterministic_top_candidate=deterministic_top_candidate,
        raw_learned_top_candidate=raw_learned_top_candidate,
        selected_candidate=selected_candidate,
        predicted_effect_proxy=selected_effect_proxy,
        predicted_effect_source=EffectSource.LEARNED_MODEL_V1,
        ranking_source=RankingSource.LEARNED_EFFECT_GUARDED,
        effect_guard_applied=False,
        effect_guard_reason=None,
    )


def _resolve_policy_selection(
    *,
    record: RichSyntheticCohortRecord,
    response,
    predicted_effect_proxy: float,
    predicted_effect_source: EffectSource,
    artifact: PolicyModelV1Artifact | None,
    enable_learned_policy: bool,
    enable_policy_effect_proxy_override: bool,
) -> _PolicyResolution:
    deterministic_action = _deterministic_policy_action(
        record=record,
        response=response,
        predicted_effect_proxy=predicted_effect_proxy,
    )
    default_resolution = _PolicyResolution(
        deterministic_action=deterministic_action,
        selected_policy_action=deterministic_action,
        action_source=PolicyActionSource.DETERMINISTIC_POLICY,
        policy_effect_proxy_used=record.expected_effect_proxy,
    )
    if artifact is None or not enable_learned_policy:
        return default_resolution

    policy_effect_proxy_used = record.expected_effect_proxy
    policy_effect_proxy_override_applied = False
    if (
        predicted_effect_source == EffectSource.LEARNED_MODEL_V1
        and enable_policy_effect_proxy_override
    ):
        policy_effect_proxy_used = predicted_effect_proxy
        policy_effect_proxy_override_applied = round(
            predicted_effect_proxy, 6
        ) != round(record.expected_effect_proxy, 6)
        raw_learned_policy_action = _predict_policy_action_with_effect_proxy_override(
            artifact=artifact,
            record=record,
            response=response,
            expected_effect_proxy=policy_effect_proxy_used,
        )
    else:
        raw_learned_policy_action = _simulation_action_from_next_action(
            predict_policy_action_v1(artifact, record)
        )
    policy_guard_reason = _policy_guard_reason(record=record, response=response)
    if policy_guard_reason is not None:
        return default_resolution.model_copy(
            update={
                "raw_learned_policy_action": raw_learned_policy_action,
                "action_source": PolicyActionSource.LEARNED_POLICY_GUARDED,
                "policy_effect_proxy_used": policy_effect_proxy_used,
                "policy_effect_proxy_override_applied": policy_effect_proxy_override_applied,
                "policy_guard_applied": raw_learned_policy_action != deterministic_action,
                "policy_guard_reason": policy_guard_reason,
            }
        )

    guarded_action = _simulation_action_from_next_action(
        apply_policy_guard(
            predicted_action=NextAction(raw_learned_policy_action.value),
            deterministic_action=NextAction(deterministic_action.value),
        )
    )
    return _PolicyResolution(
        deterministic_action=deterministic_action,
        raw_learned_policy_action=raw_learned_policy_action,
        selected_policy_action=guarded_action,
        action_source=PolicyActionSource.LEARNED_POLICY_GUARDED,
        policy_effect_proxy_used=policy_effect_proxy_used,
        policy_effect_proxy_override_applied=policy_effect_proxy_override_applied,
        policy_guard_applied=guarded_action != raw_learned_policy_action,
        policy_guard_reason=(
            "permissiveness_clamp" if guarded_action != raw_learned_policy_action else None
        ),
    )


def _predict_policy_action_with_effect_proxy_override(
    *,
    artifact: PolicyModelV1Artifact,
    record: RichSyntheticCohortRecord,
    response,
    expected_effect_proxy: float,
) -> SimulationPolicyAction:
    feature_row = build_policy_feature_dict_v1(record)
    feature_row["expected_effect_proxy"] = float(expected_effect_proxy)
    scores = predict_policy_scores_from_feature_dict_v1(artifact, feature_row)
    if _should_apply_effect_conditioned_policy_priors(record=record, response=response):
        _apply_effect_conditioned_policy_priors(
            scores=scores,
            record=record,
            predicted_effect_proxy=expected_effect_proxy,
        )
    selected_label = max(
        sorted(scores.items()),
        key=lambda item: item[1],
    )[0]
    return _simulation_action_from_next_action(NextAction(selected_label))


def _should_apply_effect_conditioned_policy_priors(
    *,
    record: RichSyntheticCohortRecord,
    response,
) -> bool:
    return (
        record.labels.risk_tier == "low"
        and response.status == RecommendationStatus.OK
    )


def _apply_effect_conditioned_policy_priors(
    *,
    scores: dict[str, float],
    record: RichSyntheticCohortRecord,
    predicted_effect_proxy: float,
) -> None:
    if predicted_effect_proxy < 0.14:
        scores[NextAction.RE_OPTIMIZE.value] = (
            scores.get(NextAction.RE_OPTIMIZE.value, 0.0)
            + RE_OPTIMIZE_EFFECT_PRIOR_BONUS
        )
        scores[NextAction.TRIGGER_SAFETY_RECHECK.value] = (
            scores.get(NextAction.TRIGGER_SAFETY_RECHECK.value, 0.0)
            - RE_OPTIMIZE_TRIGGER_PENALTY
        )
        return
    if predicted_effect_proxy < 0.24:
        scores[NextAction.MONITOR_ONLY.value] = (
            scores.get(NextAction.MONITOR_ONLY.value, 0.0)
            + MONITOR_ONLY_EFFECT_PRIOR_BONUS
        )
        if _should_apply_reoptimize_revival_prior(
            record=record,
            predicted_effect_proxy=predicted_effect_proxy,
        ):
            scores[NextAction.RE_OPTIMIZE.value] = (
                scores.get(NextAction.RE_OPTIMIZE.value, 0.0)
                + RE_OPTIMIZE_REVIVAL_BONUS
            )
            scores[NextAction.MONITOR_ONLY.value] = (
                scores.get(NextAction.MONITOR_ONLY.value, 0.0)
                - RE_OPTIMIZE_REVIVAL_MONITOR_PENALTY
            )
            scores[NextAction.CONTINUE_PLAN.value] = (
                scores.get(NextAction.CONTINUE_PLAN.value, 0.0)
                - RE_OPTIMIZE_REVIVAL_CONTINUE_PENALTY
            )
        scores[NextAction.TRIGGER_SAFETY_RECHECK.value] = (
            scores.get(NextAction.TRIGGER_SAFETY_RECHECK.value, 0.0)
            - MONITOR_ONLY_TRIGGER_PENALTY
        )
        return
    scores[NextAction.CONTINUE_PLAN.value] = (
        scores.get(NextAction.CONTINUE_PLAN.value, 0.0)
        + CONTINUE_PLAN_EFFECT_PRIOR_BONUS
    )
    scores[NextAction.TRIGGER_SAFETY_RECHECK.value] = (
        scores.get(NextAction.TRIGGER_SAFETY_RECHECK.value, 0.0)
        - CONTINUE_PLAN_TRIGGER_PENALTY
    )


def _should_apply_reoptimize_revival_prior(
    *,
    record: RichSyntheticCohortRecord,
    predicted_effect_proxy: float,
) -> bool:
    if record.trajectory_step <= 0:
        return False
    if predicted_effect_proxy < RE_OPTIMIZE_REVIVAL_PROXY_MIN:
        return False
    proxy_max = (
        RE_OPTIMIZE_CGM_REVIVAL_PROXY_MAX
        if record.request.input_availability.cgm
        else RE_OPTIMIZE_REVIVAL_PROXY_MAX
    )
    if predicted_effect_proxy > proxy_max:
        return False
    return record.request.input_availability.cgm or record.side_effect_proxy >= 0.12


def _predict_candidate_effect_scores(
    *,
    artifact: EffectModelV1Artifact,
    record: RichSyntheticCohortRecord,
    response,
    candidate_keys: set[str] | None = None,
) -> dict[str, float]:
    scores: dict[str, float] = {}
    for candidate in response.recommendations:
        if candidate_keys is not None and candidate.ingredient_key not in candidate_keys:
            continue
        transient_record = record.model_copy(
            update={
                "regimen": [
                    _candidate_regimen_item(record=record, candidate_key=candidate.ingredient_key)
                ],
                "baseline_recommendations": [candidate.ingredient_key],
            }
        )
        scores[candidate.ingredient_key] = round(
            predict_policy_effect_proxy_v1(artifact, transient_record),
            6,
        )
    return scores


def _candidate_regimen_item(
    *,
    record: RichSyntheticCohortRecord,
    candidate_key: str,
) -> RichRegimenItem:
    for regimen_item in record.regimen:
        if regimen_item.ingredient_key == candidate_key:
            return regimen_item
    base_dose, dose_unit, schedule = DOSE_TEMPLATES.get(
        candidate_key,
        (1.0, "serving", "morning"),
    )
    return RichRegimenItem(
        ingredient_key=candidate_key,
        display_name=candidate_key.replace("_", " ").title(),
        daily_dose=round(base_dose, 3),
        dose_unit=dose_unit,
        schedule=schedule,
        regimen_status="planned" if record.trajectory_step == 0 else "active",
    )


def _can_apply_learned_effect_guard(
    *,
    record: RichSyntheticCohortRecord,
    response,
) -> tuple[bool, str | None]:
    if response.status != RecommendationStatus.OK:
        return False, "non_ok_safety_status"
    if record.labels.risk_tier != "low":
        return False, "non_low_risk_user"
    if record.request.user_profile.pregnant:
        return False, "pregnancy_requires_deterministic_ranking"
    if record.request.medications:
        return False, "medication_risk_requires_deterministic_ranking"
    if record.request.conditions:
        return False, "condition_risk_requires_deterministic_ranking"
    if record.request.preferences.avoid_ingredients:
        return False, "explicit_avoid_requires_deterministic_ranking"
    if len(record.request.goals) > 2:
        return False, "goal_set_too_broad_for_low_risk_rerank"
    if len(response.recommendations) < 2:
        return False, "insufficient_candidates_for_rerank"
    return True, None


def _near_tied_candidate_keys(*, response) -> set[str]:
    if not response.recommendations:
        return set()
    top_total = max(candidate.score_breakdown.total for candidate in response.recommendations)
    return {
        candidate.ingredient_key
        for candidate in response.recommendations
        if top_total - candidate.score_breakdown.total <= LEARNED_EFFECT_NEAR_TIE_GAP
    }


def _best_candidate_key(scores: dict[str, float]) -> str | None:
    if not scores:
        return None
    return max(sorted(scores.items()), key=lambda item: item[1])[0]


def _deterministic_policy_action(
    *,
    record: RichSyntheticCohortRecord,
    response,
    predicted_effect_proxy: float,
) -> SimulationPolicyAction:
    if record.trajectory_step == 0:
        if response.next_action == NextAction.BLOCKED:
            return SimulationPolicyAction.BLOCKED
        if response.next_action == NextAction.COLLECT_MORE_INPUT:
            return SimulationPolicyAction.ASK_TARGETED_FOLLOWUP
        if response.next_action == NextAction.TRIGGER_SAFETY_RECHECK:
            return SimulationPolicyAction.TRIGGER_SAFETY_RECHECK
        return SimulationPolicyAction.START_PLAN

    if record.labels.adverse_event or record.side_effect_proxy >= 0.72:
        return SimulationPolicyAction.REDUCE_OR_STOP
    if response.status != RecommendationStatus.OK:
        return SimulationPolicyAction.TRIGGER_SAFETY_RECHECK
    if response.next_action in {
        NextAction.BLOCKED,
        NextAction.TRIGGER_SAFETY_RECHECK,
    }:
        return SimulationPolicyAction.TRIGGER_SAFETY_RECHECK
    if record.adherence_proxy < 0.65 and record.trajectory_step <= 2:
        return SimulationPolicyAction.ASK_TARGETED_FOLLOWUP
    if predicted_effect_proxy < 0.14:
        return SimulationPolicyAction.RE_OPTIMIZE
    if predicted_effect_proxy < 0.24:
        return SimulationPolicyAction.MONITOR_ONLY
    return SimulationPolicyAction.CONTINUE_PLAN


def _policy_guard_reason(
    *,
    record: RichSyntheticCohortRecord,
    response,
) -> str | None:
    if record.trajectory_step == 0:
        return "baseline_intake_kept_deterministic"
    if response.status != RecommendationStatus.OK:
        return "non_ok_safety_status"
    if record.request.user_profile.pregnant:
        return "pregnancy_requires_deterministic_policy"
    if record.request.medications:
        return "medication_risk_requires_deterministic_policy"
    if record.request.conditions:
        return "serious_condition_requires_deterministic_policy"
    if record.request.preferences.avoid_ingredients:
        return "explicit_avoid_requires_deterministic_policy"
    return None


def _simulation_action_from_next_action(action: NextAction) -> SimulationPolicyAction:
    mapped = {
        NextAction.BLOCKED: SimulationPolicyAction.BLOCKED,
        NextAction.START_PLAN: SimulationPolicyAction.START_PLAN,
        NextAction.CONTINUE_PLAN: SimulationPolicyAction.CONTINUE_PLAN,
        NextAction.RE_OPTIMIZE: SimulationPolicyAction.RE_OPTIMIZE,
        NextAction.REDUCE_OR_STOP: SimulationPolicyAction.REDUCE_OR_STOP,
        NextAction.MONITOR_ONLY: SimulationPolicyAction.MONITOR_ONLY,
        NextAction.ASK_TARGETED_FOLLOWUP: SimulationPolicyAction.ASK_TARGETED_FOLLOWUP,
        NextAction.TRIGGER_SAFETY_RECHECK: SimulationPolicyAction.TRIGGER_SAFETY_RECHECK,
        NextAction.COLLECT_MORE_INPUT: SimulationPolicyAction.ASK_TARGETED_FOLLOWUP,
    }
    return mapped[action]


def _state_after_action(
    *,
    cycle_index: int,
    action: SimulationPolicyAction,
) -> str:
    if action == SimulationPolicyAction.BLOCKED:
        return "blocked"
    if action == SimulationPolicyAction.START_PLAN:
        return "recommendation_ready"
    if action == SimulationPolicyAction.ASK_TARGETED_FOLLOWUP:
        return "baseline_questionnaire_due" if cycle_index == 0 else "re_evaluation"
    if action == SimulationPolicyAction.TRIGGER_SAFETY_RECHECK:
        return "safety_review"
    if action == SimulationPolicyAction.REDUCE_OR_STOP:
        return "stop_or_escalate"
    if action == SimulationPolicyAction.RE_OPTIMIZE:
        return "adjust_plan"
    if action == SimulationPolicyAction.MONITOR_ONLY:
        return "recommendation_ready" if cycle_index == 0 else "followup_due"
    if cycle_index == 1:
        return "intake_active"
    return "followup_due"


def _build_slice_summaries(
    *,
    mode_report: ClosedLoopBatchModeReport,
    baseline_by_user: dict[str, ClosedLoopSimulationReport],
    baseline_records: dict[str, RichSyntheticCohortRecord],
) -> dict[str, CohortSliceSummary]:
    slices: dict[str, CohortSliceSummary] = {}
    for slice_name, selector in REPLAY_SLICES.items():
        scenario_reports = [
            report
            for report in mode_report.scenario_reports
            if selector(baseline_records[report.user_id])
        ]
        effect_values = [
            step.predicted_effect_proxy
            for report in scenario_reports
            for step in report.trace
        ]
        slices[slice_name] = CohortSliceSummary(
            slice_name=slice_name,
            user_count=len(scenario_reports),
            avg_trace_length=round(
                sum(len(report.trace) for report in scenario_reports) / len(scenario_reports),
                6,
            )
            if scenario_reports
            else 0.0,
            final_state_distribution=dict(
                sorted(Counter(report.final_state for report in scenario_reports).items())
            ),
            final_action_distribution=dict(
                sorted(
                    Counter(
                        report.final_policy_action.value for report in scenario_reports
                    ).items()
                )
            ),
            avg_effect=round(sum(effect_values) / len(effect_values), 6)
            if effect_values
            else 0.0,
            adverse_event_count=sum(
                1
                for report in scenario_reports
                for step in report.trace
                if step.adverse_event
            ),
            deterministic_vs_learned_disagreement_count=sum(
                _trace_step_disagreement_count(report, baseline_by_user[report.user_id])
                for report in scenario_reports
            )
            if mode_report.mode_name != "deterministic_only"
            else 0,
            policy_guard_applied_count=sum(
                1
                for report in scenario_reports
                for step in report.trace
                if step.policy_guard_applied
            ),
            effect_guard_applied_count=sum(
                1
                for report in scenario_reports
                for step in report.trace
                if step.effect_guard_applied
            ),
        )
    return slices


def _trace_step_disagreement_count(
    report: ClosedLoopSimulationReport,
    baseline: ClosedLoopSimulationReport,
) -> int:
    disagreements = 0
    max_len = max(len(report.trace), len(baseline.trace))
    for index in range(max_len):
        if index >= len(report.trace) or index >= len(baseline.trace):
            disagreements += 1
            continue
        current = report.trace[index]
        deterministic = baseline.trace[index]
        if (
            current.selected_policy_action != deterministic.selected_policy_action
            or current.selected_candidate != deterministic.selected_candidate
            or current.state_after != deterministic.state_after
        ):
            disagreements += 1
    return disagreements


def _candidate_path_differs(
    report: ClosedLoopSimulationReport,
    baseline: ClosedLoopSimulationReport,
) -> bool:
    compared = False
    for current, deterministic in zip(report.trace, baseline.trace, strict=False):
        compared = True
        if current.selected_candidate != deterministic.selected_candidate:
            return True
    return False if compared else len(report.trace) != len(baseline.trace)


def _trace_signature(
    report: ClosedLoopSimulationReport,
) -> list[tuple[str, str | None, str, float]]:
    return [
        (
            step.selected_policy_action.value,
            step.selected_candidate,
            step.state_after,
            round(step.predicted_effect_proxy, 6),
        )
        for step in report.trace
    ]


def _build_comparison_note(
    *,
    mode_report: ClosedLoopBatchModeReport,
    differing_final_state_count: int,
    differing_final_policy_count: int,
    differing_ranking_count: int,
    differing_trace_count: int,
) -> str:
    if differing_trace_count == 0:
        reasons: list[str] = []
        if mode_report.raw_policy_disagreement_count == 0:
            reasons.append("policy model mostly reproduced the deterministic transition layer")
        if mode_report.raw_ranking_disagreement_count == 0:
            reasons.append(
                "effect model produced no candidate-order divergence on the "
                "low-risk near-tie subset"
            )
        if mode_report.policy_guard_applied_count > 0:
            reasons.append("policy guard clamped more-permissive raw actions")
        if mode_report.effect_guard_applied_count > 0:
            reasons.append("effect guard kept reranking inside the narrow low-risk subset")
        if not reasons:
            reasons.append(
                "synthetic policy/effect labels remain close to the deterministic generator"
            )
        return "; ".join(reasons)

    notes: list[str] = []
    if differing_ranking_count > 0:
        notes.append("learned effect changed candidate choice on a guarded low-risk subset")
    if differing_final_policy_count > 0:
        notes.append(
            "learned policy changed final action on some users without "
            "breaking the safety ceiling"
        )
    if differing_final_state_count > 0:
        notes.append("those action differences propagated to different terminal states")
    if not notes:
        notes.append(
            "trace-level effect differences appeared without changing final "
            "state or action"
        )
    return "; ".join(notes)


def _select_trace_samples(
    *,
    mode_reports: list[ClosedLoopBatchModeReport],
    differing_trace_user_ids: dict[str, list[str]],
) -> list[TraceSample]:
    samples: list[TraceSample] = []
    for mode_report in mode_reports:
        if mode_report.mode_name == "deterministic_only":
            continue
        candidate_user_ids = differing_trace_user_ids.get(mode_report.mode_name, [])
        if not candidate_user_ids:
            candidate_user_ids = [report.user_id for report in mode_report.scenario_reports[:1]]
        for user_id in candidate_user_ids[:1]:
            report = next(
                item for item in mode_report.scenario_reports if item.user_id == user_id
            )
            samples.append(
                TraceSample(
                    user_id=user_id,
                    mode_name=mode_report.mode_name,
                    trace=report.trace,
                )
            )
            if len(samples) >= TRACE_SAMPLE_LIMIT:
                return samples
    return samples


def _mode_name(
    *,
    enable_learned_policy: bool,
    enable_learned_reranking: bool,
) -> str:
    if enable_learned_policy and enable_learned_reranking:
        return "learned_effect_and_policy_guarded"
    if enable_learned_policy:
        return "learned_policy_guarded"
    if enable_learned_reranking:
        return "learned_effect_guarded"
    return "deterministic_only"
