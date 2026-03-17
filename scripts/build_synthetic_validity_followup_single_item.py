from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.synthetic_validity_followup_single_item import (
    build_synthetic_validity_followup_single_item,
    load_json,
    write_synthetic_validity_followup_single_item_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build one minimum-change synthetic-validity follow-up focused on "
            "calibration-target coupling."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )
    parser.add_argument(
        "--synthetic-validity-audit",
        default="artifacts/reports/synthetic_validity_audit_v1.json",
    )
    parser.add_argument(
        "--calibration-dependence-audit",
        default="artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
    )
    parser.add_argument(
        "--partition-validity-audit",
        default="artifacts/reports/dataset_f_partition_validity_audit_v1.json",
    )
    parser.add_argument(
        "--policy-proxy-replay-split-audit",
        default="artifacts/reports/policy_proxy_replay_split_audit_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/synthetic_validity_followup_single_item_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/synthetic_validity_followup_single_item_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_synthetic_validity_followup_single_item(
        dataset_path=args.dataset,
        synthetic_validity_audit=load_json(args.synthetic_validity_audit),
        synthetic_validity_audit_path=args.synthetic_validity_audit,
        calibration_dependence_audit=load_json(args.calibration_dependence_audit),
        calibration_dependence_audit_path=args.calibration_dependence_audit,
        partition_validity_audit=load_json(args.partition_validity_audit),
        partition_validity_audit_path=args.partition_validity_audit,
        policy_proxy_replay_split_audit=load_json(args.policy_proxy_replay_split_audit),
        policy_proxy_replay_split_audit_path=args.policy_proxy_replay_split_audit,
    )
    write_synthetic_validity_followup_single_item_files(
        audit=audit,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "chosen_item": audit["scope"]["chosen_item"],
                "resolution_state": audit["final_disposition"]["resolution_state"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
