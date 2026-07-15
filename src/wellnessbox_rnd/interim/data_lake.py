from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from wellnessbox_rnd.interim.contracts import DataClass
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.schemas.recommendation import (
    DataSource,
    RecommendationRequest,
    RecommendationResponse,
)

PROFILE_SNAPSHOT_SCHEMA_VERSION = "recommendation_profile_snapshot_v1"
CONSENT_SNAPSHOT_SCHEMA_VERSION = "recommendation_data_source_consents_v1"


class ExecutionEventType(StrEnum):
    CONVERSATION = "conversation"
    RECOMMENDATION = "recommendation"
    SAFETY = "safety"
    OPTIMIZATION = "optimization"
    FOLLOWUP_EVALUATION = "followup_evaluation"


class ExecutionEventSource(StrEnum):
    SYSTEM = "system"
    SURVEY = "survey"
    NHIS = "nhis"
    WEARABLE = "wearable"
    CGM = "cgm"
    GENETIC = "genetic"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExecutionEventRecord(_StrictModel):
    event_id: str
    execution_id: str
    consent_snapshot_id: str
    event_index: int
    event_type: ExecutionEventType
    source: ExecutionEventSource
    idempotency_key: str
    payload: dict[str, Any]
    payload_sha256: str
    created_at: str


class ExecutionTrace(_StrictModel):
    execution_id: str
    response_execution_id: str
    request_id: str
    profile_id: str
    profile_snapshot_id: str | None
    profile_version: int | None
    consent_snapshot_id: str
    consent_version: int
    request_sha256: str
    status: str
    created_at: str
    updated_at: str
    events: list[ExecutionEventRecord]


class AppendEventResult(_StrictModel):
    event: ExecutionEventRecord
    deduplicated: bool


class ExecutionLedgerError(RuntimeError):
    pass


class ExecutionNotFoundError(ExecutionLedgerError):
    pass


class ExecutionAlreadyRecordedError(ExecutionLedgerError):
    pass


class ConsentStorageDeniedError(ExecutionLedgerError):
    pass


class IdempotencyConflictError(ExecutionLedgerError):
    pass


def data_lake_database_path() -> Path:
    default = (
        Path(__file__).resolve().parents[3]
        / "artifacts"
        / "tips"
        / "interim"
        / "interim.sqlite3"
    )
    return Path(os.getenv("WB_RND_INTERIM_DATABASE", str(default)))


def open_data_lake_store() -> InterimStore:
    store = InterimStore(data_lake_database_path())
    store.migrate()
    return store


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _profile_id(request: RecommendationRequest) -> str:
    if request.source_profile is not None and request.source_profile.subject_id is not None:
        return request.source_profile.subject_id
    digest = hashlib.sha256(
        f"wellnessbox-rnd-request-subject:{request.request_id}".encode()
    ).hexdigest()
    return f"usr_{digest[:32]}"


def _request_payload(request: RecommendationRequest) -> dict[str, Any]:
    payload = request.model_dump(mode="json", exclude_none=False)
    if request.source_profile is not None:
        payload["source_profile"] = request.source_profile.model_dump(
            mode="json",
            exclude_none=False,
        )
    return payload


