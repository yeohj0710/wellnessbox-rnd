from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.sensor_genetic_normalization_audit import (
    build_sensor_genetic_normalization_audit,
    load_json_artifact,
    write_sensor_genetic_normalization_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a sensor/genetic/CGM normalization consistency audit "
            "from existing proof artifacts"
        )
    )
    parser.add_argument(
        "--parser-report",
        default="artifacts/reports/sensor_genetic_parser_smoke_v1.json",
        help="Sensor/genetic parser smoke JSON path",
    )
    parser.add_argument(
        "--file-schema-report",
        default="artifacts/reports/sensor_genetic_file_schema_validation_v1.json",
        help="Sensor/genetic file schema validation JSON path",
    )
    parser.add_argument(
        "--cgm-event-report",
        default="artifacts/reports/cgm_normalized_event_bridge_v1.json",
        help="CGM normalized event bridge JSON path",
    )
    parser.add_argument(
        "--cgm-slice-report",
        default="artifacts/reports/cgm_slice_bridge_summary_v1.json",
        help="CGM slice bridge summary JSON path",
    )
    parser.add_argument(
        "--weakest-slice-audit",
        default="artifacts/reports/weakest_slice_frozen_eval_audit_v1.json",
        help="Weakest-slice frozen-eval audit JSON path",
    )
    parser.add_argument(
        "--frozen-eval-dataset",
        default="data/frozen_eval/frozen_eval_v1.jsonl",
        help="Frozen eval JSONL dataset path for category-level join proof",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/sensor_genetic_normalization_audit_v1.json",
        help="Output audit JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/sensor_genetic_normalization_audit_v1.md",
        help="Output audit markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_sensor_genetic_normalization_audit(
        parser_report=load_json_artifact(args.parser_report),
        parser_report_path=args.parser_report,
        file_schema_report=load_json_artifact(args.file_schema_report),
        file_schema_report_path=args.file_schema_report,
        cgm_event_report=load_json_artifact(args.cgm_event_report),
        cgm_event_report_path=args.cgm_event_report,
        cgm_slice_report=load_json_artifact(args.cgm_slice_report),
        cgm_slice_report_path=args.cgm_slice_report,
        weakest_slice_audit=load_json_artifact(args.weakest_slice_audit),
        weakest_slice_audit_path=args.weakest_slice_audit,
        frozen_eval_dataset_path=args.frozen_eval_dataset,
    )
    write_sensor_genetic_normalization_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
