from __future__ import annotations

import argparse
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wellnessbox_rnd.governance.operational_receipts import begin_session, finish_session

ROOT = Path(__file__).resolve().parents[1]
WELLNESSBOX_ROOT = ROOT.parent / "wellnessbox"
RUNTIME_ROOT = ROOT / "etc/local_research_runtime"
DATABASE_PATH = RUNTIME_ROOT / "interim.sqlite3"
STATE_PATH = RUNTIME_ROOT / "session_processes.json"
STOP_PATH = RUNTIME_ROOT / "stop.request"
SECRET_PATH = RUNTIME_ROOT / "local_secrets.json"
CAPTURE_PATH = RUNTIME_ROOT / "operational_capture.json"
OPERATIONAL_RECEIPTS = ROOT / "data/original_plan/final_session/operational_receipts"
SIGNING_KEY = ROOT / "etc/final_session_private/final_session_signing_key.pem"
EVIDENCE_PATH = (
    ROOT / "data/original_plan/evidence/local_on_demand_research_session_v1.json"
)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _free_port(preferred: int) -> int:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            probe.bind(("127.0.0.1", 0))
            return int(probe.getsockname()[1])


def _load_or_create_secrets() -> dict[str, str]:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    STOP_PATH.unlink(missing_ok=True)
    if SECRET_PATH.is_file():
        return json.loads(SECRET_PATH.read_text(encoding="utf-8"))
    value = {
        "token": secrets.token_urlsafe(48),
        "pseudonym_salt": secrets.token_urlsafe(48),
    }
    SECRET_PATH.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return value


def _request_json(
    url: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"accept": "application/json"}
    data = None
    if body is not None:
        headers["content-type"] = "application/json"
        data = json.dumps(body).encode()
    if token:
        headers["x-wb-rnd-token"] = token
    request = urllib.request.Request(url, headers=headers, data=data)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def _wait_ready(url: str, process: subprocess.Popen[bytes], seconds: int = 180) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"프로세스가 준비 전에 종료됐습니다: {url}")
        try:
            _request_json(url)
            return
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            time.sleep(0.5)
    raise RuntimeError(f"서버 준비 시간을 초과했습니다: {url}")


def _start(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
) -> tuple[subprocess.Popen[bytes], Any]:
    log_path = RUNTIME_ROOT / f"{name}.log"
    log = log_path.open("ab")
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    return process, log


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def _api_environment(port: int, secrets_value: dict[str, str]) -> dict[str, str]:
    return os.environ.copy() | {
        "PYTHONPATH": str(ROOT / "src"),
        "WB_RND_APP_ENV": "local",
        "WB_RND_HOST": "127.0.0.1",
        "WB_RND_PORT": str(port),
        "WB_RND_WORKERS": "1",
        "WB_RND_INTERIM_ENABLED": "1",
        "WB_RND_INTERIM_DATABASE": str(DATABASE_PATH.resolve()),
        "WB_RND_INTERIM_INTERNAL_TOKEN": secrets_value["token"],
    }


def _web_environment(port: int, api_url: str, secrets_value: dict[str, str]) -> dict[str, str]:
    return os.environ.copy() | {
        "PORT": str(port),
        "WB_RND_RECOMMEND_ENABLED": "1",
        "WB_RND_SERVICE_BASE_URL": api_url,
        "WB_RND_SERVICE_TOKEN": secrets_value["token"],
        "WB_RND_RECOMMEND_TIMEOUT_MS": "15000",
        "WB_RND_INTERIM_ENABLED": "1",
        "WB_RND_INTERIM_BASE_URL": api_url,
        "WB_RND_INTERIM_TOKEN": secrets_value["token"],
        "WB_RND_INTERIM_TIMEOUT_MS": "15000",
        "WB_RND_INTERIM_PSEUDONYM_SALT": secrets_value["pseudonym_salt"],
    }


