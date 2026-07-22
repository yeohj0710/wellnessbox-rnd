from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/original_plan/op115_op116_test_matrix_health_alias_cases_v1.json"
OUTPUT = ROOT / "data/original_plan/evidence/op115_op116_test_matrix_health_alias_smoke_v1.json"
RND_SOURCES = (
    ROOT / "scripts/run_test_matrix_health_alias_smoke.py",
    ROOT / "scripts/run_deployment_contract_endpoint_smoke.py",
    ROOT / "tests/test_deployment_contract.py",
    ROOT / "apps/inference_api/routes/health.py",
    ROOT / "src/wellnessbox_rnd/deployment.py",
    DATASET,
)
SERVICE_SOURCES = (
    ".github/workflows/encoding-guard.yml",
    "app/api/internal/rnd/health/route.ts",
    "lib/server/wb-rnd-health.ts",
    "scripts/qa/check-rnd-health-alias.cts",
    "package.json",
)


def run(command: list[str], cwd: Path) -> str:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def git(root: Path, *args: str) -> str:
    return run(["git", *args], root).strip()


def blob_sha256(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    content = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=root)
    return hashlib.sha256(content).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wellnessbox-root", type=Path, required=True)
    args = parser.parse_args()
    service = args.wellnessbox_root.resolve()

    pytest_output = run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_original_plan_manifest.py",
            "tests/test_original_plan_audit.py",
            "tests/test_original_plan_audit_cli.py",
            "tests/test_original_plan_completion_report.py",
            "tests/test_deployment_contract.py",
            "-q",
        ],
        ROOT,
    )
    smoke = json.loads(
        run([sys.executable, "scripts/run_deployment_contract_endpoint_smoke.py"], ROOT)
    )
    run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "apps/inference_api/routes/health.py",
            "src/wellnessbox_rnd/deployment.py",
            "scripts/run_deployment_contract_endpoint_smoke.py",
            "scripts/run_test_matrix_health_alias_smoke.py",
            "tests/test_deployment_contract.py",
        ],
        ROOT,
    )
    with tempfile.TemporaryDirectory() as wheel_dir:
        run(
            [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", wheel_dir],
            ROOT,
        )
    run(["npm", "run", "qa:rnd:health-alias"], service)
    run(["npm", "run", "audit:encoding"], service)
    run(["npm", "run", "typecheck"], service)
    run(["npm", "run", "build"], service)

    dataset = json.loads(git(ROOT, "show", f"HEAD:{DATASET.relative_to(ROOT).as_posix()}"))
    report = {
        "schema_version": "op115_op116_test_matrix_health_alias_smoke_v1",
        "requirements": {
            "OP-115": {"required_stage": "INTEGRATED", "claimed_stage": "INTEGRATED"},
            "OP-116": {"required_stage": "OPERATED", "claimed_stage": "INTEGRATED"},
        },
        "dataset": {
            "path": DATASET.relative_to(ROOT).as_posix(),
            "case_count": len(dataset["cases"]),
            "sha256": blob_sha256(ROOT, DATASET),
        },
        "checks": {
            "rnd_focused_unit_integration_tests_passed": "passed" in pytest_output,
            "rnd_process_e2e_passed": all(smoke["checks"].values()),
            "rnd_ruff_and_wheel_build_passed": True,
            "rnd_health_ready_for_provider_deployment": smoke["observed"][
                "deployment_contract_status"
            ]
            == "READY_FOR_PROVIDER_DEPLOYMENT",
            "wellnessbox_actual_health_alias_handler_qa_passed": True,
            "wellnessbox_typecheck_encoding_and_build_passed": True,
        },
        "observed": {
            "rnd_process_smoke_case_count": smoke["dataset"]["case_count"],
            "rnd_endpoint_family_count": smoke["observed"]["endpoint_family_count"],
            "wellnessbox_alias_path": "/api/internal/rnd/health",
            "wellnessbox_alias_healthy_status": 200,
            "wellnessbox_alias_disabled_or_unhealthy_status": 503,
        },
        "source_identity": {
            "wellnessbox_rnd_commit": git(ROOT, "rev-parse", "HEAD"),
            "wellnessbox_rnd_source_blobs": {
                path.relative_to(ROOT).as_posix(): git(
                    ROOT, "rev-parse", f"HEAD:{path.relative_to(ROOT).as_posix()}"
                )
                for path in RND_SOURCES
            },
            "wellnessbox_commit": git(service, "rev-parse", "HEAD"),
            "wellnessbox_source_blobs": {
                path: git(service, "rev-parse", f"HEAD:{path}")
                for path in SERVICE_SOURCES
            },
        },
        "stage_boundary": {
            "local_rnd_process_health_proven": True,
            "actual_wellnessbox_alias_handler_proven": True,
            "production_deployment_proven": False,
            "production_traffic_proven": False,
        },
    }
    if not all(report["checks"].values()):
        raise AssertionError(report["checks"])
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
