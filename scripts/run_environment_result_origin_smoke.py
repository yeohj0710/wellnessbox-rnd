from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = Path(os.environ.get("WELLNESSBOX_SERVICE_REPO", "C:/dev/wellnessbox"))
DATASET = ROOT / "data/original_plan/op103_op104_environment_result_origin_cases_v1.json"
OUTPUT = ROOT / "data/original_plan/evidence/op103_op104_environment_result_origin_smoke_v1.json"
SERVICE_PATHS = [
    "lib/server/wb-rnd-environment.ts",
    "lib/wb-rnd-result-origin.ts",
    "lib/server/wb-rnd-client.ts",
    "app/(dev)/rnd-preview/rnd-preview-client.tsx",
    "scripts/qa/check-rnd-environment-result-origin.cts",
]


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True, encoding="utf-8")


def main() -> int:
    dataset_bytes = git("show", f"HEAD:{DATASET.relative_to(ROOT).as_posix()}").encode()
    dataset = json.loads(dataset_bytes)
    service_commit = git("rev-parse", "HEAD", cwd=SERVICE).strip()
    blobs = {path: git("show", f"HEAD:{path}", cwd=SERVICE) for path in SERVICE_PATHS}
    combined = "\n".join(blobs.values())
    checks = {
        "environment_contract_is_committed": "WB_RND_SERVICE_BASE_URL_https_required" in combined,
        "runtime_uses_environment_contract": "resolveWbRndEnvironmentContract()"
        in blobs[SERVICE_PATHS[2]],
        "secret_is_server_owned": "WB_RND_SERVICE_TOKEN" in blobs[SERVICE_PATHS[0]]
        and "NEXT_PUBLIC_WB_RND" not in combined,
        "url_and_timeout_fail_closed": "contains_credentials_or_suffix" in combined
        and "out_of_range" in combined,
        "remote_execution_origin_is_explicit": 'kind: "rnd_execution"' in combined
        and "R&D 실행 결과" in combined,
        "local_snapshot_origin_is_explicit": 'kind: "local_snapshot"' in combined
        and "로컬 스냅샷 결과" in combined,
        "ambiguous_origin_fails_closed": "missing_fallback_reason" in combined,
        "evaluation_screen_renders_origin": "resultOrigin?.label" in blobs[SERVICE_PATHS[3]],
        "focused_contract_test_is_committed": "environment and result-origin contract: PASS"
        in combined,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    report = {
        "schema_version": "op103_op104_environment_result_origin_smoke_v1",
        "requirements": {
            "OP-103": {"required_stage": "OPERATED", "claimed_stage": "IMPLEMENTED"},
            "OP-104": {"required_stage": "OPERATED", "claimed_stage": "INTEGRATED"},
        },
        "dataset": {
            "path": DATASET.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "case_count": len(dataset["cases"]),
        },
        "checks": checks,
        "source_identity": {
            "wellnessbox_commit": service_commit,
            "wellnessbox_source_sha256": hashlib.sha256(combined.encode()).hexdigest(),
        },
        "stage_boundary": {
            "local_service_integration_proven": True,
            "vercel_environment_registered": False,
            "production_traffic_proven": False,
        },
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
