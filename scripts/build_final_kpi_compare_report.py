from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.final_kpi_compare_report import (
    build_final_kpi_compare_report,
    load_json,
    write_final_kpi_compare_report_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build a readable final compare artifact for baseline, candidate, and slices."
    )
    parser.add_argument(
        "--baseline-candidate-summary",
        default="artifacts/reports/baseline_candidate_kpi_summary_v1.json",
    )
    parser.add_argument(
        "--weakest-slice-summary",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
    )
    parser.add_argument(
        "--core-kpi-path-summary",
        default="artifacts/reports/core_kpi_path_summary_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/final_kpi_compare_report_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/final_kpi_compare_report_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_final_kpi_compare_report(
        baseline_candidate_summary=load_json(args.baseline_candidate_summary),
        baseline_candidate_summary_path=args.baseline_candidate_summary,
        weakest_slice_summary=load_json(args.weakest_slice_summary),
        weakest_slice_summary_path=args.weakest_slice_summary,
        core_kpi_path_summary=load_json(args.core_kpi_path_summary),
        core_kpi_path_summary_path=args.core_kpi_path_summary,
    )
    write_final_kpi_compare_report_files(
        report,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
