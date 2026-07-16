from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from wellnessbox_rnd.interim.contracts import DataClass, EventPayloadState
from wellnessbox_rnd.interim.data_lake import (
    ConsentStorageDeniedError,
    ExecutionLedgerError,
    IdempotencyConflictError,
)
from wellnessbox_rnd.interim.store import InterimStore

USER_BEHAVIOR_LOG_CLASS = "user_behavior"
RESEARCH_EVALUATION_LOG_CLASS = "research_evaluation"

RESEARCH_EVENT_TYPES = frozenset(
    {
        "conversation",
        "recommendation",
        "safety",
        "optimization",
        "followup_evaluation",
    }
)


class BehaviorEventName(StrEnum):
    PAGE_VIEW = "page_view"
    PRODUCT_EXPOSURE = "product_exposure"
    PRODUCT_CLICK = "product_click"
    CART_ADD = "cart_add"
    ORDER_VIEW = "order_view"
    NOTIFICATION_OPEN = "notification_open"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


BEHAVIOR_EVENT_NAMES = frozenset(item.value for item in BehaviorEventName)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BehaviorEventRecord(_StrictModel):
    behavior_event_id: str
    profile_id: str
    consent_snapshot_id: str
    log_class: str
    event_name: BehaviorEventName
    occurred_at: str
    idempotency_key: str
    payload: dict[str, Any]
    payload_sha256: str
    effective_payload_sha256: str
    payload_state: EventPayloadState
    data_class: DataClass
    created_at: str


class AppendBehaviorEventResult(_StrictModel):
    event: BehaviorEventRecord
    deduplicated: bool


class LogClassSummary(_StrictModel):
    research_evaluation_event_count: int
    user_behavior_event_count: int
    research_event_table: str
    behavior_event_table: str
    research_log_class_values: list[str]
    behavior_log_class_values: list[str]
    cross_contamination_count: int


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


def _normalized_occurred_at(occurred_at: str) -> str:
    try:
        parsed = datetime.fromisoformat(occurred_at)
    except ValueError as error:
        raise ValueError(f"behavior_event_occurred_at_invalid:{occurred_at}") from error
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError("behavior_event_occurred_at_must_be_timezone_aware")
    return parsed.astimezone(UTC).isoformat()


def _record_from_row(row: sqlite3.Row) -> BehaviorEventRecord:
    return BehaviorEventRecord(
        behavior_event_id=str(row["behavior_event_id"]),
        profile_id=str(row["profile_id"]),
        consent_snapshot_id=str(row["consent_snapshot_id"]),
        log_class=str(row["log_class"]),
        event_name=str(row["event_name"]),
        occurred_at=str(row["occurred_at"]),
        idempotency_key=str(row["idempotency_key"]),
        payload=json.loads(row["payload_json"]),
        payload_sha256=str(row["payload_sha256"]),
        effective_payload_sha256=str(row["effective_payload_sha256"]),
        payload_state=str(row["payload_state"]),
        data_class=str(row["data_class"]),
        created_at=str(row["created_at"]),
    )


