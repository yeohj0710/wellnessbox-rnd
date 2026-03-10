from __future__ import annotations

import json

from wellnessbox_rnd.domain.loaders import repo_root
from wellnessbox_rnd.knowledge.runtime_db import (
    build_runtime_knowledge_db,
    validate_runtime_knowledge_db,
)


def main() -> None:
    runtime_db = build_runtime_knowledge_db()
    issues = validate_runtime_knowledge_db(runtime_db)
    if issues:
        raise SystemExit(f"runtime knowledge db validation failed: {issues}")

    root = repo_root()
    output_path = root / "data" / "knowledge" / "runtime_knowledge_db_v1.json"
    summary_json_path = root / "artifacts" / "reports" / "runtime_knowledge_db_v1_summary.json"
    summary_md_path = root / "artifacts" / "reports" / "runtime_knowledge_db_v1_summary.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(runtime_db.model_dump_json(indent=2), encoding="utf-8")

    summary = {
        "artifact_version": runtime_db.artifact_version,
        "source_reference_artifact_version": runtime_db.source_reference_artifact_version,
        "counts": {
            "ingredients": len(runtime_db.ingredients),
            "ingredient_aliases": len(runtime_db.ingredient_aliases),
            "medications": len(runtime_db.medications),
            "conditions": len(runtime_db.conditions),
            "interaction_rules": len(runtime_db.interaction_rules),
            "contraindication_rules": len(runtime_db.contraindication_rules),
            "dose_limits": len(runtime_db.dose_limits),
            "ingredient_domain_scores": len(runtime_db.ingredient_domain_scores),
            "references": len(runtime_db.references),
            "reference_spans": len(runtime_db.reference_spans),
            "workflow_policies": len(runtime_db.workflow_policies),
        },
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(_build_markdown_summary(summary), encoding="utf-8")

    print(f"Runtime knowledge DB: {output_path}")
    print(f"Summary JSON: {summary_json_path}")
    print(f"Summary Markdown: {summary_md_path}")


def _build_markdown_summary(summary: dict[str, object]) -> str:
    counts = summary["counts"]
    lines = [
        "# Runtime Knowledge DB Summary",
        "",
        f"- artifact_version: `{summary['artifact_version']}`",
        f"- source_reference_artifact_version: `{summary['source_reference_artifact_version']}`",
        "",
        "## Table counts",
        "",
    ]
    for key, value in counts.items():
        lines.append(f"- `{key}` = {value}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
