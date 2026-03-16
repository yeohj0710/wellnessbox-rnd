from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import (
    NextAction,
    RecommendationResponse,
    RecommendationStatus,
    RuleReference,
    Severity,
)

STRUCTURED_SAFETY_EVIDENCE_EVENT_SCHEMA_VERSION_V1 = "structured_safety_evidence_event_v1"


class StructuredSafetyRuleLinkV1(BaseModel):
    rule_id: str
    severity: Severity
    source: str
    message: str
    reference_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    citation_reference_ids: list[str] = Field(default_factory=list)
    citation_claim_ids: list[str] = Field(default_factory=list)


class StructuredSafetyEvidenceItemV1(BaseModel):
    evidence_type: Literal["rule", "excluded_ingredient", "user_preference"]
    code: str
    summary: str
    reference_ids: list[str] = Field(default_factory=list)


class StructuredSafetyEvidenceEventV1(BaseModel):
    schema_version: str = STRUCTURED_SAFETY_EVIDENCE_EVENT_SCHEMA_VERSION_V1
    request_id: str
    response_status: RecommendationStatus
    safety_status: RecommendationStatus
    next_action: NextAction
    next_action_reason_code: str
    safety_flags: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    rule_links: list[StructuredSafetyRuleLinkV1] = Field(default_factory=list)
    evidence_items: list[StructuredSafetyEvidenceItemV1] = Field(default_factory=list)


def build_structured_safety_evidence_event_v1(
    response: RecommendationResponse,
) -> StructuredSafetyEvidenceEventV1:
    return StructuredSafetyEvidenceEventV1(
        request_id=response.request_id,
        response_status=response.status,
        safety_status=response.safety_summary.status,
        next_action=response.next_action,
        next_action_reason_code=response.next_action_rationale.reason_code,
        safety_flags=list(response.safety_flags),
        blocked_reasons=list(response.safety_summary.blocked_reasons),
        warnings=list(response.safety_summary.warnings),
        excluded_ingredients=list(response.safety_summary.excluded_ingredients),
        rule_links=[
            _build_rule_link(rule_ref)
            for rule_ref in response.safety_summary.rule_refs
        ],
        evidence_items=[
            StructuredSafetyEvidenceItemV1(
                evidence_type=item.evidence_type,
                code=item.code,
                summary=item.summary,
                reference_ids=list(item.reference_ids),
            )
            for item in response.safety_evidence
        ],
    )


def validate_structured_safety_evidence_event_v1(
    event: StructuredSafetyEvidenceEventV1 | dict[str, object],
) -> list[str]:
    model = (
        event
        if isinstance(event, StructuredSafetyEvidenceEventV1)
        else StructuredSafetyEvidenceEventV1.model_validate(event)
    )
    issues: list[str] = []

    rule_ids = [item.rule_id for item in model.rule_links]
    if len(rule_ids) != len(set(rule_ids)):
        issues.append("duplicate_rule_id")

    rule_evidence_by_code = {
        item.code: item
        for item in model.evidence_items
        if item.evidence_type == "rule"
    }
    non_rule_evidence_codes = {
        item.code
        for item in model.evidence_items
        if item.evidence_type != "rule"
    }

    has_blocker_rule = any(rule.severity == Severity.BLOCKER for rule in model.rule_links)
    if model.safety_status == RecommendationStatus.BLOCKED and not (
        has_blocker_rule or model.blocked_reasons
    ):
        issues.append("blocked_without_blocker_rule_or_reason")

    for excluded_ingredient in model.excluded_ingredients:
        if excluded_ingredient not in non_rule_evidence_codes:
            issues.append(f"excluded_ingredient_missing_evidence::{excluded_ingredient}")

    for rule_link in model.rule_links:
        matching_evidence = rule_evidence_by_code.get(rule_link.rule_id)
        if matching_evidence is None:
            issues.append(f"missing_rule_evidence::{rule_link.rule_id}")
        elif sorted(matching_evidence.reference_ids) != sorted(rule_link.reference_ids):
            issues.append(f"rule_evidence_reference_mismatch::{rule_link.rule_id}")

        has_any_reference_payload = bool(rule_link.reference_ids or rule_link.claim_ids)
        has_any_citation_payload = bool(
            rule_link.citation_reference_ids or rule_link.citation_claim_ids
        )

        if rule_link.source == "deterministic_policy":
            if has_any_reference_payload:
                issues.append(f"deterministic_rule_has_reference_payload::{rule_link.rule_id}")
            if has_any_citation_payload:
                issues.append(f"deterministic_rule_has_citation_payload::{rule_link.rule_id}")
            continue

        expects_reference_linkage = (
            rule_link.source == "knowledge_artifact"
            or has_any_reference_payload
            or has_any_citation_payload
        )
        if not expects_reference_linkage:
            continue

        if not rule_link.reference_ids:
            issues.append(f"reference_backed_rule_missing_reference_ids::{rule_link.rule_id}")
        if not rule_link.claim_ids:
            issues.append(f"reference_backed_rule_missing_claim_ids::{rule_link.rule_id}")
        if not rule_link.citation_reference_ids:
            issues.append(f"reference_backed_rule_missing_citation_refs::{rule_link.rule_id}")
        if not rule_link.citation_claim_ids:
            issues.append(f"reference_backed_rule_missing_citation_claims::{rule_link.rule_id}")
        if sorted(set(rule_link.citation_reference_ids)) != sorted(set(rule_link.reference_ids)):
            issues.append(f"citation_reference_mismatch::{rule_link.rule_id}")
        if sorted(set(rule_link.citation_claim_ids)) != sorted(set(rule_link.claim_ids)):
            issues.append(f"citation_claim_mismatch::{rule_link.rule_id}")

    return issues


