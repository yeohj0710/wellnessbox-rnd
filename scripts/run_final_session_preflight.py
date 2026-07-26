from __future__ import annotations

import hashlib
import http.cookiejar
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT.parent / "wellnessbox"
PORTS = (8000, 8765, 3001)
FINAL_CONSOLE_READ_ONLY_BOOTSTRAP = (
    "import os;from pathlib import Path;"
    "import scripts.run_final_session_console as module;"
    "module.FinalSessionConsole._reconcile_draft_queue_state=lambda self:None;"
    "module.FinalSessionConsole._operational_database_path=lambda self:"
    "Path(os.environ['WB_RND_PREFLIGHT_DATABASE']);"
    "module.FinalSessionConsole.operational_coverage_summary=lambda self:{"
    "'required_count':len(self._stage_gap_ids()),'covered_count':0,"
    "'covered_requirement_ids':[],'missing_requirement_ids':self._stage_gap_ids(),"
    "'valid_receipt_count':0,'cumulative_session_count':0,'distinct_profile_count':0,"
    "'target_distinct_profile_count':5,'current_session_provisional_count':0,"
    "'current_session_provisional_ids':[],'evidence':{}};"
    "raise SystemExit(module.main())"
)

Probe = Callable[[Path, Path, Path, Path, Path], dict[str, Any]]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_storage(root: Path) -> dict[str, Any]:
    database = root / "etc/local_research_runtime/interim.sqlite3"
    if not database.is_file():
        raise FileNotFoundError(f"운영 DB가 없습니다: {database}")
    receipts = root / "data/original_plan/final_session/operational_receipts"
    receipt_hashes = {
        path.name: _sha256(path)
        for path in sorted(receipts.glob("*.json"))
        if path.is_file()
    }
    return {
        "database": {
            "path": str(database.resolve()),
            "sha256": _sha256(database),
            "size": database.stat().st_size,
        },
        "receipts": receipt_hashes,
    }


def _technical_blockers(checks: dict[str, Any]) -> list[dict[str, str]]:
    if "probe_error" in checks:
        return [{"id": "PREFLIGHT_PROBE_FAILED", "message": checks["probe_error"]}]

    expected_statuses = {
        "rnd_health": 200,
        "console_home": 200,
        "console_state": 200,
        "wellnessbox_health": 200,
    }
    failures = [
        f"{name}={checks.get(name)!r}"
        for name, expected in expected_statuses.items()
        if checks.get(name) != expected
    ]
    for name, expected_url in (
        ("tips", "http://127.0.0.1:3001/tips"),
        ("pharmacist", "http://127.0.0.1:3001/pharm/tips"),
    ):
        value = checks.get(name, {})
        if (
            value.get("login_status") != 307
            or value.get("page_status") != 200
            or value.get("final_url") != expected_url
        ):
            failures.append(f"{name}={value!r}")
    if checks.get("h005", {}).get("status") != 200:
        failures.append(f"h005={checks.get('h005')!r}")
    if not failures:
        return []
    return [
        {
            "id": "SERVER_OR_UI_CHECK_FAILED",
            "message": "서버 또는 UI GET 점검이 실패했습니다: " + ", ".join(failures),
        }
    ]


