import json
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.models import (
    build_policy_feature_dict_v1,
    load_policy_model_v1_artifact,
    predict_policy_scores_from_feature_dict_v1,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import NextAction, RecommendationStatus
from wellnessbox_rnd.simulation import compare_batch_simulation_modes
from wellnessbox_rnd.simulation.closed_loop_v0 import (
    CGM_THRESHOLD_EDGE_MONITOR_REFINEMENT_BONUS,
    CONTINUE_PLAN_EFFECT_PRIOR_BONUS,
    CONTINUE_PLAN_TRIGGER_PENALTY,
    MONITOR_ONLY_EFFECT_PRIOR_BONUS,
    MONITOR_ONLY_TRIGGER_PENALTY,
    RE_OPTIMIZE_EFFECT_PRIOR_BONUS,
    RE_OPTIMIZE_REVIVAL_BONUS,
    RE_OPTIMIZE_REVIVAL_CONTINUE_PENALTY,
    RE_OPTIMIZE_REVIVAL_MONITOR_PENALTY,
    RE_OPTIMIZE_TRIGGER_PENALTY,
    _load_records_by_user,
    _should_apply_cgm_threshold_edge_monitor_refinement,
    _should_apply_effect_conditioned_policy_priors,
    _should_apply_reoptimize_revival_prior,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Diagnose current patched combined replay cgm continue_plan cases and "
            "separate threshold-edge blockers from non-edge blockers"
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Rich synthetic longitudinal dataset path",
    )
    parser.add_argument("--max-cycles", type=int, default=5)
    parser.add_argument("--max-users", type=int, default=96)
    parser.add_argument(
        "--model-artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Replay-only effect artifact path",
    )
    parser.add_argument(
        "--policy-model-artifact",
        default="artifacts/models/policy_model_v1_uniform.json",
        help="Replay-only policy artifact path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/current_cgm_continue_plan_diagnostic_v1.json",
        help="Diagnostic report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/current_cgm_continue_plan_diagnostic_v1.md",
        help="Diagnostic report markdown output path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    comparison = compare_batch_simulation_modes(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
        enable_policy_effect_proxy_override=True,
        max_users=args.max_users,
    )
    combined = next(
        mode
        for mode in comparison.compared_modes
        if mode.mode_name == "learned_effect_and_policy_guarded"
    )
    records_by_user = _load_records_by_user(args.dataset)
    policy_artifact = load_policy_model_v1_artifact(args.policy_model_artifact)

    cases = []
    for scenario in combined.scenario_reports:
        user_records = records_by_user[scenario.user_id]
        if not user_records[0].request.input_availability.cgm:
            continue
        if scenario.final_policy_action.value != NextAction.CONTINUE_PLAN.value:
            continue
        cases.append(
            _build_case_diagnostic(
                scenario=scenario,
                user_records=user_records,
                policy_artifact=policy_artifact,
            )
        )

    threshold_edge_cases = [
        case
        for case in cases
        if case["final_threshold_edge_status"] == "monitor_band_still_continue"
    ]
    report = {
        "dataset_path": str(Path(args.dataset)),
        "model_artifact_path": args.model_artifact,
        "policy_model_artifact_path": args.policy_model_artifact,
        "current_cgm_final_action_distribution": combined.cohort_slice_metrics[
            "cgm_users"
        ].final_action_distribution,
        "current_cgm_disagreement_count": combined.cohort_slice_metrics[
            "cgm_users"
        ].deterministic_vs_learned_disagreement_count,
        "current_continue_plan_case_count": len(cases),
        "current_continue_plan_user_ids": [case["user_id"] for case in cases],
        "current_threshold_edge_continue_plan_case_count": len(threshold_edge_cases),
        "current_threshold_edge_continue_plan_user_ids": [
            case["user_id"] for case in threshold_edge_cases
        ],
        "non_threshold_edge_continue_plan_user_ids": [
            case["user_id"]
            for case in cases
            if case["final_threshold_edge_status"] != "monitor_band_still_continue"
        ],
        "blocker_summary": _build_blocker_summary(cases),
        "cases": cases,
    }

    report_json_target = Path(args.report_json)
    report_md_target = Path(args.report_md)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_json": str(report_json_target),
                "report_md": str(report_md_target),
                "current_continue_plan_case_count": report[
                    "current_continue_plan_case_count"
                ],
                "current_threshold_edge_continue_plan_user_ids": report[
                    "current_threshold_edge_continue_plan_user_ids"
                ],
                "blocker_summary": report["blocker_summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _build_case_diagnostic(*, scenario, user_records, policy_artifact) -> dict[str, object]:
    final_step = scenario.trace[-1]
    final_record = user_records[final_step.cycle_index]
    step_diagnostics = [
        _build_step_diagnostic(
            step=step,
            record=user_records[step.cycle_index],
            policy_artifact=policy_artifact,
        )
        for step in scenario.trace
    ]
    final_step_diagnostic = step_diagnostics[-1]
    return {
        "user_id": scenario.user_id,
        "record_id": final_record.record_id,
        "final_cycle_index": final_step.cycle_index,
        "final_day_index": final_step.day_index,
        "final_policy_action": final_step.selected_policy_action.value,
        "final_predicted_effect_proxy": round(final_step.predicted_effect_proxy, 6),
        "final_policy_effect_proxy_used": round(final_step.policy_effect_proxy_used, 6),
        "final_prior_band": final_step_diagnostic["gating_reason"]["current_prior_band"],
        "final_threshold_edge_status": _threshold_edge_status(
            step_diagnostic=final_step_diagnostic,
        ),
        "final_continue_minus_monitor_margin_after_priors": final_step_diagnostic[
            "margin_snapshot"
        ]["continue_minus_monitor_after_priors"],
        "final_distance_to_monitor_flip": final_step_diagnostic["margin_snapshot"][
            "distance_to_monitor_flip"
        ],
        "final_reoptimize_minus_continue_margin_after_priors": final_step_diagnostic[
            "margin_snapshot"
        ]["reoptimize_minus_continue_after_priors"],
        "deterministic_fallback_summary": final_step_diagnostic["deterministic_fallback"],
        "safety_ceiling_summary": final_step_diagnostic["safety_ceiling"],
        "step_diagnostics": step_diagnostics,
    }


def _build_step_diagnostic(*, step, record, policy_artifact) -> dict[str, object]:
    response = recommend(record.request)
    feature_row = build_policy_feature_dict_v1(record)
    feature_row["expected_effect_proxy"] = float(step.policy_effect_proxy_used)
    scores_before_priors = predict_policy_scores_from_feature_dict_v1(
        policy_artifact,
        feature_row,
    )
    staged = _apply_staged_effect_conditioned_priors(
        scores=scores_before_priors,
        record=record,
        response_status=response.status,
        predicted_effect_proxy=float(step.policy_effect_proxy_used),
    )

    return {
        "cycle_index": step.cycle_index,
        "day_index": step.day_index,
        "record_id": record.record_id,
        "decision_trace": {
            "state_before": step.state_before,
            "state_after": step.state_after,
            "engine_status": step.engine_status.value,
            "engine_next_action": step.engine_next_action.value,
            "reason_code": step.reason_code,
            "deterministic_action": step.deterministic_action.value,
            "raw_policy_action": (
                step.raw_learned_policy_action.value
                if step.raw_learned_policy_action is not None
                else None
            ),
            "selected_policy_action": step.selected_policy_action.value,
            "selected_candidate": step.selected_candidate,
            "predicted_effect_proxy": round(step.predicted_effect_proxy, 6),
            "policy_effect_proxy_used": round(step.policy_effect_proxy_used, 6),
        },
        "gating_reason": {
            "effect_conditioned_prior_eligible": staged["prior_gate_eligible"],
            "effect_conditioned_prior_gate_reason": staged["prior_gate_reason"],
            "current_prior_band": staged["prior_band"],
            "threshold_edge_refinement_eligible": staged[
                "threshold_edge_refinement_eligible"
            ],
            "reoptimize_revival_eligible": staged["reoptimize_revival_eligible"],
            "policy_guard_reason": step.policy_guard_reason,
            "effect_guard_reason": step.effect_guard_reason,
        },
        "prior_contribution": {
            "component_deltas": staged["component_deltas"],
            "total_delta": staged["total_delta"],
        },
        "policy_score_snapshots": {
            "before_priors": _round_scores(scores_before_priors),
            "after_priors": _round_scores(staged["scores_after_priors"]),
            "top_action_before_priors": _top_action_label(scores_before_priors),
            "top_action_after_priors": _top_action_label(staged["scores_after_priors"]),
        },
        "margin_snapshot": {
            "continue_minus_monitor_after_priors": round(
                staged["scores_after_priors"].get(NextAction.CONTINUE_PLAN.value, 0.0)
                - staged["scores_after_priors"].get(NextAction.MONITOR_ONLY.value, 0.0),
                6,
            ),
            "distance_to_monitor_flip": round(
                max(
                    0.0,
                    staged["scores_after_priors"].get(NextAction.CONTINUE_PLAN.value, 0.0)
                    - staged["scores_after_priors"].get(NextAction.MONITOR_ONLY.value, 0.0),
                ),
                6,
            ),
            "reoptimize_minus_continue_after_priors": round(
                staged["scores_after_priors"].get(NextAction.RE_OPTIMIZE.value, 0.0)
                - staged["scores_after_priors"].get(NextAction.CONTINUE_PLAN.value, 0.0),
                6,
            ),
        },
        "deterministic_fallback": {
            "effect_fallback_active": step.predicted_effect_source.value
            == "deterministic_fallback",
            "effect_source": step.predicted_effect_source.value,
            "policy_fallback_active": step.raw_learned_policy_action is None,
            "action_source": step.action_source.value,
        },
        "safety_ceiling": {
            "active": step.policy_guard_reason is not None,
            "applied": step.policy_guard_applied,
            "reason": step.policy_guard_reason,
        },
        "record_snapshot": {
            "trajectory_step": record.trajectory_step,
            "risk_tier": record.labels.risk_tier,
            "expected_effect_proxy": round(record.expected_effect_proxy, 6),
            "adherence_proxy": round(record.adherence_proxy, 6),
            "side_effect_proxy": round(record.side_effect_proxy, 6),
        },
    }


def _apply_staged_effect_conditioned_priors(
    *,
    scores: dict[str, float],
    record,
    response_status: RecommendationStatus,
    predicted_effect_proxy: float,
) -> dict[str, object]:
    prior_gate_eligible = _should_apply_effect_conditioned_policy_priors(
        record=record,
        response=_ResponseStatusOnly(status=response_status),
    )
    prior_gate_reason = _effect_conditioned_prior_gate_reason(
        record=record,
        response_status=response_status,
    )
    prior_band = _prior_band_name(record=record, predicted_effect_proxy=predicted_effect_proxy)
    scores_after_priors = deepcopy(scores)
    component_deltas: dict[str, dict[str, float]] = {}
    threshold_edge_refinement_eligible = False
    reoptimize_revival_eligible = False

    if not prior_gate_eligible:
        return {
            "prior_gate_eligible": prior_gate_eligible,
            "prior_gate_reason": prior_gate_reason,
            "prior_band": prior_band,
            "threshold_edge_refinement_eligible": threshold_edge_refinement_eligible,
            "reoptimize_revival_eligible": reoptimize_revival_eligible,
            "scores_after_priors": scores_after_priors,
            "component_deltas": component_deltas,
            "total_delta": {},
        }

    if predicted_effect_proxy < 0.14:
        _apply_component_delta(
            component_deltas,
            component_name="reoptimize_effect_prior",
            action=NextAction.RE_OPTIMIZE.value,
            delta=RE_OPTIMIZE_EFFECT_PRIOR_BONUS,
            scores=scores_after_priors,
        )
        _apply_component_delta(
            component_deltas,
            component_name="reoptimize_trigger_penalty",
            action=NextAction.TRIGGER_SAFETY_RECHECK.value,
            delta=-RE_OPTIMIZE_TRIGGER_PENALTY,
            scores=scores_after_priors,
        )
    elif predicted_effect_proxy < (0.37 if record.request.input_availability.cgm else 0.24):
        _apply_component_delta(
            component_deltas,
            component_name="monitor_only_effect_prior",
            action=NextAction.MONITOR_ONLY.value,
            delta=MONITOR_ONLY_EFFECT_PRIOR_BONUS,
            scores=scores_after_priors,
        )
        threshold_edge_refinement_eligible = _should_apply_cgm_threshold_edge_monitor_refinement(
            scores=scores_after_priors,
            record=record,
        )
        if threshold_edge_refinement_eligible:
            _apply_component_delta(
                component_deltas,
                component_name="cgm_threshold_edge_monitor_refinement",
                action=NextAction.MONITOR_ONLY.value,
                delta=CGM_THRESHOLD_EDGE_MONITOR_REFINEMENT_BONUS,
                scores=scores_after_priors,
            )
        reoptimize_revival_eligible = _should_apply_reoptimize_revival_prior(
            record=record,
            predicted_effect_proxy=predicted_effect_proxy,
        )
        if reoptimize_revival_eligible:
            _apply_component_delta(
                component_deltas,
                component_name="reoptimize_revival_bonus",
                action=NextAction.RE_OPTIMIZE.value,
                delta=RE_OPTIMIZE_REVIVAL_BONUS,
                scores=scores_after_priors,
            )
            _apply_component_delta(
                component_deltas,
                component_name="reoptimize_revival_monitor_penalty",
                action=NextAction.MONITOR_ONLY.value,
                delta=-RE_OPTIMIZE_REVIVAL_MONITOR_PENALTY,
                scores=scores_after_priors,
            )
            _apply_component_delta(
                component_deltas,
                component_name="reoptimize_revival_continue_penalty",
                action=NextAction.CONTINUE_PLAN.value,
                delta=-RE_OPTIMIZE_REVIVAL_CONTINUE_PENALTY,
                scores=scores_after_priors,
            )
        _apply_component_delta(
            component_deltas,
            component_name="monitor_only_trigger_penalty",
            action=NextAction.TRIGGER_SAFETY_RECHECK.value,
            delta=-MONITOR_ONLY_TRIGGER_PENALTY,
            scores=scores_after_priors,
        )
    else:
        _apply_component_delta(
            component_deltas,
            component_name="continue_plan_effect_prior",
            action=NextAction.CONTINUE_PLAN.value,
            delta=CONTINUE_PLAN_EFFECT_PRIOR_BONUS,
            scores=scores_after_priors,
        )
        _apply_component_delta(
            component_deltas,
            component_name="continue_plan_trigger_penalty",
            action=NextAction.TRIGGER_SAFETY_RECHECK.value,
            delta=-CONTINUE_PLAN_TRIGGER_PENALTY,
            scores=scores_after_priors,
        )

    total_delta = {
        label: round(scores_after_priors.get(label, 0.0) - scores.get(label, 0.0), 6)
        for label in sorted(set(scores) | set(scores_after_priors))
        if round(scores_after_priors.get(label, 0.0) - scores.get(label, 0.0), 6) != 0.0
    }
    return {
        "prior_gate_eligible": prior_gate_eligible,
        "prior_gate_reason": prior_gate_reason,
        "prior_band": prior_band,
        "threshold_edge_refinement_eligible": threshold_edge_refinement_eligible,
        "reoptimize_revival_eligible": reoptimize_revival_eligible,
        "scores_after_priors": scores_after_priors,
        "component_deltas": component_deltas,
        "total_delta": total_delta,
    }


def _apply_component_delta(
    component_deltas: dict[str, dict[str, float]],
    *,
    component_name: str,
    action: str,
    delta: float,
    scores: dict[str, float],
) -> None:
    scores[action] = scores.get(action, 0.0) + delta
    component_deltas.setdefault(component_name, {})
    component_deltas[component_name][action] = round(
        component_deltas[component_name].get(action, 0.0) + delta,
        6,
    )


def _threshold_edge_status(*, step_diagnostic: dict[str, object]) -> str:
    prior_band = step_diagnostic["gating_reason"]["current_prior_band"]
    if prior_band == "monitor_only_band":
        return "monitor_band_still_continue"
    return "outside_monitor_band"


def _build_blocker_summary(cases: list[dict[str, object]]) -> dict[str, int]:
    return {
        "monitor_band_still_continue_count": sum(
            1
            for case in cases
            if case["final_threshold_edge_status"] == "monitor_band_still_continue"
        ),
        "outside_monitor_band_count": sum(
            1 for case in cases if case["final_threshold_edge_status"] == "outside_monitor_band"
        ),
        "final_safety_ceiling_active_count": sum(
            1 for case in cases if case["safety_ceiling_summary"]["active"]
        ),
        "final_effect_fallback_active_count": sum(
            1
            for case in cases
            if case["deterministic_fallback_summary"]["effect_fallback_active"]
        ),
        "final_policy_fallback_active_count": sum(
            1
            for case in cases
            if case["deterministic_fallback_summary"]["policy_fallback_active"]
        ),
        "final_distance_to_monitor_flip_le_0_05_count": sum(
            1
            for case in cases
            if case["final_distance_to_monitor_flip"] <= 0.05
        ),
        "final_distance_to_monitor_flip_gt_0_30_count": sum(
            1
            for case in cases
            if case["final_distance_to_monitor_flip"] > 0.30
        ),
        "final_reoptimize_minus_continue_ge_0_count": sum(
            1
            for case in cases
            if case["final_reoptimize_minus_continue_margin_after_priors"] >= 0.0
        ),
    }


def _effect_conditioned_prior_gate_reason(*, record, response_status: RecommendationStatus) -> str:
    if record.labels.risk_tier != "low":
        return "non_low_risk_user"
    if response_status != RecommendationStatus.OK:
        return "non_ok_safety_status"
    return "eligible"


def _prior_band_name(*, record, predicted_effect_proxy: float) -> str:
    if predicted_effect_proxy < 0.14:
        return "re_optimize_band"
    if predicted_effect_proxy < (0.37 if record.request.input_availability.cgm else 0.24):
        return "monitor_only_band"
    return "continue_plan_band"


def _top_action_label(scores: dict[str, float]) -> str:
    return max(sorted(scores.items()), key=lambda item: item[1])[0]


def _round_scores(scores: dict[str, float]) -> dict[str, float]:
    return {label: round(scores[label], 6) for label in sorted(scores)}


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# current cgm continue_plan diagnostic v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- model_artifact_path: `{report['model_artifact_path']}`",
        (
            "- policy_model_artifact_path: "
            f"`{report['policy_model_artifact_path']}`"
        ),
        (
            "- current_cgm_final_action_distribution: "
            f"`{report['current_cgm_final_action_distribution']}`"
        ),
        f"- current_continue_plan_case_count: `{report['current_continue_plan_case_count']}`",
        (
            "- current_threshold_edge_continue_plan_user_ids: "
            f"`{report['current_threshold_edge_continue_plan_user_ids']}`"
        ),
        (
            "- non_threshold_edge_continue_plan_user_ids: "
            f"`{report['non_threshold_edge_continue_plan_user_ids']}`"
        ),
        f"- blocker_summary: `{report['blocker_summary']}`",
    ]
    for case in report["cases"]:
        lines.extend(
            [
                "",
                f"## {case['user_id']}",
                f"- record_id: `{case['record_id']}`",
                f"- final_policy_action: `{case['final_policy_action']}`",
                f"- final_prior_band: `{case['final_prior_band']}`",
                f"- final_threshold_edge_status: `{case['final_threshold_edge_status']}`",
                (
                    "- final_continue_minus_monitor_margin_after_priors: "
                    f"`{case['final_continue_minus_monitor_margin_after_priors']}`"
                ),
                f"- final_distance_to_monitor_flip: `{case['final_distance_to_monitor_flip']}`",
                (
                    "- final_reoptimize_minus_continue_margin_after_priors: "
                    f"`{case['final_reoptimize_minus_continue_margin_after_priors']}`"
                ),
                (
                    "- deterministic_fallback_summary: "
                    f"`{case['deterministic_fallback_summary']}`"
                ),
                f"- safety_ceiling_summary: `{case['safety_ceiling_summary']}`",
            ]
        )
        for step in case["step_diagnostics"]:
            lines.append(
                f"- cycle `{step['cycle_index']}` / record `{step['record_id']}`: "
                f"selected=`{step['decision_trace']['selected_policy_action']}`, "
                f"prior_band=`{step['gating_reason']['current_prior_band']}`, "
                f"prior_delta=`{step['prior_contribution']['total_delta']}`, "
                f"fallback=`{step['deterministic_fallback']}`, "
                f"safety_ceiling=`{step['safety_ceiling']}`"
            )
    return "\n".join(lines) + "\n"


class _ResponseStatusOnly:
    def __init__(self, *, status: RecommendationStatus) -> None:
        self.status = status


if __name__ == "__main__":
    sys_exit(main())
