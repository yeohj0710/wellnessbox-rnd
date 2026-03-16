from __future__ import annotations

import json
from argparse import ArgumentParser
from pathlib import Path
from sys import exit as sys_exit

from wellnessbox_rnd.knowledge.runtime_db import (
    build_citations_for_rule,
    build_runtime_knowledge_db,
    validate_runtime_knowledge_db,
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description=(
            "Audit runtime structured rule/reference linkage and deterministic "
            "reference boundaries without changing behavior"
        )
    )
    parser.add_argument(
        "--report-json",
        default="artifacts/reports/runtime_rule_reference_linkage_audit_v1.json",
        help="Audit report JSON output path",
    )
    parser.add_argument(
        "--report-md",
        default="artifacts/reports/runtime_rule_reference_linkage_audit_v1.md",
        help="Audit report markdown output path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    runtime_db = build_runtime_knowledge_db()
    validation_issues = validate_runtime_knowledge_db(runtime_db)

    knowledge_interaction_summary = _audit_knowledge_items(
        runtime_db=runtime_db,
        label="interaction_rules",
        items=[
            rule
            for rule in runtime_db.interaction_rules
            if rule.source_kind == "knowledge_artifact"
        ],
    )
    workflow_policy_summary = _audit_knowledge_items(
        runtime_db=runtime_db,
        label="workflow_policies",
        items=[
            policy
            for policy in runtime_db.workflow_policies
            if policy.source_kind == "knowledge_artifact"
        ],
    )
    ingredient_domain_summary = _audit_reference_backed_items(
        runtime_db=runtime_db,
        label="ingredient_domain_scores",
        items=runtime_db.ingredient_domain_scores,
    )
    deterministic_boundary_summary = _audit_deterministic_boundary(runtime_db)

    report = {
        "artifact_version": runtime_db.artifact_version,
        "source_reference_artifact_version": runtime_db.source_reference_artifact_version,
        "runtime_db_validation_issues": validation_issues,
        "runtime_db_table_counts": {
            "interaction_rules": len(runtime_db.interaction_rules),
            "contraindication_rules": len(runtime_db.contraindication_rules),
            "dose_limits": len(runtime_db.dose_limits),
            "ingredient_domain_scores": len(runtime_db.ingredient_domain_scores),
            "references": len(runtime_db.references),
            "reference_spans": len(runtime_db.reference_spans),
            "workflow_policies": len(runtime_db.workflow_policies),
        },
        "knowledge_linkage_summary": {
            "interaction_rules": knowledge_interaction_summary,
            "workflow_policies": workflow_policy_summary,
            "ingredient_domain_scores": ingredient_domain_summary,
        },
        "deterministic_boundary_summary": deterministic_boundary_summary,
        "overall_status": (
            "pass"
            if not validation_issues
            and not knowledge_interaction_summary["items_missing_citations"]
            and not workflow_policy_summary["items_missing_citations"]
            and not ingredient_domain_summary["items_missing_reference_or_claim_ids"]
            and not deterministic_boundary_summary["unexpected_reference_payload_items"]
            else "investigate"
        ),
    }

    report_json_target = Path(args.report_json)
    report_md_target = Path(args.report_md)
    report_json_target.parent.mkdir(parents=True, exist_ok=True)
    report_md_target.parent.mkdir(parents=True, exist_ok=True)
    report_json_target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_md_target.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_json": str(report_json_target),
                "report_md": str(report_md_target),
                "overall_status": report["overall_status"],
                "validation_issue_count": len(validation_issues),
                "unexpected_reference_payload_item_count": len(
                    deterministic_boundary_summary["unexpected_reference_payload_items"]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _audit_knowledge_items(*, runtime_db, label: str, items: list[object]) -> dict[str, object]:
    items_missing_reference_or_claim_ids: list[str] = []
    items_missing_citations: list[str] = []
    items_with_citations: list[dict[str, object]] = []

    for item in items:
        if not getattr(item, "reference_ids", []) or not getattr(item, "claim_ids", []):
            items_missing_reference_or_claim_ids.append(item.rule_id)
            continue
        citations = build_citations_for_rule(
            runtime_db,
            reference_ids=item.reference_ids,
            claim_ids=item.claim_ids,
        )
        if not citations:
            items_missing_citations.append(item.rule_id)
            continue
        items_with_citations.append(
            {
                "item_id": item.rule_id,
                "reference_ids": item.reference_ids,
                "claim_ids": item.claim_ids,
                "citation_count": len(citations),
            }
        )

    return {
        "label": label,
        "item_count": len(items),
        "items_missing_reference_or_claim_ids": items_missing_reference_or_claim_ids,
        "items_missing_citations": items_missing_citations,
        "items_with_citations": items_with_citations,
    }


def _audit_reference_backed_items(
    *,
    runtime_db,
    label: str,
    items: list[object],
) -> dict[str, object]:
    items_missing_reference_or_claim_ids: list[str] = []
    citation_samples: list[dict[str, object]] = []
    for item in items:
        item_id = getattr(item, "ingredient_key", "unknown")
        if not getattr(item, "reference_ids", []) or not getattr(item, "claim_ids", []):
            items_missing_reference_or_claim_ids.append(item_id)
            continue
        citations = build_citations_for_rule(
            runtime_db,
            reference_ids=item.reference_ids,
            claim_ids=item.claim_ids,
        )
        citation_samples.append(
            {
                "item_id": item_id,
                "reference_id_count": len(item.reference_ids),
                "claim_id_count": len(item.claim_ids),
                "citation_count": len(citations),
            }
        )

    return {
        "label": label,
        "item_count": len(items),
        "items_missing_reference_or_claim_ids": items_missing_reference_or_claim_ids,
        "citation_samples": citation_samples,
    }


def _audit_deterministic_boundary(runtime_db) -> dict[str, object]:
    deterministic_items = (
        list(
            rule
            for rule in runtime_db.interaction_rules
            if rule.source_kind == "deterministic_policy"
        )
        + runtime_db.contraindication_rules
        + runtime_db.dose_limits
    )
    unexpected_reference_payload_items: list[dict[str, object]] = []
    for item in deterministic_items:
        if getattr(item, "reference_ids", []) or getattr(item, "claim_ids", []):
            unexpected_reference_payload_items.append(
                {
                    "item_id": getattr(item, "rule_id", "unknown"),
                    "reference_ids": getattr(item, "reference_ids", []),
                    "claim_ids": getattr(item, "claim_ids", []),
                }
            )

    return {
        "deterministic_item_count": len(deterministic_items),
        "dose_limit_count": len(runtime_db.dose_limits),
        "contraindication_rule_count": len(runtime_db.contraindication_rules),
        "deterministic_interaction_rule_count": sum(
            1
            for rule in runtime_db.interaction_rules
            if rule.source_kind == "deterministic_policy"
        ),
        "unexpected_reference_payload_items": unexpected_reference_payload_items,
    }


def render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# runtime rule/reference linkage audit v1",
        "",
        f"- artifact_version: `{report['artifact_version']}`",
        (
            "- source_reference_artifact_version: "
            f"`{report['source_reference_artifact_version']}`"
        ),
        f"- overall_status: `{report['overall_status']}`",
        (
            "- runtime_db_validation_issues: "
            f"`{report['runtime_db_validation_issues']}`"
        ),
        f"- runtime_db_table_counts: `{report['runtime_db_table_counts']}`",
        "",
        "## Knowledge linkage summary",
        "",
    ]
    for key, summary in report["knowledge_linkage_summary"].items():
        lines.extend(
            [
                f"### {key}",
                f"- item_count: `{summary['item_count']}`",
                (
                    "- items_missing_reference_or_claim_ids: "
                    f"`{summary['items_missing_reference_or_claim_ids']}`"
                ),
            ]
        )
        if "items_missing_citations" in summary:
            lines.append(
                "- items_missing_citations: "
                f"`{summary['items_missing_citations']}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Deterministic boundary summary",
            "",
            (
                "- deterministic_boundary_summary: "
                f"`{report['deterministic_boundary_summary']}`"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys_exit(main())
