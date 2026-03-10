import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.policy import (
    build_policy_training_rows,
    evaluate_policy_model,
    fit_policy_model,
    render_policy_training_report,
    split_policy_records_by_user,
    write_policy_training_outputs,
)
from wellnessbox_rnd.training import load_synthetic_records


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Train the synthetic next-action policy model v0")
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v1.jsonl",
        help="Synthetic longitudinal dataset path",
    )
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument(
        "--artifact-path",
        default="artifacts/models/policy_model_v0.json",
        help="Model artifact output path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/policy_model_v0_eval.json",
        help="Evaluation report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/policy_model_v0_eval.md",
        help="Evaluation report markdown output path",
    )
    parser.add_argument(
        "--split-json",
        default="artifacts/reports/policy_model_v0_splits.json",
        help="Split output path",
    )
    parser.add_argument(
        "--policy-dataset-output",
        default="data/synthetic/policy_training_v0.jsonl",
        help="Flattened policy training dataset JSONL output path",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    records = load_synthetic_records(args.dataset)
    split = split_policy_records_by_user(records, seed=args.seed)
    policy_rows = build_policy_training_rows(records)
    artifact, metrics_by_split = fit_policy_model(split.train, split.val, seed=args.seed)
    test_metrics = evaluate_policy_model(artifact, split.test)
    report = render_policy_training_report(
        artifact=artifact,
        split=split,
        train_metrics=metrics_by_split["train"],
        val_metrics=metrics_by_split["val"],
        test_metrics=test_metrics,
        test_records=split.test,
    )
    write_policy_training_outputs(
        artifact=artifact,
        report=report,
        policy_rows=policy_rows,
        artifact_path=args.artifact_path,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
        split_json_path=args.split_json,
        dataset_jsonl_path=args.policy_dataset_output,
        split=split,
    )
    print(
        json.dumps(
            {
                "dataset": str(Path(args.dataset)),
                "artifact_path": args.artifact_path,
                "report_json": args.report_json,
                "report_md": args.report_md,
                "split_json": args.split_json,
                "policy_dataset_output": args.policy_dataset_output,
                "class_labels": artifact.class_labels,
                "feature_count": len(artifact.feature_names),
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
