from argparse import ArgumentParser
from pathlib import Path

from wellnessbox_rnd.evals.runner import run_eval, write_report_files


def main() -> None:
    parser = ArgumentParser(description="Run frozen eval for wellnessbox-rnd")
    parser.add_argument(
        "--dataset",
        default="data/frozen_eval/sample_cases.jsonl",
        help="Path to JSONL eval dataset",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/reports",
        help="Directory for JSON and Markdown reports",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    report = run_eval(args.dataset)
    json_path = output_dir / "eval_report.json"
    md_path = output_dir / "eval_report.md"
    write_report_files(report, json_path, md_path)

    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()

