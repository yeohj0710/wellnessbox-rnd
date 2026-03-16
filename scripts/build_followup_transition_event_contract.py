import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.schemas.followup_events import (
    summarize_followup_transition_event_contract_v1,
    write_followup_transition_event_contract_report_v1,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build follow-up transition event contract artifact")
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Synthetic longitudinal dataset path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/followup_transition_event_contract_v1.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/followup_transition_event_contract_v1.md",
        help="Output markdown report path",
    )
    parser.add_argument(
        "--example-json",
        default="artifacts/reports/followup_transition_event_example_v1.json",
        help="Output example event path",
    )
    return parser


def _load_records(dataset_path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in Path(dataset_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    args = build_parser().parse_args()
    records = _load_records(args.dataset)
    report = summarize_followup_transition_event_contract_v1(
        records,
        dataset_path=args.dataset,
    )
    write_followup_transition_event_contract_report_v1(
        report,
        output_json_path=args.report_json,
        output_md_path=args.report_md,
        output_example_json_path=args.example_json,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys_exit(main())
