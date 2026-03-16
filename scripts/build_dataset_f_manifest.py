import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.training.effect_model_v1 import (
    build_effect_dataset_manifest_v1,
    build_effect_dataset_split_manifest_v1,
    load_rich_effect_records,
    render_effect_dataset_manifest_markdown_v1,
    split_effect_records_by_user_v1,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build Dataset F effect pre/post manifest and split artifact"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Dataset F source dataset path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260311,
        help="Deterministic user-level split seed",
    )
    parser.add_argument(
        "--manifest-json",
        default="artifacts/reports/dataset_f_effect_prepost_manifest_v1.json",
        help="Dataset manifest JSON path",
    )
    parser.add_argument(
        "--manifest-md",
        default="artifacts/reports/dataset_f_effect_prepost_manifest_v1.md",
        help="Dataset manifest markdown path",
    )
    parser.add_argument(
        "--split-json",
        default="artifacts/reports/dataset_f_effect_prepost_split_manifest_v1.json",
        help="Dataset split manifest JSON path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    records = load_rich_effect_records(args.dataset)
    split = split_effect_records_by_user_v1(records, seed=args.seed)
    split_manifest = build_effect_dataset_split_manifest_v1(split, seed=args.seed)
    manifest = build_effect_dataset_manifest_v1(
        records,
        dataset_path=args.dataset,
        seed=args.seed,
        split_manifest_path=args.split_json,
    )

    manifest_json_path = Path(args.manifest_json)
    manifest_md_path = Path(args.manifest_md)
    split_json_path = Path(args.split_json)
    for path in (manifest_json_path, manifest_md_path, split_json_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    manifest_json_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest_md_path.write_text(
        render_effect_dataset_manifest_markdown_v1(manifest),
        encoding="utf-8",
    )
    split_json_path.write_text(
        json.dumps(split_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "dataset_path": str(Path(args.dataset)),
                "case_count": manifest["case_count"],
                "user_count": manifest["user_count"],
                "split_record_counts": {
                    split_name: summary["record_count"]
                    for split_name, summary in manifest["split_summary"].items()
                },
                "manifest_json": str(manifest_json_path),
                "manifest_md": str(manifest_md_path),
                "split_json": str(split_json_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
