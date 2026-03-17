from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.policy_proxy_calibration_dependence_audit import (
    build_policy_proxy_calibration_dependence_audit,
    load_effect_model_v1_artifact,
    load_json,
    write_policy_proxy_calibration_dependence_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Measure how much effect-model policy-proxy fit still depends on calibration "
            "against generator-produced expected_effect_proxy."
        )
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )
    parser.add_argument(
        "--split-manifest",
        default="artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json",
    )
    parser.add_argument(
        "--baseline-artifact",
        default="artifacts/models/effect_model_v3.json",
    )
    parser.add_argument(
        "--candidate-artifact",
        default="artifacts/models/effect_model_v3_training_view_enforced_slice_balanced_candidate.json",
    )
    parser.add_argument(
        "--candidate-eval-report",
        default="artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_eval.json",
    )
    parser.add_argument(
        "--candidate-feature-schema",
        default="artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/policy_proxy_calibration_dependence_audit_v1.md",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_policy_proxy_calibration_dependence_audit(
        dataset_path=args.dataset,
        split_manifest=load_json(args.split_manifest),
        split_manifest_path=args.split_manifest,
        baseline_artifact=load_effect_model_v1_artifact(args.baseline_artifact),
        baseline_artifact_path=args.baseline_artifact,
        candidate_artifact=load_effect_model_v1_artifact(args.candidate_artifact),
        candidate_artifact_path=args.candidate_artifact,
        candidate_eval_report=load_json(args.candidate_eval_report),
        candidate_eval_report_path=args.candidate_eval_report,
        candidate_feature_schema=load_json(args.candidate_feature_schema),
        candidate_feature_schema_path=args.candidate_feature_schema,
    )
    write_policy_proxy_calibration_dependence_audit_files(
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
