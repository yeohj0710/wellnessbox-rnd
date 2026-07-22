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
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / (
    "data/original_plan/op101_op102_deployment_contract_endpoint_cases_v1.json"
)
OUTPUT_PATH = ROOT / (
    "data/original_plan/evidence/op101_op102_deployment_contract_endpoint_smoke_v1.json"
)
SOURCE_PATHS = (
    ROOT / "scripts/run_deployment_contract_endpoint_smoke.py",
    DATASET_PATH,
    ROOT / "apps/inference_api/main.py",
    ROOT / "apps/inference_api/routes/health.py",
    ROOT / "apps/inference_api/routes/interim.py",
    ROOT / "apps/inference_api/routes/recommend.py",
    ROOT / "src/wellnessbox_rnd/deployment.py",
    ROOT / "src/wellnessbox_rnd/interim/store.py",
    ROOT / "Dockerfile",
)


def _git_blob_bytes(path: Path) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"HEAD:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )


def _git_blob_sha256(path: Path) -> str:
    return hashlib.sha256(_git_blob_bytes(path)).hexdigest()


def _source_commit() -> str:
    paths = [path.relative_to(ROOT).as_posix() for path in SOURCE_PATHS]
    return subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", *paths], cwd=ROOT, text=True
    ).strip()


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _http_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode()
    if token is not None:
        headers["x-wb-rnd-token"] = token
    call = request.Request(
        f"{base_url}{path}", method=method, headers=headers, data=body
    )
    try:
        with request.urlopen(call, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except error.HTTPError as response:
        return response.code, json.loads(response.read().decode())


def _start(environment: dict[str, str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "scripts/start_inference_api.py"],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _wait_ready(base_url: str, process: subprocess.Popen[bytes]) -> dict[str, Any]:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"deployment_process_exited:{process.returncode}")
        try:
            status, body = _http_json(base_url, "/health")
            if status == 200:
                return body
        except OSError:
            pass
        time.sleep(0.1)
    raise AssertionError("deployment_process_not_ready")


def _stop(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def _device_payload(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "profile_id": "usr_0123456789abcdef",
        "source": "W",
        "consent_scopes": ["device:write"],
        "payload": {
            "observed_at": "2026-07-22T10:00:00+09:00",
            "value": 7000,
            "unit": "steps",
            "timezone": "Asia/Seoul",
            "source_record_id": "deployment-watch-1",
        },
        "environment": "production",
    }


def main() -> int:
    dataset = json.loads(_git_blob_bytes(DATASET_PATH).decode("utf-8"))
    token = "Canonical-Deployment-Secret-2026-07-22-Alpha9"
    image_commit_path = ROOT / ".wellnessbox-rnd-image-commit"
    if image_commit_path.exists():
        raise AssertionError("local_image_commit_file_already_exists")
    image_commit_path.write_text(_source_commit(), encoding="ascii")
    atexit.register(image_commit_path.unlink, missing_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary).resolve() / "persistent" / "interim.sqlite3"
        database.parent.mkdir()
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy() | {
            "WB_RND_APP_ENV": "staging",
            "WB_RND_HOST": "127.0.0.1",
            "WB_RND_PORT": str(port),
            "WB_RND_WORKERS": "1",
            "WB_RND_INTERIM_ENABLED": "1",
            "WB_RND_INTERIM_DATABASE": str(database),
            "WB_RND_INTERIM_INTERNAL_TOKEN": token,
            "WB_RND_DEPLOYMENT_CONTRACT_ENFORCED": "1",
            "WB_RND_DEPLOYMENT_TARGET": "canonical-local-provider-boundary",
            "WB_RND_DEPLOYMENT_ID": "op101-op102-process-a",
            "WB_RND_CODE_COMMIT": _source_commit(),
            "WB_RND_DATABASE_DURABILITY": "provider_persistent_volume",
            "WB_RND_INTERNAL_AUTH_SCHEME": "shared_header_hmac_sha256_v1",
            "WB_RND_INTERNAL_TOKEN_SECRET_REF": "provider://canonical/wb-rnd-token",
        }
        process = _start(environment)
        try:
            health = _wait_ready(base_url, process)
            unauthorized_status, _ = _http_json(base_url, "/v1/interim/status")
            profile_status, _ = _http_json(
                base_url,
                "/v1/interim/profiles",
                method="POST",
                token=token,
                payload={
                    "profile_id": "usr_0123456789abcdef",
                    "consent_scopes": ["device:write"],
                    "profile": {"age": 41},
                },
            )
            device_status, device = _http_json(
                base_url,
                "/v1/interim/connectors/device",
                method="POST",
                token=token,
                payload=_device_payload("deployment-device-1"),
            )
            recommend_status, recommendation = _http_json(
                base_url,
                "/v1/recommend",
                method="POST",
                payload=json.loads(
                    (ROOT / "data/samples/api_recommend_start_plan_request_v1.json").read_text(
                        encoding="utf-8"
                    )
                ),
            )
        finally:
            _stop(process)
        environment["WB_RND_DEPLOYMENT_ID"] = "op101-op102-process-b"
        restarted = _start(environment)
        try:
            restarted_health = _wait_ready(base_url, restarted)
            replay_status, replay = _http_json(
                base_url,
                "/v1/interim/connectors/device",
                method="POST",
                token=token,
                payload=_device_payload("deployment-device-retry"),
            )
            status_code, status_body = _http_json(
                base_url, "/v1/interim/status", token=token
            )
            family_probe_statuses = {}
            for family, path in {
                "state_machine": "/v1/interim/plan-lifecycle/transitions",
                "counseling": "/v1/interim/counseling/turns",
            }.items():
                family_probe_statuses[family] = _http_json(
                    base_url, path, method="POST", token=token, payload={}
                )[0]
        finally:
            _stop(restarted)
        observed = {
            "deployment_contract_status": health["deployment_contract"]["status"],
            "endpoint_family_count": len(health["endpoint_inventory"]["families"]),
            "endpoint_inventory_sha256": health["endpoint_inventory"]["inventory_sha256"],
            "unauthorized_status": unauthorized_status,
            "profile_status": profile_status,
            "device_status": device_status,
            "recommend_status": recommend_status,
            "recommend_mode": recommendation["metadata"]["mode"],
            "restart_contract_status": restarted_health["deployment_contract"]["status"],
            "replay_status": replay_status,
            "replay_deduplicated": replay["deduplicated"],
            "replay_session_id": replay["session_id"],
            "persisted_connector_rows": status_body["counts"]["connector_sessions"],
            "status_api_status": status_code,
            "authorized_family_probe_statuses": family_probe_statuses,
        }
        checks = {
            "enforced_contract_ready_on_both_processes": observed[
                "deployment_contract_status"
            ]
            == observed["restart_contract_status"]
            == "READY_FOR_PROVIDER_DEPLOYMENT",
            "five_required_endpoint_families_mounted": observed["endpoint_family_count"]
            == 5,
            "internal_api_rejects_missing_token": unauthorized_status == 401,
            "health_recommendation_device_http_reachable": (
                device_status == profile_status == recommend_status == 200
            ),
            "state_machine_and_counseling_routes_reachable": family_probe_statuses
            == {"state_machine": 422, "counseling": 422},
            "persistent_database_survives_restart": observed["persisted_connector_rows"]
            == 1,
            "restart_replay_uses_canonical_event": replay_status == 200
            and replay["deduplicated"] is True
            and replay["session_id"] == "deployment-device-1",
            "deterministic_recommendation_preserved": observed["recommend_mode"]
            == "deterministic_baseline_v1",
        }
        if not all(checks.values()):
            raise AssertionError(f"deployment_contract_endpoint_smoke_failed:{checks}")
        report = {
            "schema_version": "op101_op102_deployment_contract_endpoint_smoke_v1",
            "requirements": {
                "OP-101": {"required_stage": "OPERATED", "claimed_stage": "INTEGRATED"},
                "OP-102": {"required_stage": "OPERATED", "claimed_stage": "INTEGRATED"},
            },
            "dataset": {
                "path": DATASET_PATH.relative_to(ROOT).as_posix(),
                "sha256": _git_blob_sha256(DATASET_PATH),
                "case_count": len(dataset["cases"]),
            },
            "checks": checks,
            "observed": observed,
            "stage_boundary": {
                "two_local_processes_and_restart_persistence_proven": True,
                "provider_deployment_proven": False,
                "production_traffic_proven": False,
            },
            "source_identity": {
                "wellnessbox_rnd_commit": _source_commit(),
                "wellnessbox_rnd_source_sha256": hashlib.sha256(
                    "".join(_git_blob_sha256(path) for path in SOURCE_PATHS).encode()
                ).hexdigest(),
            },
        }
        OUTPUT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
