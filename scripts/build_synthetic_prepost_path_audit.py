from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.synthetic_prepost_path_audit import (
    build_synthetic_prepost_path_audit,
    load_json,
    write_synthetic_prepost_path_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Audit the current synthetic pre/post Dataset F path for leakage, circularity, "
            "baseline-identical label risk, generator contamination, and frozen-eval contamination"
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )
    parser.add_argument(
        "--pair-dataset",
        default="artifacts/datasets/dataset_f_effect_prepost_pairs_v1.jsonl",
    )
    parser.add_argument(
        "--path-safety-audit",
        default="artifacts/reports/dataset_f_path_safety_audit_v2.json",
    )
    parser.add_argument(
        "--baseline-identical-audit",
        default="artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json",
    )
    parser.add_argument(
        "--partition-validity-audit",
        default="artifacts/reports/dataset_f_partition_validity_audit_v1.json",
    )
    parser.add_argument(
        "--design-sanity-audit",
        default="artifacts/reports/design_sanity_audit_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/synthetic_prepost_path_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/synthetic_prepost_path_audit_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_synthetic_prepost_path_audit(
        dataset_path=args.dataset,
        pair_dataset_path=args.pair_dataset,
        path_safety_audit=load_json(args.path_safety_audit),
        path_safety_audit_path=args.path_safety_audit,
        baseline_identical_audit=load_json(args.baseline_identical_audit),
        baseline_identical_audit_path=args.baseline_identical_audit,
        partition_validity_audit=load_json(args.partition_validity_audit),
        partition_validity_audit_path=args.partition_validity_audit,
        design_sanity_audit=load_json(args.design_sanity_audit),
        design_sanity_audit_path=args.design_sanity_audit,
    )
    write_synthetic_prepost_path_audit_files(
        audit=audit,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "verdict": audit["overall_assessment"]["verdict"],
                "principal_blocker": audit["evidence_snapshot"]["principal_blocker"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
