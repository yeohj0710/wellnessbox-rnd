import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.effect_model_v1 import (
    build_effect_dataset_pair_split_manifest_v1,
    build_effect_dataset_pairs_v1,
    load_rich_effect_records,
    render_effect_dataset_pairs_markdown_v1,
    summarize_effect_dataset_pairs_v1,
    validate_effect_dataset_pairs_v1,
    write_effect_dataset_pairs_jsonl_v1,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build Dataset F synthetic pre/post pair dataset and split manifest"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Source rich synthetic longitudinal dataset path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260311,
        help="Deterministic user-level split seed",
    )
    parser.add_argument(
        "--pairs-jsonl",
        default="artifacts/datasets/dataset_f_effect_prepost_pairs_v1.jsonl",
        help="Output pair dataset JSONL path",
    )
    parser.add_argument(
        "--summary-json",
        default="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
        help="Output summary JSON path",
    )
    parser.add_argument(
        "--summary-md",
        default="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.md",
        help="Output summary markdown path",
    )
    parser.add_argument(
        "--split-json",
        default="artifacts/reports/dataset_f_effect_prepost_pairs_split_manifest_v1.json",
        help="Output split manifest JSON path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    records = load_rich_effect_records(args.dataset)
    rows = build_effect_dataset_pairs_v1(records)
    issues = validate_effect_dataset_pairs_v1(rows)
    if issues:
        print(json.dumps({"status": "validation_failed", "issues": issues}, indent=2))
        return 1

    summary = summarize_effect_dataset_pairs_v1(
        rows,
        dataset_path=args.pairs_jsonl,
        split_manifest_path=args.split_json,
        seed=args.seed,
    )
    split_manifest = build_effect_dataset_pair_split_manifest_v1(rows, seed=args.seed)

    pairs_jsonl_path = Path(args.pairs_jsonl)
    summary_json_path = Path(args.summary_json)
    summary_md_path = Path(args.summary_md)
    split_json_path = Path(args.split_json)
    for path in (pairs_jsonl_path, summary_json_path, summary_md_path, split_json_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    write_effect_dataset_pairs_jsonl_v1(pairs_jsonl_path, rows)
    summary_json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_md_path.write_text(
        render_effect_dataset_pairs_markdown_v1(summary),
        encoding="utf-8",
    )
    split_json_path.write_text(
        json.dumps(split_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "pairs_jsonl": str(pairs_jsonl_path),
                "case_count": summary["case_count"],
                "schema_top_level_keys": list(summary["schema_key_coverage_pct"]["top_level"]),
                "split_summary": summary["split_summary"],
                "summary_json": str(summary_json_path),
                "summary_md": str(summary_md_path),
                "split_json": str(split_json_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