def classify_result(
    checks: dict[str, Any],
    *,
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    database_unchanged = before["database"] == after["database"]
    before_receipts = before["receipts"]
    after_receipts = after["receipts"]
    receipt_file_list_unchanged = list(before_receipts) == list(after_receipts)
    receipt_hashes_unchanged = before_receipts == after_receipts
    storage = {
        "database_unchanged": database_unchanged,
        "receipt_file_list_unchanged": receipt_file_list_unchanged,
        "receipt_hashes_unchanged": receipt_hashes_unchanged,
    }

    blockers = _technical_blockers(checks)
    error_ids = {item["id"] for item in blockers}
    if not database_unchanged:
        blocker = {
            "id": "OPERATIONAL_DATABASE_CHANGED",
            "message": "사전 점검 중 운영 DB의 hash 또는 크기가 바뀌었습니다.",
        }
        blockers.append(blocker)
        error_ids.add(blocker["id"])
    if not receipt_file_list_unchanged or not receipt_hashes_unchanged:
        blocker = {
            "id": "OPERATIONAL_RECEIPTS_CHANGED",
            "message": "사전 점검 중 운영 영수증 파일 목록 또는 hash가 바뀌었습니다.",
        }
        blockers.append(blocker)
        error_ids.add(blocker["id"])

    h005 = checks.get("h005", {})
    case_count = int(h005.get("case_count", 0))
    preselected = int(h005.get("preselected_count", 0))
    comment_count = int(h005.get("comment_count", 0))
    prefilled = int(h005.get("prefilled_comment_count", 0))
    if case_count != 10 or comment_count != 10:
        blockers.append(
            {
                "id": "H005_CASE_COUNT_MISMATCH",
                "message": (
                    f"H-005 화면의 사례/의견란 수가 10/10이 아닙니다: "
                    f"cases={case_count}, comments={comment_count}."
                ),
            }
        )
    elif preselected or prefilled:
        blockers.append(
            {
                "id": "H005_FORM_NOT_NEUTRAL",
                "message": (
                    f"H-005 {preselected}/{case_count} cases are preselected and "
                    f"{prefilled}/{comment_count} comments are prefilled."
                ),
            }
        )

    if error_ids:
        status, exit_code = "ERROR", 1
    elif blockers:
        status, exit_code = "BLOCKED", 2
    else:
        status, exit_code = "READY", 0
    before_manifest = hashlib.sha256(
        json.dumps(before_receipts, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    after_manifest = hashlib.sha256(
        json.dumps(after_receipts, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema_version": "final_session_preflight_v1",
        "status": status,
        "exit_code": exit_code,
        "operational_receipt_generation": False,
        "human_actions_performed": False,
        "temporary_database": True,
        "temporary_final_state": True,
        "checks": checks,
        "storage": storage,
        "storage_evidence": {
            "database_before": before["database"],
            "database_after": after["database"],
            "receipt_file_count_before": len(before_receipts),
            "receipt_file_count_after": len(after_receipts),
            "receipt_manifest_sha256_before": before_manifest,
            "receipt_manifest_sha256_after": after_manifest,
        },
        "blockers": blockers,
    }


def _assert_port_available(port: int) -> None:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(f"사전 점검 포트가 이미 사용 중입니다: {port}") from exc


def _start_process(
    name: str,
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    temporary_root: Path,
) -> tuple[subprocess.Popen[bytes], Any, Path]:
    log_path = temporary_root / f"{name}.log"
    log = log_path.open("wb")
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    return process, log, log_path


def _log_tail(log: Any, path: Path) -> str:
    log.flush()
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return " | ".join(lines[-8:])


def _stop_owned_process(process: subprocess.Popen[bytes]) -> None:
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


def _get(
    url: str,
    *,
    opener: Any | None = None,
    timeout: float = 15.0,
) -> tuple[int, str, str]:
    active_opener = opener or urllib.request.build_opener()
    with active_opener.open(url, timeout=timeout) as response:
        return (
            int(response.status),
            str(response.geturl()),
            response.read().decode("utf-8", errors="replace"),
        )


def _wait_ready(
    url: str,
    process: subprocess.Popen[bytes],
    log: Any,
    log_path: Path,
    *,
    seconds: float = 120.0,
) -> tuple[int, str, str]:
    deadline = time.monotonic() + seconds
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"서버가 준비 전에 종료됐습니다: {url}; exit={process.returncode}; "
                f"log={_log_tail(log, log_path)}"
            )
        try:
            return _get(url, timeout=5.0)
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
            time.sleep(0.5)
    raise RuntimeError(
        f"서버 준비 시간을 초과했습니다: {url}; error={last_error}; "
        f"log={_log_tail(log, log_path)}"
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Any,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


def _redirect_status(url: str) -> int:
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        return _get(url, opener=opener)[0]
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _logged_in_page(url: str) -> tuple[int, str, str]:
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    return _get(url, opener=opener, timeout=20.0)


def probe_servers(
    root: Path,
    web_root: Path,
    temporary_database: Path,
    temporary_state_root: Path,
    temporary_root: Path,
) -> dict[str, Any]:
    for port in PORTS:
        _assert_port_available(port)
    if not web_root.is_dir():
        raise FileNotFoundError(f"WellnessBox 저장소가 없습니다: {web_root}")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if npm is None:
        raise FileNotFoundError("npm 실행 파일을 찾지 못했습니다.")

    temporary_state_root.mkdir(parents=True)
    token = secrets.token_urlsafe(48)
    processes: list[tuple[subprocess.Popen[bytes], Any, Path]] = []
    checks: dict[str, Any] = {}
    try:
        api_environment = os.environ.copy() | {
            "PYTHONPATH": str(root / "src"),
            "WB_RND_APP_ENV": "local",
            "WB_RND_HOST": "127.0.0.1",
            "WB_RND_PORT": "8000",
            "WB_RND_WORKERS": "1",
            "WB_RND_INTERIM_ENABLED": "1",
            "WB_RND_INTERIM_DATABASE": str(temporary_database),
            "WB_RND_INTERIM_INTERNAL_TOKEN": token,
        }
        api = _start_process(
            "rnd_api",
            [sys.executable, "scripts/start_inference_api.py"],
            cwd=root,
            environment=api_environment,
            temporary_root=temporary_root,
        )
        processes.append(api)
        checks["rnd_health"] = _wait_ready(
            "http://127.0.0.1:8000/health", *api
        )[0]

        console = _start_process(
            "final_console",
            [
                sys.executable,
                "-c",
                FINAL_CONSOLE_READ_ONLY_BOOTSTRAP,
                "--no-browser",
                "--port",
                "8765",
                "--state-root",
                str(temporary_state_root),
            ],
            cwd=root,
            environment=os.environ.copy()
            | {
                "PYTHONPATH": str(root / "src"),
                "WB_RND_PREFLIGHT_DATABASE": str(temporary_database),
            },
            temporary_root=temporary_root,
        )
        processes.append(console)
        checks["console_home"] = _wait_ready(
            "http://127.0.0.1:8765/", *console
        )[0]
        checks["console_state"] = _get("http://127.0.0.1:8765/api/state")[0]

        web_environment = os.environ.copy() | {
            "PORT": "3001",
            "COOKIE_PASSWORD": secrets.token_urlsafe(48),
            "JWT_SECRET": secrets.token_urlsafe(48),
            "WB_RND_RECOMMEND_ENABLED": "1",
            "WB_RND_SERVICE_BASE_URL": "http://127.0.0.1:8000",
            "WB_RND_SERVICE_TOKEN": token,
            "WB_RND_RECOMMEND_TIMEOUT_MS": "15000",
            "WB_RND_INTERIM_ENABLED": "1",
            "WB_RND_INTERIM_BASE_URL": "http://127.0.0.1:8000",
            "WB_RND_INTERIM_TOKEN": token,
            "WB_RND_INTERIM_TIMEOUT_MS": "15000",
            "WB_RND_INTERIM_PSEUDONYM_SALT": secrets.token_urlsafe(48),
        }
        web = _start_process(
            "wellnessbox_web",
            [npm, "run", "dev", "--", "--port", "3001"],
            cwd=web_root,
            environment=web_environment,
            temporary_root=temporary_root,
        )
        processes.append(web)
        checks["wellnessbox_health"] = _wait_ready(
            "http://127.0.0.1:3001/api/internal/rnd/health", *web
        )[0]

        tips_login = "http://127.0.0.1:3001/research-login?redirect=/tips"
        pharmacist_login = (
            "http://127.0.0.1:3001/research-login?redirect=/pharm/tips"
        )
        tips = _logged_in_page(tips_login)
        pharmacist = _logged_in_page(pharmacist_login)
        checks["tips"] = {
            "login_status": _redirect_status(tips_login),
            "page_status": tips[0],
            "final_url": tips[1],
        }
        checks["pharmacist"] = {
            "login_status": _redirect_status(pharmacist_login),
            "page_status": pharmacist[0],
            "final_url": pharmacist[1],
        }

        h005_status, _, h005_html = _get("http://127.0.0.1:8765/op039-review")
        checked = re.findall(r"<input[^>]+checked", h005_html, flags=re.IGNORECASE)
        comments = re.findall(
            r"<textarea[^>]*>(.*?)</textarea>",
            h005_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        cases = re.findall(r"<section><h2>", h005_html, flags=re.IGNORECASE)
        checks["h005"] = {
            "status": h005_status,
            "case_count": len(cases),
            "preselected_count": len(checked),
            "comment_count": len(comments),
            "prefilled_comment_count": sum(bool(value.strip()) for value in comments),
        }
    finally:
        for process, _, _ in reversed(processes):
            _stop_owned_process(process)
        for _, log, _ in processes:
            log.close()
    for port in PORTS:
        _assert_port_available(port)
    return checks


def run_preflight(
    *,
    root: Path = ROOT,
    web_root: Path = WEB_ROOT,
    probe: Probe = probe_servers,
) -> dict[str, Any]:
    root = root.resolve()
    before = snapshot_storage(root)
    database = root / "etc/local_research_runtime/interim.sqlite3"
    with tempfile.TemporaryDirectory(prefix="wellnessbox-final-session-preflight-") as temp:
        temporary_root = Path(temp)
        temporary_database = temporary_root / "interim.sqlite3"
        temporary_state_root = temporary_root / "final-session-state"
        shutil.copy2(database, temporary_database)
        if _sha256(database) != _sha256(temporary_database):
            raise RuntimeError("운영 DB 임시 복사본의 hash가 원본과 다릅니다.")
        try:
            checks = probe(
                root,
                web_root.resolve(),
                temporary_database,
                temporary_state_root,
                temporary_root,
            )
        except Exception as exc:
            checks = {"probe_error": f"{type(exc).__name__}: {exc}"}
    after = snapshot_storage(root)
    return classify_result(checks, before=before, after=after)


def main() -> int:
    try:
        result = run_preflight()
    except Exception as exc:
        result = {
            "schema_version": "final_session_preflight_v1",
            "status": "ERROR",
            "exit_code": 1,
            "operational_receipt_generation": False,
            "human_actions_performed": False,
            "blockers": [
                {
                    "id": "PREFLIGHT_SETUP_FAILED",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            ],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
