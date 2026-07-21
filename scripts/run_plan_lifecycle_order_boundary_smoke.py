from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.inference_api.main import app  # noqa: E402
from wellnessbox_rnd.interim.jobs import WorkflowJobQueue  # noqa: E402
from wellnessbox_rnd.interim.store import InterimStore  # noqa: E402

DEFAULT_OUTPUT = ROOT / (
    "data/original_plan/evidence/"
    "op079_op080_plan_lifecycle_order_boundary_smoke_v1.json"
)
NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
PROFILE_ID = "usr_079080abcdef01"
CONSENT_ID = "consent_op079_op080"
ACTIONS = ("maintain", "adjust", "replace", "stop", "monitor")
RND_SOURCE_PATHS = (
    "apps/inference_api/routes/interim.py",
    "scripts/run_plan_lifecycle_order_boundary_smoke.py",
    "src/wellnessbox_rnd/interim/jobs.py",
    "src/wellnessbox_rnd/interim/plan_lifecycle.py",
    "tests/test_interim_api.py",
    "tests/test_plan_lifecycle.py",
)
SERVICE_SOURCE_PATHS = (
    "app/api/tips/route.ts",
    "lib/order/mutations.ts",
    "lib/order/orderStatus.ts",
)


def _hash_paths(root: Path, paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update((root / relative).read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _last_commit(root: Path, paths: tuple[str, ...]) -> str:
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *paths],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


@contextmanager
def _api_environment(database: Path):
    names = ("WB_RND_INTERIM_DATABASE", "WB_RND_INTERIM_INTERNAL_TOKEN")
    previous = {name: os.environ.get(name) for name in names}
    os.environ["WB_RND_INTERIM_DATABASE"] = str(database)
    os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = "op079-op080-token"
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _seed(database: Path) -> InterimStore:
    store = InterimStore(database)
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values (?, 'PROXY_GOLD_SIMULATION', '[]', '{}', 'p', ?)",
            (PROFILE_ID, NOW.isoformat()),
        )
        connection.execute(
            "insert into consent_snapshots values (?, ?, 1, 'v1', '{}', 'c', ?)",
            (CONSENT_ID, PROFILE_ID, NOW.isoformat()),
        )
        connection.execute(
            "insert into active_profile_consents values (?, ?, ?)",
            (PROFILE_ID, CONSENT_ID, NOW.isoformat()),
        )
        for index, action in enumerate(ACTIONS):
            execution_id = f"execution_op079_{action}"
            plan_id = f"plan_op079_{action}"
            followup_id = f"fu_op079_{action}"
            connection.execute(
                "insert into executions values (?, ?, ?, null, ?, ?, 'COMPLETE', ?, ?)",
                (
                    execution_id,
                    f"request_op079_{action}",
                    PROFILE_ID,
                    CONSENT_ID,
                    f"request-hash-{action}",
                    NOW.isoformat(),
                    NOW.isoformat(),
                ),
            )
            if action == "replace":
                replacement_payload = {
                    "plan_id": "plan_op079_replacement_active",
                    "lifecycle_role": "replacement_candidate",
                    "replaces_plan_id": plan_id,
                }
                connection.execute(
                    """
                    insert into execution_events(
                      event_id, execution_id, consent_snapshot_id, event_index,
                      event_type, source, idempotency_key, payload_json,
                      payload_sha256, effective_payload_sha256, created_at
                    ) values (?, ?, ?, 1, 'optimization', 'system', ?, ?, ?, ?, ?)
                    """,
                    (
                        "event_op079_replacement_candidate",
                        execution_id,
                        CONSENT_ID,
                        "replacement-candidate",
                        json.dumps(replacement_payload, sort_keys=True),
                        "replacement-candidate-hash",
                        "replacement-candidate-hash",
                        NOW.isoformat(),
                    ),
                )
            connection.execute(
                """
                insert into execution_events(
                  event_id, execution_id, consent_snapshot_id, event_index,
                  event_type, source, idempotency_key, payload_json,
                  payload_sha256, effective_payload_sha256, created_at
                ) values (?, ?, ?, 0, 'recommendation', 'system', ?, ?, ?, ?, ?)
                """,
                (
                    f"event_op079_seed_{action}",
                    execution_id,
                    CONSENT_ID,
                    f"seed-{action}",
                    json.dumps({"plan_id": plan_id}, sort_keys=True),
                    f"plan-hash-{action}",
                    f"plan-hash-{action}",
                    NOW.isoformat(),
                ),
            )
            connection.execute(
                """
                insert into followups(
                  followup_id, profile_id, plan_id, execution_id, due_at,
                  requested_data_json, status, created_at
                ) values (?, ?, ?, ?, ?, '["PRO"]', 'OPEN', ?)
                """,
                (
                    followup_id,
                    PROFILE_ID,
                    plan_id,
                    execution_id,
                    NOW.isoformat(),
                    NOW.isoformat(),
                ),
            )
            connection.execute(
                """
                insert into workflow_jobs(
                  job_id, job_type, status, idempotency_key, profile_id, plan_id,
                  followup_id, execution_id, scheduled_at, payload_json,
                  payload_sha256, created_at, attempt_count
                ) values (?, 'PLAN_REEVALUATION', 'READY', ?, ?, ?, ?, ?, ?, '{}', ?, ?, 0)
                """,
                (
                    f"job_op079_{action}",
                    f"job-op079-{action}",
                    PROFILE_ID,
                    plan_id,
                    followup_id,
                    execution_id,
                    NOW.isoformat(),
                    f"job-hash-{index}",
                    NOW.isoformat(),
                ),
            )
    return store


