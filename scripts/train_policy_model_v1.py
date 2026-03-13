import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.policy import (
    DEFAULT_SAMPLE_WEIGHT_PROFILE_V1,
    build_policy_feature_schema_v1,
    build_policy_prediction_slice_summaries_v1,
    build_policy_training_rows_v1,
    evaluate_policy_model_v1,
    fit_policy_model_v1,
    load_rich_synthetic_records,
    render_policy_training_report_v1,
    split_policy_records_by_user_v1,
    summarize_policy_sample_weights_v1,
    write_policy_training_outputs_v1,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Train the synthetic next-action policy model v1 on rich synthetic cohort v4"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Rich synthetic longitudinal dataset path",
    )
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument(
        "--sample-weight-profile",
        default=DEFAULT_SAMPLE_WEIGHT_PROFILE_V1,
        help="Deterministic policy sample-weight profile",
    )
    parser.add_argument(
        "--artifact-path",
        default="artifacts/models/policy_model_v1.json",
        help="Model artifact output path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/policy_model_v1_eval.json",
        help="Evaluation report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/policy_model_v1_eval.md",
        help="Evaluation report markdown output path",
    )
    parser.add_argument(
        "--split-json",
        default="artifacts/reports/policy_model_v1_splits.json",
        help="Split output path",
    )
    parser.add_argument(
        "--policy-dataset-output",
        default="data/synthetic/policy_training_v1_from_v4.jsonl",
        help="Flattened policy training dataset JSONL output path",
    )
    parser.add_argument(
        "--feature-schema-json",
        default="artifacts/reports/policy_model_v1_feature_schema.json",
        help="Feature schema JSON output path",
    )
    parser.add_argument(
        "--feature-schema-md",
        default="artifacts/reports/policy_model_v1_feature_schema.md",
        help="Feature schema markdown output path",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    records = load_rich_synthetic_records(args.dataset)
    split = split_policy_records_by_user_v1(records, seed=args.seed)
    policy_rows = build_policy_training_rows_v1(records)
    artifact, metrics_by_split = fit_policy_model_v1(
        split.train,
        split.val,
        seed=args.seed,
        sample_weight_profile=args.sample_weight_profile,
    )
    test_metrics = evaluate_policy_model_v1(artifact, split.test)
    sample_weight_summary = summarize_policy_sample_weights_v1(
        split.train,
        profile=args.sample_weight_profile,
    )
    slice_prediction_summaries = build_policy_prediction_slice_summaries_v1(
        artifact,
        train_records=split.train,
        val_records=split.val,
        test_records=split.test,
    )
    report = render_policy_training_report_v1(
        artifact=artifact,
        split=split,
        train_metrics=metrics_by_split["train"],
        val_metrics=metrics_by_split["val"],
        test_metrics=test_metrics,
        test_records=split.test,
        sample_weight_profile=args.sample_weight_profile,
        sample_weight_summary=sample_weight_summary,
        slice_prediction_summaries=slice_prediction_summaries,
    )
    feature_schema = build_policy_feature_schema_v1(artifact)
    write_policy_training_outputs_v1(
        artifact=artifact,
        report=report,
        feature_schema=feature_schema,
        policy_rows=policy_rows,
        artifact_path=args.artifact_path,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
        split_json_path=args.split_json,
        dataset_jsonl_path=args.policy_dataset_output,
        feature_schema_json_path=args.feature_schema_json,
        feature_schema_md_path=args.feature_schema_md,
        split=split,
    )
    print(
        json.dumps(
            {
                "dataset": str(Path(args.dataset)),
                "artifact_path": args.artifact_path,
                "sample_weight_profile": args.sample_weight_profile,
                "report_json": args.report_json,
                "report_md": args.report_md,
                "split_json": args.split_json,
                "policy_dataset_output": args.policy_dataset_output,
                "feature_schema_json": args.feature_schema_json,
                "feature_schema_md": args.feature_schema_md,
                "class_labels": artifact.class_labels,
                "feature_count": len(artifact.feature_names),
                "sample_weight_summary": sample_weight_summary,
                "slice_prediction_summaries": slice_prediction_summaries,
                "train_metrics": metrics_by_split["train"].model_dump(mode="json"),
                "val_metrics": metrics_by_split["val"].model_dump(mode="json"),
                "test_metrics": test_metrics.model_dump(mode="json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
