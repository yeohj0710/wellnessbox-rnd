from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from wellnessbox_rnd.interim.store import InterimStore


class WorkflowJobType(StrEnum):
    FOLLOWUP_REMINDER = "FOLLOWUP_REMINDER"
    PLAN_REEVALUATION = "PLAN_REEVALUATION"


class WorkflowJobStatus(StrEnum):
    READY = "READY"
    CLAIMED = "CLAIMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkflowJobV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "workflow_job_v1"
    job_id: str
    job_type: WorkflowJobType
    status: WorkflowJobStatus
    idempotency_key: str
    profile_id: str
    plan_id: str
    execution_id: str
    followup_id: str
    scheduled_at: datetime
    payload: dict[str, Any]
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    claim_token: str | None = None
    lease_until: datetime | None = None
    attempt_count: int = Field(ge=0)
    last_error: str | None = None


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("workflow_job_datetime_must_be_timezone_aware")
    return value.astimezone(UTC)


class WorkflowJobQueue:
    def __init__(self, store: InterimStore):
        self.store = store

    def schedule_followup_with_reminder(
        self,
        *,
        followup_id: str,
        profile_id: str,
        plan_id: str,
        execution_id: str,
        due_at: datetime,
        reminder_at: datetime,
        requested_data: list[str],
        now: datetime | None = None,
    ) -> dict[str, object]:
        due = _utc(due_at)
        reminder = _utc(reminder_at)
        created = _utc(now or datetime.now(UTC))
        if not plan_id.strip():
            raise ValueError("followup_plan_id_required")
        if reminder > due:
            raise ValueError("followup_reminder_after_due")
        payload = {
            "schema_version": "followup_reminder_job_payload_v1",
            "requested_data": sorted(set(requested_data)),
            "due_at": due.isoformat(),
            "reminder_at": reminder.isoformat(),
        }
        idempotency_key = f"followup-reminder:{followup_id}"
        with self.store.transaction(immediate=True) as connection:
            self._validate_active_execution_plan(
                connection,
                execution_id=execution_id,
                profile_id=profile_id,
                plan_id=plan_id,
            )
            self._ensure_user_profile_projection(connection, profile_id=profile_id)
            existing_followup = connection.execute(
                "select * from followups where followup_id=?", (followup_id,)
            ).fetchone()
            if existing_followup:
                expected = (
                    profile_id,
                    plan_id,
                    due.isoformat(),
                    reminder.isoformat(),
                    _json(payload["requested_data"]),
                    execution_id,
                )
                observed = (
                    str(existing_followup["profile_id"]),
                    str(existing_followup["plan_id"]),
                    str(existing_followup["due_at"]),
                    str(existing_job["scheduled_at"])
                    if (
                        existing_job := connection.execute(
                            "select scheduled_at from workflow_jobs where idempotency_key=?",
                            (idempotency_key,),
                        ).fetchone()
                    )
                    else "",
                    str(existing_followup["requested_data_json"]),
                    str(existing_followup["execution_id"]),
                )
                if observed != expected:
                    raise ValueError("followup_idempotency_payload_conflict")
            else:
                connection.execute(
                    """
                    insert into followups(
                      followup_id, profile_id, plan_id, execution_id, due_at,
                      requested_data_json, status, created_at
                    ) values (?, ?, ?, ?, ?, ?, 'OPEN', ?)
                    """,
                    (
                        followup_id,
                        profile_id,
                        plan_id,
                        execution_id,
                        due.isoformat(),
                        _json(payload["requested_data"]),
                        created.isoformat(),
                    ),
                )
            job, deduplicated = self._enqueue_in_transaction(
                connection,
                job_type=WorkflowJobType.FOLLOWUP_REMINDER,
                idempotency_key=idempotency_key,
                profile_id=profile_id,
                plan_id=plan_id,
                followup_id=followup_id,
                execution_id=execution_id,
                scheduled_at=reminder,
                payload=payload,
                created_at=created,
            )
        return {
            "followup_id": followup_id,
            "reminder_job": job.model_dump(mode="json"),
            "deduplicated": deduplicated,
        }

    @staticmethod
    def _ensure_user_profile_projection(connection, *, profile_id: str) -> None:
        existing = connection.execute(
            "select 1 from user_profiles where profile_id=?", (profile_id,)
        ).fetchone()
        if existing is not None:
            return
        snapshot = connection.execute(
            """
            select data_class, payload_json, payload_sha256, created_at
            from profile_snapshots where profile_id=? order by version desc limit 1
            """,
            (profile_id,),
        ).fetchone()
        if snapshot is None:
            raise ValueError("followup_profile_projection_required")
        connection.execute(
            """
            insert into user_profiles(
              profile_id, data_class, consent_scopes_json, payload_json,
              payload_sha256, created_at
            ) values (?, ?, '[]', ?, ?, ?)
            """,
            (
                profile_id,
                snapshot["data_class"],
                snapshot["payload_json"],
                snapshot["payload_sha256"],
                snapshot["created_at"],
            ),
        )

    def enqueue_due_plan_reevaluations(self, *, as_of: datetime) -> dict[str, object]:
        cutoff = _utc(as_of)
        jobs: list[WorkflowJobV1] = []
        deduplicated_count = 0
        with self.store.transaction(immediate=True) as connection:
            due = connection.execute(
                """
                select followup_id, profile_id, plan_id, execution_id, due_at,
                       requested_data_json
                from followups
                where status in ('OPEN', 'REEVALUATION_QUEUED')
                  and plan_id is not null and plan_id != '' and due_at <= ?
                order by due_at, followup_id
                """,
                (cutoff.isoformat(),),
            ).fetchall()
            for row in due:
                if not self._execution_plan_is_active(
                    connection,
                    execution_id=str(row["execution_id"]),
                    profile_id=str(row["profile_id"]),
                    plan_id=str(row["plan_id"]),
                ):
                    self._cancel_followup_in_transaction(
                        connection, followup_id=str(row["followup_id"]), reason="PLAN_INACTIVE"
                    )
                    continue
                payload = {
                    "schema_version": "plan_reevaluation_job_payload_v1",
                    "due_at": str(row["due_at"]),
                    "requested_data": json.loads(row["requested_data_json"]),
                }
                job, deduplicated = self._enqueue_in_transaction(
                    connection,
                    job_type=WorkflowJobType.PLAN_REEVALUATION,
                    idempotency_key=f"plan-reevaluation:{row['followup_id']}",
                    profile_id=str(row["profile_id"]),
                    plan_id=str(row["plan_id"]),
                    followup_id=str(row["followup_id"]),
                    execution_id=str(row["execution_id"]),
                    scheduled_at=datetime.fromisoformat(str(row["due_at"])),
                    payload=payload,
                    created_at=cutoff,
                )
                jobs.append(job)
                deduplicated_count += int(deduplicated)
                connection.execute(
                    "update followups set status='REEVALUATION_QUEUED' where followup_id=?",
                    (row["followup_id"],),
                )
        return {
            "schema_version": "due_plan_reevaluation_cron_result_v1",
            "as_of": cutoff.isoformat(),
            "due_followup_count": len(due),
            "created_job_count": len(jobs) - deduplicated_count,
            "deduplicated_job_count": deduplicated_count,
            "jobs": [job.model_dump(mode="json") for job in jobs],
        }

    def enqueue_input_reevaluation(
        self,
        *,
        profile_id: str,
        plan_id: str,
        execution_id: str,
        input_kind: str,
        input_id: str,
        input_sha256: str,
        received_at: datetime,
    ) -> dict[str, object]:
        received = _utc(received_at)
        kind = input_kind.strip().upper()
        if kind not in {"PRO", "DEVICE"}:
            raise ValueError("followup_input_kind_invalid")
        if not input_id.strip():
            raise ValueError("followup_input_id_required")
        invalid_hash = len(input_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in input_sha256
        )
        if invalid_hash:
            raise ValueError("followup_input_sha256_invalid")
        identity = _sha(
            {
                "execution_id": execution_id,
                "plan_id": plan_id,
                "input_kind": kind,
                "input_id": input_id,
            }
        )
        followup_id = f"fu_input_{identity[:24]}"
        idempotency_key = f"input-reevaluation:{identity}"
        payload = {
            "schema_version": "followup_input_reevaluation_job_payload_v1",
            "input_kind": kind,
            "input_id": input_id,
            "input_sha256": input_sha256,
            "received_at": received.isoformat(),
            "reason_code": f"{kind}_INPUT_RECEIVED",
        }
        with self.store.transaction(immediate=True) as connection:
            self._validate_active_execution_plan(
                connection,
                execution_id=execution_id,
                profile_id=profile_id,
                plan_id=plan_id,
            )
            self._ensure_user_profile_projection(connection, profile_id=profile_id)
            existing_followup = connection.execute(
                "select * from followups where followup_id=?", (followup_id,)
            ).fetchone()
            if existing_followup is None:
                connection.execute(
                    """
                    insert into followups(
                      followup_id, profile_id, plan_id, execution_id, due_at,
                      requested_data_json, status, created_at
                    ) values (?, ?, ?, ?, ?, ?, 'REEVALUATION_QUEUED', ?)
                    """,
                    (
                        followup_id,
                        profile_id,
                        plan_id,
                        execution_id,
                        received.isoformat(),
                        _json([kind]),
                        received.isoformat(),
                    ),
                )
            else:
                expected = (profile_id, plan_id, execution_id)
                observed = (
                    str(existing_followup["profile_id"]),
                    str(existing_followup["plan_id"]),
                    str(existing_followup["execution_id"]),
                )
                if observed != expected:
                    raise ValueError("followup_input_identity_conflict")
            job, deduplicated = self._enqueue_in_transaction(
                connection,
                job_type=WorkflowJobType.PLAN_REEVALUATION,
                idempotency_key=idempotency_key,
                profile_id=profile_id,
                plan_id=plan_id,
                followup_id=followup_id,
                execution_id=execution_id,
                scheduled_at=received,
                payload=payload,
                created_at=received,
            )
        return {
            "schema_version": "followup_input_next_job_decision_v1",
            "decision": "REEVALUATE_PLAN",
            "reason_code": f"{kind}_INPUT_RECEIVED",
            "followup_id": followup_id,
            "next_job": job.model_dump(mode="json"),
            "deduplicated": deduplicated,
        }

    def claim_ready_jobs(
        self,
        *,
        worker_id: str,
        as_of: datetime,
        limit: int = 10,
        lease_seconds: int = 300,
    ) -> list[dict[str, object]]:
        cutoff = _utc(as_of)
        if not worker_id.strip():
            raise ValueError("workflow_job_worker_id_required")
        if limit < 1 or lease_seconds < 1:
            raise ValueError("workflow_job_claim_bounds_invalid")
        claimed: list[WorkflowJobV1] = []
        with self.store.transaction(immediate=True) as connection:
            connection.execute(
                """
                update workflow_jobs
                set status='READY', claimed_at=null, lease_until=null, claim_token=null,
                    last_error='LEASE_EXPIRED'
                where status='CLAIMED' and lease_until <= ?
                """,
                (cutoff.isoformat(),),
            )
            rows = connection.execute(
                """
                select j.* from workflow_jobs j
                join followups f on f.followup_id=j.followup_id
                where j.status='READY' and j.scheduled_at <= ?
                  and f.status in ('OPEN', 'REEVALUATION_QUEUED')
                order by j.scheduled_at, j.job_id limit ?
                """,
                (cutoff.isoformat(), limit),
            ).fetchall()
            for row in rows:
                if not self._execution_plan_is_active(
                    connection,
                    execution_id=str(row["execution_id"]),
                    profile_id=str(row["profile_id"]),
                    plan_id=str(row["plan_id"]),
                ):
                    self._cancel_followup_in_transaction(
                        connection,
                        followup_id=str(row["followup_id"]),
                        reason="PLAN_INACTIVE_AT_CLAIM",
                    )
                    continue
                token = f"claim_{worker_id}_{uuid4().hex}"
                lease_until = cutoff + timedelta(seconds=lease_seconds)
                connection.execute(
                    """
                    update workflow_jobs
                    set status='CLAIMED', claimed_at=?, lease_until=?, claim_token=?,
                        attempt_count=attempt_count+1, last_error=null
                    where job_id=? and status='READY'
                    """,
                    (cutoff.isoformat(), lease_until.isoformat(), token, row["job_id"]),
                )
                claimed_row = connection.execute(
                    "select * from workflow_jobs where job_id=?", (row["job_id"],)
                ).fetchone()
                claimed.append(_job_from_row(claimed_row))
        return [job.model_dump(mode="json") for job in claimed]

    def acknowledge_job(self, *, job_id: str, claim_token: str, completed_at: datetime) -> None:
        completed = _utc(completed_at)
        with self.store.transaction(immediate=True) as connection:
            updated = connection.execute(
                """
                update workflow_jobs
                set status='COMPLETED', completed_at=?, lease_until=null, claim_token=null
                where job_id=? and status='CLAIMED' and claim_token=?
                """,
                (completed.isoformat(), job_id, claim_token),
            ).rowcount
            if updated != 1:
                raise ValueError("workflow_job_claim_mismatch")

    def retry_job(
        self,
        *,
        job_id: str,
        claim_token: str,
        retry_at: datetime,
        error: str,
    ) -> None:
        scheduled = _utc(retry_at)
        with self.store.transaction(immediate=True) as connection:
            updated = connection.execute(
                """
                update workflow_jobs
                set status='READY', scheduled_at=?, claimed_at=null, lease_until=null,
                    claim_token=null, last_error=?
                where job_id=? and status='CLAIMED' and claim_token=?
                """,
                (scheduled.isoformat(), error[:500], job_id, claim_token),
            ).rowcount
            if updated != 1:
                raise ValueError("workflow_job_claim_mismatch")

    def close_followup(self, *, followup_id: str, reason: str) -> None:
        with self.store.transaction(immediate=True) as connection:
            self._cancel_followup_in_transaction(connection, followup_id=followup_id, reason=reason)

    @staticmethod
    def _cancel_followup_in_transaction(connection, *, followup_id: str, reason: str) -> None:
        updated = connection.execute(
            "update followups set status='CLOSED' where followup_id=?",
            (followup_id,),
        ).rowcount
        if updated != 1:
            raise ValueError("unknown_followup")
        connection.execute(
            """
            update workflow_jobs set status='CANCELLED', last_error=?
            where followup_id=? and status in ('READY', 'CLAIMED')
            """,
            (f"FOLLOWUP_CLOSED:{reason}"[:500], followup_id),
        )

    @staticmethod
    def _execution_plan_is_active(
        connection, *, execution_id: str, profile_id: str, plan_id: str
    ) -> bool:
        execution = connection.execute(
            "select profile_id, status from executions where execution_id=?",
            (execution_id,),
        ).fetchone()
        if not execution or str(execution["profile_id"]) != profile_id:
            return False
        events = connection.execute(
            """
            select event_type, payload_json from execution_events
            where execution_id=? and payload_state='ACTIVE' order by event_index
            """,
            (execution_id,),
        ).fetchall()
        plan_linked = False
        discontinued = False
        for event in events:
            payload = json.loads(event["payload_json"])
            if event["event_type"] in {"recommendation", "optimization"}:
                plan_linked = plan_linked or payload.get("plan_id") == plan_id
            if (
                event["event_type"] == "followup_evaluation"
                and payload.get("plan_id") == plan_id
                and payload.get("timepoint") == "discontinuation"
            ):
                discontinued = True
        return plan_linked and not discontinued

    @classmethod
    def _validate_active_execution_plan(
        cls, connection, *, execution_id: str, profile_id: str, plan_id: str
    ) -> None:
        if not cls._execution_plan_is_active(
            connection,
            execution_id=execution_id,
            profile_id=profile_id,
            plan_id=plan_id,
        ):
            raise ValueError("followup_active_execution_plan_required")

    @staticmethod
    def _enqueue_in_transaction(
        connection,
        *,
        job_type: WorkflowJobType,
        idempotency_key: str,
        profile_id: str,
        plan_id: str,
        followup_id: str,
        execution_id: str,
        scheduled_at: datetime,
        payload: dict[str, object],
        created_at: datetime,
    ) -> tuple[WorkflowJobV1, bool]:
        payload_sha256 = _sha(payload)
        existing = connection.execute(
            "select * from workflow_jobs where idempotency_key=?", (idempotency_key,)
        ).fetchone()
        if existing:
            if str(existing["payload_sha256"]) != payload_sha256:
                raise ValueError("workflow_job_idempotency_payload_conflict")
            return _job_from_row(existing), True
        job_id = f"job_{uuid4().hex}"
        connection.execute(
            """
            insert into workflow_jobs(
              job_id, job_type, status, idempotency_key, profile_id, plan_id,
              followup_id, execution_id, scheduled_at, payload_json, payload_sha256,
              created_at, claimed_at, completed_at, lease_until, claim_token,
              attempt_count, last_error
            ) values (?, ?, 'READY', ?, ?, ?, ?, ?, ?, ?, ?, ?, null, null, null, null, 0, null)
            """,
            (
                job_id,
                job_type.value,
                idempotency_key,
                profile_id,
                plan_id,
                followup_id,
                execution_id,
                scheduled_at.isoformat(),
                _json(payload),
                payload_sha256,
                created_at.isoformat(),
            ),
        )
        row = connection.execute("select * from workflow_jobs where job_id=?", (job_id,)).fetchone()
        return _job_from_row(row), False


def _job_from_row(row) -> WorkflowJobV1:
    return WorkflowJobV1.model_validate(
        {
            "job_id": row["job_id"],
            "job_type": row["job_type"],
            "status": row["status"],
            "idempotency_key": row["idempotency_key"],
            "profile_id": row["profile_id"],
            "plan_id": row["plan_id"],
            "execution_id": row["execution_id"],
            "followup_id": row["followup_id"],
            "scheduled_at": row["scheduled_at"],
            "payload": json.loads(row["payload_json"]),
            "payload_sha256": row["payload_sha256"],
            "claim_token": row["claim_token"],
            "lease_until": row["lease_until"],
            "attempt_count": row["attempt_count"],
            "last_error": row["last_error"],
        }
    )


__all__ = [
    "WorkflowJobQueue",
    "WorkflowJobStatus",
    "WorkflowJobType",
    "WorkflowJobV1",
]
