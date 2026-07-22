from __future__ import annotations

import atexit
import hashlib
import hmac
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib import request

from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]
SERVICE = Path(os.environ.get("WELLNESSBOX_SERVICE_REPO", "C:/dev/wellnessbox"))
DATASET = ROOT / "data/original_plan/op109_op110_order_plan_context_cases_v1.json"
OUTPUT = ROOT / "data/original_plan/evidence/op109_op110_order_plan_context_smoke_v1.json"


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, encoding="utf-8").strip()


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_ready(base_url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("rnd_process_exited")
        try:
            with request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise AssertionError("rnd_process_not_ready")


def seed(database: Path, profile_id: str) -> None:
    store = InterimStore(database)
    store.migrate()
    now = datetime(2026, 7, 22, tzinfo=UTC).isoformat()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values (?, 'PROXY_GOLD_SIMULATION', '[]', '{}', 'p', ?)",
            (profile_id, now),
        )
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_op109', ?, 1, 'v1', '{}', 'c', ?)",
            (profile_id, now),
        )
        connection.execute(
            "insert into active_profile_consents values (?, 'consent_op109', ?)",
            (profile_id, now),
        )
        connection.execute(
            "insert into executions values "
            "('execution_op109', 'request_op109', ?, null, 'consent_op109', "
            "'request-hash-op109', 'COMPLETE', ?, ?)",
            (profile_id, now, now),
        )
        payload = json.dumps({"plan_id": "plan_op109"}, sort_keys=True)
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (
              'event_op109_plan', 'execution_op109', 'consent_op109', 0,
              'recommendation', 'system', 'seed-op109', ?, 'plan-hash-op109',
              'plan-hash-op109', ?
            )
            """,
            (payload, now),
        )


def main() -> int:
    dataset_bytes = subprocess.check_output(
        ["git", "show", f"HEAD:{DATASET.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )
    dataset = json.loads(dataset_bytes)
    token = "Canonical-Order-Plan-Token-2026-Alpha"
    salt = "canonical-order-plan-pseudonym-salt-2026"
    profile_id = "usr_" + hmac.new(salt.encode(), b"op109-user", hashlib.sha256).hexdigest()[:32]
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary) / "interim.sqlite3"
        seed(database, profile_id)
        api_port = available_port()
        base_url = f"http://127.0.0.1:{api_port}"
        environment = os.environ.copy() | {
            "WB_RND_HOST": "127.0.0.1",
            "WB_RND_PORT": str(api_port),
            "WB_RND_WORKERS": "1",
            "WB_RND_INTERIM_ENABLED": "1",
            "WB_RND_INTERIM_DATABASE": str(database),
            "WB_RND_INTERIM_INTERNAL_TOKEN": token,
            "WB_RND_INTERIM_BASE_URL": base_url,
            "WB_RND_INTERIM_TOKEN": token,
            "WB_RND_INTERIM_TIMEOUT_MS": "5000",
            "WB_RND_INTERIM_PSEUDONYM_SALT": salt,
        }
        process = subprocess.Popen(
            [sys.executable, "scripts/start_inference_api.py"],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        atexit.register(process.kill)
        try:
            wait_ready(base_url, process)
            completed = subprocess.run(
                [
                    "node",
                    "--conditions=react-server",
                    "--import",
                    "tsx",
                    "scripts/qa/check-rnd-order-plan-context.cts",
                ],
                cwd=SERVICE,
                env=environment,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise AssertionError(f"service_qa_failed:{completed.stderr}")
            observed = json.loads(completed.stdout.strip())
        finally:
            process.terminate()
            process.wait(timeout=10)

    checks = {
        "user_auth_denied": observed["userAuthDenied"] is True,
        "six_order_statuses_mapped": len(observed["orderStatuses"]) == 6,
        "recommendation_route_order_mutation_free": (
            observed["recommendationRouteOrderMutationSymbols"] is False
        ),
        "existing_create_order_owns_mutations": (
            observed["existingCreateOrderOwnsStockAndOrderMutation"] is True
        ),
        "order_context_read_only": all(
            item["plan_state"] == "ACTIVE" for item in observed["orderStatuses"]
        ),
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    report = {
        "schema_version": "op109_op110_order_plan_context_smoke_v1",
        "requirements": {
            "OP-109": {"required_stage": "OPERATED", "claimed_stage": "IMPLEMENTED"},
            "OP-110": {"required_stage": "OPERATED", "claimed_stage": "IMPLEMENTED"},
        },
        "dataset": {
            "path": DATASET.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "case_count": len(dataset["cases"]),
        },
        "checks": checks,
        "observed": observed,
        "source_identity": {
            "wellnessbox_commit": git("rev-parse", "HEAD", cwd=SERVICE),
            "wellnessbox_rnd_source_commit": git(
                "log",
                "-1",
                "--format=%H",
                "--",
                "scripts/run_order_plan_context_integration_smoke.py",
            ),
            "wellnessbox_rnd_source_blobs": {
                path: git("rev-parse", f"HEAD:{path}")
                for path in (
                    "apps/inference_api/routes/interim.py",
                    "data/original_plan/op109_op110_order_plan_context_cases_v1.json",
                    "scripts/run_order_plan_context_integration_smoke.py",
                    "src/wellnessbox_rnd/interim/plan_lifecycle.py",
                )
            },
        },
        "stage_boundary": {
            "actual_rnd_http_roundtrip_proven": True,
            "actual_prisma_order_or_stock_mutation_proven": False,
            "actual_prisma_order_status_query_proven": False,
            "production_operation_proven": False,
        },
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
