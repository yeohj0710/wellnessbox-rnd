from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.dataset_f_baseline_identical_signal_audit import (
    build_dataset_f_baseline_identical_signal_audit,
    load_json,
    write_dataset_f_baseline_identical_signal_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Audit whether Dataset F still carries baseline-identical learned-signal risk "
            "using existing replay, feature-schema, split-hygiene, and data-quality artifacts"
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
        "--data-quality-report",
        default="artifacts/reports/dataset_f_data_quality_v1.json",
    )
    parser.add_argument(
        "--feature-schema",
        default="artifacts/reports/effect_model_v3_training_view_enforced_heterogeneity_candidate_feature_schema.json",
    )
    parser.add_argument(
        "--pair-summary",
        default="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
    )
    parser.add_argument(
        "--split-manifest",
        default="artifacts/reports/dataset_f_effect_prepost_pairs_split_manifest_v1.json",
    )
    parser.add_argument(
        "--replay-compare-report",
        default="artifacts/reports/effect_model_v3_training_view_enforced_heterogeneity_candidate_replay_compare_vs_baseline_v1.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_dataset_f_baseline_identical_signal_audit(
        dataset_path=args.dataset,
        path_safety_audit=load_json(args.path_safety_audit),
        path_safety_audit_path=args.path_safety_audit,
        data_quality_report=load_json(args.data_quality_report),
        data_quality_report_path=args.data_quality_report,
        feature_schema=load_json(args.feature_schema),
        feature_schema_path=args.feature_schema,
        pair_summary=load_json(args.pair_summary),
        pair_summary_path=args.pair_summary,
        split_manifest=load_json(args.split_manifest),
        split_manifest_path=args.split_manifest,
        replay_compare_report=load_json(args.replay_compare_report),
        replay_compare_report_path=args.replay_compare_report,
    )
    write_dataset_f_baseline_identical_signal_audit_files(
        audit=audit,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "verdict": audit["baseline_identical_signal_assessment"]["verdict"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
