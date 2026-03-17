from __future__ import annotations

from argparse import ArgumentParser

from wellnessbox_rnd.evals.non_cgm_threshold_duration_sensitive_narrowing_decision import (
    build_non_cgm_threshold_duration_sensitive_narrowing_decision,
    load_json_artifact,
    write_non_cgm_threshold_duration_sensitive_narrowing_decision_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a bounded narrowing decision for the threshold_duration_sensitive "
            "subgroup inside the current non-CGM replay blocker."
        )
    )
    parser.add_argument(
        "--subgroup-diagnostic",
        default="artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json",
        help="Current subgroup diagnostic JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_narrowing_decision_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_narrowing_decision_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = build_non_cgm_threshold_duration_sensitive_narrowing_decision(
        subgroup_diagnostic=load_json_artifact(args.subgroup_diagnostic),
        subgroup_diagnostic_path=args.subgroup_diagnostic,
    )
    write_non_cgm_threshold_duration_sensitive_narrowing_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
