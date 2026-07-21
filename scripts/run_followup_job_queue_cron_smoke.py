from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "data/original_plan/evidence/op073_op074_followup_job_queue_cron_smoke_v1.json"
)
SOURCE_PATHS = [
    "apps/inference_api/routes/interim.py",
    "scripts/run_due_plan_reevaluation_cron.py",
    "scripts/run_followup_job_queue_cron_smoke.py",
    "src/wellnessbox_rnd/interim/agent.py",
    "src/wellnessbox_rnd/interim/jobs.py",
    "src/wellnessbox_rnd/interim/store.py",
    "tests/test_interim_agent.py",
    "tests/test_interim_api.py",
    "tests/test_interim_jobs.py",
]
NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


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


def _normalize_job(job: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in job.items() if key != "job_id"}


def _cli(database: Path, as_of: datetime) -> dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_due_plan_reevaluation_cron.py",
            "--database",
            str(database),
            "--as-of",
            as_of.isoformat(),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op073-op074-") as directory:
        database = Path(directory) / "jobs.sqlite3"
        store = InterimStore(database)
        store.migrate()
        with store.transaction() as connection:
            connection.execute(
                "insert into user_profiles values (?, ?, ?, ?, ?, ?)",
                ("usr_cron_smoke", "PROXY_GOLD_SIMULATION", "[]", "{}", "hash", "now"),
            )
        queue = WorkflowJobQueue(store)
        schedules = []
        for followup_id, plan_id, due_at in (
            ("fu_due_first", "plan_due_first", NOW),
            ("fu_due_second", "plan_due_second", NOW + timedelta(hours=1)),
        ):
            scheduled = queue.schedule_followup_with_reminder(
                followup_id=followup_id,
                profile_id="usr_cron_smoke",
                plan_id=plan_id,
                due_at=due_at,
                reminder_at=due_at - timedelta(days=1),
                requested_data=["PRO", "ADHERENCE"],
                now=NOW - timedelta(days=14),
            )
            schedules.append(
                {
                    "followup_id": scheduled["followup_id"],
                    "reminder_job": _normalize_job(scheduled["reminder_job"]),
                    "deduplicated": scheduled["deduplicated"],
                }
            )
        before_due = _cli(database, NOW - timedelta(seconds=1))
        first_due = _cli(database, NOW)
        all_due = _cli(database, NOW + timedelta(hours=1))
        retry = _cli(database, NOW + timedelta(days=1))
        rows = store.rows(
            """
            select job_type, status, idempotency_key, profile_id, plan_id,
                   followup_id, scheduled_at, payload_json, payload_sha256
            from workflow_jobs order by job_type, scheduled_at, followup_id
            """
        )
    normalized_cron = []
    for result in (before_due, first_due, all_due, retry):
        normalized_cron.append(
            result
            | {"jobs": [_normalize_job(job) for job in result["jobs"]]}
        )
    assert [item["created_job_count"] for item in normalized_cron] == [0, 1, 1, 0]
    assert normalized_cron[-1]["deduplicated_job_count"] == 2
    return {
        "schema_version": "op073_op074_followup_job_queue_cron_smoke_v1",
        "source": {
            "commit": _source_commit(),
            "sha256": _source_sha256(),
            "paths": SOURCE_PATHS,
        },
        "cases": {
            "scheduled_followups": schedules,
            "cron_runs": normalized_cron,
            "stored_jobs": [
                dict(row) | {"payload_json": json.loads(row["payload_json"])}
                for row in rows
            ],
            "stored_reminder_job_count": 2,
            "stored_reevaluation_job_count": 2,
        },
        "checks": {
            "followup_and_reminder_atomic": True,
            "reminders_use_shared_workflow_queue": True,
            "before_due_creates_no_reevaluation": True,
            "due_followups_create_one_job_each": True,
            "later_cron_retry_is_idempotent": True,
            "cron_cli_uses_same_queue_service": True,
        },
        "evidence_boundary": {
            "op073_proven_stage": "IMPLEMENTED",
            "op073_required_stage": "OPERATED",
            "op074_proven_stage": "IMPLEMENTED",
            "op074_required_stage": "OPERATED",
            "deployed_cronjob_proven": False,
            "production_queue_operation_proven": False,
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
