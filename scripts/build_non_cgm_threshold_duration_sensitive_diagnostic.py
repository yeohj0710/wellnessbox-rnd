from __future__ import annotations

from argparse import ArgumentParser

from wellnessbox_rnd.evals.non_cgm_threshold_duration_sensitive_diagnostic import (
    build_non_cgm_threshold_duration_sensitive_diagnostic,
    load_json_artifact,
    write_non_cgm_threshold_duration_sensitive_diagnostic_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a bounded replay-only diagnostic for the "
            "threshold_duration_sensitive subgroup inside the current non-CGM "
            "continue-plan to monitor-only blocker."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Synthetic longitudinal dataset path.",
    )
    parser.add_argument(
        "--policy-artifact",
        default="artifacts/models/policy_model_v1.json",
        help="Policy model artifact path.",
    )
    parser.add_argument(
        "--reference-effect-artifact",
        default="artifacts/models/effect_model_v3.json",
        help="Reference effect artifact path.",
    )
    parser.add_argument(
        "--candidate-effect-artifact",
        default=(
            "artifacts/models/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        help="Candidate effect artifact path.",
    )
    parser.add_argument(
        "--narrowing-decision",
        default="artifacts/reports/non_cgm_threshold_cross_narrowing_decision_v1.json",
        help="Current non-CGM narrowing decision JSON path.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=5,
        help="Maximum replay cycles.",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=96,
        help="Maximum replay users.",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.md",
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    diagnostic = build_non_cgm_threshold_duration_sensitive_diagnostic(
        dataset_path=args.dataset,
        max_cycles=args.max_cycles,
        max_users=args.max_users,
        policy_artifact_path=args.policy_artifact,
        reference_effect_artifact_path=args.reference_effect_artifact,
        candidate_effect_artifact_path=args.candidate_effect_artifact,
        narrowing_decision=load_json_artifact(args.narrowing_decision),
        narrowing_decision_path=args.narrowing_decision,
    )
    write_non_cgm_threshold_duration_sensitive_diagnostic_files(
        diagnostic=diagnostic,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
