from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from wellnessbox_rnd.interim.store import InterimStore


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


class PlanLifecycleState(StrEnum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    MAINTAINED = "MAINTAINED"
    ADJUSTED = "ADJUSTED"
    MONITORING = "MONITORING"
    REPLACED = "REPLACED"
    STOPPED = "STOPPED"


class PlanLifecycleAction(StrEnum):
    MAINTAIN = "maintain"
    ADJUST = "adjust"
    REPLACE = "replace"
    STOP = "stop"
    MONITOR = "monitor"


_TARGETS = {
    PlanLifecycleAction.MAINTAIN: PlanLifecycleState.MAINTAINED,
    PlanLifecycleAction.ADJUST: PlanLifecycleState.ADJUSTED,
    PlanLifecycleAction.REPLACE: PlanLifecycleState.REPLACED,
    PlanLifecycleAction.STOP: PlanLifecycleState.STOPPED,
    PlanLifecycleAction.MONITOR: PlanLifecycleState.MONITORING,
}
_TERMINAL = {PlanLifecycleState.REPLACED, PlanLifecycleState.STOPPED}


class PlanLifecycleTransitionRequestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["plan_lifecycle_transition_request_v1"] = (
        "plan_lifecycle_transition_request_v1"
    )
    execution_id: str = Field(min_length=3, max_length=128)
    profile_id: str = Field(min_length=3, max_length=128)
    plan_id: str = Field(min_length=3, max_length=128)
    expected_state: PlanLifecycleState
    action: PlanLifecycleAction
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{2,127}$")
    idempotency_key: str = Field(min_length=1, max_length=128)
    occurred_at: datetime
    replacement_plan_id: str | None = Field(default=None, min_length=3, max_length=128)

    @model_validator(mode="after")
    def validate_transition_request(self) -> PlanLifecycleTransitionRequestV1:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("plan_lifecycle_occurred_at_timezone_required")
        if self.action == PlanLifecycleAction.REPLACE:
            if not self.replacement_plan_id:
                raise ValueError("replacement_plan_id_required")
            if self.replacement_plan_id == self.plan_id:
                raise ValueError("replacement_plan_id_must_be_distinct")
        elif self.replacement_plan_id is not None:
            raise ValueError("replacement_plan_id_forbidden_for_action")
        return self


class PlanLifecycleTransitionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["plan_lifecycle_transition_result_v1"] = (
        "plan_lifecycle_transition_result_v1"
    )
    event_id: str
    execution_id: str
    profile_id: str
    plan_id: str
    action: PlanLifecycleAction
    state_before: PlanLifecycleState
    state_after: PlanLifecycleState
    replacement_plan_id: str | None
    replacement_state: PlanLifecycleState | None
    deduplicated: bool
    terminal_work_closed: bool
    order_state_effect: Literal["NONE"] = "NONE"
    order_state_mutation_allowed: Literal[False] = False


def resolve_plan_lifecycle_states(rows: list[object]) -> dict[str, PlanLifecycleState]:
    states: dict[str, PlanLifecycleState] = {}
    candidate_identity: dict[str, tuple[str, str]] = {}
    for row in rows:
        event_type = str(row["event_type"])
        payload = json.loads(str(row["payload_json"]))
        plan_id = str(payload.get("plan_id", ""))
        if event_type in {"recommendation", "optimization"} and plan_id:
            initial = (
                PlanLifecycleState.CANDIDATE
                if payload.get("lifecycle_role") == "replacement_candidate"
                else PlanLifecycleState.ACTIVE
            )
            states.setdefault(plan_id, initial)
            if initial == PlanLifecycleState.CANDIDATE:
                candidate_identity[plan_id] = (
                    str(row["event_id"]),
                    str(row["effective_payload_sha256"]),
                )
        if event_type != "followup_evaluation" or not plan_id:
            continue
        if payload.get("schema_version") == "plan_lifecycle_transition_v1":
            before = PlanLifecycleState(payload["state_before"])
            after = PlanLifecycleState(payload["state_after"])
            if states.get(plan_id) != before:
                raise ValueError("plan_lifecycle_stored_state_discontinuity")
            states[plan_id] = after
            replacement = payload.get("replacement_plan_id")
            if replacement:
                if states.get(str(replacement)) != PlanLifecycleState.CANDIDATE:
                    raise ValueError("replacement_plan_candidate_discontinuity")
                if candidate_identity.get(str(replacement)) != (
                    str(payload.get("replacement_candidate_event_id")),
                    str(payload.get("replacement_candidate_payload_sha256")),
                ):
                    raise ValueError("replacement_plan_candidate_identity_mismatch")
                states[str(replacement)] = PlanLifecycleState.ACTIVE
        elif payload.get("timepoint") == "discontinuation":
            states[plan_id] = PlanLifecycleState.STOPPED
    return states


class PlanLifecycleService:
    def __init__(self, store: InterimStore):
        self.store = store

    def transition(
        self, request: PlanLifecycleTransitionRequestV1
    ) -> PlanLifecycleTransitionResultV1:
        occurred = request.occurred_at.astimezone(UTC)
        target = _TARGETS[request.action]
        request_payload = request.model_dump(mode="json")
        request_payload["occurred_at"] = occurred.isoformat()
        request_sha256 = _sha(request_payload)
        with self.store.transaction(immediate=True) as connection:
            execution = connection.execute(
                "select * from executions where execution_id=?", (request.execution_id,)
            ).fetchone()
            if execution is None:
                raise ValueError("plan_lifecycle_execution_not_found")
            if str(execution["profile_id"]) != request.profile_id:
                raise PermissionError("plan_lifecycle_profile_mismatch")
            active_consent = connection.execute(
                "select consent_snapshot_id from active_profile_consents where profile_id=?",
                (request.profile_id,),
            ).fetchone()
            if active_consent is None or str(active_consent["consent_snapshot_id"]) != str(
                execution["consent_snapshot_id"]
            ):
                raise PermissionError("plan_lifecycle_active_consent_required")
            existing = connection.execute(
                """
                select * from execution_events
                where execution_id=? and event_type='followup_evaluation'
                  and idempotency_key=?
                """,
                (request.execution_id, request.idempotency_key),
            ).fetchone()
            if existing is not None:
                existing_payload = json.loads(str(existing["payload_json"]))
                if existing_payload.get("request_sha256") != request_sha256:
                    raise ValueError("plan_lifecycle_idempotency_conflict")
                return self._result(connection, existing, deduplicated=True)
            rows = connection.execute(
                """
                select event_id, event_type, payload_json, effective_payload_sha256, created_at
                from execution_events
                where execution_id=? and payload_state='ACTIVE' order by event_index
                """,
                (request.execution_id,),
            ).fetchall()
            states = resolve_plan_lifecycle_states(list(rows))
            current = states.get(request.plan_id)
            if current is None:
                raise ValueError("plan_lifecycle_plan_not_found")
            if current in _TERMINAL:
                raise ValueError("plan_lifecycle_terminal_state")
            if current != request.expected_state:
                raise ValueError(
                    f"plan_lifecycle_stale_state:{request.expected_state.value}:{current.value}"
                )
            latest_created_at = max(
                datetime.fromisoformat(str(row["created_at"])).astimezone(UTC) for row in rows
            )
            if occurred < latest_created_at:
                raise ValueError("plan_lifecycle_occurred_at_before_lineage")
            candidate_event_id = None
            candidate_payload_sha256 = None
            if request.replacement_plan_id:
                candidates = []
                for row in rows:
                    payload = json.loads(str(row["payload_json"]))
                    if (
                        str(row["event_type"]) in {"recommendation", "optimization"}
                        and payload.get("plan_id") == request.replacement_plan_id
                        and payload.get("lifecycle_role") == "replacement_candidate"
                        and payload.get("replaces_plan_id") == request.plan_id
                    ):
                        candidates.append(row)
                if len(candidates) != 1:
                    raise ValueError("replacement_plan_candidate_required")
                candidate = candidates[0]
                candidate_created = datetime.fromisoformat(
                    str(candidate["created_at"])
                ).astimezone(UTC)
                if candidate_created > occurred:
                    raise ValueError("replacement_plan_candidate_created_after_transition")
                if states.get(request.replacement_plan_id) != PlanLifecycleState.CANDIDATE:
                    raise ValueError("replacement_plan_candidate_not_available")
                candidate_event_id = str(candidate["event_id"])
                candidate_payload_sha256 = str(candidate["effective_payload_sha256"])
            event_payload = {
                "schema_version": "plan_lifecycle_transition_v1",
                "profile_id": request.profile_id,
                "plan_id": request.plan_id,
                "action": request.action.value,
                "state_before": request.expected_state.value,
                "state_after": target.value,
                "reason_code": request.reason_code,
                "replacement_plan_id": request.replacement_plan_id,
                "replacement_state": (
                    PlanLifecycleState.ACTIVE.value if request.replacement_plan_id else None
                ),
                "replacement_candidate_event_id": candidate_event_id,
                "replacement_candidate_payload_sha256": candidate_payload_sha256,
                "occurred_at": occurred.isoformat(),
                "request_sha256": request_sha256,
            }
            payload_sha256 = _sha(event_payload)
            event_index = int(
                connection.execute(
                    "select coalesce(max(event_index), -1) + 1 from execution_events "
                    "where execution_id=?",
                    (request.execution_id,),
                ).fetchone()[0]
            )
            event_id = "event_plan_" + hashlib.sha256(
                f"{request.execution_id}:{request.idempotency_key}".encode()
            ).hexdigest()[:24]
            connection.execute(
                """
                insert into execution_events(
                  event_id, execution_id, consent_snapshot_id, event_index, event_type,
                  source, idempotency_key, payload_json, payload_sha256,
                  effective_payload_sha256, created_at
                ) values (?, ?, ?, ?, 'followup_evaluation', 'system', ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    request.execution_id,
                    execution["consent_snapshot_id"],
                    event_index,
                    request.idempotency_key,
                    _json(event_payload),
                    payload_sha256,
                    payload_sha256,
                    occurred.isoformat(),
                ),
            )
            if target in _TERMINAL:
                connection.execute(
                    """
                    update followups set status='CLOSED'
                    where execution_id=? and plan_id=?
                      and status in ('OPEN', 'REEVALUATION_QUEUED')
                    """,
                    (request.execution_id, request.plan_id),
                )
                connection.execute(
                    """
                    update workflow_jobs set status='CANCELLED', lease_until=null,
                      claim_token=null, last_error=?
                    where execution_id=? and plan_id=? and status in ('READY', 'CLAIMED')
                    """,
                    (
                        f"PLAN_LIFECYCLE_{target.value}",
                        request.execution_id,
                        request.plan_id,
                    ),
                )
            stored = connection.execute(
                "select * from execution_events where event_id=?", (event_id,)
            ).fetchone()
            return self._result(connection, stored, deduplicated=False)

    @staticmethod
    def _result(connection, row, *, deduplicated: bool) -> PlanLifecycleTransitionResultV1:
        payload = json.loads(str(row["payload_json"]))
        terminal = payload["state_after"] in {
            PlanLifecycleState.REPLACED.value,
            PlanLifecycleState.STOPPED.value,
        }
        open_work = 0
        if terminal:
            open_work = int(
                connection.execute(
                    """
                    select
                      (select count(*) from followups where execution_id=? and plan_id=?
                        and status in ('OPEN','REEVALUATION_QUEUED')) +
                      (select count(*) from workflow_jobs where execution_id=? and plan_id=?
                        and status in ('READY','CLAIMED'))
                    """,
                    (
                        row["execution_id"],
                        payload["plan_id"],
                        row["execution_id"],
                        payload["plan_id"],
                    ),
                ).fetchone()[0]
            )
        return PlanLifecycleTransitionResultV1(
            event_id=str(row["event_id"]),
            execution_id=str(row["execution_id"]),
            profile_id=str(payload["profile_id"]),
            plan_id=str(payload["plan_id"]),
            action=payload["action"],
            state_before=payload["state_before"],
            state_after=payload["state_after"],
            replacement_plan_id=payload["replacement_plan_id"],
            replacement_state=payload["replacement_state"],
            deduplicated=deduplicated,
            terminal_work_closed=terminal and open_work == 0,
        )


__all__ = [
    "PlanLifecycleAction",
    "PlanLifecycleService",
    "PlanLifecycleState",
    "PlanLifecycleTransitionRequestV1",
    "PlanLifecycleTransitionResultV1",
    "resolve_plan_lifecycle_states",
]
