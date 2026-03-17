from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.weakest_slice_audit import (
    build_weakest_slice_frozen_eval_audit,
    load_json_artifact,
    write_weakest_slice_frozen_eval_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a weakest-slice frozen-eval-compatible audit from "
            "existing proof artifacts"
        )
    )
    parser.add_argument(
        "--eval-report",
        default="artifacts/reports/full_eval_harness_with_compare_v1/eval_report.json",
        help="Frozen eval report JSON path with weakest_slice_summary",
    )
    parser.add_argument(
        "--pro-report",
        default="artifacts/reports/pro_scoring_contract_v1.json",
        help="PRO scoring contract JSON path",
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
        "--followup-report",
        default="artifacts/reports/followup_transition_event_contract_v1.json",
        help="Follow-up transition contract JSON path",
    )
    parser.add_argument(
        "--next-action-report",
        default="artifacts/reports/next_action_workflow_contract_v1.json",
        help="Next-action workflow contract JSON path",
    )
    parser.add_argument(
        "--next-action-blocked-report",
        default="artifacts/reports/next_action_workflow_collect_more_input_contract_v1.json",
        help="Blocked collect-more-input workflow contract JSON path",
    )
    parser.add_argument(
        "--safety-report",
        default="artifacts/reports/structured_safety_evidence_contract_v1.json",
        help="Structured safety evidence contract JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/weakest_slice_frozen_eval_audit_v1.json",
        help="Output audit JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/weakest_slice_frozen_eval_audit_v1.md",
        help="Output audit markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_weakest_slice_frozen_eval_audit(
        eval_report=load_json_artifact(args.eval_report),
        eval_report_path=args.eval_report,
        pro_report=load_json_artifact(args.pro_report),
        pro_report_path=args.pro_report,
        parser_report=load_json_artifact(args.parser_report),
        parser_report_path=args.parser_report,
        file_schema_report=load_json_artifact(args.file_schema_report),
        file_schema_report_path=args.file_schema_report,
        cgm_event_report=load_json_artifact(args.cgm_event_report),
        cgm_event_report_path=args.cgm_event_report,
        cgm_slice_report=load_json_artifact(args.cgm_slice_report),
        cgm_slice_report_path=args.cgm_slice_report,
        followup_report=load_json_artifact(args.followup_report),
        followup_report_path=args.followup_report,
        next_action_report=load_json_artifact(args.next_action_report),
        next_action_report_path=args.next_action_report,
        next_action_blocked_report=load_json_artifact(args.next_action_blocked_report),
        next_action_blocked_report_path=args.next_action_blocked_report,
        safety_report=load_json_artifact(args.safety_report),
        safety_report_path=args.safety_report,
    )
    write_weakest_slice_frozen_eval_audit_files(
        audit,
        output_json_path=args.report_json,
        output_md_path=args.report_md,
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
