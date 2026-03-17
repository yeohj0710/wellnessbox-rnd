from __future__ import annotations

from argparse import ArgumentParser

from wellnessbox_rnd.evals import (
    non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic as small_drop_diagnostic,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only before-state diagnostic for the small_drop slice "
            "inside the threshold_duration_sensitive mid_margin non-CGM target."
        )
    )
    parser.add_argument(
        "--dataset-path",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Synthetic dataset path.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=5,
        help="Maximum closed-loop cycles to simulate.",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=96,
        help="Maximum users to simulate from the dataset.",
    )
    parser.add_argument(
        "--policy-artifact",
        default="artifacts/models/policy_model_v1.json",
        help="Deterministic policy artifact path.",
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
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_v1.json"
        ),
        help="Current mid-margin narrowing decision JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    diagnostic = (
        small_drop_diagnostic.build_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic(
            dataset_path=args.dataset_path,
            max_cycles=args.max_cycles,
            max_users=args.max_users,
            policy_artifact_path=args.policy_artifact,
            reference_effect_artifact_path=args.reference_effect_artifact,
            candidate_effect_artifact_path=args.candidate_effect_artifact,
            narrowing_decision=small_drop_diagnostic.load_json_artifact(
                args.narrowing_decision
            ),
            narrowing_decision_path=args.narrowing_decision,
        )
    )
    small_drop_diagnostic.write_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_files(
        diagnostic=diagnostic,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