class BehaviorLogRecorder:
    def __init__(self, store: InterimStore):
        self.store = store

    def append_event(
        self,
        *,
        profile_id: str,
        event_name: str,
        occurred_at: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> AppendBehaviorEventResult:
        if event_name in RESEARCH_EVENT_TYPES:
            raise ValueError(f"research_event_type_not_allowed_in_behavior_log:{event_name}")
        if event_name not in BEHAVIOR_EVENT_NAMES:
            raise ValueError(f"behavior_event_name_not_supported:{event_name}")
        if not idempotency_key.strip():
            raise ValueError("idempotency_key_required")
        if len(idempotency_key) > 128:
            raise ValueError("idempotency_key_too_long")
        resolved_name = BehaviorEventName(event_name)
        normalized_occurred_at = _normalized_occurred_at(occurred_at)
        payload_sha256 = _sha256(payload)
        now = _now()

        with self.store.transaction(immediate=True) as connection:
            active_consent = connection.execute(
                """
                select cs.consent_snapshot_id, cs.payload_json
                from active_profile_consents active
                join consent_snapshots cs
                  on cs.consent_snapshot_id=active.consent_snapshot_id
                where active.profile_id=?
                """,
                (profile_id,),
            ).fetchone()
            if active_consent is None:
                raise ExecutionLedgerError(f"active_consent_not_found:{profile_id}")
            consent_payload = json.loads(active_consent["payload_json"])
            survey_consent = consent_payload["sources"]["survey"]
            if not survey_consent["allow_persistent_storage"]:
                raise ConsentStorageDeniedError("persistent_storage_consent_denied:survey")

            existing = connection.execute(
                """
                select * from behavior_events
                where profile_id=? and event_name=? and idempotency_key=?
                """,
                (profile_id, resolved_name.value, idempotency_key),
            ).fetchone()
            if existing is not None:
                if (
                    existing["payload_sha256"] != payload_sha256
                    or existing["occurred_at"] != normalized_occurred_at
                ):
                    raise IdempotencyConflictError(
                        "behavior_event_idempotency_conflict:"
                        f"{profile_id}:{resolved_name.value}:{idempotency_key}"
                    )
                return AppendBehaviorEventResult(
                    event=_record_from_row(existing),
                    deduplicated=True,
                )

            behavior_event_id = f"behavior_{uuid4().hex}"
            connection.execute(
                """
                insert into behavior_events(
                  behavior_event_id, profile_id, consent_snapshot_id, log_class,
                  event_name, occurred_at, idempotency_key, payload_json,
                  payload_sha256, effective_payload_sha256, data_class, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    behavior_event_id,
                    profile_id,
                    str(active_consent["consent_snapshot_id"]),
                    USER_BEHAVIOR_LOG_CLASS,
                    resolved_name.value,
                    normalized_occurred_at,
                    idempotency_key,
                    _canonical_json(payload),
                    payload_sha256,
                    payload_sha256,
                    DataClass.INTERIM_RUNTIME_EVENT,
                    now,
                ),
            )
            event = BehaviorEventRecord(
                behavior_event_id=behavior_event_id,
                profile_id=profile_id,
                consent_snapshot_id=str(active_consent["consent_snapshot_id"]),
                log_class=USER_BEHAVIOR_LOG_CLASS,
                event_name=resolved_name,
                occurred_at=normalized_occurred_at,
                idempotency_key=idempotency_key,
                payload=payload,
                payload_sha256=payload_sha256,
                effective_payload_sha256=payload_sha256,
                payload_state=EventPayloadState.ACTIVE,
                data_class=DataClass.INTERIM_RUNTIME_EVENT,
                created_at=now,
            )
        return AppendBehaviorEventResult(event=event, deduplicated=False)

    def log_class_summary(self) -> LogClassSummary:
        research_count = int(self.store.scalar("select count(*) from execution_events"))
        behavior_count = int(self.store.scalar("select count(*) from behavior_events"))
        behavior_names_in_research = int(
            self.store.scalar(
                """
                select count(*) from execution_events
                where event_type in ({placeholders})
                """.format(
                    placeholders=",".join("?" for _ in BEHAVIOR_EVENT_NAMES)
                ),
                tuple(sorted(BEHAVIOR_EVENT_NAMES)),
            )
        )
        research_types_in_behavior = int(
            self.store.scalar(
                """
                select count(*) from behavior_events
                where event_name in ({placeholders})
                """.format(
                    placeholders=",".join("?" for _ in RESEARCH_EVENT_TYPES)
                ),
                tuple(sorted(RESEARCH_EVENT_TYPES)),
            )
        )
        wrong_behavior_log_class = int(
            self.store.scalar(
                "select count(*) from behavior_events where log_class != ?",
                (USER_BEHAVIOR_LOG_CLASS,),
            )
        )
        return LogClassSummary(
            research_evaluation_event_count=research_count,
            user_behavior_event_count=behavior_count,
            research_event_table="execution_events",
            behavior_event_table="behavior_events",
            research_log_class_values=[RESEARCH_EVALUATION_LOG_CLASS],
            behavior_log_class_values=[USER_BEHAVIOR_LOG_CLASS],
            cross_contamination_count=(
                behavior_names_in_research
                + research_types_in_behavior
                + wrong_behavior_log_class
            ),
        )


__all__ = [
    "AppendBehaviorEventResult",
    "BEHAVIOR_EVENT_NAMES",
    "BehaviorEventName",
    "BehaviorEventRecord",
    "BehaviorLogRecorder",
    "LogClassSummary",
    "RESEARCH_EVALUATION_LOG_CLASS",
    "RESEARCH_EVENT_TYPES",
    "USER_BEHAVIOR_LOG_CLASS",
]
