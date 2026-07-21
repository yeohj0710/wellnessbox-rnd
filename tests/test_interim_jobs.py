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
    return WorkflowJobQueue(store)


def _schedule(
    queue: WorkflowJobQueue,
    *,
    followup_id: str = "fu_jobs_1",
    plan_id: str = "plan_jobs_1",
    due_at: datetime = NOW + timedelta(days=14),
):
    return queue.schedule_followup_with_reminder(
        followup_id=followup_id,
        profile_id="usr_jobs",
        plan_id=plan_id,
        due_at=due_at,
        reminder_at=due_at - timedelta(days=1),
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
    assert queue.store.scalar(
        "select count(*) from workflow_jobs where job_type='PLAN_REEVALUATION'"
    ) == 1


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
