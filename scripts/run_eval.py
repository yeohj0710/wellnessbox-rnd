from argparse import ArgumentParser
from pathlib import Path

from wellnessbox_rnd.evals.runner import run_eval, write_eval_outputs


def main() -> None:
    parser = ArgumentParser(description="Run frozen eval for wellnessbox-rnd")
    parser.add_argument(
        "--dataset",
        default="data/frozen_eval/frozen_eval_v1.jsonl",
        help="Path to JSONL eval dataset",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/reports",
        help="Directory for JSON and Markdown reports",
    )
    parser.add_argument(
        "--compare-to-report",
        default=None,
        help="Optional baseline eval_report.json path for same-command comparison output",
    )
    parser.add_argument(
        "--comparison-output-json",
        default=None,
        help="Optional output path for comparison JSON; defaults under output-dir",
    )
    parser.add_argument(
        "--comparison-output-md",
        default=None,
        help="Optional output path for comparison markdown; defaults under output-dir",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    report = run_eval(args.dataset)
    outputs = write_eval_outputs(
        report=report,
        output_dir=output_dir,
        compare_to_report=args.compare_to_report,
        comparison_output_json=args.comparison_output_json,
        comparison_output_md=args.comparison_output_md,
    )

    print(f"JSON report: {outputs['eval_report_json']}")
    print(f"Markdown report: {outputs['eval_report_md']}")
    if "eval_report_comparison_json" in outputs:
        print(f"JSON comparison: {outputs['eval_report_comparison_json']}")
        print(f"Markdown comparison: {outputs['eval_report_comparison_md']}")


if __name__ == "__main__":
    main()
