from argparse import ArgumentParser
from pathlib import Path

from wellnessbox_rnd.evals.report_compare import (
    compare_eval_reports,
    load_eval_report,
    write_eval_report_comparison_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Compare two eval_report.json files")
    parser.add_argument(
        "--baseline-report",
        default="artifacts/reports/current_loop_final_eval/eval_report.json",
        help="Baseline eval_report.json path",
    )
    parser.add_argument(
        "--candidate-report",
        default="artifacts/reports/full_eval_harness_progress_v1/eval_report.json",
        help="Candidate eval_report.json path",
    )
    parser.add_argument(
        "--output-json",
        default="artifacts/reports/eval_report_comparison_v1.json",
        help="Output comparison JSON path",
    )
    parser.add_argument(
        "--output-md",
        default="artifacts/reports/eval_report_comparison_v1.md",
        help="Output comparison markdown path",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    baseline_report = load_eval_report(args.baseline_report)
    candidate_report = load_eval_report(args.candidate_report)
    comparison = compare_eval_reports(
        baseline_report,
        candidate_report,
        baseline_report_path=args.baseline_report,
        candidate_report_path=args.candidate_report,
    )
    write_eval_report_comparison_files(
        comparison,
        output_json_path=Path(args.output_json),
        output_md_path=Path(args.output_md),
    )
    print(f"JSON comparison: {args.output_json}")
    print(f"Markdown comparison: {args.output_md}")


if __name__ == "__main__":
    main()
