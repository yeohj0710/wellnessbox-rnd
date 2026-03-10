import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.efficacy_model_v0 import (
    evaluate_efficacy_model,
    fit_efficacy_model,
    load_synthetic_records,
    render_training_report,
    split_records_by_user,
    write_training_outputs,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Train efficacy quantification model v0 on synthetic cohort"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v1.jsonl",
        help="Synthetic longitudinal dataset path",
    )
    parser.add_argument("--seed", type=int, default=20260310)
    parser.add_argument(
        "--artifact",
        default="artifacts/models/efficacy_model_v0.json",
        help="Model artifact JSON path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/efficacy_model_v0_eval.json",
        help="Evaluation report JSON path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/efficacy_model_v0_eval.md",
        help="Evaluation report Markdown path",
    )
    parser.add_argument(
        "--split-json",
        default="artifacts/reports/efficacy_model_v0_splits.json",
        help="Train/val/test split artifact JSON path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    records = load_synthetic_records(args.dataset)
    split = split_records_by_user(records, seed=args.seed)
    artifact, metrics = fit_efficacy_model(split.train, split.val, seed=args.seed)
    test_metrics = evaluate_efficacy_model(artifact, split.test)
    report = render_training_report(
        artifact=artifact,
        split=split,
        train_metrics=metrics["train"],
        val_metrics=metrics["val"],
        test_metrics=test_metrics,
    )
    write_training_outputs(
        artifact=artifact,
        report=report,
        artifact_path=args.artifact,
        report_json_path=args.report_json,
        report_md_path=args.report_md,
        split_json_path=args.split_json,
        split=split,
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.artifact)),
                "report_json": str(Path(args.report_json)),
                "report_md": str(Path(args.report_md)),
                "split_json": str(Path(args.split_json)),
                "test_metrics": report["metrics"]["test"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
