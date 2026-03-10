from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ReferenceMetadata(BaseModel):
    reference_id: str
    source_title: str
    source_type: str
    page_or_section: str
    reference_uri: str


class CitationSpan(BaseModel):
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    excerpt: str = Field(min_length=1)


class RawRuleCandidate(BaseModel):
    rule_id: str
    rule_type: str
    severity: str
    if_clause: dict[str, Any] = Field(default_factory=dict, alias="if")
    then_clause: dict[str, Any] = Field(default_factory=dict, alias="then")


class RawReferenceClaim(BaseModel):
    claim_id: str
    claim_text: str
    normalized_claim_type: str
    rule_candidate: RawRuleCandidate | None = None
    ingredient_keys: list[str] = Field(default_factory=list)
    medication_keys: list[str] = Field(default_factory=list)
    domain_keys: list[str] = Field(default_factory=list)


class ParsedReferenceClaim(BaseModel):
    reference_id: str
    source_title: str
    source_type: str
    page_or_section: str
    reference_uri: str
    claim_id: str
    claim_text: str
    normalized_claim_type: str
    citation_span: CitationSpan
    ingredient_keys: list[str] = Field(default_factory=list)
    medication_keys: list[str] = Field(default_factory=list)
    domain_keys: list[str] = Field(default_factory=list)


class RuleCandidate(BaseModel):
    rule_id: str
    rule_type: str
    severity: str
    if_clause: dict[str, Any] = Field(default_factory=dict)
    then_clause: dict[str, Any] = Field(default_factory=dict)
    reference_id: str
    claim_id: str
    citation_span: CitationSpan


class IngredientDomainEvidence(BaseModel):
    ingredient_key: str
    domain_key: str
    claim_ids: list[str] = Field(default_factory=list)
    reference_ids: list[str] = Field(default_factory=list)
    medication_keys: list[str] = Field(default_factory=list)
    normalized_claim_types: list[str] = Field(default_factory=list)


class KnowledgeBaseArtifact(BaseModel):
    artifact_version: str = "reference_knowledge_base_v1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    references: list[ReferenceMetadata]
    parsed_claims: list[ParsedReferenceClaim]
    rule_candidates: list[RuleCandidate]
    ingredient_domain_evidence: list[IngredientDomainEvidence]


class IngestionSummary(BaseModel):
    artifact_version: str = "reference_knowledge_base_v1"
    reference_count: int
    claim_count: int
    rule_candidate_count: int
    ingredient_domain_evidence_count: int
    source_type_counts: dict[str, int]
    normalized_claim_type_counts: dict[str, int]
    rule_type_counts: dict[str, int]
    ingredient_counts: dict[str, int]
    medication_counts: dict[str, int]


class RawReferenceDocument(BaseModel):
    metadata: ReferenceMetadata
    claims: list[ParsedReferenceClaim]
    rule_candidates: list[RuleCandidate]


_FRONTMATTER_BOUNDARY = "---"
_FIELD_PATTERN = re.compile(r"^(?P<key>[A-Za-z0-9_]+):\s*(?P<value>.+?)\s*$")


def ingest_reference_directory(input_dir: str | Path) -> KnowledgeBaseArtifact:
    input_path = Path(input_dir)
    reference_documents = [
        parse_reference_markdown(path)
        for path in sorted(input_path.glob("*.md"))
    ]
    references = [document.metadata for document in reference_documents]
    parsed_claims = [
        claim
        for document in reference_documents
        for claim in document.claims
    ]
    rule_candidates = [
        candidate
        for document in reference_documents
        for candidate in document.rule_candidates
    ]
    ingredient_domain_evidence = _build_ingredient_domain_evidence(parsed_claims)
    return KnowledgeBaseArtifact(
        references=references,
        parsed_claims=parsed_claims,
        rule_candidates=rule_candidates,
        ingredient_domain_evidence=ingredient_domain_evidence,
    )


