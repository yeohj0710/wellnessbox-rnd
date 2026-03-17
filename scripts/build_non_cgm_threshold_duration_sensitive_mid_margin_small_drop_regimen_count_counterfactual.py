from __future__ import annotations

from argparse import ArgumentParser
from importlib import import_module

counterfactual_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_counterfactual"
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a replay-only regimen_count counterfactual inside the "
            "threshold_duration_sensitive mid_margin small_drop target."
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
        "--regimen-count-diagnostic",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_diagnostic_v1.json"
        ),
        help="Current regimen_count diagnostic JSON path.",
    )
    parser.add_argument(
        "--report-json",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_counterfactual_v1.json"
        ),
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--report-md",
        default=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_counterfactual_v1.md"
        ),
        help="Output markdown report path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    counterfactual = counterfactual_module.build_regimen_count_counterfactual(
        slice_diagnostic=counterfactual_module.load_json_artifact(args.slice_diagnostic),
        regimen_count_diagnostic=counterfactual_module.load_json_artifact(
            args.regimen_count_diagnostic
        ),
        regimen_count_diagnostic_path=args.regimen_count_diagnostic,
        slice_diagnostic_path=args.slice_diagnostic,
    )
    counterfactual_module.write_regimen_count_counterfactual_files(
        counterfactual=counterfactual,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
