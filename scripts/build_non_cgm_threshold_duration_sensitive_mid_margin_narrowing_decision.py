from __future__ import annotations

from argparse import ArgumentParser

from wellnessbox_rnd.evals import (
    non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision as narrowing_decision,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a bounded narrowing decision for the proxy-drop buckets inside the "
            "threshold_duration_sensitive mid_margin replay target."
        )
    )
    parser.add_argument(
        "--bucket-diagnostic",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json"
        ),
        help="Current bucket diagnostic JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    build_decision = (
        narrowing_decision.build_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision
    )
    decision = build_decision(
        bucket_diagnostic=narrowing_decision.load_json_artifact(args.bucket_diagnostic),
        bucket_diagnostic_path=args.bucket_diagnostic,
    )
    narrowing_decision.write_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