def summarize_ingestion(artifact: KnowledgeBaseArtifact) -> IngestionSummary:
    source_type_counts = Counter(reference.source_type for reference in artifact.references)
    claim_type_counts = Counter(
        claim.normalized_claim_type for claim in artifact.parsed_claims
    )
    rule_type_counts = Counter(candidate.rule_type for candidate in artifact.rule_candidates)
    ingredient_counts = Counter(
        ingredient_key
        for claim in artifact.parsed_claims
        for ingredient_key in claim.ingredient_keys
    )
    medication_counts = Counter(
        medication_key
        for claim in artifact.parsed_claims
        for medication_key in claim.medication_keys
    )
    return IngestionSummary(
        reference_count=len(artifact.references),
        claim_count=len(artifact.parsed_claims),
        rule_candidate_count=len(artifact.rule_candidates),
        ingredient_domain_evidence_count=len(artifact.ingredient_domain_evidence),
        source_type_counts=dict(sorted(source_type_counts.items())),
        normalized_claim_type_counts=dict(sorted(claim_type_counts.items())),
        rule_type_counts=dict(sorted(rule_type_counts.items())),
        ingredient_counts=dict(sorted(ingredient_counts.items())),
        medication_counts=dict(sorted(medication_counts.items())),
    )


def validate_knowledge_artifact(artifact: KnowledgeBaseArtifact) -> list[str]:
    issues: list[str] = []
    reference_ids = [reference.reference_id for reference in artifact.references]
    claim_ids = [claim.claim_id for claim in artifact.parsed_claims]
    rule_ids = [rule.rule_id for rule in artifact.rule_candidates]
    if len(reference_ids) != len(set(reference_ids)):
        issues.append("duplicate_reference_id")
    if len(claim_ids) != len(set(claim_ids)):
        issues.append("duplicate_claim_id")
    if len(rule_ids) != len(set(rule_ids)):
        issues.append("duplicate_rule_id")

    claim_ids_set = set(claim_ids)
    reference_ids_set = set(reference_ids)
    for claim in artifact.parsed_claims:
        if claim.reference_id not in reference_ids_set:
            issues.append(f"claim_missing_reference:{claim.claim_id}")
        if claim.citation_span.line_start > claim.citation_span.line_end:
            issues.append(f"claim_invalid_line_span:{claim.claim_id}")
        if not claim.citation_span.excerpt.strip():
            issues.append(f"claim_missing_excerpt:{claim.claim_id}")

    for rule in artifact.rule_candidates:
        if rule.claim_id not in claim_ids_set:
            issues.append(f"rule_missing_claim:{rule.rule_id}")
        if rule.reference_id not in reference_ids_set:
            issues.append(f"rule_missing_reference:{rule.rule_id}")
        if rule.citation_span.line_start > rule.citation_span.line_end:
            issues.append(f"rule_invalid_line_span:{rule.rule_id}")

    for evidence in artifact.ingredient_domain_evidence:
        if not evidence.claim_ids:
            issues.append(f"evidence_missing_claim_ids:{evidence.ingredient_key}:{evidence.domain_key}")
        if not evidence.reference_ids:
            issues.append(
                f"evidence_missing_reference_ids:{evidence.ingredient_key}:{evidence.domain_key}"
            )

    return issues


def parse_reference_markdown(path: str | Path) -> RawReferenceDocument:
    file_path = Path(path)
    lines = file_path.read_text(encoding="utf-8").splitlines()
    metadata, frontmatter_end_line = _parse_frontmatter(lines)
    claims: list[ParsedReferenceClaim] = []
    rule_candidates: list[RuleCandidate] = []
    search_start_line = max(frontmatter_end_line + 1, 1)

    for block_start, block_end, payload in _iter_json_code_blocks(lines):
        raw_claim = RawReferenceClaim.model_validate_json(payload)
        excerpt = _extract_citation_excerpt(
            lines=lines,
            start_line=search_start_line,
            end_line=block_start - 1,
        )
        citation_span = CitationSpan(
            line_start=block_start,
            line_end=block_end,
            excerpt=excerpt,
        )
        claim = ParsedReferenceClaim(
            reference_id=metadata.reference_id,
            source_title=metadata.source_title,
            source_type=metadata.source_type,
            page_or_section=metadata.page_or_section,
            reference_uri=metadata.reference_uri,
            claim_id=raw_claim.claim_id,
            claim_text=raw_claim.claim_text.strip(),
            normalized_claim_type=_normalize_key(raw_claim.normalized_claim_type),
            citation_span=citation_span,
            ingredient_keys=[_normalize_key(value) for value in raw_claim.ingredient_keys],
            medication_keys=[_normalize_key(value) for value in raw_claim.medication_keys],
            domain_keys=[_normalize_key(value) for value in raw_claim.domain_keys],
        )
        claims.append(claim)
        if raw_claim.rule_candidate is not None:
            rule_candidates.append(
                RuleCandidate(
                    rule_id=raw_claim.rule_candidate.rule_id,
                    rule_type=_normalize_key(raw_claim.rule_candidate.rule_type),
                    severity=_normalize_key(raw_claim.rule_candidate.severity),
                    if_clause=_normalize_nested_keys(raw_claim.rule_candidate.if_clause),
                    then_clause=_normalize_nested_keys(raw_claim.rule_candidate.then_clause),
                    reference_id=metadata.reference_id,
                    claim_id=claim.claim_id,
                    citation_span=citation_span,
                )
            )
        search_start_line = block_end + 2

    return RawReferenceDocument(
        metadata=metadata,
        claims=claims,
        rule_candidates=rule_candidates,
    )


