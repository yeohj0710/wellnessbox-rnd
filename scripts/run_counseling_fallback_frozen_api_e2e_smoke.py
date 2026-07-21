from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

RND_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = Path(
    os.environ.get("WELLNESSBOX_EVIDENCE_ROOT", r"C:\dev\wellnessbox")
).resolve()
DATASET_PATH = RND_ROOT / "data/original_plan/op089_op090_counseling_frozen_qa_v1.json"
RND_SOURCE_PATHS = (
    RND_ROOT / "scripts/run_counseling_fallback_frozen_api_e2e_smoke.py",
    DATASET_PATH,
    RND_ROOT / "apps/inference_api/routes/interim.py",
    RND_ROOT / "src/wellnessbox_rnd/chat/answering.py",
    RND_ROOT / "src/wellnessbox_rnd/chat/openai_adapter.py",
    RND_ROOT / "src/wellnessbox_rnd/chat/retrieval.py",
    RND_ROOT / "src/wellnessbox_rnd/chat/verifier.py",
    RND_ROOT / "src/wellnessbox_rnd/knowledge/runtime_db.py",
    RND_ROOT / "src/wellnessbox_rnd/interim/store.py",
    RND_ROOT / "data/knowledge/counseling_retrieval_corpus_manifest_v1.json",
    RND_ROOT / "data/knowledge/counseling_knowledge_scope_registry_v1.json",
    RND_ROOT / "data/knowledge/counseling_answer_verifier_policy_v1.json",
    RND_ROOT / "data/knowledge/runtime_knowledge_db_v1.json",
)
SERVICE_SOURCE_PATHS = (
    SERVICE_ROOT / "lib/server/wb-rnd-interim-client.ts",
    SERVICE_ROOT / "scripts/qa/run-rnd-counseling-frozen-api-e2e.cts",
)


