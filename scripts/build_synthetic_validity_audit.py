from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.synthetic_validity_audit import (
    build_synthetic_validity_audit,
    load_json,
    write_synthetic_validity_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Build a narrow synthetic-validity audit for circularity, generator contamination, "
            "and calibration-target coupling on Dataset F."
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
        "--baseline-identical-audit",
        default="artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json",
    )
    parser.add_argument(
        "--partition-validity-audit",
        default="artifacts/reports/dataset_f_partition_validity_audit_v1.json",
    )
    parser.add_argument(
        "--calibration-dependence-audit",
        default="artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
    )
    parser.add_argument(
        "--synthetic-prepost-audit",
        default="artifacts/reports/synthetic_prepost_path_audit_v1.json",
    )
    parser.add_argument(
        "--feature-schema",
        default="artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json",
    )
    parser.add_argument(
        "--split-manifest",
        default="artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/synthetic_validity_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/synthetic_validity_audit_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_synthetic_validity_audit(
        dataset_path=args.dataset,
        path_safety_audit=load_json(args.path_safety_audit),
        path_safety_audit_path=args.path_safety_audit,
        baseline_identical_audit=load_json(args.baseline_identical_audit),
        baseline_identical_audit_path=args.baseline_identical_audit,
        partition_validity_audit=load_json(args.partition_validity_audit),
        partition_validity_audit_path=args.partition_validity_audit,
        calibration_dependence_audit=load_json(args.calibration_dependence_audit),
        calibration_dependence_audit_path=args.calibration_dependence_audit,
        synthetic_prepost_audit=load_json(args.synthetic_prepost_audit),
        synthetic_prepost_audit_path=args.synthetic_prepost_audit,
        feature_schema=load_json(args.feature_schema),
        feature_schema_path=args.feature_schema,
        split_manifest=load_json(args.split_manifest),
        split_manifest_path=args.split_manifest,
    )
    write_synthetic_validity_audit_files(
        audit=audit,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "verdict": audit["go_no_go_memo"]["verdict"],
                "training_rerun_justified_now": audit["go_no_go_memo"][
                    "training_rerun_justified_now"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
