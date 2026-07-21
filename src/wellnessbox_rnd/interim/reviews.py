from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wellnessbox_rnd.interim.store import InterimStore


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("review_datetime_must_be_timezone_aware")
    return value.astimezone(UTC)


class PharmacistReviewDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pharmacy_id: int = Field(ge=1)
    decision: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("review_decision_required")
        return normalized

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PharmacistReviewService:
    def __init__(self, store: InterimStore):
        self.store = store

    @staticmethod
    def create_in_transaction(
        connection,
        *,
        profile_id: str,
        reason_codes: list[str],
        created_at: datetime,
        data_class: str,
        simulation_badge: bool,
        urgency: str,
        run_id: str | None = None,
        source_job_id: str | None = None,
    ) -> dict[str, Any]:
        reasons = sorted(set(reason_codes))
        if not profile_id.strip() or not reasons:
            raise ValueError("review_identity_required")
        created = _utc(created_at)
        identity = {
            "profile_id": profile_id,
            "reason_codes": reasons,
            "source_job_id": source_job_id,
        }
        review_id = f"review_{_sha(identity)[:24]}"
        expected = {
            "run_id": run_id,
            "profile_id": profile_id,
            "data_class": data_class,
            "simulation_badge": int(simulation_badge),
            "urgency": urgency,
            "reason_codes_json": _json(reasons),
            "source_job_id": source_job_id,
        }
        existing = connection.execute(
            "select * from review_tasks where review_id=?", (review_id,)
        ).fetchone()
        if existing is not None:
            observed = {key: existing[key] for key in expected}
            if observed != expected:
                raise ValueError("review_idempotency_payload_conflict")
            return dict(existing) | {"deduplicated": True}
        connection.execute(
            """
            insert into review_tasks(
              review_id, run_id, profile_id, data_class, simulation_badge,
              urgency, reason_codes_json, status, decision_json, created_at,
              completed_at, pharmacy_id, source_job_id,
              completion_postcondition_json, completion_postcondition_sha256
            ) values (?, ?, ?, ?, ?, ?, ?, 'OPEN', null, ?, null, null, ?, null, null)
            """,
            (
                review_id,
                run_id,
                profile_id,
                data_class,
                int(simulation_badge),
                urgency,
                expected["reason_codes_json"],
                created.isoformat(),
                source_job_id,
            ),
        )
        row = connection.execute(
            "select * from review_tasks where review_id=?", (review_id,)
        ).fetchone()
        return dict(row) | {"deduplicated": False}

    def complete_review(
        self,
        *,
        review_id: str,
        decision: PharmacistReviewDecisionV1,
        completed_at: datetime,
    ) -> dict[str, Any]:
        completed = _utc(completed_at)
        with self.store.transaction(immediate=True) as connection:
            row = connection.execute(
                "select * from review_tasks where review_id=?", (review_id,)
            ).fetchone()
            if row is None:
                raise ValueError("review_missing")
            if str(row["status"]) != "OPEN":
                raise ValueError("review_already_completed")
            assigned = row["pharmacy_id"]
            if assigned is not None and int(assigned) != decision.pharmacy_id:
                raise PermissionError("review_pharmacy_mismatch")
            source_job_id = row["source_job_id"]
            source_job_status = None
            serious_hold_active = None
            plan_stop_recorded = None
            if source_job_id is not None:
                job = connection.execute(
                    "select status from workflow_jobs where job_id=?", (source_job_id,)
                ).fetchone()
                if job is None or str(job["status"]) != "CANCELLED":
                    raise ValueError("review_source_job_not_cancelled")
                source_job_status = "CANCELLED"
            else:
                reasons = json.loads(str(row["reason_codes_json"]))
                if "SERIOUS_ADVERSE_EVENT" in reasons:
                    case_ids = [item for item in reasons if item != "SERIOUS_ADVERSE_EVENT"]
                    case_id = case_ids[0] if case_ids else ""
                    serious_hold_active = bool(
                        connection.execute(
                            """
                            select count(*) from adverse_events
                            where case_id=? and profile_id=? and serious=1 and status='ESCALATED'
                            """,
                            (case_id, row["profile_id"]),
                        ).fetchone()[0]
                    )
                    plan_stop_recorded = bool(
                        connection.execute(
                            """
                            select count(*) from execution_events
                            where idempotency_key=? and payload_state='ACTIVE'
                            """,
                            (f"serious-ae:{case_id}",),
                        ).fetchone()[0]
                    )
                    if not serious_hold_active or not plan_stop_recorded:
                        raise ValueError("review_serious_ae_postcondition_missing")
            decision_payload = decision.model_dump(mode="json", exclude={"pharmacy_id"})
            postconditions = {
                "schema_version": "pharmacist_review_completion_postcondition_v1",
                "review_id": review_id,
                "review_status": "COMPLETED",
                "pharmacy_id": decision.pharmacy_id,
                "decision_recorded": True,
                "source_job_id": source_job_id,
                "source_job_status": source_job_status,
                "serious_hold_active": serious_hold_active,
                "plan_stop_recorded": plan_stop_recorded,
                "completed_at": completed.isoformat(),
            }
            postcondition_sha256 = _sha(postconditions)
            changed = connection.execute(
                """
                update review_tasks
                set status='COMPLETED', decision_json=?, completed_at=?, pharmacy_id=?,
                    completion_postcondition_json=?, completion_postcondition_sha256=?
                where review_id=? and status='OPEN'
                """,
                (
                    _json(decision_payload),
                    completed.isoformat(),
                    decision.pharmacy_id,
                    _json(postconditions),
                    postcondition_sha256,
                    review_id,
                ),
            ).rowcount
            if changed != 1:
                raise ValueError("review_already_completed")
        return {
            "review_id": review_id,
            "status": "COMPLETED",
            "immutable": True,
            "postconditions": postconditions,
            "completion_postcondition_sha256": postcondition_sha256,
        }


__all__ = [
    "PharmacistReviewDecisionV1",
    "PharmacistReviewService",
]
