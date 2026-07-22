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
from pathlib import Path
from urllib import request

from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]
SERVICE = Path(os.environ.get("WELLNESSBOX_SERVICE_REPO", "C:/dev/wellnessbox"))
DATASET = ROOT / "data/original_plan/op111_op112_security_boundary_cases_v1.json"
OUTPUT = ROOT / "data/original_plan/evidence/op111_op112_security_boundary_smoke_v1.json"


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=cwd, text=True, encoding="utf-8"
    ).strip()


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


def main() -> int:
    dataset_bytes = subprocess.check_output(
        ["git", "show", f"HEAD:{DATASET.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )
    dataset = json.loads(dataset_bytes)
    token = "Canonical-Security-Boundary-Token-2026"
    salt = "canonical-security-pseudonym-salt-2026"
    with tempfile.TemporaryDirectory() as temporary:
        database = Path(temporary) / "interim.sqlite3"
        InterimStore(database).migrate()
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
                    "scripts/qa/check-rnd-security-boundary.cts",
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

    cases = {case["case_id"]: case for case in dataset["cases"]}
    expected_profile_id = "usr_" + hmac.new(
        salt.encode(),
        cases["pseudonym"]["input"]["subject_id"].encode(),
        hashlib.sha256,
    ).hexdigest()[: cases["pseudonym"]["expected"]["hex_characters"]]
    checks = {
        "three_roles_denied_without_auth": observed["deniedRoles"]
        == ["user", "pharmacy", "admin"]
        and all(
            cases[case_id]["expected"]["denied_without_auth"]
            for case_id in ("user_role", "pharmacy_role", "admin_role")
        ),
        "role_guard_decision_functions_executed": observed["roleGuardDecisionFunctionsExecuted"]
        is cases["admin_role"]["expected"]["guard_decision_functions_executed"],
        "authenticated_admin_branch_executed": observed["authenticatedAdminBranchExecuted"]
        is cases["admin_role"]["expected"]["authenticated_success"],
        "admin_fallback_error_bounded": observed["adminFallbackBounded"]
        is cases["admin_role"]["expected"]["fallback_error_bounded"],
        "user_profile_scope_server_owned": observed["userProfileSpoofIgnored"]
        is cases["user_role"]["expected"]["spoof_ignored"],
        "pharmacy_scope_server_owned": observed["pharmacyScopeOverridden"]
        is cases["pharmacy_role"]["expected"]["scope_server_owned"],
        "internal_token_accepted": observed["internalTokenAccepted"]
        is cases["internal_token"]["expected"]["accepted"],
        "invalid_internal_token_rejected": observed["invalidInternalTokenRejected"]
        is cases["internal_token"]["expected"]["invalid_rejected"],
        "deterministic_pseudonym_used": observed["profileId"] == expected_profile_id
        and cases["pseudonym"]["expected"]["algorithm"] == "HMAC-SHA256",
        "direct_identifier_payload_rejected": observed["directIdentifierPayloadRejected"]
        is cases["minimum_collection"]["expected"]["direct_identifier_rejected"],
        "direct_identifier_removed": observed["directIdentifierRemoved"]
        is cases["minimum_collection"]["expected"]["name_removed"],
        "unused_field_removed": observed["unusedFieldRemoved"]
        is cases["minimum_collection"]["expected"]["unused_field_removed"],
        "logs_masked": observed["logsMasked"]
        is cases["log_masking"]["expected"]["utility_masked"],
        "operational_log_call_site_masked": observed["operationalLogCallSiteMasked"]
        is cases["log_masking"]["expected"]["operational_call_site_masked"],
        "public_errors_bounded": observed["publicErrorsBounded"]
        is cases["bounded_error"]["expected"]["unexpected_error_bounded"],
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    report = {
        "schema_version": "op111_op112_security_boundary_smoke_v1",
        "requirements": {
            "OP-111": {"required_stage": "INTEGRATED", "claimed_stage": "INTEGRATED"},
            "OP-112": {"required_stage": "INTEGRATED", "claimed_stage": "INTEGRATED"},
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
            "wellnessbox_source_blobs": {
                path: git("rev-parse", f"HEAD:{path}", cwd=SERVICE)
                for path in (
                    "lib/server/wb-rnd-interim-client.ts",
                    "lib/server/wb-rnd-interim-route.ts",
                    "lib/server/wb-rnd-profile-adapter.ts",
                    "lib/server/route-auth.ts",
                    "lib/server/wb-rnd-security.ts",
                    "scripts/qa/check-rnd-security-boundary.cts",
                )
            },
            "wellnessbox_rnd_source_commit": git(
                "log", "-1", "--format=%H", "--", "apps/inference_api/routes/interim.py"
            ),
        },
        "stage_boundary": {
            "actual_service_route_authorization_branches_executed": True,
            "role_guard_decision_functions_executed": True,
            "actual_rnd_http_token_roundtrip_executed": True,
            "production_identity_provider_operation_proven": False,
            "production_log_sink_inspection_proven": False,
        },
    }
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
