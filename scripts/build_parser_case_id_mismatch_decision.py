from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.parser_case_id_mismatch_decision import (
    build_parser_case_id_mismatch_decision,
    load_json_artifact,
    write_parser_case_id_mismatch_decision_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a decision artifact for whether the remaining parser sample-fixture "
            "vs frozen-eval case-id mismatch still blocks KPI interpretation."
        )
    )
    parser.add_argument(
        "--parser-report",
        default="artifacts/reports/sensor_genetic_parser_smoke_v1.json",
        help="Sensor/genetic parser smoke JSON path",
    )
    parser.add_argument(
        "--normalization-audit",
        default="artifacts/reports/sensor_genetic_normalization_audit_v1.json",
        help="Sensor/genetic normalization audit JSON path",
    )
    parser.add_argument(
        "--weakest-slice-summary",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
        help="Weakest-slice summary JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/parser_case_id_mismatch_decision_v1.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/parser_case_id_mismatch_decision_v1.md",
        help="Output markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = build_parser_case_id_mismatch_decision(
        parser_report=load_json_artifact(args.parser_report),
        parser_report_path=args.parser_report,
        normalization_audit=load_json_artifact(args.normalization_audit),
        normalization_audit_path=args.normalization_audit,
        weakest_slice_summary=load_json_artifact(args.weakest_slice_summary),
        weakest_slice_summary_path=args.weakest_slice_summary,
    )
    write_parser_case_id_mismatch_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
