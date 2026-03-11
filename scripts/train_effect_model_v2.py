import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.effect_model_v1 import (
    build_effect_feature_schema_v1,
    evaluate_effect_model_v1,
    fit_effect_model_v1,
    load_rich_effect_records,
    render_effect_training_report_v1,
    split_effect_records_by_user_v1,
    write_effect_training_outputs_v1,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Train effect model v2 on rich synthetic cohort v3")
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v3.jsonl",
        help="Rich synthetic longitudinal v3 dataset path",
    )
    parser.add_argument("--seed", type=int, default=20260311)
    parser.add_argument(
        "--artifact",
        default="artifacts/models/effect_model_v2.json",
        help="Model artifact JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/effect_model_v2_eval.json",
        help="Evaluation report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/effect_model_v2_eval.md",
        help="Evaluation report markdown path",
    )
    parser.add_argument(
        "--split-json",
        default="artifacts/reports/effect_model_v2_splits.json",
        help="Train/val/test split artifact JSON path",
    )
    parser.add_argument(
        "--feature-schema-json",
        default="artifacts/reports/effect_model_v2_feature_schema.json",
        help="Feature schema JSON path",
    )
    parser.add_argument(
        "--feature-schema-md",
        default="artifacts/reports/effect_model_v2_feature_schema.md",
        help="Feature schema markdown path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    records = load_rich_effect_records(args.dataset)
    split = split_effect_records_by_user_v1(records, seed=args.seed)
    artifact, metrics = fit_effect_model_v1(split.train, split.val, seed=args.seed)
    artifact = artifact.model_copy(
        update={
            "model_name": "effect_model_v2",
            "cohort_version": records[0].cohort_version if records else artifact.cohort_version,
        }
    )
    test_metrics = evaluate_effect_model_v1(artifact, split.test)
    report = render_effect_training_report_v1(
        artifact=artifact,
        split=split,
        train_metrics=metrics["train"],
        val_metrics=metrics["val"],
        test_metrics=test_metrics,
        test_records=split.test,
    )
    feature_schema = build_effect_feature_schema_v1(artifact)
    write_effect_training_outputs_v1(
        artifact=artifact,
        report=report,
        feature_schema=feature_schema,
        artifact_path=args.artifact,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
        split_json_path=args.split_json,
        feature_schema_json_path=args.feature_schema_json,
        feature_schema_md_path=args.feature_schema_md,
        split=split,
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.artifact)),
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "split_json": str(Path(args.split_json)),
                "feature_schema_json": str(Path(args.feature_schema_json)),
                "feature_schema_md": str(Path(args.feature_schema_md)),
                "test_metrics": report["metrics"]["test"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
