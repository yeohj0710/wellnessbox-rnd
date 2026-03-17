from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

diagnostic_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_status_summary_diagnostic"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only family diagnostic for regimen_status_summary inside "
            "the threshold_duration_sensitive mid_margin small_drop target."
        )
    )
    parser.add_argument(
        "--slice-diagnostic",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        help="Current small-drop slice diagnostic JSON path.",
    )
    parser.add_argument(
        "--family-decision",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_v1.json"
        ),
        help="Current family narrowing decision JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_diagnostic_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_diagnostic_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    diagnostic = diagnostic_module.build_regimen_status_summary_diagnostic(
        slice_diagnostic=diagnostic_module.load_json_artifact(args.slice_diagnostic),
        slice_diagnostic_path=args.slice_diagnostic,
        family_decision=diagnostic_module.load_json_artifact(args.family_decision),
        family_decision_path=args.family_decision,
    )
    diagnostic_module.write_regimen_status_summary_diagnostic_files(
        diagnostic=diagnostic,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
