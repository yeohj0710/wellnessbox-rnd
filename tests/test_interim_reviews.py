from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from wellnessbox_rnd.interim.reviews import (
    PharmacistReviewDecisionV1,
    PharmacistReviewService,
)
from wellnessbox_rnd.interim.store import InterimStore

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _store_with_cancelled_job(tmp_path) -> InterimStore:
    store = InterimStore(tmp_path / "reviews.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values "
            "('usr_review', 'PROXY_GOLD_SIMULATION', '[]', '{}', 'profile', ?) ",
            (NOW.isoformat(),),
        )
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_review', 'usr_review', 1, 'v1', '{}', 'consent', ?)",
            (NOW.isoformat(),),
        )
        connection.execute(
            "insert into active_profile_consents values "
            "('usr_review', 'consent_review', ?)",
            (NOW.isoformat(),),
        )
        connection.execute(
            "insert into executions values "
            "('execution_review', 'request_review', 'usr_review', null, "
            "'consent_review', 'request', 'COMPLETE', ?, ?)",
            (NOW.isoformat(), NOW.isoformat()),
        )
        connection.execute(
            "insert into followups values "
            "('followup_review', 'usr_review', 'plan_review', 'execution_review', "
            "?, '[]', 'CLOSED', ?)",
            (NOW.isoformat(), NOW.isoformat()),
        )
        connection.execute(
            """
            insert into workflow_jobs(
              job_id, job_type, status, idempotency_key, profile_id, plan_id,
              followup_id, execution_id, scheduled_at, payload_json, payload_sha256,
              created_at, attempt_count, last_error
            ) values (
              'job_review', 'PLAN_REEVALUATION', 'CANCELLED', 'review-job',
              'usr_review', 'plan_review', 'followup_review', 'execution_review',
              ?, '{}', 'payload', ?, 1, 'STALE_EXECUTION_EVIDENCE'
            )
            """,
            (NOW.isoformat(), NOW.isoformat()),
        )
    return store


def test_review_schema_persists_provenance_and_postcondition_columns(tmp_path) -> None:
    store = InterimStore(tmp_path / "schema.sqlite3")
    store.migrate()

    columns = {row[1] for row in store.rows("pragma table_info(review_tasks)")}
    assert {
        "source_job_id",
        "completion_postcondition_json",
        "completion_postcondition_sha256",
    } <= columns


def test_job_failure_review_is_deterministic_and_completion_is_immutable(tmp_path) -> None:
    store = _store_with_cancelled_job(tmp_path)
    service = PharmacistReviewService(store)
    arguments = {
        "profile_id": "usr_review",
        "reason_codes": ["WORKFLOW_JOB_FAIL_CLOSED", "STALE_EXECUTION_EVIDENCE"],
        "created_at": NOW,
        "data_class": "INTERIM_RUNTIME_EVENT",
        "simulation_badge": True,
        "urgency": "HIGH",
        "source_job_id": "job_review",
    }
    with store.transaction(immediate=True) as connection:
        created = service.create_in_transaction(connection, **arguments)
    with store.transaction(immediate=True) as connection:
        retried = service.create_in_transaction(connection, **arguments)

    assert retried["review_id"] == created["review_id"]
    assert retried["deduplicated"] is True
    completed = service.complete_review(
        review_id=created["review_id"],
        decision=PharmacistReviewDecisionV1(
            pharmacy_id=7,
            decision="acknowledged",
            note="Reviewed failure.",
        ),
        completed_at=NOW,
    )
    assert completed["postconditions"]["source_job_status"] == "CANCELLED"
    assert completed["postconditions"]["decision_recorded"] is True
    canonical = _json(completed["postconditions"])
    assert completed["completion_postcondition_sha256"] == hashlib.sha256(
        canonical.encode()
    ).hexdigest()
    assert store.scalar("select pharmacy_id from review_tasks") == 7
    assert store.scalar("select status from review_tasks") == "COMPLETED"
    with pytest.raises(ValueError, match="review_already_completed"):
        service.complete_review(
            review_id=created["review_id"],
            decision=PharmacistReviewDecisionV1(
                pharmacy_id=8,
                decision="changed",
            ),
            completed_at=NOW,
        )


def test_review_completion_rejects_source_job_that_is_not_cancelled(tmp_path) -> None:
    store = _store_with_cancelled_job(tmp_path)
    service = PharmacistReviewService(store)
    with store.transaction(immediate=True) as connection:
        review = service.create_in_transaction(
            connection,
            profile_id="usr_review",
            reason_codes=["WORKFLOW_JOB_FAIL_CLOSED", "WORKFLOW_JOB_TIMEOUT"],
            created_at=NOW,
            data_class="INTERIM_RUNTIME_EVENT",
            simulation_badge=True,
            urgency="HIGH",
            source_job_id="job_review",
        )
        connection.execute(
            "update workflow_jobs set status='COMPLETED' where job_id='job_review'"
        )

    with pytest.raises(ValueError, match="review_source_job_not_cancelled"):
        service.complete_review(
            review_id=review["review_id"],
            decision=PharmacistReviewDecisionV1(
                pharmacy_id=7,
                decision="acknowledged",
            ),
            completed_at=NOW,
        )
