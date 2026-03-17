from __future__ import annotations

import json
from argparse import ArgumentParser

from wellnessbox_rnd.evals.next_action_state_machine_audit import (
    build_next_action_state_machine_audit,
    load_json_artifact,
    write_next_action_state_machine_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build an audit comparing follow-up transition states and "
            "next-action workflow states"
        )
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
        "--report-json",
        default="artifacts/reports/next_action_state_machine_audit_v1.json",
        help="Output audit JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/next_action_state_machine_audit_v1.md",
        help="Output audit markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_next_action_state_machine_audit(
        followup_report=load_json_artifact(args.followup_report),
        followup_report_path=args.followup_report,
        next_action_report=load_json_artifact(args.next_action_report),
        next_action_report_path=args.next_action_report,
    )
    write_next_action_state_machine_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
