import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.ingestion import (
    ingest_reference_directory,
    summarize_ingestion,
    validate_knowledge_artifact,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Ingest raw markdown references into structured knowledge artifacts"
    )
    parser.add_argument(
        "--input-dir",
        default="data/raw_references",
        help="Directory that contains raw markdown reference files",
    )
    parser.add_argument(
        "--claims-output",
        default="data/parsed_references/reference_claims_v1.jsonl",
        help="Structured parsed claims JSONL output path",
    )
    parser.add_argument(
        "--knowledge-output",
        default="data/knowledge/reference_knowledge_base_v1.json",
        help="Knowledge base JSON output path",
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/reference_ingestion_v1_summary.json",
        help="Summary report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/reference_ingestion_v1_summary.md",
        help="Summary report markdown output path",
    )
    return parser


def render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# reference ingestion summary",
        "",
        f"- artifact_version: `{summary['artifact_version']}`",
        f"- reference_count: `{summary['reference_count']}`",
        f"- claim_count: `{summary['claim_count']}`",
        f"- rule_candidate_count: `{summary['rule_candidate_count']}`",
        f"- ingredient_domain_evidence_count: `{summary['ingredient_domain_evidence_count']}`",
        "",
        "## Source Types",
    ]
    for key, value in summary["source_type_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Claim Types"])
    for key, value in summary["normalized_claim_type_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Rule Types"])
    for key, value in summary["rule_type_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Ingredients"])
    for key, value in summary["ingredient_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Medications"])
    for key, value in summary["medication_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    artifact = ingest_reference_directory(args.input_dir)
    issues = validate_knowledge_artifact(artifact)
    if issues:
        print(json.dumps({"issues": issues}, ensure_ascii=False, indent=2))
        return 1

    summary = summarize_ingestion(artifact)

    claims_output = Path(args.claims_output)
    knowledge_output = Path(args.knowledge_output)
    report_json = Path(args.report_json)
    report_md = Path(args.report_md)
    claims_output.parent.mkdir(parents=True, exist_ok=True)
    knowledge_output.parent.mkdir(parents=True, exist_ok=True)
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)

    claims_output.write_text(
        "\n".join(
            claim.model_dump_json()
            for claim in artifact.parsed_claims
        )
        + "\n",
        encoding="utf-8",
    )
    knowledge_output.write_text(
        artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_json.write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )
    report_md.write_text(
        render_markdown(summary.model_dump(mode="json")),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "claims_output": str(claims_output),
                "knowledge_output": str(knowledge_output),
                "report_json": str(report_json),
                "report_md": str(report_md),
                "reference_count": summary.reference_count,
                "claim_count": summary.claim_count,
                "rule_candidate_count": summary.rule_candidate_count,
                "ingredient_domain_evidence_count": summary.ingredient_domain_evidence_count,
                "issues": [],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys_exit(main())
