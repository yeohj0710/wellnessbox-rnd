from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.domain.sensor_parser import normalize_sensor_genetic_payloads
from wellnessbox_rnd.schemas import (
    build_cgm_normalized_event_v1,
    summarize_cgm_slice_bridge_v1,
    write_cgm_slice_bridge_report_v1,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build CGM slice bridge summary from parser cases")
    parser.add_argument(
        "--cases-json",
        default="data/samples/sensor_genetic_parser_cases_v1.json",
        help="Sensor/genetic parser cases JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/cgm_slice_bridge_summary_v1.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/cgm_slice_bridge_summary_v1.md",
        help="Output markdown report path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cases = json.loads(Path(args.cases_json).read_text(encoding="utf-8"))
    cgm_case_ids: list[str] = []
    cgm_events = []
    for case in cases:
        cgm_payload = case.get("cgm_payload")
        if not cgm_payload:
            continue
        snapshot = normalize_sensor_genetic_payloads(cgm_payload=cgm_payload)
        cgm_case_ids.append(case["case_id"])
        cgm_events.append(build_cgm_normalized_event_v1(snapshot))

    report = summarize_cgm_slice_bridge_v1(
        cgm_events,
        source_cases_path=args.cases_json,
        case_ids=cgm_case_ids,
    )
    write_cgm_slice_bridge_report_v1(
        report,
        output_json_path=args.report_json,
        output_md_path=args.report_md,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys_exit(main())