def _run(database: Path, service_root: Path) -> dict[str, object]:
    store = _seed(database)
    headers = {"x-wb-rnd-token": "op079-op080-token"}
    cases: dict[str, object] = {}
    with _api_environment(database):
        client = TestClient(app)
        for action in ACTIONS:
            plan_id = f"plan_op079_{action}"
            execution_id = f"execution_op079_{action}"
            payload = {
                "execution_id": execution_id,
                "profile_id": PROFILE_ID,
                "plan_id": plan_id,
                "expected_state": "ACTIVE",
                "action": action,
                "reason_code": f"OP079_{action.upper()}",
                "idempotency_key": f"op079-{action}",
                "occurred_at": NOW.isoformat(),
            }
            if action == "replace":
                payload["replacement_plan_id"] = "plan_op079_replacement_active"
            response = client.post(
                "/v1/interim/plan-lifecycle/transitions",
                headers=headers,
                json=payload,
            )
            if response.status_code != 200:
                raise RuntimeError(f"lifecycle_{action}_failed:{response.text}")
            result = response.json()
            retry = client.post(
                "/v1/interim/plan-lifecycle/transitions",
                headers=headers,
                json=payload,
            )
            if retry.status_code != 200:
                raise RuntimeError(f"lifecycle_{action}_retry_failed:{retry.text}")
            cases[action] = {
                "event_id": result["event_id"],
                "state_before": result["state_before"],
                "state_after": result["state_after"],
                "replacement_plan_id": result["replacement_plan_id"],
                "replacement_state": result["replacement_state"],
                "exact_retry_same_event": retry.json()["event_id"] == result["event_id"],
                "exact_retry_deduplicated": retry.json()["deduplicated"],
                "followup_status": store.scalar(
                    "select status from followups where execution_id=?", (execution_id,)
                ),
                "job_status": store.scalar(
                    "select status from workflow_jobs where execution_id=?", (execution_id,)
                ),
                "order_state_effect": result["order_state_effect"],
                "order_state_mutation_allowed": result["order_state_mutation_allowed"],
            }
        forbidden_payload = {
            "execution_id": "execution_op079_monitor",
            "profile_id": PROFILE_ID,
            "plan_id": "plan_op079_monitor",
            "expected_state": "MONITORING",
            "action": "maintain",
            "reason_code": "OP080_ORDER_FIELD_REJECTED",
            "idempotency_key": "op080-order-field",
            "occurred_at": NOW.isoformat(),
            "order_status": "PAID",
        }
        forbidden = client.post(
            "/v1/interim/plan-lifecycle/transitions",
            headers=headers,
            json=forbidden_payload,
        )
    with store.transaction() as connection:
        replacement_active = WorkflowJobQueue._execution_plan_is_active(
            connection,
            execution_id="execution_op079_replace",
            profile_id=PROFILE_ID,
            plan_id="plan_op079_replacement_active",
        )
        replaced_inactive = not WorkflowJobQueue._execution_plan_is_active(
            connection,
            execution_id="execution_op079_replace",
            profile_id=PROFILE_ID,
            plan_id="plan_op079_replace",
        )
    lifecycle_source = (ROOT / "src/wellnessbox_rnd/interim/plan_lifecycle.py").read_text(
        encoding="utf-8"
    )
    route_source = (ROOT / "apps/inference_api/routes/interim.py").read_text(
        encoding="utf-8"
    )
    service_mutations = (service_root / "lib/order/mutations.ts").read_text(
        encoding="utf-8"
    )
    forbidden_symbols = ("updateOrderStatus", "prisma.order", "writeClientCartItems")
    return {
        "schema_version": "op079_op080_plan_lifecycle_order_boundary_smoke_v1",
        "case_count": len(cases),
        "cases": cases,
        "checks": {
            "all_required_actions_executed_through_fastapi": set(cases) == set(ACTIONS),
            "all_transitions_stored_in_execution_events": store.scalar(
                "select count(*) from execution_events "
                "where event_type='followup_evaluation'"
            )
            == len(ACTIONS),
            "nonterminal_work_preserved": all(
                cases[action]["followup_status"] == "OPEN"
                and cases[action]["job_status"] == "READY"
                for action in ("maintain", "adjust", "monitor")
            ),
            "terminal_work_closed": all(
                cases[action]["followup_status"] == "CLOSED"
                and cases[action]["job_status"] == "CANCELLED"
                for action in ("replace", "stop")
            ),
            "replacement_plan_activated": replacement_active,
            "replaced_plan_deactivated": replaced_inactive,
            "order_field_http_status": forbidden.status_code,
            "order_field_rejected_before_event_write": forbidden.status_code == 422
            and store.scalar(
                "select count(*) from execution_events where idempotency_key=?",
                ("op080-order-field",),
            )
            == 0,
            "rnd_lifecycle_has_no_service_order_mutation_symbols": not any(
                symbol in lifecycle_source or symbol in route_source
                for symbol in forbidden_symbols
            ),
            "service_retains_separate_order_status_mutator": "updateOrderStatus"
            in service_mutations,
            "actual_order_mutation_executed": False,
            "production_operation_proven": False,
        },
        "requirement_stages": {"OP-079": "IMPLEMENTED", "OP-080": "IMPLEMENTED"},
        "source_identity": {
            "wellnessbox_rnd_commit": _last_commit(ROOT, RND_SOURCE_PATHS),
            "wellnessbox_rnd_sha256": _hash_paths(ROOT, RND_SOURCE_PATHS),
            "wellnessbox_commit": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=service_root,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout.strip(),
            "wellnessbox_sha256": _hash_paths(service_root, SERVICE_SOURCE_PATHS),
            "wellnessbox_paths": list(SERVICE_SOURCE_PATHS),
            "wellnessbox_rnd_paths": list(RND_SOURCE_PATHS),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    service_root = Path(
        os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", str(ROOT.parent / "wellnessbox"))
    ).resolve()
    with TemporaryDirectory() as temporary:
        report = _run(Path(temporary) / "op079-op080.sqlite3", service_root)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
