from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wellnessbox_rnd.domain.loaders import repo_root
from wellnessbox_rnd.ingestion.reference_ingestion import (
    KnowledgeBaseArtifact,
    validate_knowledge_artifact,
)
from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.evidence import EvidenceRegistry
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.schemas.recommendation import RecommendationResponse


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: str | bytes) -> str:
    payload = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class KnowledgeLineageSummary:
    source_count: int
    passage_count: int
    claim_count: int
    rule_count: int
    claim_rule_link_count: int


class KnowledgeLineageRegistry:
    """Persist the canonical local reference artifact as normalized audit lineage."""

    def __init__(
        self,
        store: InterimStore,
        artifact_path: str | Path | None = None,
    ) -> None:
        self.store = store
        self.artifact_path = Path(artifact_path) if artifact_path else (
            repo_root() / "data" / "knowledge" / "reference_knowledge_base_v1.json"
        )

    def sync_reference_artifact(self) -> KnowledgeLineageSummary:
        artifact = KnowledgeBaseArtifact.model_validate_json(
            self.artifact_path.read_text(encoding="utf-8")
        )
        issues = validate_knowledge_artifact(artifact)
        if issues:
            raise ValueError(f"invalid_knowledge_artifact:{','.join(issues)}")

        references = {item.reference_id: item for item in artifact.references}
        claims = {item.claim_id: item for item in artifact.parsed_claims}
        rules_by_claim: dict[str, list[object]] = {}
        for rule in artifact.rule_candidates:
            rules_by_claim.setdefault(rule.claim_id, []).append(rule)

        evidence_registry = EvidenceRegistry(self.store)
        evidence_ids: dict[str, str] = {}
        source_quarantine: dict[str, bool] = {}
        for reference in artifact.references:
            source_path = self._resolve_local_source(reference.parsed_source_uri)
            content_checksum = _sha(source_path.read_bytes())
            source_result = evidence_registry.register_source(
                source_id=reference.reference_id,
                source_tier=reference.source_type,
                title=reference.source_title,
                canonical_uri=reference.parsed_source_uri,
                license_status=reference.license_status,
                effective_at=reference.effective_at,
                retired_at=reference.retired_at,
                metadata={
                    "artifact_version": artifact.artifact_version,
                    "content_checksum": content_checksum,
                    "date_semantics": "local_artifact_effective_at",
                    "page_or_section": reference.page_or_section,
                    "upstream_reference_uri": reference.reference_uri,
                },
            )
            source_quarantine[reference.reference_id] = source_result.quarantined

        for claim in artifact.parsed_claims:
            reference = references[claim.reference_id]
            claim_rules = rules_by_claim.get(claim.claim_id, [])
            approved_for_safety = any(
                getattr(rule, "severity", "") == "blocker" for rule in claim_rules
            )
            passage = evidence_registry.add_passage(
                evidence_id=f"ev_{_sha(claim.claim_id)[:20]}",
                source_id=claim.reference_id,
                passage_text=claim.citation_span.excerpt,
                page_or_section=claim.page_or_section,
                line_start=claim.citation_span.line_start,
                line_end=claim.citation_span.line_end,
                approved_for_safety=approved_for_safety,
                effective_at=reference.effective_at,
                metadata={
                    "artifact_version": artifact.artifact_version,
                    "claim_id": claim.claim_id,
                    "reference_uri": claim.reference_uri,
                },
            )
            evidence_ids[claim.claim_id] = passage.identifier

        data_class = DataClass.PROXY_GOLD_SIMULATION
        with self.store.transaction(immediate=True) as connection:
            for claim in artifact.parsed_claims:
                reference = references[claim.reference_id]
                claim_body = {
                    "claim_id": claim.claim_id,
                    "evidence_id": evidence_ids[claim.claim_id],
                    "normalized_claim_type": claim.normalized_claim_type,
                    "claim_text": claim.claim_text,
                    "ingredient_keys": claim.ingredient_keys,
                    "medication_keys": claim.medication_keys,
                    "domain_keys": claim.domain_keys,
                    "effective_at": reference.effective_at,
                    "retired_at": reference.retired_at,
                }
                connection.execute(
                    """
                    insert into knowledge_claims(
                      claim_id, evidence_id, normalized_claim_type, claim_text,
                      ingredient_keys_json, medication_keys_json, domain_keys_json,
                      checksum, effective_at, retired_at, data_class
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(claim_id) do update set
                      evidence_id=excluded.evidence_id,
                      normalized_claim_type=excluded.normalized_claim_type,
                      claim_text=excluded.claim_text,
                      ingredient_keys_json=excluded.ingredient_keys_json,
                      medication_keys_json=excluded.medication_keys_json,
                      domain_keys_json=excluded.domain_keys_json,
                      checksum=excluded.checksum,
                      effective_at=excluded.effective_at,
                      retired_at=excluded.retired_at,
                      data_class=excluded.data_class
                    """,
                    (
                        claim.claim_id,
                        evidence_ids[claim.claim_id],
                        claim.normalized_claim_type,
                        claim.claim_text,
                        _canonical(claim.ingredient_keys),
                        _canonical(claim.medication_keys),
                        _canonical(claim.domain_keys),
                        _sha(_canonical(claim_body)),
                        reference.effective_at,
                        reference.retired_at,
                        data_class,
                    ),
                )

            for rule in artifact.rule_candidates:
                reference = references[rule.reference_id]
                rule_body = {
                    "rule_id": rule.rule_id,
                    "rule_type": rule.rule_type,
                    "severity": rule.severity,
                    "source_kind": "knowledge_artifact",
                    "predicate": rule.if_clause,
                    "action": rule.then_clause,
                    "valid_from": reference.effective_at,
                    "valid_to": reference.retired_at,
                }
                connection.execute(
                    """
                    insert into knowledge_rules(
                      rule_id, rule_type, severity, source_kind, predicate_json,
                      action_json, checksum, valid_from, valid_to, status, data_class
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    on conflict(rule_id) do update set
                      rule_type=excluded.rule_type,
                      severity=excluded.severity,
                      source_kind=excluded.source_kind,
                      predicate_json=excluded.predicate_json,
                      action_json=excluded.action_json,
                      checksum=excluded.checksum,
                      valid_from=excluded.valid_from,
                      valid_to=excluded.valid_to,
                      status=excluded.status,
                      data_class=excluded.data_class
                    """,
                    (
                        rule.rule_id,
                        rule.rule_type,
                        rule.severity,
                        "knowledge_artifact",
                        _canonical(rule.if_clause),
                        _canonical(rule.then_clause),
                        _sha(_canonical(rule_body)),
                        reference.effective_at,
                        reference.retired_at,
                        (
                            "RETIRED"
                            if reference.retired_at
                            else (
                                "QUARANTINED"
                                if source_quarantine[reference.reference_id]
                                else "ACTIVE"
                            )
                        ),
                        data_class,
                    ),
                )
                connection.execute(
                    "insert or ignore into claim_rule_links(claim_id, rule_id) values (?, ?)",
                    (rule.claim_id, rule.rule_id),
                )

        return KnowledgeLineageSummary(
            source_count=len(references),
            passage_count=len(claims),
            claim_count=len(claims),
            rule_count=len(artifact.rule_candidates),
            claim_rule_link_count=len(artifact.rule_candidates),
        )

    @staticmethod
    def _resolve_local_source(reference_uri: str) -> Path:
        source_path = (repo_root() / reference_uri).resolve()
        root = repo_root().resolve()
        if source_path != root and root not in source_path.parents:
            raise ValueError(f"reference_outside_repository:{reference_uri}")
        if not source_path.is_file():
            raise ValueError(f"reference_source_missing:{reference_uri}")
        return source_path


