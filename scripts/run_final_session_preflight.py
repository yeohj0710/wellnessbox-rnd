from __future__ import annotations

import hashlib
import http.cookiejar
import json
import os
import secrets
import shutil
import socket
import sqlite3
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
RUNTIME_CONTROL_FILES = (
    "operational_capture.json",
    "session_processes.json",
    "stop.request",
)
H005_RENDERED_DOM_SCRIPT = r"""
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const response = await page.goto(process.argv[1], { waitUntil: 'networkidle' });
    const status = response ? response.status() : 0;
    const result = await page.evaluate(status => {
      const cases = Array.from(document.querySelectorAll('section')).filter(
        section => section.querySelector('h2')
      );
      const selected = section => {
        const toggles = Array.from(
          section.querySelectorAll('input[type="radio"], input[type="checkbox"]')
        );
        const selects = Array.from(section.querySelectorAll('select'));
        return toggles.some(control => control.checked) ||
          selects.some(control => control.value.trim() !== '');
      };
      const comments = section => Array.from(
        section.querySelectorAll('textarea, input[type="text"]')
      );
      return {
        status,
        case_count: cases.length,
        preselected_count: cases.filter(selected).length,
        comment_count: cases.filter(section => comments(section).length > 0).length,
        prefilled_comment_count: cases.filter(
          section => comments(section).some(control => control.value.trim() !== '')
        ).length,
      };
    }, status);
    process.stdout.write(JSON.stringify(result));
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
"""
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


def _path_snapshot(path: Path) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "path": str(path.resolve()),
        "exists": path.is_file(),
    }
    if snapshot["exists"]:
        snapshot |= {"sha256": _sha256(path), "size": path.stat().st_size}
    return snapshot


def _file_manifest(files: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _database_family_snapshot(database: Path) -> dict[str, Any]:
    return {
        name: _path_snapshot(database.with_name(name))
        for name in ("interim.sqlite3", "interim.sqlite3-wal", "interim.sqlite3-shm")
    }


def copy_sqlite_database(source: Path, target: Path) -> None:
    before = _database_family_snapshot(source)
    shutil.copy2(source, target)
    source_wal = source.with_name(f"{source.name}-wal")
    if source_wal.is_file():
        shutil.copy2(source_wal, target.with_name(f"{target.name}-wal"))
    after = _database_family_snapshot(source)
    if before != after:
        raise RuntimeError("운영 DB 파일이 임시 복사 중 바뀌었습니다.")

    target_connection = sqlite3.connect(target)
    try:
        integrity = target_connection.execute("PRAGMA integrity_check").fetchone()
    finally:
        target_connection.close()
    if integrity != ("ok",):
        raise RuntimeError(f"운영 DB 임시 복사본이 손상됐습니다: {integrity!r}")


def snapshot_storage(root: Path) -> dict[str, Any]:
    database = root / "etc/local_research_runtime/interim.sqlite3"
    if not database.is_file():
        raise FileNotFoundError(f"운영 DB가 없습니다: {database}")
    runtime_root = database.parent
    database_family = _database_family_snapshot(database)
    runtime_controls = {name: _path_snapshot(runtime_root / name) for name in RUNTIME_CONTROL_FILES}
    final_state_root = root / "data/original_plan/final_session"
    final_state = {
        path.name: _path_snapshot(path)
        for path in sorted(final_state_root.iterdir())
        if path.is_file()
    }
    receipts = root / "data/original_plan/final_session/operational_receipts"
    receipt_files = {
        path.relative_to(receipts).as_posix(): _path_snapshot(path)
        for path in sorted(receipts.rglob("*"))
        if path.is_file()
    }
    return {
        "database_family": database_family,
        "runtime_controls": runtime_controls,
        "final_state": final_state,
        "receipts": receipt_files,
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
    database_unchanged = before["database_family"] == after["database_family"]
    runtime_controls_unchanged = before["runtime_controls"] == after["runtime_controls"]
    final_state_unchanged = before["final_state"] == after["final_state"]
    before_receipts = before["receipts"]
    after_receipts = after["receipts"]
    receipt_file_list_unchanged = list(before_receipts) == list(after_receipts)
    receipt_hashes_unchanged = before_receipts == after_receipts
    storage = {
        "database_unchanged": database_unchanged,
        "runtime_controls_unchanged": runtime_controls_unchanged,
        "final_state_unchanged": final_state_unchanged,
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
    if not runtime_controls_unchanged:
        blocker = {
            "id": "RUNTIME_CONTROL_FILES_CHANGED",
            "message": "사전 점검 중 운영 캡처 또는 프로세스 제어 파일이 바뀌었습니다.",
        }
        blockers.append(blocker)
        error_ids.add(blocker["id"])
    if not final_state_unchanged:
        blocker = {
            "id": "FINAL_SESSION_STATE_CHANGED",
            "message": "사전 점검 중 실제 최종 세션 상태 파일이 바뀌었습니다.",
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
            "database_family_before": before["database_family"],
            "database_family_after": after["database_family"],
            "runtime_control_manifest_sha256_before": _file_manifest(before["runtime_controls"]),
            "runtime_control_manifest_sha256_after": _file_manifest(after["runtime_controls"]),
            "final_state_file_count_before": len(before["final_state"]),
            "final_state_file_count_after": len(after["final_state"]),
            "final_state_manifest_sha256_before": _file_manifest(before["final_state"]),
            "final_state_manifest_sha256_after": _file_manifest(after["final_state"]),
            "receipt_file_count_before": len(before_receipts),
            "receipt_file_count_after": len(after_receipts),
            "receipt_manifest_sha256_before": _file_manifest(before_receipts),
            "receipt_manifest_sha256_after": _file_manifest(after_receipts),
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
        f"서버 준비 시간을 초과했습니다: {url}; error={last_error}; log={_log_tail(log, log_path)}"
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


def inspect_rendered_h005(url: str, *, web_root: Path) -> dict[str, int]:
    node = shutil.which("node")
    if node is None:
        raise FileNotFoundError("node 실행 파일을 찾지 못했습니다.")
    completed = subprocess.run(
        [node, "-e", H005_RENDERED_DOM_SCRIPT, url],
        cwd=web_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )
    value = json.loads(completed.stdout)
    required = {
        "status",
        "case_count",
        "preselected_count",
        "comment_count",
        "prefilled_comment_count",
    }
    if set(value) != required or not all(isinstance(value[key], int) for key in required):
        raise ValueError(f"H-005 렌더링 검사 결과가 잘못됐습니다: {value!r}")
    return value


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
        checks["rnd_health"] = _wait_ready("http://127.0.0.1:8000/health", *api)[0]

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
        checks["console_home"] = _wait_ready("http://127.0.0.1:8765/", *console)[0]
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
        pharmacist_login = "http://127.0.0.1:3001/research-login?redirect=/pharm/tips"
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

        checks["h005"] = inspect_rendered_h005(
            "http://127.0.0.1:8765/op039-review", web_root=web_root
        )
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
        copy_sqlite_database(database, temporary_database)
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
