import csv
import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.domain.sensor_parser import (
    normalize_sensor_genetic_payloads,
    validate_cgm_summary_csv_schema,
)
from wellnessbox_rnd.schemas.cgm_events import (
    build_cgm_normalized_event_v1,
    summarize_cgm_normalized_event_bridge_v1,
    write_cgm_normalized_event_bridge_report_v1,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build normalized CGM event bridge artifact")
    parser.add_argument(
        "--cgm-csv",
        default="data/samples/cgm_summary_v1.csv",
        help="CGM summary CSV fixture path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/cgm_normalized_event_bridge_v1.json",
        help="Output JSON report path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/cgm_normalized_event_bridge_v1.md",
        help="Output markdown report path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    csv_text = Path(args.cgm_csv).read_text(encoding="utf-8")
    schema_result = validate_cgm_summary_csv_schema(csv_text)
    if not schema_result.passed:
        raise SystemExit(f"CGM CSV fixture failed schema validation: {schema_result.failure_types}")
    row = next(csv.DictReader(csv_text.splitlines()))
    snapshot = normalize_sensor_genetic_payloads(cgm_payload=row)
    event = build_cgm_normalized_event_v1(snapshot)
    report = summarize_cgm_normalized_event_bridge_v1(event, source_fixture_path=args.cgm_csv)
    write_cgm_normalized_event_bridge_report_v1(
        report,
        output_json_path=args.report_json,
        output_md_path=args.report_md,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys_exit(main())
