import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Build a deterministic Dataset F effect training prep contract"
    )
    parser.add_argument(
        "--dataset",
        default="data/synthetic/synthetic_longitudinal_v4.jsonl",
        help="Source Dataset F path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260311,
        help="Deterministic training split seed",
    )
    parser.add_argument(
        "--source-split-manifest",
        default="artifacts/reports/dataset_f_effect_prepost_split_manifest_v1.json",
        help="Pinned source split manifest path",
    )
    parser.add_argument(
        "--artifact",
        default="artifacts/models/effect_model_v3_trainprep_candidate.json",
        help="Candidate artifact output path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/effect_model_v3_trainprep_candidate_eval.json",
        help="Candidate eval JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/effect_model_v3_trainprep_candidate_eval.md",
        help="Candidate eval markdown output path",
    )
    parser.add_argument(
        "--split-json",
        default="artifacts/reports/effect_model_v3_trainprep_candidate_splits.json",
        help="Candidate split output path",
    )
    parser.add_argument(
        "--feature-schema-json",
        default="artifacts/reports/effect_model_v3_trainprep_candidate_feature_schema.json",
        help="Candidate feature schema JSON path",
    )
    parser.add_argument(
        "--feature-schema-md",
        default="artifacts/reports/effect_model_v3_trainprep_candidate_feature_schema.md",
        help="Candidate feature schema markdown path",
    )
    parser.add_argument(
        "--contract-json",
        default="artifacts/reports/effect_model_v3_trainprep_contract_v1.json",
        help="Training prep contract JSON path",
    )
    parser.add_argument(
        "--contract-md",
        default="artifacts/reports/effect_model_v3_trainprep_contract_v1.md",
        help="Training prep contract markdown path",
    )
    return parser


def _render_markdown(contract: dict[str, object]) -> str:
    lines = [
        "# effect model v3 train prep contract",
        "",
        f"- entrypoint: `{contract['entrypoint']}`",
        f"- dataset: `{contract['dataset']}`",
        f"- seed: `{contract['seed']}`",
        f"- source_split_manifest: `{contract['source_split_manifest']}`",
        "",
        "## Candidate Outputs",
    ]
    for key, value in contract["candidate_outputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Validation"])
    for command in contract["validation_commands"]:
        lines.append(f"- `{command}`")
    lines.extend(["", "## Train Command"])
    lines.append(f"- `{contract['train_command']}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = build_parser().parse_args()
    candidate_outputs = {
        "artifact": args.artifact,
        "report_json": args.report_json,
        "report_md": args.report_md,
        "split_json": args.split_json,
        "feature_schema_json": args.feature_schema_json,
        "feature_schema_md": args.feature_schema_md,
    }
    train_command = (
        "python scripts/train_effect_model_v3.py "
        f"--dataset {args.dataset} "
        f"--seed {args.seed} "
        f"--artifact {args.artifact} "
        f"--report-json {args.report_json} "
        f"--report-md {args.report_md} "
        f"--split-json {args.split_json} "
        f"--feature-schema-json {args.feature_schema_json} "
        f"--feature-schema-md {args.feature_schema_md}"
    )
    contract = {
        "entrypoint": "scripts/train_effect_model_v3.py",
        "dataset": args.dataset,
        "seed": args.seed,
        "source_split_manifest": args.source_split_manifest,
        "candidate_outputs": candidate_outputs,
        "validation_commands": [
            "python -m pytest tests/test_effect_model_v1.py -q",
            (
                "python -m ruff check scripts/train_effect_model_v3.py "
                "scripts/build_effect_training_prep_contract.py "
                "src/wellnessbox_rnd/training/effect_model_v1.py "
                "tests/test_effect_model_v1.py"
            ),
        ],
        "train_command": train_command,
    }

    contract_json_path = Path(args.contract_json)
    contract_md_path = Path(args.contract_md)
    for path in (contract_json_path, contract_md_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    contract_json_path.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    contract_md_path.write_text(_render_markdown(contract), encoding="utf-8")
    print(json.dumps(contract, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys_exit(main())
