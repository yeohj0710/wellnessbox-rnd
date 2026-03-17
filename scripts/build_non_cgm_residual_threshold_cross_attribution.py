from __future__ import annotations

from argparse import ArgumentParser

from wellnessbox_rnd.evals.non_cgm_residual_threshold_cross_attribution import (
    build_non_cgm_residual_threshold_cross_attribution,
    load_json_artifact,
    write_non_cgm_residual_threshold_cross_attribution_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only residual attribution report for the remaining "
            "non-CGM continue-plan to monitor-only threshold-cross cases inside "
            "threshold_duration_sensitive / mid_margin / {large_drop, medium_drop}."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Synthetic longitudinal dataset path.",
    )
    parser.add_argument("--max-cycles", type=int, default=5)
    parser.add_argument("--max-users", type=int, default=96)
    parser.add_argument(
        "--policy-artifact",
        default="artifacts/models/policy_model_v1.json",
        help="Fixed replay policy artifact path.",
    )
    parser.add_argument(
        "--reference-effect-artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Reference effect artifact path.",
    )
    parser.add_argument(
        "--candidate-effect-artifact",
        default="artifacts/models/effect_model_v3_training_view_enforced_slice_balanced_candidate.json",
        help="Candidate effect artifact path.",
    )
    parser.add_argument(
        "--family-diagnostic",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
    )
    parser.add_argument(
        "--subgroup-diagnostic",
        default="artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json",
    )
    parser.add_argument(
        "--mid-margin-diagnostic",
        default="artifacts/reports/non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json",
    )
    parser.add_argument(
        "--prior-small-drop-attribution",
        default="artifacts/reports/non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/non_cgm_residual_threshold_cross_attribution_v2.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/non_cgm_residual_threshold_cross_attribution_v2.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_non_cgm_residual_threshold_cross_attribution(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        policy_artifact_path=args.policy_artifact,
        reference_effect_artifact_path=args.reference_effect_artifact,
        candidate_effect_artifact_path=args.candidate_effect_artifact,
        family_diagnostic=load_json_artifact(args.family_diagnostic),
        family_diagnostic_path=args.family_diagnostic,
        subgroup_diagnostic=load_json_artifact(args.subgroup_diagnostic),
        subgroup_diagnostic_path=args.subgroup_diagnostic,
        mid_margin_diagnostic=load_json_artifact(args.mid_margin_diagnostic),
        mid_margin_diagnostic_path=args.mid_margin_diagnostic,
        prior_small_drop_attribution=load_json_artifact(args.prior_small_drop_attribution),
        prior_small_drop_attribution_path=args.prior_small_drop_attribution,
    )
    write_non_cgm_residual_threshold_cross_attribution_files(
        report=report,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
