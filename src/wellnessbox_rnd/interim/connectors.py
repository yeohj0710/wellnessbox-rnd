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
    data_class: DataClass | str | None = None,
) -> dict[str, Any]:
    if source not in {"W", "C", "G"}:
        raise ValueError("unsupported_device_source")
    if "device:write" not in consent_scopes:
        raise PermissionError("missing_device_consent")
    expected_data_class = {
        "simulation": DataClass.SIMULATED_DEVICE_SESSION,
        "production": DataClass.PRODUCTION_DEVICE_SESSION,
    }.get(environment)
    if expected_data_class is None:
        raise ValueError("unsupported_device_environment")
    effective_data_class = DataClass(data_class or expected_data_class)
    if effective_data_class != expected_data_class:
        raise ValueError("device_environment_data_class_mismatch")
    required = {"observed_at", "value", "unit", "timezone", "source_record_id"}
    schema_valid = required.issubset(payload)
    unit_valid = str(payload.get("unit", "")).strip() not in {"", "unknown"}
    timezone_valid = str(payload.get("timezone", "")).startswith(("+", "-", "UTC", "Asia/"))
    provenance_saved = bool(payload.get("source_record_id"))
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    row_hash = hashlib.sha256(canonical.encode()).hexdigest()
    success = schema_valid and unit_valid and timezone_valid and provenance_saved
    source_record_id = str(payload.get("source_record_id", "")).strip() or None
    identity_material = (
        f"{profile_id}:{source}:{source_record_id}"
        if source_record_id is not None
        else f"{profile_id}:{source}:missing:{session_id}"
    )
    event_identity = "device_event_" + hashlib.sha256(
        identity_material.encode("utf-8")
    ).hexdigest()
    with store.transaction(immediate=True) as connection:
        receipt = connection.execute(
            "select * from device_event_receipts where event_identity=?",
            (event_identity,),
        ).fetchone()
        if receipt is not None:
            expected = {
                "profile_id": profile_id,
                "source": source,
                "source_record_id": source_record_id,
                "data_class": effective_data_class.value,
                "payload_sha256": row_hash,
            }
            if any(receipt[key] != value for key, value in expected.items()):
                raise ValueError("duplicate_device_event_conflict")
            return _device_ingestion_result(
                session_id=str(receipt["session_id"]),
                event_identity=event_identity,
                success=bool(receipt["success"]),
                deduplicated=True,
                schema_valid=bool(receipt["schema_valid"]),
                unit_valid=bool(receipt["unit_valid"]),
                timezone_valid=bool(receipt["timezone_valid"]),
                provenance_saved=bool(receipt["provenance_saved"]),
                data_class=effective_data_class,
            )
        session = connection.execute(
            "select row_sha256 from connector_sessions where session_id=?",
            (session_id,),
        ).fetchone()
        if session is not None:
            raise ValueError("device_session_identity_conflict")
        connection.execute(
            """
            insert into connector_sessions(
              session_id, profile_id, source, environment, data_class, success,
              schema_valid, unit_valid, timezone_valid, deduplicated, provenance_saved,
              row_sha256, payload_json
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                profile_id,
                source,
                environment,
                effective_data_class,
                int(success),
                int(schema_valid),
                int(unit_valid),
                int(timezone_valid),
                0,
                int(provenance_saved),
                row_hash,
                canonical,
            ),
        )
        connection.execute(
            """
            insert into device_event_receipts(
              event_identity, session_id, profile_id, source, source_record_id,
              data_class, success, schema_valid, unit_valid, timezone_valid,
              provenance_saved, payload_sha256, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_identity,
                session_id,
                profile_id,
                source,
                source_record_id,
                effective_data_class,
                int(success),
                int(schema_valid),
                int(unit_valid),
                int(timezone_valid),
                int(provenance_saved),
                row_hash,
                datetime.now(UTC).isoformat(),
            ),
        )
    return _device_ingestion_result(
        session_id=session_id,
        event_identity=event_identity,
        success=success,
        deduplicated=False,
        schema_valid=schema_valid,
        unit_valid=unit_valid,
        timezone_valid=timezone_valid,
        provenance_saved=provenance_saved,
        data_class=effective_data_class,
    )


def _device_ingestion_result(
    *,
    session_id: str,
    event_identity: str,
    success: bool,
    deduplicated: bool,
    schema_valid: bool,
    unit_valid: bool,
    timezone_valid: bool,
    provenance_saved: bool,
    data_class: DataClass,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "event_identity": event_identity,
        "success": success,
        "deduplicated": deduplicated,
        "data_class": data_class.value,
        "postconditions": {
            "schema": schema_valid,
            "unit": unit_valid,
            "timezone": timezone_valid,
            "provenance": provenance_saved,
        },
        "recorded_at": datetime.now(UTC).isoformat(),
    }
