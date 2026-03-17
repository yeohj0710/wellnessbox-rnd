from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

narrowing_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "regimen_status_summary_narrowing_decision"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only narrowing decision for the regimen_status_summary "
            "family inside the threshold_duration_sensitive mid_margin small_drop target."
        )
    )
    parser.add_argument(
        "--family-diagnostic",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_diagnostic_v1.json"
        ),
        help="Current family diagnostic JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_narrowing_decision_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_narrowing_decision_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = narrowing_module.build_regimen_status_summary_narrowing_decision(
        family_diagnostic=narrowing_module.load_json_artifact(args.family_diagnostic),
        family_diagnostic_path=args.family_diagnostic,
    )
    narrowing_module.write_regimen_status_summary_narrowing_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