def _persisted_profile_payload(request: RecommendationRequest) -> dict[str, Any] | None:
    persisted_sources: dict[str, dict[str, Any]] = {}
    consents = request.data_source_consents

    if consents.survey.allow_persistent_storage:
        survey_payload: dict[str, Any] = {
            "user_profile": request.user_profile.model_dump(mode="json"),
            "goals": [goal.value for goal in request.goals],
            "symptoms": [
                item if isinstance(item, str) else item.model_dump(mode="json")
                for item in request.symptoms
            ],
            "conditions": [
                item if isinstance(item, str) else item.model_dump(mode="json")
                for item in request.conditions
            ],
            "allergies": list(request.allergies),
            "risk_flags": [
                item if isinstance(item, str) else item.model_dump(mode="json")
                for item in request.risk_flags
            ],
            "medications": [item.model_dump(mode="json") for item in request.medications],
            "current_supplements": [
                item.model_dump(mode="json") for item in request.current_supplements
            ],
            "dietary_patterns": [
                item if isinstance(item, str) else item.model_dump(mode="json")
                for item in request.dietary_patterns
            ],
            "lifestyle": request.lifestyle.model_dump(mode="json"),
            "preferences": request.preferences.model_dump(mode="json"),
            "laboratory_observations": [
                item.model_dump(mode="json")
                for item in request.laboratory_observations
                if item.source == DataSource.SURVEY
            ],
        }
        if request.source_profile is not None:
            survey_payload["source_profile"] = request.source_profile.profile.model_dump(
                mode="json",
                exclude_none=True,
            )
        persisted_sources[DataSource.SURVEY.value] = survey_payload

    for source in (DataSource.NHIS, DataSource.WEARABLE, DataSource.CGM, DataSource.GENETIC):
        consent = getattr(consents, source.value)
        if not consent.allow_persistent_storage:
            continue
        observations = [
            item.model_dump(mode="json")
            for item in request.laboratory_observations
            if item.source == source
        ]
        if observations:
            persisted_sources[source.value] = {"laboratory_observations": observations}

    if not persisted_sources:
        return None
    return {
        "schema_version": PROFILE_SNAPSHOT_SCHEMA_VERSION,
        "persisted_sources": persisted_sources,
    }


def _consent_payload(request: RecommendationRequest) -> dict[str, Any]:
    return {
        "schema_version": CONSENT_SNAPSHOT_SCHEMA_VERSION,
        "sources": request.data_source_consents.model_dump(mode="json"),
    }


def _all_used_sources_allow_storage(request: RecommendationRequest) -> bool:
    used_sources = {DataSource.SURVEY}
    for source in (DataSource.NHIS, DataSource.WEARABLE, DataSource.CGM, DataSource.GENETIC):
        if getattr(request.input_availability, source.value) and getattr(
            request.data_source_consents, source.value
        ).use_for_recommendation:
            used_sources.add(source)
    return all(
        getattr(request.data_source_consents, source.value).allow_persistent_storage
        for source in used_sources
    )


def _redacted_request_id(request_id: str) -> str:
    digest = hashlib.sha256(f"wellnessbox-rnd-request-id:{request_id}".encode()).hexdigest()
    return f"request_{digest[:32]}"


def _event_from_row(row: sqlite3.Row) -> ExecutionEventRecord:
    return ExecutionEventRecord(
        event_id=str(row["event_id"]),
        execution_id=str(row["execution_id"]),
        consent_snapshot_id=str(row["consent_snapshot_id"]),
        event_index=int(row["event_index"]),
        event_type=str(row["event_type"]),
        source=str(row["source"]),
        idempotency_key=str(row["idempotency_key"]),
        payload=json.loads(row["payload_json"]),
        payload_sha256=str(row["payload_sha256"]),
        created_at=str(row["created_at"]),
    )


