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

from wellnessbox_rnd.interim.contracts import DataClass, EventPayloadState
from wellnessbox_rnd.interim.execution_identity import (
    DatasetIdentityRecord,
    ExecutionIdentityRecord,
    build_execution_identity,
)
from wellnessbox_rnd.interim.knowledge_lineage import persist_execution_knowledge_lineage
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.pro_followup import (
    PROFollowUpEventV1,
    is_versioned_pro_followup_payload_v1,
    normalize_pro_followup_event_v1,
    validate_pro_followup_sequence_v1,
)
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


class KnowledgeOutputType(StrEnum):
    RECOMMENDATION_ITEM = "recommendation_item"
    SAFETY_RULE = "safety_rule"
    RECOMMENDATION_DECISION = "recommendation_decision"


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
    effective_payload_sha256: str
    payload_state: EventPayloadState
    created_at: str


class KnowledgeLineageRecord(_StrictModel):
    lineage_id: str
    execution_id: str
    event_id: str
    event_type: ExecutionEventType
    output_type: KnowledgeOutputType
    output_key: str
    rule_id: str
    rule_type: str
    rule_severity: str
    rule_valid_from: str | None
    rule_valid_to: str | None
    rule_status: str
    claim_id: str
    normalized_claim_type: str
    claim_text: str
    evidence_id: str
    passage_text: str
    page_or_section: str | None
    line_start: int | None
    line_end: int | None
    source_id: str
    source_title: str
    source_type: str
    source_uri: str
    upstream_reference_uri: str | None
    license_status: str
    source_effective_at: str | None
    source_retired_at: str | None
    source_content_checksum: str | None
    data_class: DataClass
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
    knowledge_lineage: list[KnowledgeLineageRecord]
    execution_identity: ExecutionIdentityRecord | None = None


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


def derive_profile_id(request: RecommendationRequest) -> str:
    """Return the canonical execution-ledger profile identity for a request."""
    return _profile_id(request)


def _request_payload(request: RecommendationRequest) -> dict[str, Any]:
    payload = request.model_dump(mode="json", exclude_none=False)
    if request.source_profile is not None:
        payload["source_profile"] = request.source_profile.model_dump(
            mode="json",
            exclude_none=False,
        )
    return payload


def replay_response_payload(response: RecommendationResponse) -> dict[str, Any]:
    payload = response.model_dump(mode="json", exclude_none=False)
    payload.pop("execution_id", None)
    payload.pop("decision_id", None)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("generated_at", None)
    safety_summary = payload.get("safety_summary")
    if isinstance(safety_summary, dict):
        safety_summary.pop("applied_at", None)
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
        source_payload: dict[str, Any] = {}
        if observations:
            source_payload["laboratory_observations"] = observations
        snapshot = request.sensor_genetic_snapshot
        if snapshot is not None:
            if source == DataSource.WEARABLE and snapshot.wearable_available:
                source_payload["sensor_genetic_snapshot"] = {
                    "sleep_hours": snapshot.sleep_hours,
                    "steps": snapshot.steps,
                    "resting_heart_rate": snapshot.resting_heart_rate,
                }
            elif source == DataSource.CGM and snapshot.cgm_available:
                source_payload["sensor_genetic_snapshot"] = {
                    "mean_glucose_mg_dl": snapshot.mean_glucose_mg_dl,
                    "time_in_range_pct": snapshot.time_in_range_pct,
                    "time_in_range_low_mg_dl": snapshot.time_in_range_low_mg_dl,
                    "time_in_range_high_mg_dl": snapshot.time_in_range_high_mg_dl,
                    "postprandial_peak_mg_dl": snapshot.postprandial_peak_mg_dl,
                    "postprandial_rise_mg_dl": snapshot.postprandial_rise_mg_dl,
                    "post_meal_spike_concern": snapshot.post_meal_spike_concern,
                }
            elif source == DataSource.GENETIC and snapshot.genetic_available:
                source_payload["sensor_genetic_snapshot"] = {
                    "genetic_tags": list(snapshot.genetic_tags),
                    "genetic_variants": [
                        item.model_dump(mode="json") for item in snapshot.genetic_variants
                    ],
                }
        if source_payload:
            persisted_sources[source.value] = source_payload

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


def _all_request_sources_allow_storage(request: RecommendationRequest) -> bool:
    represented_sources = {DataSource.SURVEY}
    for source in (DataSource.NHIS, DataSource.WEARABLE, DataSource.CGM, DataSource.GENETIC):
        if getattr(request.input_availability, source.value) or any(
            observation.source == source for observation in request.laboratory_observations
        ):
            represented_sources.add(source)
    return all(
        getattr(request.data_source_consents, source.value).allow_persistent_storage
        for source in represented_sources
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
        effective_payload_sha256=str(row["effective_payload_sha256"]),
        payload_state=str(row["payload_state"]),
        created_at=str(row["created_at"]),
    )


