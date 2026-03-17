from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.dataset_f_partition_validity_audit import (
    build_dataset_f_partition_validity_audit,
    load_json,
    write_dataset_f_partition_validity_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Split Dataset F validity into supported effect-enriched versus unsupported "
            "base-clone partitions."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )
    parser.add_argument(
        "--path-safety-audit",
        default="artifacts/reports/dataset_f_path_safety_audit_v2.json",
    )
    parser.add_argument(
        "--calibration-dependence-audit",
        default="artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
    )
    parser.add_argument(
        "--pair-summary",
        default="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/dataset_f_partition_validity_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/dataset_f_partition_validity_audit_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_dataset_f_partition_validity_audit(
        dataset_path=args.dataset,
        path_safety_audit=load_json(args.path_safety_audit),
        path_safety_audit_path=args.path_safety_audit,
        calibration_dependence_audit=load_json(args.calibration_dependence_audit),
        calibration_dependence_audit_path=args.calibration_dependence_audit,
        pair_summary=load_json(args.pair_summary),
        pair_summary_path=args.pair_summary,
    )
    write_dataset_f_partition_validity_audit_files(
        audit=audit,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "verdict": audit["assessment"]["verdict"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