class _ProviderFailureHandler(BaseHTTPRequestHandler):
    request_count = 0

    def do_POST(self) -> None:  # noqa: N802
        type(self).request_count += 1
        body = b'{"error":"injected_provider_outage"}'
        self.send_response(503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_ready(process: subprocess.Popen[str], port: int) -> None:
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError(f"rnd_api_exited:{process.returncode}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("rnd_api_not_ready")


def _git_source_commit(root: Path, paths: tuple[Path, ...]) -> str:
    relative_paths = [path.relative_to(root).as_posix() for path in paths]
    value = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", *relative_paths],
        cwd=root,
        text=True,
    ).strip()
    if not value:
        raise RuntimeError(f"source_commit_not_found:{root}")
    return value


def _git_blob_sha256(root: Path, path: Path) -> str:
    content = subprocess.check_output(
        ["git", "show", f"HEAD:{path.relative_to(root).as_posix()}"], cwd=root
    )
    return hashlib.sha256(content).hexdigest()


def _source_key(root: Path, path: Path, prefix: str) -> str:
    return f"{prefix}/{path.relative_to(root).as_posix()}"


def _run_once(database: Path) -> dict[str, object]:
    _ProviderFailureHandler.request_count = 0
    provider_server = ThreadingHTTPServer(("127.0.0.1", 0), _ProviderFailureHandler)
    provider_thread = threading.Thread(target=provider_server.serve_forever, daemon=True)
    provider_thread.start()
    provider_port = int(provider_server.server_address[1])
    api_port = _free_port()
    env = os.environ.copy()
    env.update(
        {
            "WB_RND_INTERIM_DATABASE": str(database),
            "WB_RND_INTERIM_INTERNAL_TOKEN": "op090-live-token",
            "WB_RND_INTERIM_ENABLED": "1",
            "WB_RND_APP_ENV": "local",
            "WELLNESSBOX_CHAT_ALLOW_LIVE_API": "1",
            "OPENAI_API_KEY": "injected-provider-key",
            "WELLNESSBOX_CHAT_OPENAI_BASE_URL": f"http://127.0.0.1:{provider_port}",
            "WELLNESSBOX_CHAT_OPENAI_TIMEOUT_SECONDS": "1",
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
            str(api_port),
        ],
        cwd=RND_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        _wait_ready(process, api_port)
        node_env = env | {
            "WB_RND_INTERIM_BASE_URL": f"http://127.0.0.1:{api_port}",
            "WB_RND_INTERIM_TOKEN": "op090-live-token",
            "WB_RND_INTERIM_PSEUDONYM_SALT": "op090-live-salt",
            "WB_RND_COUNSELING_QA_DATASET": str(DATASET_PATH),
        }
        completed = subprocess.run(
            [
                "node",
                "--conditions=react-server",
                "--import",
                "tsx",
                "scripts/qa/run-rnd-counseling-frozen-api-e2e.cts",
            ],
            cwd=SERVICE_ROOT,
            env=node_env,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        connection = sqlite3.connect(database)
        try:
            persisted_counts = {
                table: int(connection.execute(f"select count(*) from {table}").fetchone()[0])
                for table in ("agent_runs", "agent_steps", "recommendation_runs")
            }
        finally:
            connection.close()
        first = payload["first"]
        repeated = payload["repeated"]
        cases = [
            {
                "case_id": item["service_session_id"].removeprefix("op090-"),
                "status": item["answer"]["status"],
                "used_chunk_ids": item["answer"]["used_chunk_ids"],
                "answer_sha256": hashlib.sha256(
                    json.dumps(
                        item["answer"],
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
                "answer_text": item["answer"]["answer_text"],
                "verification": item["verification"],
                "answer_execution": item["answer_execution"],
                "recommendation_execution": (
                    None
                    if item["recommendation_execution"] is None
                    else {
                        "status": item["recommendation_execution"]["status"],
                        "simulation": item["recommendation_execution"]["simulation"],
                    }
                ),
                "fallback_reason": item["answer_execution"]["fallback_reason"],
                "attempted_live_call": item["answer_execution"]["attempted_live_call"],
                "deduplicated_on_repeat": repeated[index]["deduplicated"],
                "binding_stable": (
                    repeated[index]["session_binding_sha256"]
                    == item["session_binding_sha256"]
                ),
            }
            for index, item in enumerate(first)
        ]
        return {
            "case_count": len(cases),
            "cases": cases,
            "provider_request_count": _ProviderFailureHandler.request_count,
            "persisted_counts": persisted_counts,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=5)
        time.sleep(0.25)


def main() -> int:
    output = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/original_plan/evidence/op089_op090_counseling_fallback_api_e2e_v1.json"
    )
    output = output if output.is_absolute() else RND_ROOT / output
    temporary_root = RND_ROOT / "etc"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
        first = _run_once(Path(directory) / "first.sqlite3")
        second = _run_once(Path(directory) / "second.sqlite3")
    deterministic = first == second
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    report = {
        "schema_version": "op089_op090_counseling_fallback_api_e2e_v1",
        "requirements": ["OP-089", "OP-090"],
        "result": "PASS" if deterministic else "FAIL",
        "dataset": {
            "path": "data/original_plan/op089_op090_counseling_frozen_qa_v1.json",
            "schema_version": dataset["schema_version"],
            "case_count": dataset["case_count"],
            "sha256": _git_blob_sha256(RND_ROOT, DATASET_PATH),
        },
        "checks": first,
        "normalized_runs_byte_identical": deterministic,
        "local_provider_failure_injected": True,
        "real_rnd_http_api_observed": True,
        "real_service_typescript_client_observed": True,
        "service_chat_route_observed": False,
        "service_database_persistence_observed": False,
        "production_operation_observed": False,
        "source_identity": {
            "wellnessbox_rnd_commit": _git_source_commit(RND_ROOT, RND_SOURCE_PATHS),
            "wellnessbox_service_commit": _git_source_commit(
                SERVICE_ROOT, SERVICE_SOURCE_PATHS
            ),
            "files": {
                **{
                    _source_key(RND_ROOT, path, "wellnessbox-rnd"): _git_blob_sha256(
                        RND_ROOT, path
                    )
                    for path in RND_SOURCE_PATHS
                },
                **{
                    _source_key(SERVICE_ROOT, path, "wellnessbox"): _git_blob_sha256(
                        SERVICE_ROOT, path
                    )
                    for path in SERVICE_SOURCE_PATHS
                },
            },
        },
        "stage_boundary": {
            "OP-089": (
                "Local injected failure proves deterministic fallback implementation, "
                "not production operation."
            ),
            "OP-090": (
                "The real service client and R&D HTTP API ran, but /api/chat and the "
                "service database were not exercised."
            ),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
