from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

narrowing_decision = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a bounded narrowing decision for the small_drop slice inside the "
            "threshold_duration_sensitive mid_margin replay target."
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
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = (
        narrowing_decision.build_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision(
            slice_diagnostic=narrowing_decision.load_json_artifact(args.slice_diagnostic),
            slice_diagnostic_path=args.slice_diagnostic,
        )
    )
    narrowing_decision.write_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
