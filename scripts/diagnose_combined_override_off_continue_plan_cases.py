import json
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.models import (
    build_policy_feature_dict_v1,
    load_policy_model_v1_artifact,
    predict_policy_scores_from_feature_dict_v1,
    predict_policy_scores_v1,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.policy import apply_policy_guard
from wellnessbox_rnd.schemas.recommendation import NextAction, RecommendationStatus
from wellnessbox_rnd.simulation import compare_batch_simulation_modes
from wellnessbox_rnd.simulation.closed_loop_v0 import (
    _apply_effect_conditioned_policy_priors,
    _load_records_by_user,
    _should_apply_effect_conditioned_policy_priors,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Diagnose combined replay cases that still end in continue_plan when "
            "policy effect override is disabled"
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
        default="artifacts/reports/combined_override_off_continue_plan_diagnostic_v1.json",
        help="Diagnostic report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/combined_override_off_continue_plan_diagnostic_v1.md",
        help="Diagnostic report markdown output path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    override_on_report = compare_batch_simulation_modes(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
        enable_policy_effect_proxy_override=True,
    )
    override_off_report = compare_batch_simulation_modes(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
        enable_policy_effect_proxy_override=False,
    )
    override_on = _extract_combined_mode(override_on_report)
    override_off = _extract_combined_mode(override_off_report)
    override_on_by_user = {
        scenario.user_id: scenario for scenario in override_on.scenario_reports
    }
    records_by_user = _load_records_by_user(args.dataset)
    policy_artifact = load_policy_model_v1_artifact(args.policy_model_artifact)

    cases = [
        _build_case_diagnostic(
            override_off_scenario=scenario,
            override_on_scenario=override_on_by_user[scenario.user_id],
            records_by_user=records_by_user,
            policy_artifact=policy_artifact,
        )
        for scenario in override_off.scenario_reports
        if records_by_user[scenario.user_id][0].request.input_availability.cgm
        and scenario.final_policy_action.value == NextAction.CONTINUE_PLAN.value
    ]

    report = {
        "dataset_path": str(Path(args.dataset)),
        "model_artifact_path": args.model_artifact,
        "policy_model_artifact_path": args.policy_model_artifact,
        "continue_plan_case_count": len(cases),
        "continue_plan_user_ids": [case["user_id"] for case in cases],
        "override_off_cgm_final_action_distribution": override_off.cohort_slice_metrics[
            "cgm_users"
        ].final_action_distribution,
        "override_on_cgm_final_action_distribution": override_on.cohort_slice_metrics[
            "cgm_users"
        ].final_action_distribution,
        "override_off_cgm_disagreement_count": override_off.cohort_slice_metrics[
            "cgm_users"
        ].deterministic_vs_learned_disagreement_count,
        "override_on_cgm_disagreement_count": override_on.cohort_slice_metrics[
            "cgm_users"
        ].deterministic_vs_learned_disagreement_count,
        "final_action_transition_counts": _count_transitions(cases),
        "flipped_to_monitor_only_user_ids": [
            case["user_id"]
            for case in cases
            if case["override_on_reference"]["final_policy_action"] == "monitor_only"
        ],
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
                "continue_plan_case_count": report["continue_plan_case_count"],
                "final_action_transition_counts": report["final_action_transition_counts"],
                "flipped_to_monitor_only_user_ids": report[
                    "flipped_to_monitor_only_user_ids"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _build_case_diagnostic(
    *,
    override_off_scenario,
    override_on_scenario,
    records_by_user,
    policy_artifact,
) -> dict[str, object]:
    final_step = override_off_scenario.trace[-1]
    final_record = records_by_user[override_off_scenario.user_id][final_step.cycle_index]
    step_diagnostics = [
        _build_step_diagnostic(
            override_off_step=off_step,
            override_on_step=on_step,
            record=records_by_user[override_off_scenario.user_id][off_step.cycle_index],
            policy_artifact=policy_artifact,
        )
        for off_step, on_step in zip(
            override_off_scenario.trace,
            override_on_scenario.trace,
            strict=True,
        )
    ]
    return {
        "user_id": override_off_scenario.user_id,
        "record_id": final_record.record_id,
        "final_cycle_index": final_step.cycle_index,
        "final_day_index": final_step.day_index,
        "override_off_final_policy_action": final_step.selected_policy_action.value,
        "override_off_final_predicted_effect_proxy": round(
            final_step.predicted_effect_proxy,
            6,
        ),
        "override_off_final_policy_effect_proxy_used": round(
            final_step.policy_effect_proxy_used,
            6,
        ),
        "override_on_reference": {
            "final_policy_action": override_on_scenario.final_policy_action.value,
            "final_state": override_on_scenario.final_state,
        },
        "step_diagnostics": step_diagnostics,
    }


def _build_step_diagnostic(
    *,
    override_off_step,
    override_on_step,
    record,
    policy_artifact,
) -> dict[str, object]:
    response = recommend(record.request)
    actual_scores = predict_policy_scores_v1(policy_artifact, record)
    override_feature_row = build_policy_feature_dict_v1(record)
    override_feature_row["expected_effect_proxy"] = float(
        override_on_step.policy_effect_proxy_used
    )
    override_scores_before_prior = predict_policy_scores_from_feature_dict_v1(
        policy_artifact,
        override_feature_row,
    )
    override_scores_after_prior = deepcopy(override_scores_before_prior)
    prior_gate_eligible = _should_apply_effect_conditioned_policy_priors(
        record=record,
        response=response,
    )
    if prior_gate_eligible:
        _apply_effect_conditioned_policy_priors(
            scores=override_scores_after_prior,
            record=record,
            predicted_effect_proxy=override_on_step.policy_effect_proxy_used,
        )

    counterfactual_raw_after_prior = _top_action_label(override_scores_after_prior)
    counterfactual_guarded_after_prior = _guarded_action_label(
        predicted_action=counterfactual_raw_after_prior,
        deterministic_action=override_off_step.deterministic_action.value,
        policy_guard_reason=override_off_step.policy_guard_reason,
    )
    actual_top_action = _top_action_label(actual_scores)

    return {
        "cycle_index": override_off_step.cycle_index,
        "day_index": override_off_step.day_index,
        "record_id": record.record_id,
        "decision_trace": {
            "override_off": {
                "state_before": override_off_step.state_before,
                "state_after": override_off_step.state_after,
                "engine_status": override_off_step.engine_status.value,
                "engine_next_action": override_off_step.engine_next_action.value,
                "reason_code": override_off_step.reason_code,
                "deterministic_action": override_off_step.deterministic_action.value,
                "raw_policy_action": (
                    override_off_step.raw_learned_policy_action.value
                    if override_off_step.raw_learned_policy_action is not None
                    else None
                ),
                "selected_policy_action": override_off_step.selected_policy_action.value,
                "selected_candidate": override_off_step.selected_candidate,
                "predicted_effect_proxy": round(
                    override_off_step.predicted_effect_proxy,
                    6,
                ),
                "policy_effect_proxy_used": round(
                    override_off_step.policy_effect_proxy_used,
                    6,
                ),
            },
            "override_on_reference": {
                "raw_policy_action": (
                    override_on_step.raw_learned_policy_action.value
                    if override_on_step.raw_learned_policy_action is not None
                    else None
                ),
                "selected_policy_action": override_on_step.selected_policy_action.value,
                "predicted_effect_proxy": round(
                    override_on_step.predicted_effect_proxy,
                    6,
                ),
                "policy_effect_proxy_used": round(
                    override_on_step.policy_effect_proxy_used,
                    6,
                ),
            },
        },
        "gating_reason": {
            "effect_guard_reason": override_off_step.effect_guard_reason,
            "policy_guard_reason": override_off_step.policy_guard_reason,
            "override_off_policy_path_reason": "policy_effect_override_disabled",
            "effect_conditioned_prior_eligibility": prior_gate_eligible,
            "effect_conditioned_prior_gate_reason": _effect_conditioned_prior_gate_reason(
                record=record,
                response=response,
            ),
            "counterfactual_prior_band": _prior_band_name(
                record=record,
                predicted_effect_proxy=override_on_step.policy_effect_proxy_used,
            ),
        },
        "prior_contribution": {
            "override_off_actual": {},
            "override_on_counterfactual": _score_delta(
                before=override_scores_before_prior,
                after=override_scores_after_prior,
            ),
        },
        "policy_score_snapshots": {
            "override_off_actual": _round_scores(actual_scores),
            "override_off_actual_top_action": actual_top_action,
            "override_on_counterfactual_before_prior": _round_scores(
                override_scores_before_prior
            ),
            "override_on_counterfactual_after_prior": _round_scores(
                override_scores_after_prior
            ),
            "override_on_counterfactual_top_action_before_prior": _top_action_label(
                override_scores_before_prior
            ),
            "override_on_counterfactual_top_action_after_prior": counterfactual_raw_after_prior,
        },
        "safety_ceiling": {
            "override_off_active": override_off_step.policy_guard_reason is not None,
            "override_off_applied": override_off_step.policy_guard_applied,
            "override_off_reason": override_off_step.policy_guard_reason,
            "override_on_counterfactual_active": override_off_step.policy_guard_reason
            is not None,
            "override_on_counterfactual_guarded_action": counterfactual_guarded_after_prior,
            "override_on_counterfactual_applied": (
                counterfactual_guarded_after_prior != counterfactual_raw_after_prior
            ),
            "override_on_counterfactual_reason": override_off_step.policy_guard_reason,
        },
        "record_snapshot": {
            "trajectory_step": record.trajectory_step,
            "risk_tier": record.labels.risk_tier,
            "expected_effect_proxy": round(record.expected_effect_proxy, 6),
            "adherence_proxy": round(record.adherence_proxy, 6),
            "side_effect_proxy": round(record.side_effect_proxy, 6),
        },
    }


def _extract_combined_mode(report):
    return next(
        mode
        for mode in report.compared_modes
        if mode.mode_name == "learned_effect_and_policy_guarded"
    )


def _effect_conditioned_prior_gate_reason(*, record, response) -> str:
    if record.labels.risk_tier != "low":
        return "non_low_risk_user"
    if response.status != RecommendationStatus.OK:
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


def _guarded_action_label(
    *,
    predicted_action: str,
    deterministic_action: str,
    policy_guard_reason: str | None,
) -> str:
    if policy_guard_reason is not None:
        return deterministic_action
    return apply_policy_guard(
        predicted_action=NextAction(predicted_action),
        deterministic_action=NextAction(deterministic_action),
    ).value


def _round_scores(scores: dict[str, float]) -> dict[str, float]:
    return {
        label: round(scores[label], 6)
        for label in sorted(scores)
    }


def _score_delta(
    *,
    before: dict[str, float],
    after: dict[str, float],
) -> dict[str, float]:
    labels = sorted(set(before) | set(after))
    return {
        label: round(after.get(label, 0.0) - before.get(label, 0.0), 6)
        for label in labels
        if round(after.get(label, 0.0) - before.get(label, 0.0), 6) != 0.0
    }


def _count_transitions(cases: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        transition = (
            f"{case['override_off_final_policy_action']}"
            f"->{case['override_on_reference']['final_policy_action']}"
        )
        counts[transition] = counts.get(transition, 0) + 1
    return dict(sorted(counts.items()))


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# combined override-off continue_plan diagnostic v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- model_artifact_path: `{report['model_artifact_path']}`",
        f"- policy_model_artifact_path: `{report['policy_model_artifact_path']}`",
        f"- continue_plan_case_count: `{report['continue_plan_case_count']}`",
        (
            "- override_off_cgm_final_action_distribution: "
            f"`{report['override_off_cgm_final_action_distribution']}`"
        ),
        (
            "- override_on_cgm_final_action_distribution: "
            f"`{report['override_on_cgm_final_action_distribution']}`"
        ),
        (
            "- final_action_transition_counts: "
            f"`{report['final_action_transition_counts']}`"
        ),
        (
            "- flipped_to_monitor_only_user_ids: "
            f"`{report['flipped_to_monitor_only_user_ids']}`"
        ),
    ]
    for case in report["cases"]:
        lines.extend(
            [
                "",
                f"## {case['user_id']}",
                f"- record_id: `{case['record_id']}`",
                (
                    "- final_action: "
                    f"`{case['override_off_final_policy_action']}`"
                ),
                (
                    "- override_on_reference_final_action: "
                    f"`{case['override_on_reference']['final_policy_action']}`"
                ),
            ]
        )
        for step in case["step_diagnostics"]:
            off_action = step["decision_trace"]["override_off"]["selected_policy_action"]
            on_action = step["decision_trace"]["override_on_reference"][
                "selected_policy_action"
            ]
            prior_band = step["gating_reason"]["counterfactual_prior_band"]
            prior_delta = step["prior_contribution"]["override_on_counterfactual"]
            safety_reason = step["safety_ceiling"]["override_off_reason"]
            lines.extend(
                [
                    (
                        f"- cycle `{step['cycle_index']}` / record `{step['record_id']}`: "
                        f"off=`{off_action}`, "
                        f"on=`{on_action}`, "
                        f"prior_band=`{prior_band}`, "
                        f"prior_delta=`{prior_delta}`, "
                        f"safety_ceiling=`{safety_reason}`"
                    )
                ]
            )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
