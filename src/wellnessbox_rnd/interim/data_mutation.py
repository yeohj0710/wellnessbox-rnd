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
    ExecutionLedgerError,
    IdempotencyConflictError,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.pro_followup import (
    is_versioned_pro_followup_payload_v1,
    normalize_pro_followup_event_v1,
)


class EventMutationTargetType(StrEnum):
    EXECUTION_EVENT = "execution_event"
    BEHAVIOR_EVENT = "behavior_event"


class EventMutationOperation(StrEnum):
    CORRECTION = "correction"
    DELETION = "deletion"


class EventMutationNotFoundError(ExecutionLedgerError):
    pass


class EventMutationStateError(ExecutionLedgerError):
    pass


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventMutationRecord(_StrictModel):
    mutation_id: str
    profile_id: str
    target_type: EventMutationTargetType
    target_event_id: str
    operation: EventMutationOperation
    idempotency_key: str
    request_sha256: str
    prior_payload_sha256: str
    result_payload_sha256: str
    previous_mutation_id: str | None
    previous_mutation_sha256: str | None
    mutation_index: int
    mutation_sha256: str
    created_at: str


class EventMutationResult(_StrictModel):
    mutation: EventMutationRecord
    deduplicated: bool


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


def _record_from_row(row: sqlite3.Row) -> EventMutationRecord:
    return EventMutationRecord(
        mutation_id=str(row["mutation_id"]),
        profile_id=str(row["profile_id"]),
        target_type=str(row["target_type"]),
        target_event_id=str(row["target_event_id"]),
        operation=str(row["operation"]),
        idempotency_key=str(row["idempotency_key"]),
        request_sha256=str(row["request_sha256"]),
        prior_payload_sha256=str(row["prior_payload_sha256"]),
        result_payload_sha256=str(row["result_payload_sha256"]),
        previous_mutation_id=(
            None
            if row["previous_mutation_id"] is None
            else str(row["previous_mutation_id"])
        ),
        previous_mutation_sha256=(
            None
            if row["previous_mutation_sha256"] is None
            else str(row["previous_mutation_sha256"])
        ),
        mutation_index=int(row["mutation_index"]),
        mutation_sha256=str(row["mutation_sha256"]),
        created_at=str(row["created_at"]),
    )