class ExecutionLedger:
    def __init__(self, store: InterimStore):
        self.store = store

    def record_recommendation(
        self,
        *,
        request: RecommendationRequest,
        response: RecommendationResponse,
    ) -> ExecutionTrace:
        execution_id = response.execution_id
        profile_id = _profile_id(request)
        request_sha256 = _sha256(_request_payload(request))
        profile_payload = _persisted_profile_payload(request)
        consent_payload = _consent_payload(request)
        store_derived_outputs = _all_used_sources_allow_storage(request)
        stored_request_id = (
            request.request_id
            if store_derived_outputs
            else _redacted_request_id(request.request_id)
        )
        now = _now()

        with self.store.transaction(immediate=True) as connection:
            if connection.execute(
                "select 1 from executions where execution_id=?",
                (execution_id,),
            ).fetchone():
                raise ExecutionAlreadyRecordedError(
                    f"execution_already_recorded:{execution_id}"
                )

            profile_snapshot_id, _profile_version = self._resolve_profile_snapshot(
                connection=connection,
                profile_id=profile_id,
                profile_payload=profile_payload,
                created_at=now,
            )
            consent_snapshot_id, _consent_version = self._resolve_consent_snapshot(
                connection=connection,
                profile_id=profile_id,
                consent_payload=consent_payload,
                created_at=now,
            )
            connection.execute(
                """
                insert into active_profile_consents(
                  profile_id, consent_snapshot_id, updated_at
                ) values (?, ?, ?)
                on conflict(profile_id) do update set
                  consent_snapshot_id=excluded.consent_snapshot_id,
                  updated_at=excluded.updated_at
                """,
                (profile_id, consent_snapshot_id, now),
            )
            connection.execute(
                """
                insert into executions(
                  execution_id, request_id, profile_id, profile_snapshot_id,
                  consent_snapshot_id, request_sha256, status, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, 'RECOMMENDATION_COMPLETED', ?, ?)
                """,
                (
                    execution_id,
                    stored_request_id,
                    profile_id,
                    profile_snapshot_id,
                    consent_snapshot_id,
                    request_sha256,
                    now,
                    now,
                ),
            )
            core_events = self._core_event_payloads(
                response,
                store_derived_outputs=store_derived_outputs,
            )
            for event_index, (event_type, payload) in enumerate(core_events):
                self._insert_event(
                    connection=connection,
                    execution_id=execution_id,
                    consent_snapshot_id=consent_snapshot_id,
                    event_index=event_index,
                    event_type=event_type,
                    source=ExecutionEventSource.SYSTEM,
                    idempotency_key="core",
                    payload=payload,
                    created_at=now,
                )
        return self.get_trace(execution_id)

    def append_event(
        self,
        *,
        execution_id: str,
        event_type: str | ExecutionEventType,
        source: str | ExecutionEventSource,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> AppendEventResult:
        resolved_type = ExecutionEventType(event_type)
        if resolved_type not in {
            ExecutionEventType.CONVERSATION,
            ExecutionEventType.FOLLOWUP_EVALUATION,
        }:
            raise ValueError(f"delayed_event_type_not_allowed:{resolved_type.value}")
        resolved_source = ExecutionEventSource(source)
        if resolved_source == ExecutionEventSource.SYSTEM:
            raise ValueError("delayed_event_source_must_be_user_data_source")
        if (
            resolved_type == ExecutionEventType.CONVERSATION
            and resolved_source != ExecutionEventSource.SURVEY
        ):
            raise ValueError("conversation_event_source_must_be_survey")
        if not idempotency_key.strip():
            raise ValueError("idempotency_key_required")
        if len(idempotency_key) > 128:
            raise ValueError("idempotency_key_too_long")
        payload_sha256 = _sha256(payload)
        now = _now()

        with self.store.transaction(immediate=True) as connection:
            execution = connection.execute(
                "select * from executions where execution_id=?",
                (execution_id,),
            ).fetchone()
            if execution is None:
                raise ExecutionNotFoundError(f"execution_not_found:{execution_id}")
            active_consent = connection.execute(
                """
                select cs.consent_snapshot_id, cs.payload_json
                from active_profile_consents active
                join consent_snapshots cs
                  on cs.consent_snapshot_id=active.consent_snapshot_id
                where active.profile_id=?
                """,
                (execution["profile_id"],),
            ).fetchone()
            if active_consent is None:
                raise ExecutionLedgerError(
                    f"active_consent_not_found:{execution['profile_id']}"
                )
            consent_payload = json.loads(active_consent["payload_json"])
            source_consent = consent_payload["sources"][resolved_source.value]
            if not source_consent["allow_persistent_storage"]:
                raise ConsentStorageDeniedError(
                    f"persistent_storage_consent_denied:{resolved_source.value}"
                )

            existing = connection.execute(
                """
                select * from execution_events
                where execution_id=? and event_type=? and idempotency_key=?
                """,
                (execution_id, resolved_type.value, idempotency_key),
            ).fetchone()
            if existing is not None:
                if (
                    existing["source"] != resolved_source.value
                    or existing["payload_sha256"] != payload_sha256
                ):
                    raise IdempotencyConflictError(
                        "event_idempotency_conflict:"
                        f"{execution_id}:{resolved_type.value}:{idempotency_key}"
                    )
                return AppendEventResult(
                    event=_event_from_row(existing),
                    deduplicated=True,
                )

            event_index = int(
                connection.execute(
                    """
                    select coalesce(max(event_index), -1) + 1
                    from execution_events where execution_id=?
                    """,
                    (execution_id,),
                ).fetchone()[0]
            )
            event = self._insert_event(
                connection=connection,
                execution_id=execution_id,
                consent_snapshot_id=str(active_consent["consent_snapshot_id"]),
                event_index=event_index,
                event_type=resolved_type,
                source=resolved_source,
                idempotency_key=idempotency_key,
                payload=payload,
                created_at=now,
            )
            status = (
                "FOLLOWUP_EVALUATION_RECORDED"
                if resolved_type == ExecutionEventType.FOLLOWUP_EVALUATION
                else "CONVERSATION_RECORDED"
            )
            connection.execute(
                "update executions set status=?, updated_at=? where execution_id=?",
                (status, now, execution_id),
            )
        return AppendEventResult(event=event, deduplicated=False)

    def get_trace(self, execution_id: str) -> ExecutionTrace:
        rows = self.store.rows(
            """
            select e.*, ps.version as profile_version, cs.version as consent_version
            from executions e
            left join profile_snapshots ps
              on ps.profile_snapshot_id=e.profile_snapshot_id
            join consent_snapshots cs
              on cs.consent_snapshot_id=e.consent_snapshot_id
            where e.execution_id=?
            """,
            (execution_id,),
        )
        if not rows:
            raise ExecutionNotFoundError(f"execution_not_found:{execution_id}")
        row = rows[0]
        events = [
            _event_from_row(event)
            for event in self.store.rows(
                """
                select * from execution_events
                where execution_id=? order by event_index
                """,
                (execution_id,),
            )
        ]
        return ExecutionTrace(
            execution_id=str(row["execution_id"]),
            response_execution_id=str(row["execution_id"]),
            request_id=str(row["request_id"]),
            profile_id=str(row["profile_id"]),
            profile_snapshot_id=(
                None if row["profile_snapshot_id"] is None else str(row["profile_snapshot_id"])
            ),
            profile_version=(
                None if row["profile_version"] is None else int(row["profile_version"])
            ),
            consent_snapshot_id=str(row["consent_snapshot_id"]),
            consent_version=int(row["consent_version"]),
            request_sha256=str(row["request_sha256"]),
            status=str(row["status"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            events=events,
        )

    @staticmethod
    def _resolve_profile_snapshot(
        *,
        connection: sqlite3.Connection,
        profile_id: str,
        profile_payload: dict[str, Any] | None,
        created_at: str,
    ) -> tuple[str | None, int | None]:
        if profile_payload is None:
            return None, None
        payload_sha256 = _sha256(profile_payload)
        existing = connection.execute(
            """
            select profile_snapshot_id, version from profile_snapshots
            where profile_id=? and payload_sha256=?
            """,
            (profile_id, payload_sha256),
        ).fetchone()
        if existing is not None:
            return str(existing["profile_snapshot_id"]), int(existing["version"])
        version = int(
            connection.execute(
                "select coalesce(max(version), 0) + 1 from profile_snapshots where profile_id=?",
                (profile_id,),
            ).fetchone()[0]
        )
        snapshot_id = f"profile_snapshot_{uuid4().hex}"
        persisted_sources = sorted(profile_payload["persisted_sources"])
        connection.execute(
            """
            insert into profile_snapshots(
              profile_snapshot_id, profile_id, version, schema_version, data_class,
              persisted_sources_json, payload_json, payload_sha256, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                profile_id,
                version,
                PROFILE_SNAPSHOT_SCHEMA_VERSION,
                DataClass.INTERIM_RUNTIME_EVENT,
                _canonical_json(persisted_sources),
                _canonical_json(profile_payload),
                payload_sha256,
                created_at,
            ),
        )
        return snapshot_id, version

    @staticmethod
    def _resolve_consent_snapshot(
        *,
        connection: sqlite3.Connection,
        profile_id: str,
        consent_payload: dict[str, Any],
        created_at: str,
    ) -> tuple[str, int]:
        payload_sha256 = _sha256(consent_payload)
        existing = connection.execute(
            """
            select consent_snapshot_id, version from consent_snapshots
            where profile_id=? and payload_sha256=?
            """,
            (profile_id, payload_sha256),
        ).fetchone()
        if existing is not None:
            return str(existing["consent_snapshot_id"]), int(existing["version"])
        version = int(
            connection.execute(
                "select coalesce(max(version), 0) + 1 from consent_snapshots where profile_id=?",
                (profile_id,),
            ).fetchone()[0]
        )
        snapshot_id = f"consent_snapshot_{uuid4().hex}"
        connection.execute(
            """
            insert into consent_snapshots(
              consent_snapshot_id, profile_id, version, schema_version,
              payload_json, payload_sha256, created_at
            ) values (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                profile_id,
                version,
                CONSENT_SNAPSHOT_SCHEMA_VERSION,
                _canonical_json(consent_payload),
                payload_sha256,
                created_at,
            ),
        )
        return snapshot_id, version

    @staticmethod
    def _core_event_payloads(
        response: RecommendationResponse,
        *,
        store_derived_outputs: bool,
    ) -> list[tuple[ExecutionEventType, dict[str, Any]]]:
        if not store_derived_outputs:
            metadata_only = {"storage_scope": "metadata_only"}
            return [
                (ExecutionEventType.RECOMMENDATION, metadata_only),
                (ExecutionEventType.SAFETY, metadata_only),
                (ExecutionEventType.OPTIMIZATION, metadata_only),
            ]
        return [
            (
                ExecutionEventType.RECOMMENDATION,
                {
                    "request_id": response.request_id,
                    "decision_id": response.decision_id,
                    "status": response.status.value,
                    "next_action": response.next_action.value,
                    "follow_up_window_days": response.follow_up_window_days,
                },
            ),
            (
                ExecutionEventType.SAFETY,
                {
                    "status": response.safety_summary.status.value,
                    "safety_flags": list(response.safety_flags),
                    "blocked_reasons": list(response.safety_summary.blocked_reasons),
                    "warnings": list(response.safety_summary.warnings),
                    "excluded_ingredients": list(
                        response.safety_summary.excluded_ingredients
                    ),
                    "rule_ids": [
                        rule.rule_id for rule in response.safety_summary.rule_refs
                    ],
                },
            ),
            (
                ExecutionEventType.OPTIMIZATION,
                {
                    "status": (
                        "blocked"
                        if response.status.value == "blocked"
                        else "completed"
                    ),
                    "selected_count": len(response.recommendations),
                    "selected_ingredient_keys": [
                        item.ingredient_key for item in response.recommendations
                    ],
                },
            ),
        ]

    @staticmethod
    def _insert_event(
        *,
        connection: sqlite3.Connection,
        execution_id: str,
        consent_snapshot_id: str,
        event_index: int,
        event_type: ExecutionEventType,
        source: ExecutionEventSource,
        idempotency_key: str,
        payload: dict[str, Any],
        created_at: str,
    ) -> ExecutionEventRecord:
        event_id = f"event_{uuid4().hex}"
        payload_sha256 = _sha256(payload)
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type, source,
              idempotency_key, payload_json, payload_sha256, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                execution_id,
                consent_snapshot_id,
                event_index,
                event_type.value,
                source.value,
                idempotency_key,
                _canonical_json(payload),
                payload_sha256,
                created_at,
            ),
        )
        return ExecutionEventRecord(
            event_id=event_id,
            execution_id=execution_id,
            consent_snapshot_id=consent_snapshot_id,
            event_index=event_index,
            event_type=event_type,
            source=source,
            idempotency_key=idempotency_key,
            payload=payload,
            payload_sha256=payload_sha256,
            created_at=created_at,
        )


__all__ = [
    "AppendEventResult",
    "CONSENT_SNAPSHOT_SCHEMA_VERSION",
    "ConsentStorageDeniedError",
    "ExecutionAlreadyRecordedError",
    "ExecutionEventRecord",
    "ExecutionEventSource",
    "ExecutionEventType",
    "ExecutionLedger",
    "ExecutionLedgerError",
    "ExecutionNotFoundError",
    "ExecutionTrace",
    "IdempotencyConflictError",
    "PROFILE_SNAPSHOT_SCHEMA_VERSION",
    "data_lake_database_path",
    "open_data_lake_store",
]
