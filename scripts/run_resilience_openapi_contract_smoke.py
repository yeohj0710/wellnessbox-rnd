from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/original_plan/op113_op114_resilience_contract_cases_v1.json"
EVIDENCE = ROOT / "data/original_plan/evidence/op113_op114_resilience_contract_smoke_v1.json"
RND_CONTRACT = ROOT / "data/contracts/wb_rnd_interim_openapi_surface_v1.json"


def git(*arguments: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *arguments], cwd=cwd, text=True).strip()


def run_node(
    script: str, service: Path, environment: dict[str, str] | None = None
) -> dict[str, Any]:
    result = subprocess.run(
        ["node", "--conditions=react-server", "--import", "tsx", script],
        cwd=service,
        env=os.environ.copy() | (environment or {}),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wellnessbox-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    service = args.wellnessbox_root.resolve()
    dataset_bytes = subprocess.check_output(
        ["git", "show", f"HEAD:{DATASET.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )
    dataset = json.loads(dataset_bytes)
    cases = {case["case_id"]: case for case in dataset["cases"]}

    resilience = run_node("scripts/qa/check-rnd-resilience-contract.cts", service)
    contract = run_node("scripts/qa/check-rnd-openapi-contract.cts", service)
    subprocess.run(
        ["python", "scripts/build_interim_openapi_contract.py", "--check"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    service_contract = service / "contracts/wb-rnd/interim-openapi-surface-v1.json"
    exact_contract_match = RND_CONTRACT.read_bytes() == service_contract.read_bytes()

    checks = {
        "retryable_get_retried_once": resilience["observed"]["retryCalls"]
        == cases["retryable_get"]["expected"]["attempts"],
        "retry_backoff_bounded": resilience["observed"]["retrySleeps"]
        == cases["retryable_get"]["expected"]["backoff_ms"],
        "non_json_retryable_response_retried": resilience["checks"]
        ["non_json_retryable_response_retried"],
        "post_not_retried": resilience["observed"]["postCalls"]
        == cases["non_idempotent_post"]["expected"]["attempts"],
        "actual_timeout_timer_clamped_and_aborted": resilience["checks"]
        ["actual_timeout_timer_clamped_and_aborted"],
        "non_retryable_4xx_does_not_open_circuit": resilience["checks"]
        ["non_retryable_4xx_does_not_open_circuit"],
        "circuit_opens_and_skips_network": resilience["observed"]["circuitFetchCalls"]
        == cases["circuit_breaker"]["expected"]["network_attempts"]
        and resilience["checks"]["open_circuit_skips_network"],
        "half_open_recovers": resilience["checks"]["half_open_recovers_after_30_seconds"],
        "half_open_allows_single_probe": resilience["checks"]["half_open_allows_single_probe"],
        "actual_route_fallback_bounded": resilience["checks"]
        ["actual_admin_route_fallback_bounded"],
        "generated_openapi_snapshot_current": True,
        "cross_repository_contract_exact": exact_contract_match,
        "typescript_registry_covers_used_paths": contract["registeredOperationCount"]
        == cases["typescript_registry"]["expected"]["registered_operation_count"]
        and contract["discoveredUsedPathCount"]
        == cases["typescript_registry"]["expected"]["used_path_count"],
        "typescript_registry_scans_all_service_sources": contract["scannedSourceFileCount"] > 100,
    }
    if not all(checks.values()):
        raise AssertionError(checks)

    report = {
        "schema_version": "op113_op114_resilience_contract_smoke_v1",
        "requirements": {
            "OP-113": {"required_stage": "INTEGRATED", "claimed_stage": "INTEGRATED"},
            "OP-114": {"required_stage": "INTEGRATED", "claimed_stage": "INTEGRATED"},
        },
        "dataset": {
            "path": DATASET.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(dataset_bytes).hexdigest(),
            "case_count": len(dataset["cases"]),
        },
        "checks": checks,
        "observed": {"resilience": resilience, "contract": contract},
        "source_identity": {
            "wellnessbox_commit": git("rev-parse", "HEAD", cwd=service),
            "wellnessbox_source_blobs": {
                path: git("rev-parse", f"HEAD:{path}", cwd=service)
                for path in (
                    "lib/server/wb-rnd-interim-client.ts",
                    "lib/server/wb-rnd-interim-contract.ts",
                    "scripts/qa/check-rnd-resilience-contract.cts",
                    "scripts/qa/check-rnd-openapi-contract.cts",
                    "contracts/wb-rnd/interim-openapi-surface-v1.json",
                )
            },
            "rnd_openapi_generator_commit": git(
                "log", "-1", "--format=%H", "--", "scripts/build_interim_openapi_contract.py"
            ),
        },
        "stage_boundary": {
            "actual_typescript_client_policy_executed": True,
            "actual_fastapi_openapi_generated": True,
            "actual_admin_fallback_route_executed": True,
            "production_outage_injected": False,
            "production_traffic_observed": False,
        },
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
