from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.store import InterimStore

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


def _queue(tmp_path) -> WorkflowJobQueue:
    store = InterimStore(tmp_path / "jobs.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values (?, ?, ?, ?, ?, ?)",
            ("usr_jobs", "PROXY_GOLD_SIMULATION", "[]", "{}", "hash", "now"),
        )
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_jobs', 'usr_jobs', 1, 'v1', '{}', 'consent-jobs', 'now')"
        )
        connection.execute(
            "insert into active_profile_consents values "
            "('usr_jobs', 'consent_jobs', 'now')"
        )
    return WorkflowJobQueue(store)


def _register_plan(queue: WorkflowJobQueue, *, execution_id: str, plan_id: str) -> None:
    consent_id = "consent_jobs"
    with queue.store.transaction() as connection:
        connection.execute(
            "insert or ignore into executions values "
            "(?, ?, 'usr_jobs', null, ?, ?, 'COMPLETE', ?, ?)",
            (
                execution_id,
                execution_id,
                consent_id,
                execution_id,
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
        payload = f'{{"plan_id":"{plan_id}"}}'
        connection.execute(
            """
            insert or ignore into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (?, ?, ?, 0, 'recommendation', 'system', 'plan', ?, ?, ?, ?)
            """,
            (
                f"event_{execution_id}",
                execution_id,
                consent_id,
                payload,
                plan_id,
                plan_id,
                NOW.isoformat(),
            ),
        )


def _schedule(
    queue: WorkflowJobQueue,
    *,
    followup_id: str = "fu_jobs_1",
    plan_id: str = "plan_jobs_1",
    execution_id: str | None = None,
    due_at: datetime = NOW + timedelta(days=14),
    reminder_at: datetime | None = None,
):
    execution_id = execution_id or f"execution_{plan_id}"
    _register_plan(queue, execution_id=execution_id, plan_id=plan_id)
    return queue.schedule_followup_with_reminder(
        followup_id=followup_id,
        profile_id="usr_jobs",
        plan_id=plan_id,
        execution_id=execution_id,
        due_at=due_at,
        reminder_at=reminder_at or due_at - timedelta(days=1),
        requested_data=["PRO", "ADHERENCE", "PRO"],
        now=NOW,
    )


def test_followup_and_reminder_job_are_stored_atomically(tmp_path) -> None:
    queue = _queue(tmp_path)
    result = _schedule(queue)

    assert result["deduplicated"] is False
    assert result["reminder_job"]["job_type"] == "FOLLOWUP_REMINDER"
    assert result["reminder_job"]["status"] == "READY"
    assert queue.store.scalar("select count(*) from followups") == 1
    assert queue.store.scalar("select count(*) from workflow_jobs") == 1
    assert queue.store.scalar("select plan_id from followups") == "plan_jobs_1"


def test_followup_schedule_is_idempotent_and_conflicts_fail(tmp_path) -> None:
    queue = _queue(tmp_path)
    first = _schedule(queue)
    second = _schedule(queue)

    assert second["deduplicated"] is True
    assert second["reminder_job"]["job_id"] == first["reminder_job"]["job_id"]
    with pytest.raises(ValueError, match="followup_idempotency_payload_conflict"):
        _schedule(queue, plan_id="plan_changed")
    with pytest.raises(ValueError, match="followup_idempotency_payload_conflict"):
        _schedule(queue, reminder_at=NOW + timedelta(days=12))
    assert queue.store.scalar("select count(*) from workflow_jobs") == 1


def test_cron_creates_one_reevaluation_job_only_when_due(tmp_path) -> None:
    queue = _queue(tmp_path)
    _schedule(queue, due_at=NOW + timedelta(hours=2))

    before = queue.enqueue_due_plan_reevaluations(as_of=NOW + timedelta(hours=1))
    due = queue.enqueue_due_plan_reevaluations(as_of=NOW + timedelta(hours=2))
    retry = queue.enqueue_due_plan_reevaluations(as_of=NOW + timedelta(days=1))

    assert before["due_followup_count"] == 0
    assert due["created_job_count"] == 1
    assert due["jobs"][0]["job_type"] == "PLAN_REEVALUATION"
    assert retry["created_job_count"] == 0
    assert retry["deduplicated_job_count"] == 1
    assert (
        queue.store.scalar("select count(*) from workflow_jobs where job_type='PLAN_REEVALUATION'")
        == 1
    )


def test_cron_orders_multiple_due_followups_and_excludes_closed(tmp_path) -> None:
    queue = _queue(tmp_path)
    _schedule(queue, followup_id="fu_later", plan_id="plan_later", due_at=NOW)
    _schedule(
        queue,
        followup_id="fu_earlier",
        plan_id="plan_earlier",
        due_at=NOW - timedelta(hours=1),
    )
    _schedule(queue, followup_id="fu_closed", plan_id="plan_closed", due_at=NOW)
    with queue.store.transaction() as connection:
        connection.execute("update followups set status='CLOSED' where followup_id='fu_closed'")

    result = queue.enqueue_due_plan_reevaluations(as_of=NOW)

    assert [job["followup_id"] for job in result["jobs"]] == ["fu_earlier", "fu_later"]
    assert result["created_job_count"] == 2


def test_schedule_requires_plan_and_timezone_aware_datetimes(tmp_path) -> None:
    queue = _queue(tmp_path)
    with pytest.raises(ValueError, match="followup_plan_id_required"):
        _schedule(queue, plan_id="")
    with pytest.raises(ValueError, match="workflow_job_datetime_must_be_timezone_aware"):
        queue.enqueue_due_plan_reevaluations(as_of=datetime(2026, 7, 21, 12, 0))


def test_schedule_rejects_plan_not_linked_to_execution(tmp_path) -> None:
    queue = _queue(tmp_path)
    _register_plan(queue, execution_id="execution_known", plan_id="plan_known")
    with pytest.raises(ValueError, match="followup_active_execution_plan_required"):
        queue.schedule_followup_with_reminder(
            followup_id="fu_unlinked",
            profile_id="usr_jobs",
            plan_id="plan_other",
            execution_id="execution_known",
            due_at=NOW,
            reminder_at=NOW,
            requested_data=["PRO"],
            now=NOW,
        )


def test_claim_ack_and_explicit_retry(tmp_path) -> None:
    queue = _queue(tmp_path)
    _schedule(queue, due_at=NOW, reminder_at=NOW)
    first = queue.claim_ready_jobs(worker_id="one", as_of=NOW, limit=1, lease_seconds=60)[0]
    assert queue.claim_ready_jobs(worker_id="two", as_of=NOW, limit=1) == []
    with pytest.raises(ValueError, match="workflow_job_claim_mismatch"):
        queue.acknowledge_job(job_id=first["job_id"], claim_token="wrong", completed_at=NOW)
    queue.retry_job(
        job_id=first["job_id"],
        claim_token=first["claim_token"],
        retry_at=NOW + timedelta(minutes=5),
        error="temporary",
    )
    assert queue.claim_ready_jobs(worker_id="three", as_of=NOW + timedelta(minutes=4)) == []
    final = queue.claim_ready_jobs(worker_id="three", as_of=NOW + timedelta(minutes=5))[0]
    queue.acknowledge_job(
        job_id=final["job_id"],
        claim_token=final["claim_token"],
        completed_at=NOW,
    )
    assert queue.store.scalar("select status from workflow_jobs") == "COMPLETED"


def test_expired_claim_fails_closed_and_creates_one_review(tmp_path) -> None:
    queue = _queue(tmp_path)
    _schedule(queue, due_at=NOW, reminder_at=NOW)
    claimed = queue.claim_ready_jobs(
        worker_id="one", as_of=NOW, limit=1, lease_seconds=60
    )[0]

    assert queue.claim_ready_jobs(
        worker_id="two", as_of=NOW + timedelta(seconds=61), limit=1
    ) == []
    assert queue.store.scalar("select status from workflow_jobs") == "CANCELLED"
    assert queue.store.scalar("select last_error from workflow_jobs") == (
        "WORKFLOW_JOB_TIMEOUT"
    )
    assert queue.store.scalar("select status from followups") == "CLOSED"
    assert queue.store.scalar("select count(*) from review_tasks") == 1
    with pytest.raises(ValueError, match="workflow_job_claim_mismatch"):
        queue.acknowledge_job(
            job_id=claimed["job_id"],
            claim_token=claimed["claim_token"],
            completed_at=NOW + timedelta(seconds=62),
        )


def test_stale_evidence_and_consent_loss_fail_closed(tmp_path) -> None:
    stale_queue = _queue(tmp_path / "stale")
    _schedule(stale_queue, due_at=NOW, reminder_at=NOW)
    with stale_queue.store.transaction() as connection:
        connection.execute(
            "update execution_events set effective_payload_sha256='changed'"
        )
    assert stale_queue.claim_ready_jobs(worker_id="one", as_of=NOW) == []
    assert stale_queue.store.scalar("select last_error from workflow_jobs") == (
        "STALE_EXECUTION_EVIDENCE"
    )
    assert stale_queue.store.scalar("select count(*) from review_tasks") == 1

    consent_queue = _queue(tmp_path / "consent")
    _schedule(consent_queue, due_at=NOW, reminder_at=NOW)
    with consent_queue.store.transaction() as connection:
        connection.execute(
            "delete from active_profile_consents where profile_id='usr_jobs'"
        )
    assert consent_queue.claim_ready_jobs(worker_id="one", as_of=NOW) == []
    assert consent_queue.store.scalar("select last_error from workflow_jobs") == (
        "CONSENT_NOT_ACTIVE"
    )
    assert consent_queue.store.scalar("select count(*) from review_tasks") == 1


def test_exact_schedule_retry_keeps_original_guard_for_fail_closed_claim(tmp_path) -> None:
    queue = _queue(tmp_path)
    first = _schedule(queue, due_at=NOW, reminder_at=NOW)
    with queue.store.transaction() as connection:
        connection.execute(
            "update execution_events set effective_payload_sha256='changed-before-retry'"
        )

    retry = _schedule(queue, due_at=NOW, reminder_at=NOW)

    assert retry["deduplicated"] is True
    assert retry["reminder_job"]["job_id"] == first["reminder_job"]["job_id"]
    assert queue.claim_ready_jobs(worker_id="one", as_of=NOW) == []
    assert queue.store.scalar("select last_error from workflow_jobs limit 1") == (
        "STALE_EXECUTION_EVIDENCE"
    )


def test_acknowledgement_rechecks_evidence_and_commits_cancellation(tmp_path) -> None:
    queue = _queue(tmp_path)
    _schedule(queue, due_at=NOW, reminder_at=NOW)
    claimed = queue.claim_ready_jobs(
        worker_id="one", as_of=NOW, limit=1, lease_seconds=300
    )[0]
    with queue.store.transaction() as connection:
        connection.execute(
            "update execution_events set effective_payload_sha256='changed-after-claim'"
        )

    with pytest.raises(ValueError, match="stale_execution_evidence"):
        queue.acknowledge_job(
            job_id=claimed["job_id"],
            claim_token=claimed["claim_token"],
            completed_at=NOW + timedelta(seconds=1),
        )
    assert queue.store.scalar("select status from workflow_jobs") == "CANCELLED"
    assert queue.store.scalar("select count(*) from review_tasks") == 1


def test_closed_or_discontinued_followup_cancels_ready_jobs(tmp_path) -> None:
    queue = _queue(tmp_path)
    _schedule(queue, due_at=NOW, reminder_at=NOW)
    queue.close_followup(followup_id="fu_jobs_1", reason="USER_STOPPED")
    assert queue.store.scalar("select status from workflow_jobs") == "CANCELLED"

    _schedule(queue, followup_id="fu_discontinued", plan_id="plan_stopped", due_at=NOW)
    with queue.store.transaction() as connection:
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (?, ?, ?, 1, 'followup_evaluation', 'survey', 'stop', ?, 'stop', 'stop', ?)
            """,
            (
                "event_stop",
                "execution_plan_stopped",
                "consent_jobs",
                '{"plan_id":"plan_stopped","timepoint":"discontinuation"}',
                NOW.isoformat(),
            ),
        )
    result = queue.enqueue_due_plan_reevaluations(as_of=NOW)
    assert result["created_job_count"] == 0
    assert (
        queue.store.scalar("select status from followups where followup_id='fu_discontinued'")
        == "CLOSED"
    )


def test_claim_rechecks_plan_after_cron_enqueue(tmp_path) -> None:
    queue = _queue(tmp_path)
    _schedule(queue, due_at=NOW, reminder_at=NOW - timedelta(days=1))
    queue.enqueue_due_plan_reevaluations(as_of=NOW)
    with queue.store.transaction() as connection:
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (?, ?, 'consent_jobs', 1, 'followup_evaluation', 'survey',
                      'stop-after-cron', ?, 'stop-after-cron', 'stop-after-cron', ?)
            """,
            (
                "event_stop_after_cron",
                "execution_plan_jobs_1",
                '{"plan_id":"plan_jobs_1","timepoint":"discontinuation"}',
                NOW.isoformat(),
            ),
        )
    assert queue.claim_ready_jobs(worker_id="worker", as_of=NOW, limit=10) == []
    assert queue.store.scalar(
        "select count(*) from workflow_jobs where status='CANCELLED'"
    ) == 2


def test_pro_and_device_inputs_decide_immediate_reevaluation_jobs(tmp_path) -> None:
    queue = _queue(tmp_path)
    _register_plan(queue, execution_id="execution_inputs", plan_id="plan_inputs")

    pro = queue.enqueue_input_reevaluation(
        profile_id="usr_jobs",
        plan_id="plan_inputs",
        execution_id="execution_inputs",
        input_kind="PRO",
        input_id="event_pro_1",
        input_sha256="a" * 64,
        received_at=NOW,
    )
    retry = queue.enqueue_input_reevaluation(
        profile_id="usr_jobs",
        plan_id="plan_inputs",
        execution_id="execution_inputs",
        input_kind="PRO",
        input_id="event_pro_1",
        input_sha256="a" * 64,
        received_at=NOW,
    )
    device = queue.enqueue_input_reevaluation(
        profile_id="usr_jobs",
        plan_id="plan_inputs",
        execution_id="execution_inputs",
        input_kind="DEVICE",
        input_id="device_1",
        input_sha256="b" * 64,
        received_at=NOW + timedelta(minutes=1),
    )

    assert pro["decision"] == "REEVALUATE_PLAN"
    assert pro["next_job"]["scheduled_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert retry["deduplicated"] is True
    assert device["reason_code"] == "DEVICE_INPUT_RECEIVED"
    assert queue.store.scalar("select count(*) from workflow_jobs") == 2


def test_input_reevaluation_rejects_changed_receipt_and_stopped_plan(tmp_path) -> None:
    queue = _queue(tmp_path)
    _register_plan(queue, execution_id="execution_inputs", plan_id="plan_inputs")
    arguments = {
        "profile_id": "usr_jobs",
        "plan_id": "plan_inputs",
        "execution_id": "execution_inputs",
        "input_kind": "PRO",
        "input_id": "event_pro_1",
        "received_at": NOW,
    }
    queue.enqueue_input_reevaluation(input_sha256="a" * 64, **arguments)
    with pytest.raises(ValueError, match="workflow_job_idempotency_payload_conflict"):
        queue.enqueue_input_reevaluation(input_sha256="b" * 64, **arguments)

    with queue.store.transaction() as connection:
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (?, ?, 'consent_jobs', 1, 'followup_evaluation', 'survey',
                      'stop-inputs', ?, 'stop-inputs', 'stop-inputs', ?)
            """,
            (
                "event_stop_inputs",
                "execution_inputs",
                '{"plan_id":"plan_inputs","timepoint":"discontinuation"}',
                NOW.isoformat(),
            ),
        )
    with pytest.raises(ValueError, match="followup_active_execution_plan_required"):
        queue.enqueue_input_reevaluation(
            input_sha256="c" * 64,
            input_id="event_pro_2",
            **{key: value for key, value in arguments.items() if key != "input_id"},
        )