def persist_execution_knowledge_lineage(
    *,
    connection: sqlite3.Connection,
    execution_id: str,
    response: RecommendationResponse,
    event_ids: dict[str, str],
    created_at: str,
) -> int:
    """Link persisted recommendation outputs to existing normalized knowledge rows."""

    inserted = 0

    def insert_lineage(
        *,
        event_id: str,
        output_type: str,
        output_key: str,
        rule_id: str,
        claim_id: str,
    ) -> None:
        nonlocal inserted
        row = connection.execute(
            """
            select kc.evidence_id, ep.source_id
            from claim_rule_links link
            join knowledge_claims kc on kc.claim_id=link.claim_id
            join evidence_passages ep on ep.evidence_id=kc.evidence_id
            where link.rule_id=? and link.claim_id=?
            """,
            (rule_id, claim_id),
        ).fetchone()
        if row is None:
            return
        identity: dict[str, Any] = {
            "execution_id": execution_id,
            "event_id": event_id,
            "output_type": output_type,
            "output_key": output_key,
            "rule_id": rule_id,
            "claim_id": claim_id,
        }
        lineage_id = f"lineage_{_sha(_canonical(identity))[:32]}"
        cursor = connection.execute(
            """
            insert or ignore into execution_knowledge_lineage(
              lineage_id, execution_id, event_id, output_type, output_key,
              rule_id, claim_id, evidence_id, source_id, data_class, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lineage_id,
                execution_id,
                event_id,
                output_type,
                output_key,
                rule_id,
                claim_id,
                str(row["evidence_id"]),
                str(row["source_id"]),
                DataClass.INTERIM_RUNTIME_EVENT,
                created_at,
            ),
        )
        inserted += max(cursor.rowcount, 0)

    recommendation_event_id = event_ids.get("recommendation")
    safety_event_id = event_ids.get("safety")
    optimization_event_id = event_ids.get("optimization")
    for rule in response.safety_summary.rule_refs:
        for claim_id in rule.claim_ids:
            if safety_event_id is not None:
                insert_lineage(
                    event_id=safety_event_id,
                    output_type="safety_rule",
                    output_key=rule.rule_id,
                    rule_id=rule.rule_id,
                    claim_id=claim_id,
                )
            if recommendation_event_id is not None:
                insert_lineage(
                    event_id=recommendation_event_id,
                    output_type="recommendation_decision",
                    output_key=response.decision_id,
                    rule_id=rule.rule_id,
                    claim_id=claim_id,
                )

    if optimization_event_id is not None:
        claim_rows = connection.execute(
            """
            select kc.claim_id, kc.ingredient_keys_json, link.rule_id
            from knowledge_claims kc
            join claim_rule_links link on link.claim_id=kc.claim_id
            """
        ).fetchall()
        for candidate in response.recommendations:
            for row in claim_rows:
                ingredient_keys = set(json.loads(row["ingredient_keys_json"]))
                if candidate.ingredient_key not in ingredient_keys:
                    continue
                insert_lineage(
                    event_id=optimization_event_id,
                    output_type="recommendation_item",
                    output_key=candidate.ingredient_key,
                    rule_id=str(row["rule_id"]),
                    claim_id=str(row["claim_id"]),
                )

    return inserted


__all__ = [
    "KnowledgeLineageRegistry",
    "KnowledgeLineageSummary",
    "persist_execution_knowledge_lineage",
]
