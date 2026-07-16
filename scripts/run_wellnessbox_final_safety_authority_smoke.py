from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "original_plan"
    / "evidence"
    / "op040_final_safety_authority_integration_smoke_v1.json"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the WellnessBox client against a real R&D API process."
    )
    default_service_root = os.getenv(
        "WELLNESSBOX_EVIDENCE_ROOT",
        str(PROJECT_ROOT.parent / "wellnessbox"),
    )
    parser.add_argument(
        "--wellnessbox-root",
        type=Path,
        default=Path(default_service_root),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser.parse_args()


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_health(base_url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 30
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout is not None else ""
            raise RuntimeError(
                f"R&D API exited before health check (code={process.returncode}): {output}"
            )
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if response.status == 200 and payload.get("status") == "ok":
                return
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            last_error = error
        time.sleep(0.1)
    raise RuntimeError(f"R&D API health check timed out: {last_error}")


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _api_python() -> str:
    if os.name == "nt":
        project_python = PROJECT_ROOT / ".venv-interim" / "Scripts" / "python.exe"
    else:
        project_python = PROJECT_ROOT / ".venv-interim" / "bin" / "python"
    return str(project_python) if project_python.is_file() else sys.executable


def _git_source_commit(root: Path, relative_paths: list[str]) -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *relative_paths],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _source_bundle_sha256(root: Path, relative_paths: list[str]) -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(relative_paths):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / relative_path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run_smoke(*, wellnessbox_root: Path, output_path: Path) -> dict[str, object]:
    wellnessbox_root = wellnessbox_root.resolve()
    if not (wellnessbox_root / "package.json").is_file():
        raise FileNotFoundError(
            f"WellnessBox service package.json not found: {wellnessbox_root}"
        )

    with tempfile.TemporaryDirectory(prefix="op040-authority-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        api_environment = os.environ.copy()
        api_environment.update(
            {
                "WB_RND_APP_ENV": "test",
                "WB_RND_INTERIM_DATABASE": str(temporary_root / "interim.sqlite3"),
                "WB_RND_INTERIM_ENABLED": "1",
                "WB_RND_INTERIM_INTERNAL_TOKEN": "op040-integration-token",
                "WB_RND_LOG_LEVEL": "WARNING",
            }
        )
        process: subprocess.Popen[str] | None = None
        base_url = ""
        startup_errors: list[str] = []
        for _attempt in range(3):
            port = _reserve_local_port()
            base_url = f"http://127.0.0.1:{port}"
            candidate = subprocess.Popen(
                [
                    _api_python(),
                    "-m",
                    "uvicorn",
                    "apps.inference_api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=PROJECT_ROOT,
                env=api_environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            )
            try:
                _wait_for_health(base_url, candidate)
                process = candidate
                break
            except RuntimeError as error:
                startup_errors.append(str(error))
                _stop_process(candidate)
        if process is None:
            raise RuntimeError("R&D API failed to start: " + " | ".join(startup_errors))
        try:
            client_output_path = temporary_root / "client-result.json"
            service_environment = os.environ.copy()
            service_environment.update(
                {
                    "NODE_ENV": "test",
                    "WB_RND_INTERIM_ENABLED": "1",
                    "WB_RND_INTERIM_BASE_URL": base_url,
                    "WB_RND_INTERIM_TOKEN": "op040-integration-token",
                    "WB_RND_INTERIM_PSEUDONYM_SALT": "op040-integration-salt",
                    "WB_RND_INTERIM_TIMEOUT_MS": "15000",
                    "WB_RND_AUTHORITY_SMOKE_OUTPUT": str(client_output_path),
                }
            )
            result = subprocess.run(
                [_npm_command(), "run", "qa:rnd:final-safety-authority"],
                cwd=wellnessbox_root,
                env=service_environment,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "WellnessBox final safety authority client failed:\n"
                    f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                )
            client_result = json.loads(client_output_path.read_text(encoding="utf-8"))
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("WellnessBox final safety authority client timed out") from error
        finally:
            _stop_process(process)

    rnd_source_paths = [
        "apps/inference_api/routes/interim.py",
        "scripts/run_wellnessbox_final_safety_authority_smoke.py",
        "src/wellnessbox_rnd/interim/safety.py",
    ]
    service_source_paths = [
        "app/api/tips/route.ts",
        "lib/server/wb-rnd-interim-client.ts",
        "lib/server/wb-rnd-interim-route.ts",
        "lib/server/wb-rnd-interim-safety-authority.ts",
        "lib/server/wb-rnd-tips-route-test-hook.ts",
        "package.json",
        "scripts/qa/check-rnd-final-safety-authority.cts",
    ]
    report: dict[str, object] = {
        "schema_version": "op040_final_safety_authority_integration_smoke_v2",
        "requirement_id": "OP-040",
        "claimed_evidence_stage": "INTEGRATED",
        "production_operation_proven": False,
        "source_identity": {
            "wellnessbox_rnd_commit": _git_source_commit(
                PROJECT_ROOT, rnd_source_paths
            ),
            "wellnessbox_rnd_source_sha256": _source_bundle_sha256(
                PROJECT_ROOT, rnd_source_paths
            ),
            "wellnessbox_commit": _git_source_commit(
                wellnessbox_root, service_source_paths
            ),
            "wellnessbox_source_sha256": _source_bundle_sha256(
                wellnessbox_root, service_source_paths
            ),
        },
        "processes": [
            "wellnessbox-rnd FastAPI /v1/interim/recommendations",
            "wellnessbox POST /api/tips route handler",
        ],
        "transport": "localhost_http",
        "checks": client_result["checks"],
        "observed": client_result["observed"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    args = _parse_args()
    report = run_smoke(
        wellnessbox_root=args.wellnessbox_root,
        output_path=args.output,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
