import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.metrics.pro_scoring import (
    summarize_pro_form_contract_v1,
    write_pro_form_contract_report_v1,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build deterministic PRO scoring contract artifact")
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Rich synthetic longitudinal dataset path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/pro_scoring_contract_v1.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/pro_scoring_contract_v1.md",
        help="Output markdown report path",
    )
    return parser


def _load_records(dataset_path: str | Path) -> list[RichSyntheticCohortRecord]:
    rows: list[RichSyntheticCohortRecord] = []
    for line in Path(dataset_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(RichSyntheticCohortRecord.model_validate_json(line))
    return rows


def main() -> int:
    args = build_parser().parse_args()
    records = _load_records(args.dataset)
    report = summarize_pro_form_contract_v1(records, dataset_path=args.dataset)
    write_pro_form_contract_report_v1(
        report,
        output_json_path=args.report_json,
        output_md_path=args.report_md,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys_exit(main())