def _knowledge_lineage_from_row(row: sqlite3.Row) -> KnowledgeLineageRecord:
    source_metadata = json.loads(row["source_metadata_json"])
    return KnowledgeLineageRecord(
        lineage_id=str(row["lineage_id"]),
        execution_id=str(row["execution_id"]),
        event_id=str(row["event_id"]),
        event_type=str(row["event_type"]),
        output_type=str(row["output_type"]),
        output_key=str(row["output_key"]),
        rule_id=str(row["rule_id"]),
        rule_type=str(row["rule_type"]),
        rule_severity=str(row["rule_severity"]),
        rule_valid_from=(
            None if row["rule_valid_from"] is None else str(row["rule_valid_from"])
        ),
        rule_valid_to=(
            None if row["rule_valid_to"] is None else str(row["rule_valid_to"])
        ),
        rule_status=str(row["rule_status"]),
        claim_id=str(row["claim_id"]),
        normalized_claim_type=str(row["normalized_claim_type"]),
        claim_text=str(row["claim_text"]),
        evidence_id=str(row["evidence_id"]),
        passage_text=str(row["passage_text"]),
        page_or_section=(
            None if row["page_or_section"] is None else str(row["page_or_section"])
        ),
        line_start=None if row["line_start"] is None else int(row["line_start"]),
        line_end=None if row["line_end"] is None else int(row["line_end"]),
        source_id=str(row["source_id"]),
        source_title=str(row["source_title"]),
        source_type=str(row["source_type"]),
        source_uri=str(row["source_uri"]),
        upstream_reference_uri=source_metadata.get("upstream_reference_uri"),
        license_status=str(row["license_status"]),
        source_effective_at=(
            None
            if row["source_effective_at"] is None
            else str(row["source_effective_at"])
        ),
        source_retired_at=(
            None
            if row["source_retired_at"] is None
            else str(row["source_retired_at"])
        ),
        source_content_checksum=source_metadata.get("content_checksum"),
        data_class=str(row["data_class"]),
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
        if response.plan_id != request.plan_id:
            raise ValueError("recommendation_plan_id_mismatch")
        execution_id = response.execution_id
        profile_id = _profile_id(request)
        request_payload = _request_payload(request)
        request_sha256 = _sha256(request_payload)
        profile_payload = _persisted_profile_payload(request)
        consent_payload = _consent_payload(request)
        store_derived_outputs = _all_used_sources_allow_storage(request)
        store_replay_snapshot = _all_request_sources_allow_storage(request)
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
            identity = build_execution_identity(
                execution_id=execution_id,
                response=response,
                created_at=now,
            )
            connection.execute(
                """
                insert into execution_identities(
                  execution_id, model_id, engine_version, code_commit,
                  code_commit_source, dataset_ids_json, config_json,
                  config_sha256, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identity.execution_id,
                    identity.model_id,
                    identity.engine_version,
                    identity.code_commit,
                    identity.code_commit_source,
                    _canonical_json(
                        [item.model_dump(mode="json") for item in identity.datasets]
                    ),
                    _canonical_json(identity.config),
                    identity.config_sha256,
                    identity.created_at,
                ),
            )
            if store_replay_snapshot:
                expected_output = replay_response_payload(response)
                connection.execute(
                    """
                    insert into execution_replay_snapshots(
                      execution_id, request_json, request_sha256,
                      expected_output_json, expected_output_sha256, created_at
                    ) values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        execution_id,
                        _canonical_json(request_payload),
                        request_sha256,
                        _canonical_json(expected_output),
                        _sha256(expected_output),
                        now,
                    ),
                )
            core_events = self._core_event_payloads(
                response,
                store_derived_outputs=store_derived_outputs,
            )
            event_ids: dict[str, str] = {}
            for event_index, (event_type, payload) in enumerate(core_events):
                event = self._insert_event(
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
                event_ids[event_type.value] = event.event_id
            if store_derived_outputs:
                persist_execution_knowledge_lineage(
                    connection=connection,
                    execution_id=execution_id,
                    response=response,
                    event_ids=event_ids,
                    created_at=now,
                )
        return self.get_trace(execution_id)

    def get_trace_for_request(
        self,
        request: RecommendationRequest,
    ) -> ExecutionTrace | None:
        rows = self.store.rows(
            """
            select execution_id, request_sha256 from executions
            where request_id=? and profile_id=? order by created_at
            """,
            (request.request_id, _profile_id(request)),
        )
        if not rows:
            return None
        if len(rows) != 1:
            raise IdempotencyConflictError(
                f"duplicate_recommendation_request_id:{request.request_id}"
            )
        expected_sha256 = _sha256(_request_payload(request))
        if rows[0]["request_sha256"] != expected_sha256:
            raise IdempotencyConflictError(
                f"recommendation_request_id_conflict:{request.request_id}"
            )
        return self.get_trace(str(rows[0]["execution_id"]))

    def append_event(
        self,
        *,
        execution_id: str,
        event_type: str | ExecutionEventType,
        source: str | ExecutionEventSource,
        idempotency_key: str,
        payload: dict[str, Any] | PROFollowUpEventV1,
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
        versioned_pro_event = None
        payload_is_versioned_pro = is_versioned_pro_followup_payload_v1(payload)
        if (
            payload_is_versioned_pro
            and resolved_type != ExecutionEventType.FOLLOWUP_EVALUATION
        ):
            raise ValueError(
                "versioned_pro_followup_requires_followup_evaluation_event_type"
            )
        if (
            resolved_type == ExecutionEventType.FOLLOWUP_EVALUATION
            and payload_is_versioned_pro
        ):
            versioned_pro_event = normalize_pro_followup_event_v1(payload)
            if resolved_source != ExecutionEventSource.SURVEY:
                raise ValueError("versioned_pro_followup_source_must_be_survey")
            resolved_payload = versioned_pro_event.model_dump(mode="json")
        elif isinstance(payload, dict):
            resolved_payload = payload
        else:
            raise TypeError("delayed event payload must be a dictionary")
        payload_sha256 = _sha256(resolved_payload)
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

            if versioned_pro_event is not None:
                recommendation_row = connection.execute(
                    """
                    select payload_json from execution_events
                    where execution_id=? and event_type=?
                    order by event_index
                    limit 1
                    """,
                    (execution_id, ExecutionEventType.RECOMMENDATION.value),
                ).fetchone()
                if recommendation_row is None:
                    raise ValueError("pro_followup_recommendation_event_not_found")
                recommendation_payload = json.loads(recommendation_row["payload_json"])
                if recommendation_payload.get("plan_id") != versioned_pro_event.plan_id:
                    raise ValueError("pro_followup_plan_id_mismatch")
                prior_pro_events = []
                for row in connection.execute(
                    """
                    select payload_json from execution_events
                    where execution_id=? and event_type=?
                    order by event_index
                    """,
                    (execution_id, ExecutionEventType.FOLLOWUP_EVALUATION.value),
                ):
                    prior_payload = json.loads(row["payload_json"])
                    if is_versioned_pro_followup_payload_v1(prior_payload):
                        prior_pro_events.append(
                            normalize_pro_followup_event_v1(prior_payload)
                        )
                sequence_issues = validate_pro_followup_sequence_v1(
                    prior_pro_events,
                    versioned_pro_event,
                )
                if sequence_issues:
                    raise ValueError(
                        "invalid_pro_followup_sequence::" + "|".join(sequence_issues)
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
                payload=resolved_payload,
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
        knowledge_lineage = [
            _knowledge_lineage_from_row(lineage)
            for lineage in self.store.rows(
                """
                select l.*, ee.event_type,
                       kr.rule_type, kr.severity as rule_severity,
                       kr.valid_from as rule_valid_from,
                       kr.valid_to as rule_valid_to,
                       kr.status as rule_status,
                       kc.normalized_claim_type, kc.claim_text,
                       ep.passage_text, ep.page_or_section,
                       ep.line_start, ep.line_end,
                       src.title as source_title,
                       src.source_tier as source_type,
                       src.canonical_uri as source_uri,
                       src.license_status,
                       src.effective_at as source_effective_at,
                       src.retired_at as source_retired_at,
                       src.metadata_json as source_metadata_json
                from execution_knowledge_lineage l
                join execution_events ee on ee.event_id=l.event_id
                join knowledge_rules kr on kr.rule_id=l.rule_id
                join knowledge_claims kc on kc.claim_id=l.claim_id
                join evidence_passages ep on ep.evidence_id=l.evidence_id
                join source_registry src on src.source_id=l.source_id
                where l.execution_id=?
                order by ee.event_index, l.output_type, l.output_key, l.claim_id
                """,
                (execution_id,),
            )
        ]
        identity_rows = self.store.rows(
            "select * from execution_identities where execution_id=?",
            (execution_id,),
        )
        execution_identity = None
        if identity_rows:
            identity_row = identity_rows[0]
            config = json.loads(identity_row["config_json"])
            execution_identity = ExecutionIdentityRecord(
                execution_id=str(identity_row["execution_id"]),
                model_id=str(identity_row["model_id"]),
                engine_version=str(identity_row["engine_version"]),
                code_commit=str(identity_row["code_commit"]),
                code_commit_source=str(identity_row["code_commit_source"]),
                datasets=[
                    DatasetIdentityRecord(**item)
                    for item in json.loads(identity_row["dataset_ids_json"])
                ],
                config=config,
                config_sha256=str(identity_row["config_sha256"]),
                created_at=str(identity_row["created_at"]),
            )
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
            knowledge_lineage=knowledge_lineage,
            execution_identity=execution_identity,
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
                    "plan_id": response.plan_id,
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
                    "plan_id": response.plan_id,
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
              idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            effective_payload_sha256=payload_sha256,
            payload_state=EventPayloadState.ACTIVE,
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
    "replay_response_payload",
    "IdempotencyConflictError",
    "KnowledgeLineageRecord",
    "KnowledgeOutputType",
    "PROFILE_SNAPSHOT_SCHEMA_VERSION",
    "data_lake_database_path",
    "open_data_lake_store",
]
