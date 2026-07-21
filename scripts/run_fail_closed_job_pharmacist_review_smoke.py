from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.reviews import (
    PharmacistReviewDecisionV1,
    PharmacistReviewService,
)
from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "data/original_plan/evidence/op077_op078_fail_closed_job_review_smoke_v1.json"
)
SOURCE_PATHS = [
    "apps/inference_api/routes/interim.py",
    "scripts/run_fail_closed_job_pharmacist_review_smoke.py",
    "src/wellnessbox_rnd/interim/agent.py",
    "src/wellnessbox_rnd/interim/jobs.py",
    "src/wellnessbox_rnd/interim/reviews.py",
    "src/wellnessbox_rnd/interim/store.py",
    "tests/test_interim_agent.py",
    "tests/test_interim_api.py",
    "tests/test_interim_jobs.py",
    "tests/test_interim_reviews.py",
    "tests/test_interim_store.py",
]
NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
PROFILE_ID = "usr_op077_op078"
EXECUTION_ID = "execution_op077_op078"
PLAN_ID = "plan_op077_op078"
CONSENT_ID = "consent_op077_op078"


def _source_sha256() -> str:
    digest = hashlib.sha256()
    for relative in sorted(SOURCE_PATHS):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((ROOT / relative).read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _source_commit() -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *SOURCE_PATHS],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _seed(store: InterimStore) -> WorkflowJobQueue:
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values (?, ?, '[]', '{}', 'profile-hash', ?)",
            (PROFILE_ID, "PROXY_GOLD_SIMULATION", NOW.isoformat()),
        )
        connection.execute(
            "insert into consent_snapshots values (?, ?, 1, 'v1', '{}', 'consent-hash', ?)",
            (CONSENT_ID, PROFILE_ID, NOW.isoformat()),
        )
        connection.execute(
            "insert into active_profile_consents values (?, ?, ?)",
            (PROFILE_ID, CONSENT_ID, NOW.isoformat()),
        )
        connection.execute(
            "insert into executions values (?, 'request_op077_op078', ?, null, ?, "
            "'request-hash', 'COMPLETE', ?, ?)",
            (EXECUTION_ID, PROFILE_ID, CONSENT_ID, NOW.isoformat(), NOW.isoformat()),
        )
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (
              'event_op077_op078_plan', ?, ?, 0, 'recommendation', 'system',
              'plan', ?, 'plan-hash', 'plan-hash', ?
            )
            """,
            (
                EXECUTION_ID,
                CONSENT_ID,
                json.dumps({"plan_id": PLAN_ID}),
                NOW.isoformat(),
            ),
        )
    return WorkflowJobQueue(store)


def _schedule(queue: WorkflowJobQueue, *, suffix: str) -> dict[str, object]:
    return queue.schedule_followup_with_reminder(
        followup_id=f"followup_{suffix}",
        profile_id=PROFILE_ID,
        plan_id=PLAN_ID,
        execution_id=EXECUTION_ID,
        due_at=NOW,
        reminder_at=NOW,
        requested_data=["PRO"],
        now=NOW,
    )


def _duplicate_case(database: Path) -> dict[str, object]:
    queue = _seed(InterimStore(database))
    first = _schedule(queue, suffix="duplicate")
    retry = _schedule(queue, suffix="duplicate")
    claimed = queue.claim_ready_jobs(worker_id="worker_a", as_of=NOW, limit=10)
    second_claim = queue.claim_ready_jobs(worker_id="worker_b", as_of=NOW, limit=10)
    assert first["reminder_job"]["job_id"] == retry["reminder_job"]["job_id"]
    assert retry["deduplicated"] is True
    assert len(claimed) == 1
    assert second_claim == []
    return {
        "stored_job_count": int(queue.store.scalar("select count(*) from workflow_jobs")),
        "first_claim_count": len(claimed),
        "second_claim_count": len(second_claim),
        "exact_retry_deduplicated": True,
    }


def _stale_case(database: Path) -> dict[str, object]:
    queue = _seed(InterimStore(database))
    _schedule(queue, suffix="stale")
    with queue.store.transaction() as connection:
        connection.execute(
            "update execution_events set effective_payload_sha256='new-evidence-hash'"
        )
    assert queue.claim_ready_jobs(worker_id="worker", as_of=NOW) == []
    return {
        "job_status": queue.store.scalar("select status from workflow_jobs"),
        "failure_reason": queue.store.scalar("select last_error from workflow_jobs"),
        "followup_status": queue.store.scalar("select status from followups"),
        "review_count": int(queue.store.scalar("select count(*) from review_tasks")),
    }


def _consent_case(database: Path) -> dict[str, object]:
    queue = _seed(InterimStore(database))
    _schedule(queue, suffix="consent")
    with queue.store.transaction() as connection:
        connection.execute(
            "delete from active_profile_consents where profile_id=?", (PROFILE_ID,)
        )
    assert queue.claim_ready_jobs(worker_id="worker", as_of=NOW) == []
    return {
        "job_status": queue.store.scalar("select status from workflow_jobs"),
        "failure_reason": queue.store.scalar("select last_error from workflow_jobs"),
        "review_count": int(queue.store.scalar("select count(*) from review_tasks")),
    }


def _timeout_and_review_case(database: Path) -> tuple[dict[str, object], dict[str, object]]:
    queue = _seed(InterimStore(database))
    _schedule(queue, suffix="timeout")
    claimed = queue.claim_ready_jobs(
        worker_id="worker", as_of=NOW, limit=1, lease_seconds=60
    )
    assert len(claimed) == 1
    assert queue.claim_ready_jobs(
        worker_id="recovery", as_of=NOW + timedelta(seconds=61), limit=1
    ) == []
    review = queue.store.rows("select * from review_tasks")[0]
    completed = PharmacistReviewService(queue.store).complete_review(
        review_id=str(review["review_id"]),
        decision=PharmacistReviewDecisionV1(
            pharmacy_id=7,
            decision="acknowledged",
            note="Verified fail-closed timeout.",
        ),
        completed_at=NOW + timedelta(seconds=62),
    )
    mutation_error = None
    try:
        PharmacistReviewService(queue.store).complete_review(
            review_id=str(review["review_id"]),
            decision=PharmacistReviewDecisionV1(
                pharmacy_id=8,
                decision="changed",
            ),
            completed_at=NOW + timedelta(seconds=63),
        )
    except ValueError as error:
        mutation_error = str(error)
    stored = queue.store.rows("select * from review_tasks")[0]
    postconditions = json.loads(str(stored["completion_postcondition_json"]))
    canonical = json.dumps(
        postconditions, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == str(
        stored["completion_postcondition_sha256"]
    )
    assert mutation_error == "review_already_completed"
    return (
        {
            "job_status": queue.store.scalar("select status from workflow_jobs"),
            "failure_reason": queue.store.scalar("select last_error from workflow_jobs"),
            "review_count": int(queue.store.scalar("select count(*) from review_tasks")),
        },
        {
            "review_status": completed["status"],
            "assigned_pharmacy_id": postconditions["pharmacy_id"],
            "source_job_status": postconditions["source_job_status"],
            "decision_recorded": postconditions["decision_recorded"],
            "postcondition_hash_verified": True,
            "second_decision_error": mutation_error,
        },
    )


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op077-op078-") as directory:
        root = Path(directory)
        duplicate = _duplicate_case(root / "duplicate.sqlite3")
        stale = _stale_case(root / "stale.sqlite3")
        consent = _consent_case(root / "consent.sqlite3")
        timeout, review = _timeout_and_review_case(root / "timeout.sqlite3")
    assert stale["failure_reason"] == "STALE_EXECUTION_EVIDENCE"
    assert consent["failure_reason"] == "CONSENT_NOT_ACTIVE"
    assert timeout["failure_reason"] == "WORKFLOW_JOB_TIMEOUT"
    assert all(
        case["job_status"] == "CANCELLED" for case in (stale, consent, timeout)
    )
    assert all(case["review_count"] == 1 for case in (stale, consent, timeout))
    return {
        "schema_version": "op077_op078_fail_closed_job_review_smoke_v1",
        "source": {
            "commit": _source_commit(),
            "sha256": _source_sha256(),
            "paths": SOURCE_PATHS,
        },
        "cases": {
            "case_count": 5,
            "duplicate_execution": duplicate,
            "stale_execution_evidence": stale,
            "consent_not_active": consent,
            "workflow_job_timeout": timeout,
            "pharmacist_review_completion": review,
        },
        "checks": {
            "exact_duplicate_has_one_executable_job": True,
            "stale_evidence_cancels_before_execution": True,
            "timeout_cancels_instead_of_requeueing": True,
            "consent_loss_cancels_before_execution": True,
            "each_fail_closed_job_creates_one_existing_review_task": True,
            "review_completion_postconditions_are_hashed": True,
            "completed_review_is_immutable": True,
        },
        "evidence_boundary": {
            "op077_proven_stage": "IMPLEMENTED",
            "op077_required_stage": "OPERATED",
            "op078_proven_stage": "IMPLEMENTED",
            "op078_required_stage": "OPERATED",
            "deployed_worker_operation_proven": False,
            "production_pharmacist_review_proven": False,
            "service_integration_proven": False,
            "production_deployment_proven": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    output = parser.parse_args().output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(run_smoke(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
