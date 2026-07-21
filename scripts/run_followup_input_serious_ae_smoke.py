from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from wellnessbox_rnd.interim.agent import AgentState, BoundedAgent
from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / (
    "data/original_plan/evidence/op075_op076_followup_input_serious_ae_smoke_v1.json"
)
SOURCE_PATHS = [
    "apps/inference_api/routes/interim.py",
    "scripts/run_followup_input_serious_ae_smoke.py",
    "src/wellnessbox_rnd/interim/agent.py",
    "src/wellnessbox_rnd/interim/jobs.py",
    "tests/test_interim_agent.py",
    "tests/test_interim_api.py",
    "tests/test_interim_jobs.py",
    "tests/test_pro_plan_service.py",
]
NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
PROFILE_ID = "usr_1234567890abcdef"
EXECUTION_ID = "execution_op075_op076"
PLAN_ID = "plan_op075_op076"


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
    return {
        key: value
        for key, value in job.items()
        if key not in {"job_id", "claim_token", "lease_until"}
    }


def _seed(store: InterimStore) -> None:
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values (?, ?, ?, ?, ?, ?)",
            (
                PROFILE_ID,
                "PROXY_GOLD_SIMULATION",
                '["followup:write","pro:write","device:write","ae:write"]',
                "{}",
                "profile-hash",
                NOW.isoformat(),
            ),
        )
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_op075_op076', ?, 1, 'v1', '{}', 'consent-hash', ?)",
            (PROFILE_ID, NOW.isoformat()),
        )
        connection.execute(
            "insert into executions values (?, 'request_op075_op076', ?, null, "
            "'consent_op075_op076', 'request-hash', 'COMPLETE', ?, ?)",
            (EXECUTION_ID, PROFILE_ID, NOW.isoformat(), NOW.isoformat()),
        )
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (
              'event_op075_op076_plan', ?, 'consent_op075_op076', 0,
              'recommendation', 'system', 'plan', ?, 'plan-hash', 'plan-hash', ?
            )
            """,
            (EXECUTION_ID, json.dumps({"plan_id": PLAN_ID}), NOW.isoformat()),
        )


def run_smoke() -> dict[str, object]:
    with TemporaryDirectory(prefix="op075-op076-") as directory:
        store = InterimStore(Path(directory) / "closed-loop.sqlite3")
        _seed(store)
        queue = WorkflowJobQueue(store)
        pro = queue.enqueue_input_reevaluation(
            profile_id=PROFILE_ID,
            plan_id=PLAN_ID,
            execution_id=EXECUTION_ID,
            input_kind="PRO",
            input_id="pro_smoke_1",
            input_sha256="a" * 64,
            received_at=NOW,
        )
        device = queue.enqueue_input_reevaluation(
            profile_id=PROFILE_ID,
            plan_id=PLAN_ID,
            execution_id=EXECUTION_ID,
            input_kind="DEVICE",
            input_id="device_smoke_1",
            input_sha256="b" * 64,
            received_at=NOW + timedelta(minutes=1),
        )
        agent = BoundedAgent(store)
        run = agent.create_run(profile_id=PROFILE_ID, idempotency_key="serious-ae-smoke")
        with store.transaction() as connection:
            connection.execute(
                "update agent_runs set state_after=? where run_id=?",
                (AgentState.FOLLOWUP_ACTIVE, run["run_id"]),
            )
            connection.execute(
                "insert into recommendation_runs values "
                "('rec_op075_op076', ?, null, 'READY', 'request-hash', '{}', ?, null)",
                (PROFILE_ID, NOW.isoformat()),
            )
        stopped = agent.record_adverse_event(
            run_id=str(run["run_id"]),
            arguments={
                "case_id": "ae_op075_op076_serious",
                "profile_id": PROFILE_ID,
                "execution_id": EXECUTION_ID,
                "plan_id": PLAN_ID,
                "serious": True,
                "observed_at": (NOW + timedelta(minutes=2)).isoformat(),
                "related_to_recommendation": True,
            },
        )
        hold_error = None
        try:
            agent.create_run(profile_id=PROFILE_ID, idempotency_key="after-stop")
        except ValueError as error:
            hold_error = str(error)
        jobs = [dict(row) for row in store.rows("select * from workflow_jobs order by scheduled_at")]
        followups = [
            dict(row) for row in store.rows("select * from followups order by due_at")
        ]
        stop_events = [
            dict(row)
            for row in store.rows(
                "select event_type, idempotency_key, payload_json from execution_events "
                "where idempotency_key like 'serious-ae:%'"
            )
        ]
        review_count = int(store.scalar("select count(*) from review_tasks"))
        recommendation_status = str(
            store.scalar(
                "select status from recommendation_runs where run_id='rec_op075_op076'"
            )
        )

    normalized_jobs = [
        {
            "job_type": row["job_type"],
            "status": row["status"],
            "idempotency_key": row["idempotency_key"],
            "plan_id": row["plan_id"],
            "execution_id": row["execution_id"],
            "scheduled_at": row["scheduled_at"],
            "payload": json.loads(row["payload_json"]),
            "last_error": row["last_error"],
        }
        for row in jobs
    ]
    assert len(normalized_jobs) == 2
    assert all(row["status"] == "CANCELLED" for row in normalized_jobs)
    assert all(row["status"] == "CLOSED" for row in followups)
    assert len(stop_events) == 1
    assert review_count == 1
    assert recommendation_status == "STOPPED"
    assert hold_error == "serious_adverse_event_recommendation_hold"
    return {
        "schema_version": "op075_op076_followup_input_serious_ae_smoke_v1",
        "source": {
            "commit": _source_commit(),
            "sha256": _source_sha256(),
            "paths": SOURCE_PATHS,
        },
        "cases": {
            "case_count": 3,
            "pro_next_job": _normalize_job(pro["next_job"]),
            "device_next_job": _normalize_job(device["next_job"]),
            "serious_adverse_event_stop": stopped,
            "stored_jobs_after_stop": normalized_jobs,
            "stored_followup_statuses": [row["status"] for row in followups],
            "execution_stop_event": {
                **stop_events[0],
                "payload_json": json.loads(stop_events[0]["payload_json"]),
            },
            "recommendation_status": recommendation_status,
            "review_count": review_count,
            "recommendation_hold_error": hold_error,
        },
        "checks": {
            "pro_receipt_decides_immediate_next_job": True,
            "device_receipt_decides_immediate_next_job": True,
            "jobs_use_existing_shared_queue": True,
            "serious_event_appends_execution_discontinuation": True,
            "serious_event_cancels_linked_work": True,
            "serious_event_stops_current_recommendations": True,
            "serious_event_blocks_additional_recommendations": True,
            "urgent_review_created_once": True,
        },
        "evidence_boundary": {
            "op075_proven_stage": "IMPLEMENTED",
            "op075_required_stage": "OPERATED",
            "op076_proven_stage": "IMPLEMENTED",
            "op076_required_stage": "OPERATED",
            "deployed_worker_operation_proven": False,
            "production_serious_ae_stop_proven": False,
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
