import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.dataset_f_path_safety_audit import (
    build_dataset_f_path_safety_audit,
    write_dataset_f_path_safety_audit_files,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build a minimal safety audit for the current Dataset F synthetic path"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Dataset F synthetic source dataset path",
    )
    parser.add_argument(
        "--pair-summary-json",
        default="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
        help="Dataset F pair summary JSON path",
    )
    parser.add_argument(
        "--feature-schema-json",
        default="artifacts/reports/effect_model_v3_training_view_enforced_candidate_feature_schema.json",
        help="Current training-view-enforced feature schema JSON path",
    )
    parser.add_argument(
        "--eval-report-json",
        default="artifacts/reports/effect_model_v3_training_view_enforced_candidate_eval.json",
        help="Current training-view-enforced eval report JSON path",
    )
    parser.add_argument(
        "--frozen-eval-dataset",
        default="data/frozen_eval/frozen_eval_v1.jsonl",
        help="Frozen eval dataset path used for contamination checks",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/dataset_f_path_safety_audit_v2.json",
        help="Output audit JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/dataset_f_path_safety_audit_v2.md",
        help="Output audit markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    audit = build_dataset_f_path_safety_audit(
        dataset_path=args.dataset,
        pair_summary_path=args.pair_summary_json,
        feature_schema_path=args.feature_schema_json,
        eval_report_path=args.eval_report_json,
        frozen_eval_dataset_path=args.frozen_eval_dataset,
    )
    write_dataset_f_path_safety_audit_files(
        audit=audit,
        json_path=args.report_json,
        md_path=args.report_md,
    )
    print(
        json.dumps(
            {
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "highest_risk_family": audit["overall_assessment"]["highest_risk_family"],
                "case_count": audit["dataset_summary"]["case_count"],
                "user_count": audit["dataset_summary"]["user_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
