import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

import wellnessbox_rnd.simulation.closed_loop_v0 as simulation_module
from wellnessbox_rnd.schemas.recommendation import NextAction
from wellnessbox_rnd.simulation import compare_batch_simulation_modes

CURRENT_CGM_MONITOR_ONLY_THRESHOLD = 0.37
SWEEP_POINTS = (
    ("slightly_tighter", 0.36),
    ("current", 0.37),
    ("slightly_looser", 0.38),
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Run a bounded 3-point sweep over the cgm monitor-only threshold-edge "
            "prior band without changing the checked-in replay behavior"
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
        default="artifacts/reports/cgm_threshold_edge_monitor_band_threshold_sweep_v1.json",
        help="Sweep report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/cgm_threshold_edge_monitor_band_threshold_sweep_v1.md",
        help="Sweep report markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    sweep_results = [
        _run_sweep_point(
            label=label,
            cgm_monitor_only_threshold=threshold,
            dataset_path=args.dataset,
            max_cycles=args.max_cycles,
            max_users=args.max_users,
            model_artifact_path=args.model_artifact,
            policy_model_artifact_path=args.policy_model_artifact,
        )
        for label, threshold in SWEEP_POINTS
    ]
    current_result = next(
        result for result in sweep_results if result["label"] == "current"
    )
    report = {
        "dataset_path": str(Path(args.dataset)),
        "model_artifact_path": args.model_artifact,
        "policy_model_artifact_path": args.policy_model_artifact,
        "sweep_target": {
            "parameter_name": "cgm_monitor_only_threshold",
            "current_checked_in_value": CURRENT_CGM_MONITOR_ONLY_THRESHOLD,
            "point_labels": [label for label, _ in SWEEP_POINTS],
        },
        "sweep_results": sweep_results,
        "recommended_candidate": _recommend_candidate(
            sweep_results=sweep_results,
            current_result=current_result,
        ),
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
                "recommended_candidate": report["recommended_candidate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _run_sweep_point(
    *,
    label: str,
    cgm_monitor_only_threshold: float,
    dataset_path: str,
    max_cycles: int,
    max_users: int,
    model_artifact_path: str,
    policy_model_artifact_path: str,
) -> dict[str, object]:
    original_apply = simulation_module._apply_effect_conditioned_policy_priors

    def patched_apply(
        *,
        scores: dict[str, float],
        record,
        predicted_effect_proxy: float,
    ) -> None:
        if predicted_effect_proxy < 0.14:
            scores[NextAction.RE_OPTIMIZE.value] = (
                scores.get(NextAction.RE_OPTIMIZE.value, 0.0)
                + simulation_module.RE_OPTIMIZE_EFFECT_PRIOR_BONUS
            )
            scores[NextAction.TRIGGER_SAFETY_RECHECK.value] = (
                scores.get(NextAction.TRIGGER_SAFETY_RECHECK.value, 0.0)
                - simulation_module.RE_OPTIMIZE_TRIGGER_PENALTY
            )
            return
        threshold = (
            cgm_monitor_only_threshold
            if record.request.input_availability.cgm
            else 0.24
        )
        if predicted_effect_proxy < threshold:
            scores[NextAction.MONITOR_ONLY.value] = (
                scores.get(NextAction.MONITOR_ONLY.value, 0.0)
                + simulation_module.MONITOR_ONLY_EFFECT_PRIOR_BONUS
            )
            if simulation_module._should_apply_reoptimize_revival_prior(
                record=record,
                predicted_effect_proxy=predicted_effect_proxy,
            ):
                scores[NextAction.RE_OPTIMIZE.value] = (
                    scores.get(NextAction.RE_OPTIMIZE.value, 0.0)
                    + simulation_module.RE_OPTIMIZE_REVIVAL_BONUS
                )
                scores[NextAction.MONITOR_ONLY.value] = (
                    scores.get(NextAction.MONITOR_ONLY.value, 0.0)
                    - simulation_module.RE_OPTIMIZE_REVIVAL_MONITOR_PENALTY
                )
                scores[NextAction.CONTINUE_PLAN.value] = (
                    scores.get(NextAction.CONTINUE_PLAN.value, 0.0)
                    - simulation_module.RE_OPTIMIZE_REVIVAL_CONTINUE_PENALTY
                )
            scores[NextAction.TRIGGER_SAFETY_RECHECK.value] = (
                scores.get(NextAction.TRIGGER_SAFETY_RECHECK.value, 0.0)
                - simulation_module.MONITOR_ONLY_TRIGGER_PENALTY
            )
            return
        scores[NextAction.CONTINUE_PLAN.value] = (
            scores.get(NextAction.CONTINUE_PLAN.value, 0.0)
            + simulation_module.CONTINUE_PLAN_EFFECT_PRIOR_BONUS
        )
        scores[NextAction.TRIGGER_SAFETY_RECHECK.value] = (
            scores.get(NextAction.TRIGGER_SAFETY_RECHECK.value, 0.0)
            - simulation_module.CONTINUE_PLAN_TRIGGER_PENALTY
        )

    try:
        simulation_module._apply_effect_conditioned_policy_priors = patched_apply
        comparison_report = compare_batch_simulation_modes(
            dataset_path=dataset_path,
            max_cycles=max_cycles,
            max_users=max_users,
            model_artifact_path=model_artifact_path,
            policy_model_artifact_path=policy_model_artifact_path,
            enable_policy_effect_proxy_override=True,
        )
    finally:
        simulation_module._apply_effect_conditioned_policy_priors = original_apply

    combined_mode = next(
        mode
        for mode in comparison_report.compared_modes
        if mode.mode_name == "learned_effect_and_policy_guarded"
    )
    cgm_slice = combined_mode.cohort_slice_metrics["cgm_users"]
    low_risk_slice = combined_mode.cohort_slice_metrics["low_risk_users"]
    return {
        "label": label,
        "cgm_monitor_only_threshold": cgm_monitor_only_threshold,
        "combined_final_policy_action_counts": combined_mode.final_policy_action_counts,
        "cgm_final_action_distribution": cgm_slice.final_action_distribution,
        "low_risk_final_action_distribution": low_risk_slice.final_action_distribution,
        "cgm_disagreement_count": cgm_slice.deterministic_vs_learned_disagreement_count,
        "low_risk_disagreement_count": low_risk_slice.deterministic_vs_learned_disagreement_count,
        "policy_effect_override_applied_count": combined_mode.policy_effect_override_applied_count,
        "policy_guard_applied_count": combined_mode.policy_guard_applied_count,
        "effect_guard_applied_count": combined_mode.effect_guard_applied_count,
    }


def _recommend_candidate(
    *,
    sweep_results: list[dict[str, object]],
    current_result: dict[str, object],
) -> dict[str, object]:
    current_low_risk_monitor_only = current_result["low_risk_final_action_distribution"].get(
        "monitor_only",
        0,
    )
    current_cgm_monitor_only = current_result["cgm_final_action_distribution"].get(
        "monitor_only",
        0,
    )
    current_cgm_reoptimize = current_result["cgm_final_action_distribution"].get(
        "re_optimize",
        0,
    )

    eligible = [
        result
        for result in sweep_results
        if result["low_risk_final_action_distribution"].get("monitor_only", 0)
        >= current_low_risk_monitor_only
    ]
    best = max(
        eligible,
        key=lambda result: (
            result["cgm_final_action_distribution"].get("monitor_only", 0),
            result["cgm_final_action_distribution"].get("re_optimize", 0),
            -result["cgm_disagreement_count"],
            -result["low_risk_disagreement_count"],
            result["cgm_monitor_only_threshold"],
        ),
    )
    return {
        "label": best["label"],
        "cgm_monitor_only_threshold": best["cgm_monitor_only_threshold"],
        "why": (
            "maximizes cgm monitor_only among sweep points that do not reduce "
            "low-risk richness, without changing checked-in behavior in this loop"
        ),
        "delta_vs_current": {
            "cgm_monitor_only_delta": best["cgm_final_action_distribution"].get(
                "monitor_only",
                0,
            )
            - current_cgm_monitor_only,
            "cgm_re_optimize_delta": best["cgm_final_action_distribution"].get(
                "re_optimize",
                0,
            )
            - current_cgm_reoptimize,
            "low_risk_monitor_only_delta": best["low_risk_final_action_distribution"].get(
                "monitor_only",
                0,
            )
            - current_low_risk_monitor_only,
            "cgm_disagreement_delta": best["cgm_disagreement_count"]
            - current_result["cgm_disagreement_count"],
            "low_risk_disagreement_delta": best["low_risk_disagreement_count"]
            - current_result["low_risk_disagreement_count"],
        },
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# cgm threshold-edge monitor band threshold sweep v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- model_artifact_path: `{report['model_artifact_path']}`",
        f"- policy_model_artifact_path: `{report['policy_model_artifact_path']}`",
        (
            "- sweep_target: "
            f"`{report['sweep_target']['parameter_name']}` current="
            f"`{report['sweep_target']['current_checked_in_value']}`"
        ),
        "",
        "## Sweep Results",
    ]
    for result in report["sweep_results"]:
        lines.extend(
            [
                "",
                f"### {result['label']}",
                f"- cgm_monitor_only_threshold: `{result['cgm_monitor_only_threshold']}`",
                (
                    "- cgm_final_action_distribution: "
                    f"`{result['cgm_final_action_distribution']}`"
                ),
                (
                    "- low_risk_final_action_distribution: "
                    f"`{result['low_risk_final_action_distribution']}`"
                ),
                f"- cgm_disagreement_count: `{result['cgm_disagreement_count']}`",
                f"- low_risk_disagreement_count: `{result['low_risk_disagreement_count']}`",
                (
                    "- combined_final_policy_action_counts: "
                    f"`{result['combined_final_policy_action_counts']}`"
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Recommended Candidate",
            f"- label: `{report['recommended_candidate']['label']}`",
            (
                "- cgm_monitor_only_threshold: "
                f"`{report['recommended_candidate']['cgm_monitor_only_threshold']}`"
            ),
            f"- why: `{report['recommended_candidate']['why']}`",
            (
                "- delta_vs_current: "
                f"`{report['recommended_candidate']['delta_vs_current']}`"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
