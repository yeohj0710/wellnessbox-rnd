from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(
    os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")
).resolve()
PORT = 8878
RND_SOURCE_PATHS = (
    RND_ROOT / "scripts/run_counseling_session_service_adapter_smoke.py",
    RND_ROOT / "apps/inference_api/routes/interim.py",
    RND_ROOT / "src/wellnessbox_rnd/interim/store.py",
    RND_ROOT / "data/knowledge/counseling_retrieval_corpus_manifest_v1.json",
)
SERVICE_SOURCE_PATHS = (
    SERVICE_ROOT / "app/api/chat/route-service.ts",
    SERVICE_ROOT / "app/api/chat/save/route-service.ts",
    SERVICE_ROOT / "lib/server/wb-rnd-interim-client.ts",
    SERVICE_ROOT / "scripts/qa/run-rnd-counseling-live-smoke.cts",
    SERVICE_ROOT / "scripts/qa/check-rnd-counseling-adapter.cts",
)
SOURCE_PATHS = RND_SOURCE_PATHS + SERVICE_SOURCE_PATHS


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_source_commit(root: Path, paths: tuple[Path, ...]) -> str:
    relative_paths = [path.relative_to(root).as_posix() for path in paths]
    commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", *relative_paths],
        cwd=root,
        text=True,
    ).strip()
    if not commit:
        raise RuntimeError(f"source_commit_not_found:{root}")
    return commit


def _source_key(path: Path) -> str:
    if path.is_relative_to(SERVICE_ROOT):
        return f"wellnessbox/{path.relative_to(SERVICE_ROOT).as_posix()}"
    return f"wellnessbox-rnd/{path.relative_to(RND_ROOT).as_posix()}"


def _wait_ready(process: subprocess.Popen[str]) -> None:
    for _ in range(60):
        if process.poll() is not None:
            raise RuntimeError(f"rnd_api_exited:{process.returncode}")
        try:
            with urlopen(f"http://127.0.0.1:{PORT}/health", timeout=0.5) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("rnd_api_not_ready")


def _one_run(database: Path) -> dict[str, object]:
    env = os.environ.copy()
    env.update(
        {
            "WB_RND_INTERIM_DATABASE": str(database),
            "WB_RND_INTERIM_INTERNAL_TOKEN": "op088-live-token",
            "WB_RND_INTERIM_ENABLED": "1",
            "WB_RND_APP_ENV": "local",
        }
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "apps.inference_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=RND_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        _wait_ready(process)
        node_env = env | {
            "WB_RND_INTERIM_BASE_URL": f"http://127.0.0.1:{PORT}",
            "WB_RND_INTERIM_TOKEN": "op088-live-token",
            "WB_RND_INTERIM_PSEUDONYM_SALT": "op088-live-salt",
        }
        completed = subprocess.run(
            [
                "node",
                "--conditions=react-server",
                "--import",
                "tsx",
                "scripts/qa/run-rnd-counseling-live-smoke.cts",
            ],
            cwd=SERVICE_ROOT,
            env=node_env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        store_check = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sqlite3,sys,json; c=sqlite3.connect(sys.argv[1]); "
                    "print(json.dumps({"
                    "'agent_runs':c.execute('select count(*) from agent_runs')"
                    ".fetchone()[0],"
                    "'agent_steps':c.execute('select count(*) from agent_steps')"
                    ".fetchone()[0],"
                    "'recommendation_runs':c.execute("
                    "'select count(*) from recommendation_runs').fetchone()[0]}))"
                ),
                str(database),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        counts = json.loads(store_check.stdout)
        answer_text = str(payload["answer"]["answer_text"])
        return {
            "service_session_id": payload["service_session_id"],
            "turn_id": payload["turn_id"],
            "verified": payload["verification"]["passed"],
            "answer_status": payload["answer"]["status"],
            "answer_sha256": hashlib.sha256(answer_text.encode()).hexdigest(),
            "agent_run_id_valid": bool(re.fullmatch(r"run_[a-f0-9]{32}", payload["agent_run_id"])),
            "recommendation_run_id_valid": bool(
                re.fullmatch(
                    r"rec_[a-f0-9]{32}", payload["recommendation_execution"]["run_id"]
                )
            ),
            "recommendation_status": payload["recommendation_execution"]["status"],
            "simulation": payload["recommendation_execution"]["simulation"],
            "binding_sha256_valid": bool(
                re.fullmatch(r"[a-f0-9]{64}", payload["session_binding_sha256"])
            ),
            "persisted_counts": counts,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    report_path = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else (
            "data/original_plan/evidence/"
            "op087_op088_counseling_session_service_adapter_smoke_v1.json"
        )
    )
    report_path = report_path if report_path.is_absolute() else RND_ROOT / report_path
    temporary_root = RND_ROOT / "etc"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
        first = _one_run(Path(directory) / "first.sqlite3")
        second = _one_run(Path(directory) / "second.sqlite3")
    deterministic = first == second
    report = {
        "schema_version": "op087_op088_counseling_session_service_adapter_smoke_v1",
        "requirements": ["OP-087", "OP-088"],
        "result": "PASS" if deterministic else "FAIL",
        "local_two_process_integration": True,
        "production_operation_observed": False,
        "service_database_persistence_observed": False,
        "normalized_runs_byte_identical": deterministic,
        "checks": first,
        "source_identity": {
            "wellnessbox_rnd_commit": _git_source_commit(
                RND_ROOT,
                RND_SOURCE_PATHS,
            ),
            "wellnessbox_service_commit": _git_source_commit(
                SERVICE_ROOT,
                SERVICE_SOURCE_PATHS,
            ),
            "files": {_source_key(path): _sha256(path) for path in SOURCE_PATHS},
        },
        "stage_boundary": {
            "OP-087": "Local integration does not prove required OPERATED production use.",
            "OP-088": (
                "The real service TypeScript adapter called the real localhost R&D API; "
                "the /api/chat route and service database were not exercised."
            ),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    report_path.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
