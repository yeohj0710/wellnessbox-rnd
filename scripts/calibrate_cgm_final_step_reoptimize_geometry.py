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
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import NextAction
from wellnessbox_rnd.simulation import simulate_closed_loop_batch
from wellnessbox_rnd.simulation.closed_loop_v0 import (
    RE_OPTIMIZE_CGM_REVIVAL_PROXY_MAX,
    RE_OPTIMIZE_REVIVAL_PROXY_MIN,
    _apply_effect_conditioned_policy_priors,
    _load_records_by_user,
    _should_apply_effect_conditioned_policy_priors,
)

TRACKED_FEATURES = (
    "policy_effect_proxy_used",
    "adherence_proxy",
    "side_effect_proxy",
    "baseline::blood_glucose",
    "follow_up::blood_glucose",
    "delta::blood_glucose",
    "trajectory_step",
    "day_index",
)
CGM_FINAL_STEP_GLUCOSE_GEOMETRY_SCALING = 0.3
CGM_FINAL_STEP_GLUCOSE_FEATURES = (
    "baseline::blood_glucose",
    "delta::blood_glucose",
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Counterfactually calibrate final-step cgm continue_plan vs re_optimize "
            "score geometry without changing runtime logic"
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
        "--blocker-report-json",
        default="artifacts/reports/current_cgm_continue_plan_diagnostic_v1.json",
        help="Existing blocker-family evidence report",
    )
    parser.add_argument(
        "--feature-audit-json",
        default="artifacts/reports/cgm_combined_replay_feature_audit_v1.json",
        help="Existing feature-family evidence report",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/cgm_final_step_reoptimize_geometry_calibration_v1.json",
        help="Calibration report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/cgm_final_step_reoptimize_geometry_calibration_v1.md",
        help="Calibration report markdown output path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    blocker_report = _load_json_report(args.blocker_report_json)
    feature_audit = _load_json_report(args.feature_audit_json)
    records_by_user = _load_records_by_user(args.dataset)
    policy_artifact = load_policy_model_v1_artifact(args.policy_model_artifact)
    comparison = simulate_closed_loop_batch(
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

    proxy_weight_gap = _proxy_weight_gap(policy_artifact)
    feature_gap_weights = _feature_gap_weights(policy_artifact)
    final_cgm_cases = _build_final_cgm_cases(
        scenario_reports=comparison.scenario_reports,
        records_by_user=records_by_user,
        proxy_weight_gap=proxy_weight_gap,
        feature_gap_weights=feature_gap_weights,
        policy_artifact=policy_artifact,
    )
    selected_continue_cases = [
        case
        for case in final_cgm_cases
        if case["selected_final_action"] == NextAction.CONTINUE_PLAN.value
    ]
    report = {
        "dataset_path": str(Path(args.dataset)),
        "model_artifact_path": args.model_artifact,
        "policy_model_artifact_path": args.policy_model_artifact,
        "blocker_evidence": {
            "source_report": str(Path(args.blocker_report_json)),
            "current_cgm_final_action_distribution": blocker_report[
                "current_cgm_final_action_distribution"
            ],
            "current_continue_plan_case_count": blocker_report[
                "current_continue_plan_case_count"
            ],
            "blocker_summary": blocker_report["blocker_summary"],
            "blocker_family_summary": blocker_report["blocker_family_summary"],
        },
        "feature_family_evidence": {
            "source_report": str(Path(args.feature_audit_json)),
            "proxy_weight_gap_continue_minus_reoptimize": round(proxy_weight_gap, 6),
            "tracked_feature_gap_weights": {
                feature: round(weight, 6)
                for feature, weight in sorted(feature_gap_weights.items())
                if feature in TRACKED_FEATURES
            },
            "feature_audit_findings": feature_audit["summary_findings"],
        },
        "decision_surface_overlap_explanation": _build_overlap_explanation(
            feature_audit=feature_audit,
            selected_continue_cases=selected_continue_cases,
        ),
        "replay_only_calibration": {
            "name": "proxy_overshoot_plus_positive_glucose_geometry_credit",
            "formula": (
                "re_optimize += proxy_overshoot_credit + 0.3 * max(0, "
                "continue_minus_reoptimize(baseline::blood_glucose)) + 0.3 * max(0, "
                "continue_minus_reoptimize(delta::blood_glucose))"
            ),
            "target_scope": "selected_final_continue_plan_cgm_cases_only",
            "rationale": (
                "Neutralize only the replay-time proxy overshoot plus the positive final-step "
                "blood-glucose geometry that stacks with it on blocker-family cgm "
                "continue_plan cases, without widening monitor thresholds or changing runtime."
            ),
        },
        "cgm_final_geometry_summary": _summarize_geometry(final_cgm_cases),
        "selected_continue_geometry_summary": _summarize_margin_shift(
            selected_continue_cases
        ),
        "selected_continue_mean_feature_gap_contributions": _mean_feature_gap_summary(
            selected_continue_cases
        ),
        "selected_continue_cases": selected_continue_cases,
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
                "selected_continue_geometry_summary": report[
                    "selected_continue_geometry_summary"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _load_json_report(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_final_cgm_cases(
    *,
    scenario_reports,
    records_by_user,
    proxy_weight_gap: float,
    feature_gap_weights: dict[str, float],
    policy_artifact,
) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    for scenario in scenario_reports:
        user_records = records_by_user[scenario.user_id]
        if not user_records[0].request.input_availability.cgm:
            continue
        final_step = scenario.trace[-1]
        record = user_records[final_step.cycle_index]
        response = recommend(record.request)
        feature_row = build_policy_feature_dict_v1(record)
        feature_row["expected_effect_proxy"] = float(final_step.policy_effect_proxy_used)
        scores_before_priors = predict_policy_scores_from_feature_dict_v1(
            policy_artifact,
            feature_row,
        )
        scores_after_priors = deepcopy(scores_before_priors)
        if _should_apply_effect_conditioned_policy_priors(
            record=record,
            response=response,
        ):
            _apply_effect_conditioned_policy_priors(
                scores=scores_after_priors,
                record=record,
                predicted_effect_proxy=float(final_step.policy_effect_proxy_used),
            )
        proxy_bonus = _compute_proxy_overshoot_reoptimize_credit(
            expected_effect_proxy=float(record.expected_effect_proxy),
            policy_effect_proxy_used=float(final_step.policy_effect_proxy_used),
            proxy_weight_gap=proxy_weight_gap,
        )
        feature_gap_contributions = _feature_gap_contributions(
            record=record,
            feature_gap_weights=feature_gap_weights,
            policy_effect_proxy_used=float(final_step.policy_effect_proxy_used),
        )
        glucose_geometry_bonus = 0.0
        if final_step.selected_policy_action.value == NextAction.CONTINUE_PLAN.value:
            glucose_geometry_bonus = _compute_final_step_glucose_geometry_credit(
                feature_gap_contributions=feature_gap_contributions
            )
        total_bonus = proxy_bonus + glucose_geometry_bonus
        calibrated_scores = deepcopy(scores_after_priors)
        calibrated_scores[NextAction.RE_OPTIMIZE.value] = (
            calibrated_scores.get(NextAction.RE_OPTIMIZE.value, 0.0) + total_bonus
        )
        cases.append(
            {
                "user_id": scenario.user_id,
                "record_id": record.record_id,
                "label_next_action": record.labels.next_action.value,
                "label_reason_code": record.labels.reason_code,
                "selected_final_action": final_step.selected_policy_action.value,
                "raw_learned_policy_action": (
                    final_step.raw_learned_policy_action.value
                    if final_step.raw_learned_policy_action is not None
                    else None
                ),
                "current_top_action_after_priors": _top_label(scores_after_priors),
                "calibrated_top_action_after_priors": _top_label(calibrated_scores),
                "expected_effect_proxy": round(float(record.expected_effect_proxy), 6),
                "policy_effect_proxy_used": round(
                    float(final_step.policy_effect_proxy_used), 6
                ),
                "proxy_overshoot": round(
                    float(final_step.policy_effect_proxy_used)
                    - float(record.expected_effect_proxy),
                    6,
                ),
                "proxy_overshoot_reoptimize_credit": round(proxy_bonus, 6),
                "positive_glucose_geometry_reoptimize_credit": round(
                    glucose_geometry_bonus,
                    6,
                ),
                "total_reoptimize_credit": round(total_bonus, 6),
                "predicted_effect_proxy": round(float(final_step.predicted_effect_proxy), 6),
                "adherence_proxy": round(float(record.adherence_proxy), 6),
                "side_effect_proxy": round(float(record.side_effect_proxy), 6),
                "delta_blood_glucose": round(
                    float(record.delta_z_by_domain.get("blood_glucose", 0.0)),
                    6,
                ),
                "baseline_blood_glucose": round(
                    float(record.baseline_pro.domain_z.get("blood_glucose", 0.0)),
                    6,
                ),
                "follow_up_blood_glucose": round(
                    float(record.follow_up_pro.domain_z.get("blood_glucose", 0.0)),
                    6,
                ),
                "reoptimize_revival_window_eligible": (
                    RE_OPTIMIZE_REVIVAL_PROXY_MIN
                    <= float(final_step.policy_effect_proxy_used)
                    <= RE_OPTIMIZE_CGM_REVIVAL_PROXY_MAX
                ),
                "continue_minus_reoptimize_before_calibration": round(
                    scores_after_priors.get(NextAction.CONTINUE_PLAN.value, 0.0)
                    - scores_after_priors.get(NextAction.RE_OPTIMIZE.value, 0.0),
                    6,
                ),
                "continue_minus_reoptimize_after_calibration": round(
                    calibrated_scores.get(NextAction.CONTINUE_PLAN.value, 0.0)
                    - calibrated_scores.get(NextAction.RE_OPTIMIZE.value, 0.0),
                    6,
                ),
                "score_gap_reduction": round(total_bonus, 6),
                "feature_gap_contributions": {
                    feature: round(value, 6)
                    for feature, value in sorted(feature_gap_contributions.items())
                },
            }
        )
    cases.sort(key=lambda case: (case["selected_final_action"], case["user_id"]))
    return cases


def _proxy_weight_gap(policy_artifact) -> float:
    feature_weights = _feature_gap_weights(policy_artifact)
    return float(feature_weights["expected_effect_proxy"])


def _feature_gap_weights(policy_artifact) -> dict[str, float]:
    continue_index = policy_artifact.class_labels.index(NextAction.CONTINUE_PLAN.value)
    reoptimize_index = policy_artifact.class_labels.index(NextAction.RE_OPTIMIZE.value)
    continue_weights = dict(
        zip(
            policy_artifact.feature_names,
            policy_artifact.weights[continue_index],
            strict=True,
        )
    )
    reoptimize_weights = dict(
        zip(
            policy_artifact.feature_names,
            policy_artifact.weights[reoptimize_index],
            strict=True,
        )
    )
    return {
        feature_name: float(continue_weights.get(feature_name, 0.0))
        - float(reoptimize_weights.get(feature_name, 0.0))
        for feature_name in policy_artifact.feature_names
    }


def _compute_proxy_overshoot_reoptimize_credit(
    *,
    expected_effect_proxy: float,
    policy_effect_proxy_used: float,
    proxy_weight_gap: float,
) -> float:
    return max(0.0, policy_effect_proxy_used - expected_effect_proxy) * proxy_weight_gap


def _compute_final_step_glucose_geometry_credit(
    *,
    feature_gap_contributions: dict[str, float],
    scaling_factor: float = CGM_FINAL_STEP_GLUCOSE_GEOMETRY_SCALING,
) -> float:
    positive_glucose_geometry = sum(
        max(0.0, float(feature_gap_contributions.get(feature, 0.0)))
        for feature in CGM_FINAL_STEP_GLUCOSE_FEATURES
    )
    return positive_glucose_geometry * scaling_factor


def _feature_gap_contributions(
    *,
    record,
    feature_gap_weights: dict[str, float],
    policy_effect_proxy_used: float,
) -> dict[str, float]:
    return {
        "policy_effect_proxy_used": policy_effect_proxy_used
        * feature_gap_weights.get("expected_effect_proxy", 0.0),
        "adherence_proxy": float(record.adherence_proxy)
        * feature_gap_weights.get("adherence_proxy", 0.0),
        "side_effect_proxy": float(record.side_effect_proxy)
        * feature_gap_weights.get("side_effect_proxy", 0.0),
        "baseline::blood_glucose": float(
            record.baseline_pro.domain_z.get("blood_glucose", 0.0)
        )
        * feature_gap_weights.get("baseline::blood_glucose", 0.0),
        "follow_up::blood_glucose": float(
            record.follow_up_pro.domain_z.get("blood_glucose", 0.0)
        )
        * feature_gap_weights.get("follow_up::blood_glucose", 0.0),
        "delta::blood_glucose": float(record.delta_z_by_domain.get("blood_glucose", 0.0))
        * feature_gap_weights.get("delta::blood_glucose", 0.0),
        "trajectory_step": float(record.trajectory_step)
        * feature_gap_weights.get("trajectory_step", 0.0),
        "day_index": float(record.day_index) * feature_gap_weights.get("day_index", 0.0),
    }


def _build_overlap_explanation(
    *,
    feature_audit: dict[str, object],
    selected_continue_cases: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "current_blocker_read": (
            "Existing blocker evidence says final cgm continue_plan cases are almost all "
            "outside the monitor band with large gaps, not threshold-edge cases."
        ),
        "surface_overlap_reason": [
            (
                "The final cgm replay surface keeps re_optimize suppressed because "
                "the same proxy family both boosts continue_plan and penalizes "
                "re_optimize with a large weight gap."
            ),
            (
                "Adherence and blood-glucose delta families move in the same "
                "direction as the proxy on final selected continue_plan cases, so "
                "the overlap is structural rather than a one-threshold bug."
            ),
            (
                "The re_optimize revival window is inactive on the final selected "
                "continue_plan cases, so there is no late-stage re_optimize prior "
                "to counterbalance the continue_plan surface."
            ),
        ],
        "selected_continue_revival_window_case_count": sum(
            1 for case in selected_continue_cases if case["reoptimize_revival_window_eligible"]
        ),
        "selected_continue_positive_proxy_overshoot_case_count": sum(
            1 for case in selected_continue_cases if case["proxy_overshoot"] > 0.0
        ),
        "feature_audit_anchor_findings": feature_audit["summary_findings"][:3],
    }


def _summarize_geometry(cases: list[dict[str, object]]) -> dict[str, object]:
    return {
        "final_cgm_case_count": len(cases),
        "selected_final_action_distribution": dict(
            sorted(Counter(case["selected_final_action"] for case in cases).items())
        ),
        "current_top_action_after_priors_distribution": dict(
            sorted(Counter(case["current_top_action_after_priors"] for case in cases).items())
        ),
        "calibrated_top_action_after_priors_distribution": dict(
            sorted(
                Counter(case["calibrated_top_action_after_priors"] for case in cases).items()
            )
        ),
    }


def _summarize_margin_shift(cases: list[dict[str, object]]) -> dict[str, object]:
    before_gaps = [
        float(case["continue_minus_reoptimize_before_calibration"]) for case in cases
    ]
    after_gaps = [
        float(case["continue_minus_reoptimize_after_calibration"]) for case in cases
    ]
    return {
        "selected_continue_case_count": len(cases),
        "mean_continue_minus_reoptimize_before_calibration": round(
            sum(before_gaps) / len(before_gaps),
            6,
        ),
        "mean_continue_minus_reoptimize_after_calibration": round(
            sum(after_gaps) / len(after_gaps),
            6,
        ),
        "gap_reduction_sum": round(sum(before_gaps) - sum(after_gaps), 6),
        "gap_reduction_mean": round(
            (sum(before_gaps) - sum(after_gaps)) / len(before_gaps),
            6,
        ),
        "case_count_gap_le_1_before": sum(gap <= 1.0 for gap in before_gaps),
        "case_count_gap_le_1_after": sum(gap <= 1.0 for gap in after_gaps),
        "continue_to_reoptimize_top_action_flip_count": sum(
            1
            for case in cases
            if case["current_top_action_after_priors"] == NextAction.CONTINUE_PLAN.value
            and case["calibrated_top_action_after_priors"] == NextAction.RE_OPTIMIZE.value
        ),
        "continue_to_reoptimize_top_action_flip_user_ids": [
            case["user_id"]
            for case in cases
            if case["current_top_action_after_priors"] == NextAction.CONTINUE_PLAN.value
            and case["calibrated_top_action_after_priors"] == NextAction.RE_OPTIMIZE.value
        ],
    }


def _mean_feature_gap_summary(cases: list[dict[str, object]]) -> dict[str, float]:
    means: dict[str, float] = {}
    for feature in TRACKED_FEATURES:
        means[feature] = sum(
            float(case["feature_gap_contributions"][feature]) for case in cases
        ) / len(cases)
    return {
        feature: round(value, 6)
        for feature, value in sorted(means.items(), key=lambda item: item[1], reverse=True)
    }


def _top_label(scores: dict[str, float]) -> str:
    return max(sorted(scores.items()), key=lambda item: item[1])[0]


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# cgm final-step re_optimize geometry calibration v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- model_artifact_path: `{report['model_artifact_path']}`",
        f"- policy_model_artifact_path: `{report['policy_model_artifact_path']}`",
        "",
        "## Blocker Evidence",
        f"- blocker_summary: `{report['blocker_evidence']['blocker_summary']}`",
        f"- blocker_family_summary: `{report['blocker_evidence']['blocker_family_summary']}`",
        "",
        "## Why The Surface Overlaps",
        (
            "- proxy_weight_gap_continue_minus_reoptimize: "
            f"`{report['feature_family_evidence']['proxy_weight_gap_continue_minus_reoptimize']}`"
        ),
        (
            "- selected_continue_mean_feature_gap_contributions: "
            f"`{report['selected_continue_mean_feature_gap_contributions']}`"
        ),
    ]
    for sentence in report["decision_surface_overlap_explanation"]["surface_overlap_reason"]:
        lines.append(f"- explanation: `{sentence}`")
    lines.extend(
        [
            "",
            "## Replay-only Calibration",
            (
                "- calibration_formula: "
                f"`{report['replay_only_calibration']['formula']}`"
            ),
            (
                "- calibration_target_scope: "
                f"`{report['replay_only_calibration']['target_scope']}`"
            ),
            (
                "- cgm_final_geometry_summary: "
                f"`{report['cgm_final_geometry_summary']}`"
            ),
            (
                "- selected_continue_geometry_summary: "
                f"`{report['selected_continue_geometry_summary']}`"
            ),
            "",
            "## Selected Continue Cases",
        ]
    )
    ranked_cases = sorted(
        report["selected_continue_cases"],
        key=lambda case: case["continue_minus_reoptimize_after_calibration"],
    )
    for case in ranked_cases:
        lines.extend(
            [
                "",
                f"### {case['user_id']}",
                f"- record_id: `{case['record_id']}`",
                (
                    "- actions: "
                    f"`selected={case['selected_final_action']}, "
                    f"current_top={case['current_top_action_after_priors']}, "
                    f"calibrated_top={case['calibrated_top_action_after_priors']}`"
                ),
                (
                    "- proxies: "
                    f"`expected={case['expected_effect_proxy']}, "
                    f"used={case['policy_effect_proxy_used']}, "
                    f"overshoot={case['proxy_overshoot']}, "
                    f"proxy_credit={case['proxy_overshoot_reoptimize_credit']}, "
                    f"glucose_credit={case['positive_glucose_geometry_reoptimize_credit']}, "
                    f"total_credit={case['total_reoptimize_credit']}`"
                ),
                (
                    "- gaps: "
                    f"`before={case['continue_minus_reoptimize_before_calibration']}, "
                    f"after={case['continue_minus_reoptimize_after_calibration']}`"
                ),
                (
                    "- feature_gap_contributions: "
                    f"`{case['feature_gap_contributions']}`"
                ),
            ]
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
