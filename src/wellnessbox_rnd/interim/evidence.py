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
            "title": title,
            "canonical_uri": canonical_uri,
            "effective_at": effective_at,
            "retired_at": retired_at,
            "metadata": metadata or {},
        }
        checksum = _sha(_canonical(payload))
        quarantined = normalized_license not in APPROVED_LICENSES or retired_at is not None
        reason = "license_not_approved" if normalized_license not in APPROVED_LICENSES else None
        if retired_at is not None:
            reason = "source_retired"
        stored_metadata = {**(metadata or {}), "quarantined": quarantined, "reason": reason}
        with self.store.transaction() as connection:
            previous = connection.execute(
                "select checksum from source_registry where source_id = ?", (source_id,)
            ).fetchone()
            if previous is not None and previous[0] != checksum:
                quarantined = True
                reason = "content_changed_requires_review"
                stored_metadata["content_changed"] = True
                stored_metadata["previous_checksum"] = previous[0]
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
        metadata = json.loads(source[0]["metadata_json"])
        quarantined = bool(metadata.get("quarantined"))
        if approved_for_safety and quarantined:
            raise ValueError("quarantined_source_cannot_support_safety")
        checksum = _sha(passage_text.strip())
        evidence_id = f"ev_{checksum[:20]}"
        with self.store.transaction() as connection:
            connection.execute(
                """
                insert into evidence_passages(
                  evidence_id, source_id, passage_text, effective_at, checksum,
                  approved_for_safety, data_class
                ) values (?, ?, ?, ?, ?, ?, ?)
                on conflict(evidence_id) do nothing
                """,
                (
                    evidence_id,
                    source_id,
                    passage_text.strip(),
                    effective_at or datetime.now(UTC).isoformat(),
                    checksum,
                    int(approved_for_safety),
                    DataClass.PROXY_GOLD_SIMULATION,
                ),
            )
        return EvidenceResult(evidence_id, checksum, quarantined)

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