def summarize_structured_safety_evidence_contract_v1(
    event: StructuredSafetyEvidenceEventV1,
    *,
    request_fixture_path: str | Path,
) -> dict[str, object]:
    issues = validate_structured_safety_evidence_event_v1(event)
    deterministic_rule_count = sum(
        1 for item in event.rule_links if item.source == "deterministic_policy"
    )
    reference_backed_rule_count = sum(
        1
        for item in event.rule_links
        if item.source == "knowledge_artifact"
        or item.reference_ids
        or item.claim_ids
        or item.citation_reference_ids
        or item.citation_claim_ids
    )
    return {
        "contract_id": STRUCTURED_SAFETY_EVIDENCE_EVENT_SCHEMA_VERSION_V1,
        "request_fixture_path": str(request_fixture_path),
        "schema_version": STRUCTURED_SAFETY_EVIDENCE_EVENT_SCHEMA_VERSION_V1,
        "response_status": event.response_status.value,
        "safety_status": event.safety_status.value,
        "next_action": event.next_action.value,
        "next_action_reason_code": event.next_action_reason_code,
        "rule_count": len(event.rule_links),
        "deterministic_rule_count": deterministic_rule_count,
        "reference_backed_rule_count": reference_backed_rule_count,
        "excluded_ingredient_count": len(event.excluded_ingredients),
        "evidence_item_count": len(event.evidence_items),
        "issue_count": len(issues),
        "issues": issues,
        "connected_flows": {
            "safety_determinism": [
                "safety_status",
                "blocked_reasons",
                "warnings",
                "rule_links.severity",
                "rule_links.source",
            ],
            "evidence_linkage": [
                "rule_links.reference_ids",
                "rule_links.claim_ids",
                "rule_links.citation_reference_ids",
                "rule_links.citation_claim_ids",
                "evidence_items.reference_ids",
            ],
            "recommendation_and_follow_up": [
                "response_status",
                "next_action",
                "next_action_reason_code",
            ],
        },
        "kpi_trustworthiness_note": (
            "This contract keeps deterministic safety blockers and citation-backed "
            "knowledge rules structurally separate so safety-reference integrity can "
            "be validated without relaxing runtime precedence."
        ),
        "example_event": event.model_dump(mode="json"),
    }


def write_structured_safety_evidence_contract_report_v1(
    report: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
    output_example_json_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    example_path = Path(output_example_json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    example_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        render_structured_safety_evidence_contract_markdown_v1(report),
        encoding="utf-8",
    )
    example_path.write_text(
        json.dumps(report["example_event"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_structured_safety_evidence_contract_markdown_v1(
    report: dict[str, object],
) -> str:
    lines = [
        "# structured safety evidence contract v1",
        "",
        f"- request_fixture_path: {report['request_fixture_path']}",
        f"- schema_version: {report['schema_version']}",
        f"- response_status: {report['response_status']}",
        f"- safety_status: {report['safety_status']}",
        f"- next_action: {report['next_action']}",
        f"- next_action_reason_code: {report['next_action_reason_code']}",
        f"- rule_count: {report['rule_count']}",
        f"- deterministic_rule_count: {report['deterministic_rule_count']}",
        f"- reference_backed_rule_count: {report['reference_backed_rule_count']}",
        f"- excluded_ingredient_count: {report['excluded_ingredient_count']}",
        f"- evidence_item_count: {report['evidence_item_count']}",
        f"- issue_count: {report['issue_count']}",
        "",
        "## connected flows",
        "",
    ]
    for flow_name, fields in report["connected_flows"].items():
        lines.append(f"- {flow_name}: {', '.join(fields)}")

    example_event = report["example_event"]
    lines.extend(
        [
            "",
            "## KPI trustworthiness note",
            "",
            f"- {report['kpi_trustworthiness_note']}",
            "",
            "## validation",
            "",
            f"- issues: {report['issues']}",
            "",
            "## example event preview",
            "",
            f"- rule_ids: {[item['rule_id'] for item in example_event['rule_links']]}",
            f"- evidence_codes: {[item['code'] for item in example_event['evidence_items']]}",
            f"- excluded_ingredients: {example_event['excluded_ingredients']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _build_rule_link(rule_ref: RuleReference) -> StructuredSafetyRuleLinkV1:
    return StructuredSafetyRuleLinkV1(
        rule_id=rule_ref.rule_id,
        severity=rule_ref.severity,
        source=rule_ref.source,
        message=rule_ref.message,
        reference_ids=list(rule_ref.reference_ids),
        claim_ids=list(rule_ref.claim_ids),
        citation_reference_ids=[item.reference_id for item in rule_ref.citations],
        citation_claim_ids=[
            item.claim_id
            for item in rule_ref.citations
            if item.claim_id is not None
        ],
    )


__all__ = [
    "STRUCTURED_SAFETY_EVIDENCE_EVENT_SCHEMA_VERSION_V1",
    "StructuredSafetyEvidenceEventV1",
    "StructuredSafetyEvidenceItemV1",
    "StructuredSafetyRuleLinkV1",
    "build_structured_safety_evidence_event_v1",
    "render_structured_safety_evidence_contract_markdown_v1",
    "summarize_structured_safety_evidence_contract_v1",
    "validate_structured_safety_evidence_event_v1",
    "write_structured_safety_evidence_contract_report_v1",
]
