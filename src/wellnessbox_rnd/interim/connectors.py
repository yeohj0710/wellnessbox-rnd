from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.store import InterimStore

OFFICIAL_SOURCE_ADAPTERS = {
    "pubmed": "https://pubmed.ncbi.nlm.nih.gov/",
    "clinicaltrials": "https://clinicaltrials.gov/",
    "dailymed": "https://dailymed.nlm.nih.gov/",
    "openfda": "https://open.fda.gov/",
    "rxnorm": "https://rxnav.nlm.nih.gov/",
    "ods": "https://ods.od.nih.gov/",
    "dsld": "https://dsld.od.nih.gov/",
    "mfds": "https://www.mfds.go.kr/",
}


@dataclass(frozen=True)
class AdapterContract:
    name: str
    base_url: str
    enabled: bool
    gate: str | None


def source_adapters(enabled: set[str] | None = None) -> list[AdapterContract]:
    allowed = enabled or set()
    return [
        AdapterContract(name, url, name in allowed, None if name in allowed else "environment_gate")
        for name, url in OFFICIAL_SOURCE_ADAPTERS.items()
    ]


def ingest_device_session(
    store: InterimStore,
    *,
    session_id: str,
    profile_id: str,
    source: str,
    consent_scopes: set[str],
    payload: dict[str, Any],
    environment: str = "simulation",
) -> dict[str, Any]:
    if source not in {"W", "C", "G"}:
        raise ValueError("unsupported_device_source")
    if "device:write" not in consent_scopes:
        raise PermissionError("missing_device_consent")
    required = {"observed_at", "value", "unit", "timezone", "source_record_id"}
    schema_valid = required.issubset(payload)
    unit_valid = str(payload.get("unit", "")).strip() not in {"", "unknown"}
    timezone_valid = str(payload.get("timezone", "")).startswith(("+", "-", "UTC", "Asia/"))
    provenance_saved = bool(payload.get("source_record_id"))
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    row_hash = hashlib.sha256(canonical.encode()).hexdigest()
    success = schema_valid and unit_valid and timezone_valid and provenance_saved
    with store.transaction() as connection:
        duplicate = connection.execute(
            "select 1 from connector_sessions where session_id=?", (session_id,)
        ).fetchone()
        connection.execute(
            """
            insert into connector_sessions(
              session_id, profile_id, source, environment, data_class, success,
              schema_valid, unit_valid, timezone_valid, deduplicated, provenance_saved,
              row_sha256, payload_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(session_id) do nothing
            """,
            (
                session_id,
                profile_id,
                source,
                environment,
                DataClass.INTERIM_RUNTIME_EVENT,
                int(success),
                int(schema_valid),
                int(unit_valid),
                int(timezone_valid),
                int(duplicate is not None),
                int(provenance_saved),
                row_hash,
                canonical,
            ),
        )
    return {
        "session_id": session_id,
        "success": success,
        "deduplicated": duplicate is not None,
        "postconditions": {
            "schema": schema_valid,
            "unit": unit_valid,
            "timezone": timezone_valid,
            "provenance": provenance_saved,
        },
        "recorded_at": datetime.now(UTC).isoformat(),
    }
