import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.dataset_f_data_quality import (
    build_dataset_f_data_quality_report,
    write_dataset_f_data_quality_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build a compact Dataset F data-quality report for synthetic_longitudinal_v4"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Dataset F source dataset path",
    )
    parser.add_argument(
        "--manifest-json",
        default="artifacts/reports/dataset_f_effect_prepost_manifest_v1.json",
        help="Existing Dataset F manifest JSON path",
    )
    parser.add_argument(
        "--pair-summary-json",
        default="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
        help="Existing Dataset F pair summary JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/dataset_f_data_quality_v1.json",
        help="Output report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/dataset_f_data_quality_v1.md",
        help="Output report markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_dataset_f_data_quality_report(
        dataset_path=args.dataset,
        manifest_path=args.manifest_json,
        pair_summary_path=args.pair_summary_json,
    )
    write_dataset_f_data_quality_files(
        report=report,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "case_count": report["dataset_summary"]["case_count"],
                "weakest_slice": report["overall_assessment"]["weakest_slice"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
