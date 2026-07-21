from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
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
    followup_id: str
    scheduled_at: datetime
    payload: dict[str, Any]
    payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


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
        }
        idempotency_key = f"followup-reminder:{followup_id}"
        with self.store.transaction(immediate=True) as connection:
            existing_followup = connection.execute(
                "select * from followups where followup_id=?", (followup_id,)
            ).fetchone()
            if existing_followup:
                expected = (
                    profile_id,
                    plan_id,
                    due.isoformat(),
                    _json(payload["requested_data"]),
                )
                observed = (
                    str(existing_followup["profile_id"]),
                    str(existing_followup["plan_id"]),
                    str(existing_followup["due_at"]),
                    str(existing_followup["requested_data_json"]),
                )
                if observed != expected:
                    raise ValueError("followup_idempotency_payload_conflict")
            else:
                connection.execute(
                    """
                    insert into followups(
                      followup_id, profile_id, plan_id, due_at,
                      requested_data_json, status, created_at
                    ) values (?, ?, ?, ?, ?, 'OPEN', ?)
                    """,
                    (
                        followup_id,
                        profile_id,
                        plan_id,
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
                scheduled_at=reminder,
                payload=payload,
                created_at=created,
            )
        return {
            "followup_id": followup_id,
            "reminder_job": job.model_dump(mode="json"),
            "deduplicated": deduplicated,
        }

    def enqueue_due_plan_reevaluations(
        self, *, as_of: datetime
    ) -> dict[str, object]:
        cutoff = _utc(as_of)
        jobs: list[WorkflowJobV1] = []
        deduplicated_count = 0
        with self.store.transaction(immediate=True) as connection:
            due = connection.execute(
                """
                select followup_id, profile_id, plan_id, due_at, requested_data_json
                from followups
                where status in ('OPEN', 'REEVALUATION_QUEUED')
                  and plan_id is not null and plan_id != '' and due_at <= ?
                order by due_at, followup_id
                """,
                (cutoff.isoformat(),),
            ).fetchall()
            for row in due:
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

    @staticmethod
    def _enqueue_in_transaction(
        connection,
        *,
        job_type: WorkflowJobType,
        idempotency_key: str,
        profile_id: str,
        plan_id: str,
        followup_id: str,
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
              followup_id, scheduled_at, payload_json, payload_sha256, created_at,
              claimed_at, completed_at
            ) values (?, ?, 'READY', ?, ?, ?, ?, ?, ?, ?, ?, null, null)
            """,
            (
                job_id,
                job_type.value,
                idempotency_key,
                profile_id,
                plan_id,
                followup_id,
                scheduled_at.isoformat(),
                _json(payload),
                payload_sha256,
                created_at.isoformat(),
            ),
        )
        row = connection.execute(
            "select * from workflow_jobs where job_id=?", (job_id,)
        ).fetchone()
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
            "followup_id": row["followup_id"],
            "scheduled_at": row["scheduled_at"],
            "payload": json.loads(row["payload_json"]),
            "payload_sha256": row["payload_sha256"],
        }
    )


__all__ = [
    "WorkflowJobQueue",
    "WorkflowJobStatus",
    "WorkflowJobType",
    "WorkflowJobV1",
]
