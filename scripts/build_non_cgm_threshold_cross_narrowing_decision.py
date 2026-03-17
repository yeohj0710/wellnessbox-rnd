from __future__ import annotations

from argparse import ArgumentParser

from wellnessbox_rnd.evals.non_cgm_threshold_cross_narrowing_decision import (
    build_non_cgm_threshold_cross_narrowing_decision,
    load_json_artifact,
    write_non_cgm_threshold_cross_narrowing_decision_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a bounded narrowing decision for the non-cgm continue-plan "
            "to monitor-only replay blocker."
        )
    )
    parser.add_argument(
        "--non-cgm-diagnostic",
        default=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        help="Current non-CGM threshold-cross diagnostic JSON path.",
    )
    parser.add_argument(
        "--reject-decision",
        default="artifacts/reports/latest_effect_candidate_reject_decision_v1.json",
        help="Latest candidate reject decision JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/non_cgm_threshold_cross_narrowing_decision_v1.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/non_cgm_threshold_cross_narrowing_decision_v1.md",
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = build_non_cgm_threshold_cross_narrowing_decision(
        non_cgm_diagnostic=load_json_artifact(args.non_cgm_diagnostic),
        non_cgm_diagnostic_path=args.non_cgm_diagnostic,
        reject_decision=load_json_artifact(args.reject_decision),
        reject_decision_path=args.reject_decision,
    )
    write_non_cgm_threshold_cross_narrowing_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
