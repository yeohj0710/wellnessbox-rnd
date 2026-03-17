from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.evals.kpi_candidate_summary import (
    build_kpi_candidate_summary,
    load_json,
    write_kpi_candidate_summary_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a compact readable summary across baseline KPI reference, "
            "candidate deltas, and weakest-slice audit context"
        )
    )
    parser.add_argument(
        "--baseline-eval-report",
        default="artifacts/reports/full_eval_harness_with_compare_v1/eval_report.json",
    )
    parser.add_argument(
        "--candidate-compare-report",
        default="artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_replay_compare_vs_baseline_v1.json",
    )
    parser.add_argument(
        "--weakest-slice-summary",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/baseline_candidate_kpi_summary_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/baseline_candidate_kpi_summary_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = build_kpi_candidate_summary(
        baseline_eval_report=load_json(args.baseline_eval_report),
        baseline_eval_report_path=args.baseline_eval_report,
        candidate_compare_report=load_json(args.candidate_compare_report),
        candidate_compare_report_path=args.candidate_compare_report,
        weakest_slice_summary=load_json(args.weakest_slice_summary),
        weakest_slice_summary_path=args.weakest_slice_summary,
    )
    write_kpi_candidate_summary_files(
        summary,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "decision": summary["adoption_summary"]["decision"],
                "conclusion": summary["adoption_summary"]["one_line_conclusion"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