def _write_state(processes: dict[str, subprocess.Popen[bytes]], urls: dict[str, str]) -> None:
    STATE_PATH.write_text(
        json.dumps(
            {
                "schema_version": "local_research_session_processes_v1",
                "started_at": _now(),
                "processes": {name: process.pid for name, process in processes.items()},
                "urls": urls,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _persistence_probe(api_url: str, token: str) -> str:
    profile_id = "usr_0123456789abcdef0123456789abcdef"
    response = _request_json(
        f"{api_url}/v1/interim/profiles",
        token=token,
        body={
            "profile_id": profile_id,
            "consent_scopes": ["local_research_session"],
            "profile": {"age": 40, "goals": ["sleep"]},
        },
    )
    if response != {"profile_id": profile_id, "stored": True}:
        raise AssertionError(response)
    return profile_id


def _database_contains(profile_id: str) -> bool:
    with sqlite3.connect(DATABASE_PATH) as connection:
        row = connection.execute(
            "select count(*) from user_profiles where profile_id=?", (profile_id,)
        ).fetchone()
    return bool(row and row[0] == 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="필요할 때만 로컬 연구 서버를 실행합니다.")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--api-only", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-once", action="store_true")
    args = parser.parse_args()
    if args.verify_once:
        args.verify = True
        args.no_browser = True
    if not WELLNESSBOX_ROOT.is_dir() and not args.api_only:
        raise SystemExit(f"웰니스박스 저장소가 없습니다: {WELLNESSBOX_ROOT}")

    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    secrets_value = _load_or_create_secrets()
    api_port = _free_port(8000)
    console_port = _free_port(8765)
    web_port = _free_port(3001)
    api_url = f"http://127.0.0.1:{api_port}"
    console_url = f"http://127.0.0.1:{console_port}"
    web_url = f"http://127.0.0.1:{web_port}"
    processes: dict[str, subprocess.Popen[bytes]] = {}
    logs: list[Any] = []
    try:
        api, log = _start(
            "rnd_api",
            [sys.executable, "scripts/start_inference_api.py"],
            cwd=ROOT,
            environment=_api_environment(api_port, secrets_value),
        )
        processes["rnd_api"] = api
        logs.append(log)
        _wait_ready(f"{api_url}/health", api)

        console, log = _start(
            "final_console",
            [
                sys.executable,
                "scripts/run_final_session_console.py",
                "--no-browser",
                "--port",
                str(console_port),
            ],
            cwd=ROOT,
            environment=os.environ.copy() | {"PYTHONPATH": str(ROOT / "src")},
        )
        processes["final_console"] = console
        logs.append(log)
        _wait_ready(f"{console_url}/api/state", console)

        if not args.api_only:
            npm = "npm.cmd" if os.name == "nt" else "npm"
            web, log = _start(
                "wellnessbox_web",
                [npm, "run", "dev", "--", "--port", str(web_port)],
                cwd=WELLNESSBOX_ROOT,
                environment=_web_environment(web_port, api_url, secrets_value),
            )
            processes["wellnessbox_web"] = web
            logs.append(log)
            _wait_ready(f"{web_url}/api/internal/rnd/health", web)

        urls = {"rnd_api": api_url, "final_console": console_url}
        if not args.api_only:
            urls["wellnessbox"] = web_url
        _write_state(processes, urls)
        capture = begin_session(ROOT, DATABASE_PATH, urls)
        CAPTURE_PATH.write_text(
            json.dumps(capture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("로컬 연구 서버가 준비됐습니다.")
        print(f"최종 확인 화면: {console_url}")
        if not args.api_only:
            print(f"웰니스박스: {web_url}")
        print("이 창에서 Ctrl+C를 누르면 모든 연구 서버가 종료됩니다.")

        profile_id = None
        if args.verify:
            profile_id = _persistence_probe(api_url, secrets_value["token"])
            if not _database_contains(profile_id):
                raise AssertionError("SQLite 저장 결과를 확인하지 못했습니다.")
            restart_status = "NOT_RUN"
            if args.verify_once:
                _stop(processes["rnd_api"])
                restarted_api, restarted_log = _start(
                    "rnd_api_restart",
                    [sys.executable, "scripts/start_inference_api.py"],
                    cwd=ROOT,
                    environment=_api_environment(api_port, secrets_value),
                )
                processes["rnd_api"] = restarted_api
                logs.append(restarted_log)
                _wait_ready(f"{api_url}/health", restarted_api)
                if not _database_contains(profile_id):
                    raise AssertionError("API 재시작 후 SQLite 데이터가 사라졌습니다.")
                restart_status = "PASS"
            EVIDENCE_PATH.write_text(
                json.dumps(
                    {
                        "schema_version": "local_on_demand_research_session_v1",
                        "status": "PASS",
                        "recorded_at": _now(),
                        "checks": {
                            "rnd_api_health": "PASS",
                            "final_console": "PASS",
                            "wellnessbox_roundtrip": (
                                "NOT_RUN" if args.api_only else "PASS"
                            ),
                            "sqlite_write": "PASS",
                            "sqlite_restart_persistence": restart_status,
                        },
                        "runtime": {
                            "mode": "local_on_demand",
                            "always_on": False,
                            "additional_cloud_cost": 0,
                            "database": "etc/local_research_runtime/interim.sqlite3",
                        },
                        "stage_boundary": {
                            "local_integration_proven": True,
                            "production_deployment_proven": False,
                            "operated_claim_allowed": False,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            print(f"로컬 검증 증거: {EVIDENCE_PATH}")
            if args.verify_once:
                return 0

        if not args.no_browser:
            webbrowser.open(console_url)
            if not args.api_only:
                webbrowser.open(web_url)
        while True:
            time.sleep(1)
            if STOP_PATH.exists():
                print("종료 요청을 받아 모든 연구 서버를 종료합니다.")
                break
            failed = [name for name, process in processes.items() if process.poll() is not None]
            if failed:
                raise RuntimeError("서버가 예기치 않게 종료됐습니다: " + ", ".join(failed))
    except KeyboardInterrupt:
        print("\n로컬 연구 서버를 종료합니다.")
    finally:
        for process in reversed(list(processes.values())):
            _stop(process)
        for log in logs:
            log.close()
        if CAPTURE_PATH.is_file():
            capture = json.loads(CAPTURE_PATH.read_text(encoding="utf-8"))
            receipt = finish_session(
                ROOT,
                DATABASE_PATH,
                capture,
                OPERATIONAL_RECEIPTS,
                key_path=SIGNING_KEY,
            )
            print(f"운영 영수증: {receipt['receipt_path']}")
            CAPTURE_PATH.unlink(missing_ok=True)
        STATE_PATH.unlink(missing_ok=True)
        STOP_PATH.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
