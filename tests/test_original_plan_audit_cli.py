from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path("scripts/audit_original_plan_requirements.py")
WORKFLOW_PATH = Path(".github/workflows/original-plan-evidence.yml")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_original_plan_audit_cli_returns_zero_for_current_manifest() -> None:
    result = _run_cli()
    report = json.loads(result.stdout)

    assert result.returncode == 0
    assert report["status"] == "PASS"
    assert report["requirement_count"] == 120
    assert report["claimed_requirement_count"] == 11
    assert report["issues"] == []


def test_original_plan_audit_cli_returns_one_for_failed_audit(tmp_path: Path) -> None:
    payload = json.loads(
        Path("data/original_plan/requirements_manifest_v1.json").read_text(
            encoding="utf-8"
        )
    )
    payload["original_plan_sha256"] = "0" * 64
    manifest_path = tmp_path / "failed_manifest.json"
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = _run_cli("--manifest", str(manifest_path))
    report = json.loads(result.stdout)

    assert result.returncode == 1
    assert report["status"] == "FAIL"
    assert any(
        issue["code"] == "original_plan_sha256_mismatch"
        for issue in report["issues"]
    )


def test_original_plan_audit_workflow_runs_cli_and_contract_tests() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python scripts/audit_original_plan_requirements.py" in workflow
    assert "tests/test_original_plan_manifest.py" in workflow
    assert "tests/test_original_plan_audit.py" in workflow
    assert "tests/test_original_plan_audit_cli.py" in workflow
