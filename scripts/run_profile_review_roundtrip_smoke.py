from __future__ import annotations

import atexit
import hashlib
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

from wellnessbox_rnd.interim.reviews import PharmacistReviewService
from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]
SERVICE = Path(os.environ.get("WELLNESSBOX_SERVICE_REPO", "C:/dev/wellnessbox"))
DATASET = ROOT / "data/original_plan/op105_op106_profile_review_roundtrip_cases_v1.json"
OUTPUT = ROOT / "data/original_plan/evidence/op105_op106_profile_review_roundtrip_smoke_v1.json"
SERVICE_PATHS = (
    "scripts/qa/check-rnd-profile-review-roundtrip.cts",
    "lib/server/wb-rnd-interim-client.ts",
    "lib/server/wb-rnd-interim-route.ts",
    "components/tips/InterimRoleConsole.tsx",
)


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, encoding="utf-8").strip()


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_ready(base_url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"rnd_process_exited:{process.returncode}")
        try:
            with request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise AssertionError("rnd_process_not_ready")


def main() -> int:
    dataset_bytes = subprocess.check_output(
        ["git", "show", f"HEAD:{DATASET.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )
    dataset = json.loads(dataset_bytes)
    token = "Canonical-Profile-Review-Token-2026-Alpha"
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary) / "interim.sqlite3"
        store = InterimStore(database)
        store.migrate()
        with store.transaction(immediate=True) as connection:
            PharmacistReviewService.create_in_transaction(
                connection,
                profile_id="usr_105106abcdef0123456789abcdef",
                reason_codes=["CANONICAL_PROFILE_REVIEW"],
                created_at=datetime.now(UTC),
                data_class="PROXY_GOLD_SIMULATION",
                simulation_badge=True,
                urgency="ROUTINE",
            )
        port = free_port()
        base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy() | {
            "WB_RND_HOST": "127.0.0.1",
            "WB_RND_PORT": str(port),
            "WB_RND_WORKERS": "1",
            "WB_RND_INTERIM_ENABLED": "1",
            "WB_RND_INTERIM_DATABASE": str(database),
            "WB_RND_INTERIM_INTERNAL_TOKEN": token,
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
            node_env = environment | {
                "WB_RND_INTERIM_BASE_URL": base_url,
                "WB_RND_INTERIM_TOKEN": token,
                "WB_RND_INTERIM_TIMEOUT_MS": "5000",
            }
            completed = subprocess.run(
                [
                    "node",
                    "--conditions=react-server",
                    "--import",
                    "tsx",
                    "scripts/qa/check-rnd-profile-review-roundtrip.cts",
                ],
                cwd=SERVICE,
                env=node_env,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            )
            observed = json.loads(completed.stdout.strip().splitlines()[-1])
        finally:
            process.terminate()
            process.wait(timeout=10)
    service_blobs = "\n".join(git("show", f"HEAD:{path}", cwd=SERVICE) for path in SERVICE_PATHS)
    checks = {
        "profile_roundtrip_completed": observed["profileId"] == "usr_105106abcdef0123456789abcdef",
        "recommendation_roundtrip_completed": str(observed["recommendationRunId"]).startswith(
            "run_"
        ),
        "review_queue_roundtrip_completed": str(observed["reviewId"]).startswith("review_"),
        "review_decision_completed": observed["reviewStatus"] == "COMPLETED",
        "review_replay_rejected": observed["immutableReplayRejected"] is True,
        "service_auth_routes_committed": "requireUserSession" in service_blobs
        and "requirePharmSession" in service_blobs,
        "pharmacist_screen_uses_service_api": '"/api/pharm/tips/reviews"' in service_blobs,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    report = {
        "schema_version": "op105_op106_profile_review_roundtrip_smoke_v1",
        "requirements": {
            "OP-105": {"required_stage": "OPERATED", "claimed_stage": "INTEGRATED"},
            "OP-106": {"required_stage": "OPERATED", "claimed_stage": "INTEGRATED"},
        },
        "dataset": {
            "path": DATASET.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "case_count": len(dataset["cases"]),
        },
        "checks": checks,
        "observed": observed,
        "source_identity": {"wellnessbox_commit": git("rev-parse", "HEAD", cwd=SERVICE)},
        "stage_boundary": {
            "local_two_process_roundtrip_proven": True,
            "public_deployment_proven": False,
            "production_pharmacist_operation_proven": False,
        },
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