class DataMutationLedger:
    """Apply event corrections or deletions while retaining hash lineage."""

    def __init__(self, store: InterimStore):
        self.store = store

    def apply(
        self,
        *,
        profile_id: str,
        target_type: str | EventMutationTargetType,
        target_event_id: str,
        operation: str | EventMutationOperation,
        idempotency_key: str,
        replacement_payload: dict[str, Any] | None = None,
    ) -> EventMutationResult:
        resolved_target_type = EventMutationTargetType(target_type)
        resolved_operation = EventMutationOperation(operation)
        self._validate_request(
            profile_id=profile_id,
            target_event_id=target_event_id,
            idempotency_key=idempotency_key,
            operation=resolved_operation,
            replacement_payload=replacement_payload,
        )
        request_identity = {
            "profile_id": profile_id,
            "target_type": resolved_target_type.value,
            "target_event_id": target_event_id,
            "operation": resolved_operation.value,
            "replacement_payload": replacement_payload,
        }
        request_sha256 = _sha256(request_identity)

        should_secure_compact = False
        with self.store.transaction(immediate=True) as connection:
            existing = connection.execute(
                """
                select * from event_mutations
                where profile_id=? and target_type=? and target_event_id=?
                  and idempotency_key=?
                """,
                (
                    profile_id,
                    resolved_target_type.value,
                    target_event_id,
                    idempotency_key,
                ),
            ).fetchone()
            if existing is not None:
                if existing["request_sha256"] != request_sha256:
                    raise IdempotencyConflictError(
                        "event_mutation_idempotency_conflict:"
                        f"{profile_id}:{resolved_target_type.value}:"
                        f"{target_event_id}:{idempotency_key}"
                    )
                should_secure_compact = (
                    str(existing["operation"])
                    == EventMutationOperation.DELETION.value
                )
                result = EventMutationResult(
                    mutation=_record_from_row(existing),
                    deduplicated=True,
                )
            else:
                target = self._target_row(
                    connection=connection,
                    profile_id=profile_id,
                    target_type=resolved_target_type,
                    target_event_id=target_event_id,
                )
                if str(target["payload_state"]) == EventPayloadState.DELETED.value:
                    raise EventMutationStateError(
                        "event_payload_already_deleted:"
                        f"{resolved_target_type.value}:{target_event_id}"
                    )
                if resolved_target_type == EventMutationTargetType.EXECUTION_EVENT:
                    current_payload = json.loads(target["payload_json"])
                    if current_payload.get("schema_version") == "plan_lifecycle_transition_v1":
                        raise EventMutationStateError(
                            f"plan_lifecycle_event_immutable:{target_event_id}"
                        )
                    consumed = connection.execute(
                        """
                        select 1 from execution_events
                        where payload_state='ACTIVE'
                          and json_extract(payload_json, '$.schema_version')=
                            'plan_lifecycle_transition_v1'
                          and json_extract(payload_json, '$.replacement_candidate_event_id')=?
                        limit 1
                        """,
                        (target_event_id,),
                    ).fetchone()
                    if consumed is not None:
                        raise EventMutationStateError(
                            f"consumed_replacement_candidate_immutable:{target_event_id}"
                        )
                if (
                    resolved_operation == EventMutationOperation.CORRECTION
                    and resolved_target_type == EventMutationTargetType.EXECUTION_EVENT
                ):
                    assert replacement_payload is not None
                    current_payload = json.loads(target["payload_json"])
                    current_is_pro = is_versioned_pro_followup_payload_v1(
                        current_payload
                    )
                    replacement_is_pro = is_versioned_pro_followup_payload_v1(
                        replacement_payload
                    )
                    if current_is_pro != replacement_is_pro:
                        raise ValueError(
                            "pro_followup_correction_cannot_change_contract_kind"
                        )
                    if not current_is_pro:
                        replacement_pro_event = None
                    else:
                        current_pro_event = normalize_pro_followup_event_v1(
                            current_payload
                        )
                        replacement_pro_event = normalize_pro_followup_event_v1(
                            replacement_payload
                        )
                    if replacement_pro_event is not None:
                        immutable_identity_fields = (
                            "assessment_id",
                            "plan_id",
                            "data_class",
                            "timepoint",
                            "scheduled_day_index",
                            "actual_day_index",
                            "observed_at",
                        )
                        if any(
                            getattr(current_pro_event, field_name)
                            != getattr(replacement_pro_event, field_name)
                            for field_name in immutable_identity_fields
                        ):
                            raise ValueError(
                                "pro_followup_correction_cannot_change_event_identity"
                            )
                        current_score_identity = {
                            item.instrument: (
                                item.contract_version,
                                item.instrument_scoring_version,
                                item.baseline_distribution.source_scores_sha256,
                            )
                            for item in current_pro_event.standardized_scores
                        }
                        replacement_score_identity = {
                            item.instrument: (
                                item.contract_version,
                                item.instrument_scoring_version,
                                item.baseline_distribution.source_scores_sha256,
                            )
                            for item in replacement_pro_event.standardized_scores
                        }
                        if current_score_identity != replacement_score_identity:
                            raise ValueError(
                                "pro_followup_correction_cannot_change_score_identity"
                            )
                        replacement_payload = replacement_pro_event.model_dump(
                            mode="json"
                        )

                latest = connection.execute(
                    """
                    select * from event_mutations
                    where target_type=? and target_event_id=?
                    order by mutation_index desc
                    limit 1
                    """,
                    (resolved_target_type.value, target_event_id),
                ).fetchone()
                prior_payload_sha256 = str(target["effective_payload_sha256"])
                if latest is None and prior_payload_sha256 != str(
                    target["payload_sha256"]
                ):
                    raise EventMutationStateError(
                        "event_mutation_chain_origin_mismatch:"
                        f"{resolved_target_type.value}:{target_event_id}"
                    )
                if latest is not None and (
                    str(latest["result_payload_sha256"])
                    != prior_payload_sha256
                ):
                    raise EventMutationStateError(
                        "event_mutation_chain_payload_mismatch:"
                        f"{resolved_target_type.value}:{target_event_id}"
                    )
                previous_mutation_id = (
                    None if latest is None else str(latest["mutation_id"])
                )
                previous_mutation_sha256 = (
                    None if latest is None else str(latest["mutation_sha256"])
                )
                mutation_index = 0 if latest is None else int(latest["mutation_index"]) + 1
                mutation_id = f"mutation_{uuid4().hex}"
                if resolved_operation == EventMutationOperation.CORRECTION:
                    assert replacement_payload is not None
                    result_payload = replacement_payload
                    result_state = EventPayloadState.CORRECTED
                else:
                    result_payload = {"deleted": True, "mutation_id": mutation_id}
                    result_state = EventPayloadState.DELETED
                    should_secure_compact = True
                result_payload_sha256 = _sha256(result_payload)
                created_at = _now()
                mutation_identity = {
                    "mutation_id": mutation_id,
                    "profile_id": profile_id,
                    "target_type": resolved_target_type.value,
                    "target_event_id": target_event_id,
                    "operation": resolved_operation.value,
                    "idempotency_key": idempotency_key,
                    "request_sha256": request_sha256,
                    "prior_payload_sha256": prior_payload_sha256,
                    "result_payload_sha256": result_payload_sha256,
                    "previous_mutation_id": previous_mutation_id,
                    "previous_mutation_sha256": previous_mutation_sha256,
                    "mutation_index": mutation_index,
                    "created_at": created_at,
                }
                mutation_sha256 = _sha256(mutation_identity)

                table_name, id_column = self._target_table(resolved_target_type)
                connection.execute(
                    f"update {table_name} set payload_json=?, "
                    f"effective_payload_sha256=?, payload_state=? "
                    f"where {id_column}=?",
                    (
                        _canonical_json(result_payload),
                        result_payload_sha256,
                        result_state.value,
                        target_event_id,
                    ),
                )
                connection.execute(
                    """
                    insert into event_mutations(
                      mutation_id, profile_id, target_type, target_event_id,
                      operation, idempotency_key, request_sha256,
                      prior_payload_sha256, result_payload_sha256,
                      previous_mutation_id, previous_mutation_sha256,
                      mutation_index, mutation_sha256, created_at
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mutation_id,
                        profile_id,
                        resolved_target_type.value,
                        target_event_id,
                        resolved_operation.value,
                        idempotency_key,
                        request_sha256,
                        prior_payload_sha256,
                        result_payload_sha256,
                        previous_mutation_id,
                        previous_mutation_sha256,
                        mutation_index,
                        mutation_sha256,
                        created_at,
                    ),
                )
                if resolved_operation == EventMutationOperation.DELETION:
                    connection.execute(
                        """
                        insert into event_mutation_cleanup(
                          mutation_id, status, requested_at, completed_at
                        ) values (?, 'PENDING', ?, null)
                        """,
                        (mutation_id, created_at),
                    )
                self._insert_audit(
                    connection=connection,
                    mutation_identity=mutation_identity,
                    mutation_sha256=mutation_sha256,
                )
                row = connection.execute(
                    "select * from event_mutations where mutation_id=?",
                    (mutation_id,),
                ).fetchone()
                assert row is not None
                result = EventMutationResult(
                    mutation=_record_from_row(row),
                    deduplicated=False,
                )
        if should_secure_compact:
            self.store.complete_pending_secure_compactions()
        return result

    def get(self, mutation_id: str) -> EventMutationRecord:
        rows = self.store.rows(
            "select * from event_mutations where mutation_id=?",
            (mutation_id,),
        )
        if not rows:
            raise EventMutationNotFoundError(
                f"event_mutation_not_found:{mutation_id}"
            )
        return _record_from_row(rows[0])

    def verify_chain(
        self,
        *,
        target_type: str | EventMutationTargetType,
        target_event_id: str,
    ) -> bool:
        resolved_target_type = EventMutationTargetType(target_type)
        rows = self.store.rows(
            """
            select * from event_mutations
            where target_type=? and target_event_id=?
            order by mutation_index
            """,
            (resolved_target_type.value, target_event_id),
        )
        previous: sqlite3.Row | None = None
        for expected_index, row in enumerate(rows):
            identity = self._mutation_identity_from_row(row)
            if int(row["mutation_index"]) != expected_index:
                return False
            if row["previous_mutation_id"] != (
                None if previous is None else previous["mutation_id"]
            ):
                return False
            if row["previous_mutation_sha256"] != (
                None if previous is None else previous["mutation_sha256"]
            ):
                return False
            if previous is not None and row["prior_payload_sha256"] != previous[
                "result_payload_sha256"
            ]:
                return False
            if str(row["mutation_sha256"]) != _sha256(identity):
                return False
            previous = row
        if previous is None:
            return True
        table_name, id_column = self._target_table(resolved_target_type)
        current_rows = self.store.rows(
            f"select payload_json, payload_sha256, effective_payload_sha256 "
            f"from {table_name} "
            f"where {id_column}=?",
            (target_event_id,),
        )
        return bool(
            current_rows
            and rows[0]["prior_payload_sha256"]
            == current_rows[0]["payload_sha256"]
            and _sha256(json.loads(current_rows[0]["payload_json"]))
            == current_rows[0]["effective_payload_sha256"]
            and current_rows[0]["effective_payload_sha256"]
            == previous["result_payload_sha256"]
        )

    @staticmethod
    def _mutation_identity_from_row(row: sqlite3.Row) -> dict[str, object]:
        return {
            "mutation_id": str(row["mutation_id"]),
            "profile_id": str(row["profile_id"]),
            "target_type": str(row["target_type"]),
            "target_event_id": str(row["target_event_id"]),
            "operation": str(row["operation"]),
            "idempotency_key": str(row["idempotency_key"]),
            "request_sha256": str(row["request_sha256"]),
            "prior_payload_sha256": str(row["prior_payload_sha256"]),
            "result_payload_sha256": str(row["result_payload_sha256"]),
            "previous_mutation_id": row["previous_mutation_id"],
            "previous_mutation_sha256": row["previous_mutation_sha256"],
            "mutation_index": int(row["mutation_index"]),
            "created_at": str(row["created_at"]),
        }

    @staticmethod
    def _validate_request(
        *,
        profile_id: str,
        target_event_id: str,
        idempotency_key: str,
        operation: EventMutationOperation,
        replacement_payload: dict[str, Any] | None,
    ) -> None:
        if not profile_id.strip():
            raise ValueError("profile_id_required")
        if not target_event_id.strip():
            raise ValueError("target_event_id_required")
        if not idempotency_key.strip():
            raise ValueError("idempotency_key_required")
        if len(idempotency_key) > 128:
            raise ValueError("idempotency_key_too_long")
        if operation == EventMutationOperation.CORRECTION:
            if replacement_payload is None:
                raise ValueError("correction_replacement_payload_required")
        elif replacement_payload is not None:
            raise ValueError("deletion_replacement_payload_not_allowed")

    @staticmethod
    def _target_table(
        target_type: EventMutationTargetType,
    ) -> tuple[str, str]:
        if target_type == EventMutationTargetType.EXECUTION_EVENT:
            return "execution_events", "event_id"
        return "behavior_events", "behavior_event_id"

    @classmethod
    def _target_row(
        cls,
        *,
        connection: sqlite3.Connection,
        profile_id: str,
        target_type: EventMutationTargetType,
        target_event_id: str,
    ) -> sqlite3.Row:
        if target_type == EventMutationTargetType.EXECUTION_EVENT:
            row = connection.execute(
                """
                select ev.*
                from execution_events ev
                join executions e on e.execution_id=ev.execution_id
                where ev.event_id=? and e.profile_id=?
                """,
                (target_event_id, profile_id),
            ).fetchone()
        else:
            row = connection.execute(
                """
                select * from behavior_events
                where behavior_event_id=? and profile_id=?
                """,
                (target_event_id, profile_id),
            ).fetchone()
        if row is None:
            raise EventMutationNotFoundError(
                f"event_mutation_target_not_found:{target_type.value}:"
                f"{target_event_id}"
            )
        return row

    @staticmethod
    def _insert_audit(
        *,
        connection: sqlite3.Connection,
        mutation_identity: dict[str, object],
        mutation_sha256: str,
    ) -> None:
        metadata = {**mutation_identity, "mutation_sha256": mutation_sha256}
        connection.execute(
            "insert into audit_events values (?, ?, ?, ?, ?, ?, ?)",
            (
                f"audit_{uuid4().hex}",
                f"data_{mutation_identity['operation']}",
                mutation_identity["target_event_id"],
                DataClass.INTERIM_RUNTIME_EVENT,
                _sha256(metadata),
                _canonical_json(metadata),
                mutation_identity["created_at"],
            ),
        )


__all__ = [
    "DataMutationLedger",
    "EventMutationNotFoundError",
    "EventMutationOperation",
    "EventMutationRecord",
    "EventMutationResult",
    "EventMutationStateError",
    "EventMutationTargetType",
]