def _build_ingredient_domain_evidence(
    parsed_claims: list[ParsedReferenceClaim],
) -> list[IngredientDomainEvidence]:
    grouped: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(
        lambda: {
            "claim_ids": set(),
            "reference_ids": set(),
            "medication_keys": set(),
            "normalized_claim_types": set(),
        }
    )
    for claim in parsed_claims:
        for ingredient_key in claim.ingredient_keys:
            for domain_key in claim.domain_keys:
                bucket = grouped[(ingredient_key, domain_key)]
                bucket["claim_ids"].add(claim.claim_id)
                bucket["reference_ids"].add(claim.reference_id)
                bucket["normalized_claim_types"].add(claim.normalized_claim_type)
                bucket["medication_keys"].update(claim.medication_keys)
    return [
        IngredientDomainEvidence(
            ingredient_key=ingredient_key,
            domain_key=domain_key,
            claim_ids=sorted(values["claim_ids"]),
            reference_ids=sorted(values["reference_ids"]),
            medication_keys=sorted(values["medication_keys"]),
            normalized_claim_types=sorted(values["normalized_claim_types"]),
        )
        for (ingredient_key, domain_key), values in sorted(grouped.items())
    ]


def _parse_frontmatter(lines: list[str]) -> tuple[ReferenceMetadata, int]:
    if not lines or lines[0].strip() != _FRONTMATTER_BOUNDARY:
        raise ValueError("reference markdown must start with frontmatter")
    frontmatter: dict[str, str] = {}
    for line_index in range(1, len(lines)):
        line = lines[line_index]
        if line.strip() == _FRONTMATTER_BOUNDARY:
            return ReferenceMetadata.model_validate(frontmatter), line_index + 1
        match = _FIELD_PATTERN.match(line)
        if match is None:
            raise ValueError(f"invalid frontmatter line: {line}")
        frontmatter[match.group("key")] = match.group("value")
    raise ValueError("unterminated frontmatter")


def _iter_json_code_blocks(lines: list[str]) -> list[tuple[int, int, str]]:
    blocks: list[tuple[int, int, str]] = []
    in_block = False
    block_lines: list[str] = []
    block_start = 0
    for line_index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not in_block and stripped.startswith("```"):
            language = stripped[3:].strip().lower()
            if language.startswith("json"):
                in_block = True
                block_start = line_index + 1
                block_lines = []
            continue
        if in_block and stripped == "```":
            blocks.append((block_start, line_index - 1, "\n".join(block_lines)))
            in_block = False
            block_lines = []
            continue
        if in_block:
            block_lines.append(line)
    return blocks


def _extract_citation_excerpt(
    *,
    lines: list[str],
    start_line: int,
    end_line: int,
) -> str:
    if end_line < start_line:
        return "Structured claim block."
    relevant_lines = []
    for line in lines[start_line - 1 : end_line]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == _FRONTMATTER_BOUNDARY:
            continue
        if _FIELD_PATTERN.match(stripped):
            continue
        if stripped.startswith("```"):
            continue
        relevant_lines.append(stripped)
    excerpt_lines = relevant_lines[-3:]
    if not excerpt_lines:
        return "Structured claim block."
    return " ".join(excerpt_lines)


def _normalize_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _normalize_nested_keys(payload: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        normalized_key = _normalize_key(key)
        if isinstance(value, str):
            normalized[normalized_key] = _normalize_key(value)
        elif isinstance(value, list):
            normalized[normalized_key] = [
                _normalize_key(item) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, dict):
            normalized[normalized_key] = _normalize_nested_keys(value)
        else:
            normalized[normalized_key] = value
    return normalized
