from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/original_plan/op117_op118_browser_operational_evidence_cases_v1.json"
OUTPUT = ROOT / "data/original_plan/evidence/op117_op118_browser_operational_evidence_smoke_v1.json"
MANIFEST = ROOT / "data/original_plan/requirements_manifest_v1.json"
RND_SOURCE_PATHS = (
    "scripts/run_browser_operational_evidence_smoke.py",
    "data/original_plan/op117_op118_browser_operational_evidence_cases_v1.json",
    "data/original_plan/requirements_manifest_v1.json",
)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_ready(url: str, process: subprocess.Popen[str]) -> None:
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError("next_dev_exited")
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("next_dev_ready_timeout")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def rnd_source_commit() -> str:
    return git(ROOT, "log", "-1", "--format=%H", "--", *RND_SOURCE_PATHS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wellnessbox-root", required=True, type=Path)
    args = parser.parse_args()
    service = args.wellnessbox_root.resolve()
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    requirements = [item for group in manifest["groups"] for item in group["requirements"]]
    non_external = [item for item in requirements if item.get("required_stage") != "EXTERNAL"]
    linked = [item for item in non_external if item.get("evidence")]
    operated = [item for item in non_external if item.get("claimed_stage") == "OPERATED"]
    external = [item for item in requirements if item.get("required_stage") == "EXTERNAL"]

    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    admin_password = "op117-local-browser-admin-password"
    passthrough = ("PATH", "SystemRoot", "TEMP", "TMP", "LOCALAPPDATA", "APPDATA", "USERPROFILE")
    environment = {key: os.environ[key] for key in passthrough if key in os.environ} | {
        "PORT": str(port),
        "ADMIN_PASSWORD": admin_password,
        "JWT_SECRET": "op117-local-jwt-secret-at-least-32-bytes",
        "COOKIE_PASSWORD": "op117-local-cookie-password-at-least-32-bytes",
    }
    process = subprocess.Popen(
        [shutil.which("npm") or "npm", "run", "dev", "--", "--port", str(port)],
        cwd=service,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        wait_ready(f"{base_url}/survey", process)
        completed = subprocess.run(
            ["node", "scripts/qa/check-rnd-role-browser-paths.cjs"],
            cwd=service,
            env=environment | {"BASE_URL": base_url},
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode:
            raise RuntimeError(
                f"browser_qa_failed stdout={completed.stdout!r} "
                f"stderr={completed.stderr!r}"
            )
        browser = json.loads(completed.stdout.strip().splitlines()[-1])
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    observed = {
        "browser_case_count": len(browser["cases"]),
        "non_external_requirement_count": len(non_external),
        "evidence_linked_count": len(linked),
        "external_requirement_count": len(external),
        "operated_requirement_count": len(operated),
        "operated_gap_count": len(non_external) - len(operated),
    }
    if observed["browser_case_count"] != 3 or len(dataset["cases"]) != 8:
        raise AssertionError(observed)
    if (
        observed["non_external_requirement_count"] != 119
        or observed["external_requirement_count"] != 1
    ):
        raise AssertionError(observed)
    if observed["evidence_linked_count"] != 118 or observed["operated_requirement_count"] != 0:
        raise AssertionError(observed)

    report = {
        "schema_version": "op117_op118_browser_operational_evidence_smoke_v1",
        "requirements": {
            "OP-117": {"required_stage": "OPERATED", "claimed_stage": "IMPLEMENTED"},
            "OP-118": {"required_stage": "OPERATED", "claimed_stage": "IMPLEMENTED"},
        },
        "dataset": {
            "path": DATASET.relative_to(ROOT).as_posix(),
            "case_count": len(dataset["cases"]),
            "sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        },
        "browser": browser,
        "observed": observed,
        "operated_gap_requirement_ids": [
            item["requirement_id"]
            for item in non_external
            if item.get("claimed_stage") != "OPERATED"
        ],
        "source_identity": {
            "wellnessbox_rnd_commit": rnd_source_commit(),
            "wellnessbox_commit": git(service, "rev-parse", "HEAD"),
            "wellnessbox_browser_script_sha256": hashlib.sha256(
                (service / "scripts/qa/check-rnd-role-browser-paths.cjs").read_bytes()
            ).hexdigest(),
        },
        "stage_boundary": {
            "local_real_browser_proven": True,
            "pharmacist_authenticated_session_proven": False,
            "production_deployment_proven": False,
            "production_traffic_proven": False,
            "all_non_external_operated_proven": False,
        },
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
