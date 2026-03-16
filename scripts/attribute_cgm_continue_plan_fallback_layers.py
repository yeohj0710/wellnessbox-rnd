import json
from argparse import ArgumentParser
from collections import Counter
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
from wellnessbox_rnd.schemas.recommendation import NextAction
from wellnessbox_rnd.simulation import simulate_closed_loop_batch
from wellnessbox_rnd.simulation.closed_loop_v0 import (
    EffectSource,
    _apply_effect_conditioned_policy_priors,
    _load_records_by_user,
    _should_apply_effect_conditioned_policy_priors,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Attribute final cgm continue_plan outcomes between neutralized policy, "
            "override-only proxy substitution, and override-plus-priors stages"
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
        default="artifacts/reports/cgm_continue_plan_fallback_attribution_v1.json",
        help="Attribution report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/cgm_continue_plan_fallback_attribution_v1.md",
        help="Attribution report markdown output path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    records_by_user = _load_records_by_user(args.dataset)
    policy_artifact = load_policy_model_v1_artifact(args.policy_model_artifact)
    combined_report = simulate_closed_loop_batch(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        model_artifact_path=args.model_artifact,
        policy_model_artifact_path=args.policy_model_artifact,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_and_policy_guarded",
    )

    cgm_scenarios = [
        scenario
        for scenario in combined_report.scenario_reports
        if records_by_user[scenario.user_id][0].request.input_availability.cgm
    ]
    final_cgm_cases = [
        _build_case_diagnostic(
            scenario=scenario,
            record=records_by_user[scenario.user_id][scenario.trace[-1].cycle_index],
            policy_artifact=policy_artifact,
        )
        for scenario in cgm_scenarios
    ]
    continue_plan_cases = [
        case
        for case in final_cgm_cases
        if case["actual_final_selected_policy_action"] == NextAction.CONTINUE_PLAN.value
    ]

    report = {
        "dataset_path": str(Path(args.dataset)),
        "model_artifact_path": args.model_artifact,
        "policy_model_artifact_path": args.policy_model_artifact,
        "neutralized_effect_definition": (
            "policy scores computed from the fixed policy artifact with "
            "record.expected_effect_proxy and no effect-conditioned priors"
        ),
        "combined_current_cgm_final_action_distribution": dict(
            sorted(
                Counter(
                    scenario.final_policy_action.value for scenario in cgm_scenarios
                ).items()
            )
        ),
        "cgm_final_case_count": len(final_cgm_cases),
        "cgm_continue_plan_case_count": len(continue_plan_cases),
        "all_final_cgm_stage_action_distributions": _build_stage_action_distributions(
            final_cgm_cases
        ),
        "all_final_cgm_layer_flip_counts": _build_stage_flip_counts(final_cgm_cases),
        "continue_plan_attribution_summary": _build_continue_plan_attribution_summary(
            continue_plan_cases
        ),
        "continue_plan_margin_summary": _build_continue_plan_margin_summary(
            continue_plan_cases
        ),
        "continue_plan_cases": continue_plan_cases,
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
                "cgm_continue_plan_case_count": report["cgm_continue_plan_case_count"],
                "continue_plan_attribution_summary": report[
                    "continue_plan_attribution_summary"
                ],
                "all_final_cgm_layer_flip_counts": report[
                    "all_final_cgm_layer_flip_counts"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _build_case_diagnostic(*, scenario, record, policy_artifact) -> dict[str, object]:
    final_step = scenario.trace[-1]
    response = recommend(record.request)
    neutralized_scores = predict_policy_scores_v1(policy_artifact, record)
    override_gate_active = (
        final_step.predicted_effect_source == EffectSource.LEARNED_MODEL_V1
    )
    override_only_scores = _override_only_scores(
        policy_artifact=policy_artifact,
        record=record,
        predicted_effect_proxy=final_step.predicted_effect_proxy,
        override_gate_active=override_gate_active,
    )
    prior_gate_eligible = override_gate_active and _should_apply_effect_conditioned_policy_priors(
        record=record,
        response=response,
    )
    override_plus_priors_scores = deepcopy(override_only_scores)
    if prior_gate_eligible:
        _apply_effect_conditioned_policy_priors(
            scores=override_plus_priors_scores,
            record=record,
            predicted_effect_proxy=final_step.predicted_effect_proxy,
        )

    neutralized_top = _top_label(neutralized_scores)
    override_only_top = _top_label(override_only_scores)
    override_plus_priors_top = _top_label(override_plus_priors_scores)
    actual_final_action = final_step.selected_policy_action.value
    attribution_label = _attribution_label(
        actual_final_action=actual_final_action,
        raw_final_action=(
            final_step.raw_learned_policy_action.value
            if final_step.raw_learned_policy_action is not None
            else None
        ),
        neutralized_top=neutralized_top,
        override_only_top=override_only_top,
        override_plus_priors_top=override_plus_priors_top,
        policy_guard_applied=final_step.policy_guard_applied,
    )

    return {
        "user_id": scenario.user_id,
        "record_id": record.record_id,
        "final_cycle_index": final_step.cycle_index,
        "final_day_index": final_step.day_index,
        "engine_status": final_step.engine_status.value,
        "deterministic_action": final_step.deterministic_action.value,
        "raw_learned_policy_action": (
            final_step.raw_learned_policy_action.value
            if final_step.raw_learned_policy_action is not None
            else None
        ),
        "actual_final_selected_policy_action": actual_final_action,
        "policy_guard_applied": final_step.policy_guard_applied,
        "policy_guard_reason": final_step.policy_guard_reason,
        "override_gate_active": override_gate_active,
        "prior_gate_eligible": prior_gate_eligible,
        "predicted_effect_source": final_step.predicted_effect_source.value,
        "expected_effect_proxy": round(record.expected_effect_proxy, 6),
        "predicted_effect_proxy": round(final_step.predicted_effect_proxy, 6),
        "policy_effect_proxy_used": round(final_step.policy_effect_proxy_used, 6),
        "neutralized_top_action": neutralized_top,
        "override_only_top_action": override_only_top,
        "override_plus_priors_top_action": override_plus_priors_top,
        "continue_plan_attribution": attribution_label,
        "continue_plan_margin_deltas": {
            "override_only_minus_neutralized": round(
                _margin(override_only_scores, NextAction.CONTINUE_PLAN.value)
                - _margin(neutralized_scores, NextAction.CONTINUE_PLAN.value),
                6,
            ),
            "override_plus_priors_minus_override_only": round(
                _margin(override_plus_priors_scores, NextAction.CONTINUE_PLAN.value)
                - _margin(override_only_scores, NextAction.CONTINUE_PLAN.value),
                6,
            ),
        },
        "stage_scores": {
            "neutralized": _rounded_scores(neutralized_scores),
            "override_only": _rounded_scores(override_only_scores),
            "override_plus_priors": _rounded_scores(override_plus_priors_scores),
        },
    }


def _override_only_scores(
    *,
    policy_artifact,
    record,
    predicted_effect_proxy: float,
    override_gate_active: bool,
) -> dict[str, float]:
    if not override_gate_active:
        return predict_policy_scores_v1(policy_artifact, record)
    feature_row = build_policy_feature_dict_v1(record)
    feature_row["expected_effect_proxy"] = float(predicted_effect_proxy)
    return predict_policy_scores_from_feature_dict_v1(policy_artifact, feature_row)


def _top_label(scores: dict[str, float]) -> str:
    return max(sorted(scores.items()), key=lambda item: item[1])[0]


def _margin(scores: dict[str, float], label: str) -> float:
    runner_up = max(
        score for candidate_label, score in scores.items() if candidate_label != label
    )
    return float(scores[label] - runner_up)


def _rounded_scores(scores: dict[str, float]) -> dict[str, float]:
    return {label: round(score, 6) for label, score in sorted(scores.items())}


def _attribution_label(
    *,
    actual_final_action: str,
    raw_final_action: str | None,
    neutralized_top: str,
    override_only_top: str,
    override_plus_priors_top: str,
    policy_guard_applied: bool,
) -> str:
    if actual_final_action != NextAction.CONTINUE_PLAN.value:
        return "not_a_continue_plan_case"
    if policy_guard_applied and raw_final_action != NextAction.CONTINUE_PLAN.value:
        return "deterministic_guard_or_fallback"
    if neutralized_top != NextAction.CONTINUE_PLAN.value:
        if override_only_top == NextAction.CONTINUE_PLAN.value:
            return "combined_override_gate_primary"
        if override_plus_priors_top == NextAction.CONTINUE_PLAN.value:
            return "effect_priors_primary"
    if (
        neutralized_top == NextAction.CONTINUE_PLAN.value
        and override_only_top != NextAction.CONTINUE_PLAN.value
        and override_plus_priors_top == NextAction.CONTINUE_PLAN.value
    ):
        return "effect_priors_restore_continue_plan"
    if (
        neutralized_top == NextAction.CONTINUE_PLAN.value
        and override_only_top == NextAction.CONTINUE_PLAN.value
        and override_plus_priors_top == NextAction.CONTINUE_PLAN.value
    ):
        return "neutralized_policy_primary"
    return "mixed_or_non_incremental"


def _build_stage_action_distributions(
    cases: list[dict[str, object]],
) -> dict[str, dict[str, int]]:
    return {
        "neutralized": dict(
            sorted(Counter(case["neutralized_top_action"] for case in cases).items())
        ),
        "override_only": dict(
            sorted(Counter(case["override_only_top_action"] for case in cases).items())
        ),
        "override_plus_priors": dict(
            sorted(Counter(case["override_plus_priors_top_action"] for case in cases).items())
        ),
        "actual_final_selected_policy_action": dict(
            sorted(
                Counter(case["actual_final_selected_policy_action"] for case in cases).items()
            )
        ),
    }


def _build_stage_flip_counts(cases: list[dict[str, object]]) -> dict[str, object]:
    override_stage_changes = [
        case for case in cases if case["neutralized_top_action"] != case["override_only_top_action"]
    ]
    prior_stage_changes = [
        case
        for case in cases
        if case["override_only_top_action"] != case["override_plus_priors_top_action"]
    ]
    return {
        "override_stage_top_action_change_count": len(override_stage_changes),
        "prior_stage_top_action_change_count": len(prior_stage_changes),
        "override_stage_continue_plan_gain_count": sum(
            1
            for case in override_stage_changes
            if case["override_only_top_action"] == NextAction.CONTINUE_PLAN.value
            and case["neutralized_top_action"] != NextAction.CONTINUE_PLAN.value
        ),
        "prior_stage_continue_plan_gain_count": sum(
            1
            for case in prior_stage_changes
            if case["override_plus_priors_top_action"] == NextAction.CONTINUE_PLAN.value
            and case["override_only_top_action"] != NextAction.CONTINUE_PLAN.value
        ),
        "override_stage_continue_plan_loss_count": sum(
            1
            for case in override_stage_changes
            if case["neutralized_top_action"] == NextAction.CONTINUE_PLAN.value
            and case["override_only_top_action"] != NextAction.CONTINUE_PLAN.value
        ),
        "prior_stage_continue_plan_loss_count": sum(
            1
            for case in prior_stage_changes
            if case["override_only_top_action"] == NextAction.CONTINUE_PLAN.value
            and case["override_plus_priors_top_action"] != NextAction.CONTINUE_PLAN.value
        ),
    }


def _build_continue_plan_attribution_summary(
    continue_plan_cases: list[dict[str, object]],
) -> dict[str, object]:
    label_counts = Counter(
        case["continue_plan_attribution"] for case in continue_plan_cases
    )
    return {
        "total_continue_plan_cases": len(continue_plan_cases),
        "label_counts": dict(sorted(label_counts.items())),
        "user_ids_by_label": {
            label: [
                case["user_id"]
                for case in continue_plan_cases
                if case["continue_plan_attribution"] == label
            ]
            for label in sorted(label_counts)
        },
    }


def _build_continue_plan_margin_summary(
    continue_plan_cases: list[dict[str, object]],
) -> dict[str, object]:
    override_deltas = [
        float(case["continue_plan_margin_deltas"]["override_only_minus_neutralized"])
        for case in continue_plan_cases
    ]
    prior_deltas = [
        float(case["continue_plan_margin_deltas"]["override_plus_priors_minus_override_only"])
        for case in continue_plan_cases
    ]
    return {
        "override_delta_sum": round(sum(override_deltas), 6),
        "prior_delta_sum": round(sum(prior_deltas), 6),
        "override_gt_prior_case_count": sum(
            1 for override_delta, prior_delta in zip(override_deltas, prior_deltas, strict=True)
            if override_delta > prior_delta
        ),
        "prior_gt_override_case_count": sum(
            1 for override_delta, prior_delta in zip(override_deltas, prior_deltas, strict=True)
            if prior_delta > override_delta
        ),
        "override_eq_prior_case_count": sum(
            1 for override_delta, prior_delta in zip(override_deltas, prior_deltas, strict=True)
            if round(override_delta - prior_delta, 6) == 0.0
        ),
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# cgm continue_plan fallback attribution v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- model_artifact_path: `{report['model_artifact_path']}`",
        f"- policy_model_artifact_path: `{report['policy_model_artifact_path']}`",
        (
            "- neutralized_effect_definition: "
            f"`{report['neutralized_effect_definition']}`"
        ),
        "",
        "## Summary",
        (
            "- combined_current_cgm_final_action_distribution: "
            f"`{report['combined_current_cgm_final_action_distribution']}`"
        ),
        (
            "- all_final_cgm_stage_action_distributions: "
            f"`{report['all_final_cgm_stage_action_distributions']}`"
        ),
        (
            "- all_final_cgm_layer_flip_counts: "
            f"`{report['all_final_cgm_layer_flip_counts']}`"
        ),
        (
            "- continue_plan_attribution_summary: "
            f"`{report['continue_plan_attribution_summary']}`"
        ),
        (
            "- continue_plan_margin_summary: "
            f"`{report['continue_plan_margin_summary']}`"
        ),
        "",
        "## Continue Plan Cases",
    ]
    for case in report["continue_plan_cases"]:
        lines.extend(
            [
                "",
                f"### {case['user_id']}",
                f"- record_id: `{case['record_id']}`",
                (
                    "- stage_actions: "
                    f"`neutralized={case['neutralized_top_action']}, "
                    f"override_only={case['override_only_top_action']}, "
                    f"override_plus_priors={case['override_plus_priors_top_action']}, "
                    f"actual={case['actual_final_selected_policy_action']}`"
                ),
                (
                    "- effect_proxies: "
                    f"`expected={case['expected_effect_proxy']}, "
                    f"predicted={case['predicted_effect_proxy']}, "
                    f"used={case['policy_effect_proxy_used']}`"
                ),
                (
                    "- gating: "
                    f"`override_gate_active={case['override_gate_active']}, "
                    f"prior_gate_eligible={case['prior_gate_eligible']}, "
                    f"policy_guard_applied={case['policy_guard_applied']}, "
                    f"policy_guard_reason={case['policy_guard_reason']}`"
                ),
                (
                    "- continue_plan_attribution: "
                    f"`{case['continue_plan_attribution']}`"
                ),
                (
                    "- continue_plan_margin_deltas: "
                    f"`{case['continue_plan_margin_deltas']}`"
                ),
            ]
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
