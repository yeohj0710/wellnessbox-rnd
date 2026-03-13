import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.models.policy_model_v1 import load_policy_model_v1_artifact
from wellnessbox_rnd.policy import (
    build_policy_prediction_slice_summaries_v1,
    evaluate_policy_model_v1,
    load_rich_synthetic_records,
    split_policy_records_by_user_v1,
)
from wellnessbox_rnd.simulation import compare_batch_simulation_modes


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Compare two replay-only policy artifacts on the fixed v4 reshaped cohort"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Rich synthetic longitudinal dataset path",
    )
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument(
        "--effect-artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Replay-only effect artifact path",
    )
    parser.add_argument(
        "--reference-policy-artifact",
        default="artifacts/models/policy_model_v1_uniform.json",
        help="Reference policy artifact path",
    )
    parser.add_argument(
        "--candidate-policy-artifact",
        default="artifacts/models/policy_model_v1_weighted_cgm_threshold_edge_balance_v1.json",
        help="Candidate policy artifact path",
    )
    parser.add_argument(
        "--reference-label",
        default="uniform_policy",
        help="Reference artifact label",
    )
    parser.add_argument(
        "--candidate-label",
        default="weighted_policy",
        help="Candidate artifact label",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/policy_artifact_replay_comparison_v1.json",
        help="Comparison report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/policy_artifact_replay_comparison_v1.md",
        help="Comparison report markdown output path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    records = load_rich_synthetic_records(args.dataset)
    split = split_policy_records_by_user_v1(records, seed=args.seed)

    reference_report = _build_artifact_report(
        label=args.reference_label,
        policy_artifact_path=args.reference_policy_artifact,
        effect_artifact_path=args.effect_artifact,
        dataset_path=args.dataset,
        split=split,
    )
    candidate_report = _build_artifact_report(
        label=args.candidate_label,
        policy_artifact_path=args.candidate_policy_artifact,
        effect_artifact_path=args.effect_artifact,
        dataset_path=args.dataset,
        split=split,
    )
    comparison_report = {
        "dataset_path": str(Path(args.dataset)),
        "seed": args.seed,
        "effect_artifact_path": args.effect_artifact,
        "reference_label": args.reference_label,
        "candidate_label": args.candidate_label,
        "reference": reference_report,
        "candidate": candidate_report,
        "deltas": _build_deltas(
            reference=reference_report,
            candidate=candidate_report,
        ),
    }

    report_json_target = Path(args.report_json)
    report_md_target = Path(args.report_md)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(
        json.dumps(comparison_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(
        render_markdown(comparison_report),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "report_json": str(report_json_target),
                "report_md": str(report_md_target),
                "reference_label": args.reference_label,
                "candidate_label": args.candidate_label,
                "deltas": comparison_report["deltas"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _build_artifact_report(
    *,
    label: str,
    policy_artifact_path: str,
    effect_artifact_path: str,
    dataset_path: str,
    split,
) -> dict[str, object]:
    artifact = load_policy_model_v1_artifact(policy_artifact_path)
    test_metrics = evaluate_policy_model_v1(artifact, split.test).model_dump(mode="json")
    slice_prediction_summaries = build_policy_prediction_slice_summaries_v1(
        artifact,
        train_records=split.train,
        val_records=split.val,
        test_records=split.test,
    )
    replay_report = compare_batch_simulation_modes(
        dataset_path=dataset_path,
        max_cycles=5,
        max_users=96,
        model_artifact_path=effect_artifact_path,
        policy_model_artifact_path=policy_artifact_path,
    )
    replay_modes = {mode.mode_name: mode for mode in replay_report.compared_modes}
    return {
        "label": label,
        "policy_artifact_path": policy_artifact_path,
        "alpha": artifact.alpha,
        "test_metrics": test_metrics,
        "slice_prediction_summaries": {
            "test": slice_prediction_summaries["test"],
        },
        "replay_summary": {
            mode_name: _extract_replay_mode_summary(replay_modes[mode_name])
            for mode_name in (
                "learned_policy_guarded",
                "learned_effect_and_policy_guarded",
            )
        },
    }


def _extract_replay_mode_summary(mode) -> dict[str, object]:
    return {
        "final_policy_action_counts": mode.final_policy_action_counts,
        "low_risk_final_action_distribution": mode.cohort_slice_metrics[
            "low_risk_users"
        ].final_action_distribution,
        "cgm_final_action_distribution": mode.cohort_slice_metrics[
            "cgm_users"
        ].final_action_distribution,
        "low_risk_disagreement_count": mode.cohort_slice_metrics[
            "low_risk_users"
        ].deterministic_vs_learned_disagreement_count,
        "cgm_disagreement_count": mode.cohort_slice_metrics[
            "cgm_users"
        ].deterministic_vs_learned_disagreement_count,
        "policy_effect_override_applied_count": mode.policy_effect_override_applied_count,
    }


def _build_deltas(
    *,
    reference: dict[str, object],
    candidate: dict[str, object],
) -> dict[str, object]:
    return {
        "test_guarded_accuracy_delta": round(
            candidate["test_metrics"]["guarded_accuracy"]
            - reference["test_metrics"]["guarded_accuracy"],
            6,
        ),
        "test_raw_accuracy_delta": round(
            candidate["test_metrics"]["raw_accuracy"]
            - reference["test_metrics"]["raw_accuracy"],
            6,
        ),
        "test_low_risk_cgm_threshold_edge_reoptimize_delta": _action_count_delta(
            reference["slice_prediction_summaries"]["test"]["low_risk_cgm_threshold_edge"][
                "raw_predicted_action_counts"
            ],
            candidate["slice_prediction_summaries"]["test"]["low_risk_cgm_threshold_edge"][
                "raw_predicted_action_counts"
            ],
            "re_optimize",
        ),
        "policy_only_low_risk_monitor_only_delta": _action_count_delta(
            reference["replay_summary"]["learned_policy_guarded"][
                "low_risk_final_action_distribution"
            ],
            candidate["replay_summary"]["learned_policy_guarded"][
                "low_risk_final_action_distribution"
            ],
            "monitor_only",
        ),
        "policy_only_cgm_monitor_only_delta": _action_count_delta(
            reference["replay_summary"]["learned_policy_guarded"][
                "cgm_final_action_distribution"
            ],
            candidate["replay_summary"]["learned_policy_guarded"][
                "cgm_final_action_distribution"
            ],
            "monitor_only",
        ),
        "combined_low_risk_monitor_only_delta": _action_count_delta(
            reference["replay_summary"]["learned_effect_and_policy_guarded"][
                "low_risk_final_action_distribution"
            ],
            candidate["replay_summary"]["learned_effect_and_policy_guarded"][
                "low_risk_final_action_distribution"
            ],
            "monitor_only",
        ),
        "combined_cgm_monitor_only_delta": _action_count_delta(
            reference["replay_summary"]["learned_effect_and_policy_guarded"][
                "cgm_final_action_distribution"
            ],
            candidate["replay_summary"]["learned_effect_and_policy_guarded"][
                "cgm_final_action_distribution"
            ],
            "monitor_only",
        ),
    }


def _action_count_delta(
    reference_counts: dict[str, int],
    candidate_counts: dict[str, int],
    action: str,
) -> int:
    return candidate_counts.get(action, 0) - reference_counts.get(action, 0)


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# policy artifact replay comparison v1",
        "",
        f"- dataset_path: `{report['dataset_path']}`",
        f"- effect_artifact_path: `{report['effect_artifact_path']}`",
        f"- reference_label: `{report['reference_label']}`",
        f"- candidate_label: `{report['candidate_label']}`",
        "",
        "## Deltas",
    ]
    for key, value in report["deltas"].items():
        lines.append(f"- `{key}`: `{value}`")
    for artifact_key in ("reference", "candidate"):
        artifact_report = report[artifact_key]
        lines.extend(
            [
                "",
                f"## {artifact_key.title()}",
                f"- label: `{artifact_report['label']}`",
                f"- policy_artifact_path: `{artifact_report['policy_artifact_path']}`",
                f"- alpha: `{artifact_report['alpha']}`",
                (
                    "- test_metrics: "
                    f"`{artifact_report['test_metrics']}`"
                ),
                (
                    "- test low_risk_cgm_threshold_edge raw predictions: "
                    f"`{artifact_report['slice_prediction_summaries']['test']['low_risk_cgm_threshold_edge']['raw_predicted_action_counts']}`"
                ),
                (
                    "- learned_policy_guarded low-risk final actions: "
                    f"`{artifact_report['replay_summary']['learned_policy_guarded']['low_risk_final_action_distribution']}`"
                ),
                (
                    "- learned_policy_guarded cgm final actions: "
                    f"`{artifact_report['replay_summary']['learned_policy_guarded']['cgm_final_action_distribution']}`"
                ),
                (
                    "- learned_effect_and_policy_guarded low-risk final actions: "
                    f"`{artifact_report['replay_summary']['learned_effect_and_policy_guarded']['low_risk_final_action_distribution']}`"
                ),
                (
                    "- learned_effect_and_policy_guarded cgm final actions: "
                    f"`{artifact_report['replay_summary']['learned_effect_and_policy_guarded']['cgm_final_action_distribution']}`"
                ),
            ]
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
