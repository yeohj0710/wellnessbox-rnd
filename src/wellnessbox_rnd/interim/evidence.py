from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.store import InterimStore

APPROVED_LICENSES = {"OPEN", "PUBLIC_DOMAIN", "APPROVED_INTERNAL"}


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvidenceResult:
    identifier: str
    checksum: str
    quarantined: bool
    reason: str | None = None


class EvidenceRegistry:
    """Versioned evidence registry with explicit license and freshness gates."""

    def __init__(self, store: InterimStore):
        self.store = store

    def register_source(
        self,
        *,
        source_id: str,
        source_tier: str,
        title: str,
        canonical_uri: str,
        license_status: str,
        effective_at: str | None = None,
        retired_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceResult:
        normalized_license = license_status.upper()
        payload = {
            "source_id": source_id,
            "source_tier": source_tier,
            "title": title,
            "canonical_uri": canonical_uri,
            "license_status": normalized_license,
            "effective_at": effective_at,
            "retired_at": retired_at,
            "metadata": metadata or {},
        }
        legacy_payload = {
            key: payload[key]
            for key in (
                "source_id",
                "title",
                "canonical_uri",
                "effective_at",
                "retired_at",
                "metadata",
            )
        }
        checksum = _sha(_canonical(payload))
        legacy_checksum = _sha(_canonical(legacy_payload))
        quarantined = normalized_license not in APPROVED_LICENSES or retired_at is not None
        reason = "license_not_approved" if normalized_license not in APPROVED_LICENSES else None
        if retired_at is not None:
            reason = "source_retired"
        stored_metadata = {**(metadata or {}), "quarantined": quarantined, "reason": reason}
        with self.store.transaction() as connection:
            previous = connection.execute(
                """
                select checksum, metadata_json, source_tier, license_status
                from source_registry where source_id = ?
                """,
                (source_id,),
            ).fetchone()
            previous_metadata = (
                {} if previous is None else json.loads(previous["metadata_json"])
            )
            legacy_envelope_upgrade = (
                previous is not None
                and previous["checksum"] == legacy_checksum
                and previous["source_tier"] == source_tier
                and previous["license_status"] == normalized_license
                and not previous_metadata.get("content_changed")
            )
            if (
                previous is not None
                and previous["checksum"] != checksum
                and not legacy_envelope_upgrade
            ):
                quarantined = True
                reason = "content_changed_requires_review"
                stored_metadata["content_changed"] = True
                stored_metadata["previous_checksum"] = previous_metadata.get(
                    "previous_checksum",
                    previous["checksum"],
                )
                stored_metadata["quarantined"] = True
                stored_metadata["reason"] = reason
            elif previous is not None:
                if previous_metadata.get("content_changed"):
                    quarantined = True
                    reason = "content_changed_requires_review"
                    stored_metadata["content_changed"] = True
                    stored_metadata["previous_checksum"] = previous_metadata[
                        "previous_checksum"
                    ]
                    stored_metadata["quarantined"] = True
                    stored_metadata["reason"] = reason
            connection.execute(
                """
                insert into source_registry(
                  source_id, source_tier, title, canonical_uri, license_status,
                  effective_at, retired_at, checksum, data_class, metadata_json
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(source_id) do update set
                  source_tier=excluded.source_tier, title=excluded.title,
                  canonical_uri=excluded.canonical_uri,
                  license_status=excluded.license_status,
                  effective_at=excluded.effective_at, retired_at=excluded.retired_at,
                  checksum=excluded.checksum, metadata_json=excluded.metadata_json
                """,
                (
                    source_id,
                    source_tier,
                    title,
                    canonical_uri,
                    normalized_license,
                    effective_at,
                    retired_at,
                    checksum,
                    DataClass.PROXY_GOLD_SIMULATION,
                    _canonical(stored_metadata),
                ),
            )
        return EvidenceResult(source_id, checksum, quarantined, reason)

    def add_passage(
        self,
        *,
        source_id: str,
        passage_text: str,
        approved_for_safety: bool = False,
        effective_at: str | None = None,
        evidence_id: str | None = None,
        page_or_section: str | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceResult:
        source = self.store.rows(
            """
            select license_status, retired_at, metadata_json
            from source_registry where source_id=?
            """,
            (source_id,),
        )
        if not source:
            raise ValueError("unknown_source")
        source_metadata = json.loads(source[0]["metadata_json"])
        quarantined = bool(source_metadata.get("quarantined"))
        if approved_for_safety and quarantined:
            raise ValueError("quarantined_source_cannot_support_safety")
        normalized_passage = passage_text.strip()
        has_span_metadata = any(
            value is not None for value in (page_or_section, line_start, line_end)
        ) or bool(metadata)
        if has_span_metadata:
            passage_payload = {
                "passage_text": normalized_passage,
                "page_or_section": page_or_section,
                "line_start": line_start,
                "line_end": line_end,
                "metadata": metadata or {},
            }
            checksum = _sha(_canonical(passage_payload))
        else:
            checksum = _sha(normalized_passage)
        resolved_evidence_id = evidence_id or f"ev_{checksum[:20]}"
        with self.store.transaction() as connection:
            connection.execute(
                """
                insert into evidence_passages(
                  evidence_id, source_id, passage_text, page_or_section,
                  line_start, line_end, metadata_json, effective_at, checksum,
                  approved_for_safety, data_class
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(evidence_id) do update set
                  source_id=excluded.source_id,
                  passage_text=excluded.passage_text,
                  page_or_section=excluded.page_or_section,
                  line_start=excluded.line_start,
                  line_end=excluded.line_end,
                  metadata_json=excluded.metadata_json,
                  effective_at=excluded.effective_at,
                  checksum=excluded.checksum,
                  approved_for_safety=excluded.approved_for_safety,
                  data_class=excluded.data_class
                """,
                (
                    resolved_evidence_id,
                    source_id,
                    normalized_passage,
                    page_or_section,
                    line_start,
                    line_end,
                    _canonical(metadata or {}),
                    effective_at or datetime.now(UTC).isoformat(),
                    checksum,
                    int(approved_for_safety),
                    DataClass.PROXY_GOLD_SIMULATION,
                ),
            )
        return EvidenceResult(resolved_evidence_id, checksum, quarantined)

    def activate_rule(
        self,
        *,
        rule_id: str,
        version: int,
        severity: str,
        action: str,
        predicate: dict[str, Any],
        evidence_ids: list[str],
        valid_from: str,
    ) -> str:
        critical = action in {"BLOCK", "STOP_AND_ESCALATE"}
        if critical:
            placeholders = ",".join("?" for _ in evidence_ids) or "null"
            approved = self.store.scalar(
                f"select count(*) from evidence_passages where evidence_id in ({placeholders}) "
                "and approved_for_safety = 1",
                tuple(evidence_ids),
            )
            if not evidence_ids or approved != len(evidence_ids):
                raise ValueError("critical_rule_requires_approved_evidence")
        rule_version_id = f"{rule_id}:v{version}"
        body = {
            "rule_id": rule_id,
            "version": version,
            "severity": severity,
            "action": action,
            "predicate": predicate,
            "evidence_ids": evidence_ids,
            "valid_from": valid_from,
        }
        with self.store.transaction() as connection:
            connection.execute(
                """
                insert into safety_rules(
                  rule_version_id, rule_id, version, severity, action, predicate_json,
                  evidence_ids_json, valid_from, valid_to, review_status, rule_sha256, data_class
                ) values (?, ?, ?, ?, ?, ?, ?, ?, null, 'ACTIVE', ?, ?)
                """,
                (
                    rule_version_id,
                    rule_id,
                    version,
                    severity,
                    action,
                    _canonical(predicate),
                    _canonical(evidence_ids),
                    valid_from,
                    _sha(_canonical(body)),
                    DataClass.PROXY_GOLD_SIMULATION,
                ),
            )
            event_id = f"audit_{uuid4().hex}"
            connection.execute(
                "insert into audit_events values (?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    "safety_rule_activated",
                    rule_version_id,
                    DataClass.PROXY_GOLD_SIMULATION,
                    _sha(_canonical(body)),
                    _canonical({"critical": critical}),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return rule_version_id
