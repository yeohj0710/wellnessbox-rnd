from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.structured_safety_rule_overlap_decision import (
    build_structured_safety_rule_overlap_decision,
    load_json_artifact,
    write_structured_safety_rule_overlap_decision_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a decision artifact for whether the remaining partial structured-safety "
            "rule-family overlap still blocks KPI interpretation."
        )
    )
    parser.add_argument(
        "--weakest-slice-audit",
        default="artifacts/reports/weakest_slice_frozen_eval_audit_v1.json",
        help="Weakest-slice audit JSON path",
    )
    parser.add_argument(
        "--weakest-slice-summary",
        default="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
        help="Weakest-slice summary JSON path",
    )
    parser.add_argument(
        "--eval-report",
        default="artifacts/reports/full_eval_harness_with_compare_v1/eval_report.json",
        help="Frozen-eval report JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/structured_safety_rule_overlap_decision_v1.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/structured_safety_rule_overlap_decision_v1.md",
        help="Output markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = build_structured_safety_rule_overlap_decision(
        weakest_slice_audit=load_json_artifact(args.weakest_slice_audit),
        weakest_slice_audit_path=args.weakest_slice_audit,
        weakest_slice_summary=load_json_artifact(args.weakest_slice_summary),
        weakest_slice_summary_path=args.weakest_slice_summary,
        eval_report=load_json_artifact(args.eval_report),
        eval_report_path=args.eval_report,
    )
    write_structured_safety_rule_overlap_decision_files(
        decision=decision,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
