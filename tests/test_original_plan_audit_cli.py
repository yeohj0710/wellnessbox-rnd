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
    assert report["claimed_requirement_count"] == 109
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
    assert "python scripts/build_original_plan_completion_report.py --check" in workflow
    assert "tests/test_original_plan_completion_report.py" in workflow
    assert workflow.count('"docs/original_plan/**"') == 2
    assert workflow.count('"tests/test_original_plan_completion_report.py"') == 2
    assert "tests/test_health_input_contracts.py" in workflow
    assert "tests/test_diet_lifestyle_lab_input_contracts.py" in workflow
    assert "tests/test_consent_and_input_hash_contracts.py" in workflow
    assert "tests/test_unsupported_input_contracts.py" in workflow
    assert "tests/test_wellnessbox_profile_adapter_contract.py" in workflow
    assert "tests/test_inference_api.py" in workflow
    assert workflow.count('"tests/test_interim_safety.py"') == 2
    assert workflow.count("          tests/test_interim_safety.py") == 2
    assert "tests/test_event_idempotency_data_mutation.py" in workflow
    assert "scripts/run_event_idempotency_data_mutation_smoke.py" in workflow
    assert "python scripts/run_interaction_dose_aggregation_smoke.py" in workflow
    assert workflow.count('"scripts/run_interaction_dose_aggregation_smoke.py"') == 2
    assert (
        "python scripts/run_versioned_pro_scoring_baseline_percentile_smoke.py"
        in workflow
    )
    assert (
        workflow.count(
            '"scripts/run_versioned_pro_scoring_baseline_percentile_smoke.py"'
        )
        == 2
    )
    assert "tests/test_versioned_pro_instrument_scoring.py" in workflow
    assert workflow.count('"src/wellnessbox_rnd/metrics/calculators.py"') == 2
    assert (
        "python scripts/run_pro_followup_adherence_interpretation_smoke.py"
        in workflow
    )
    assert (
        workflow.count(
            '"scripts/run_pro_followup_adherence_interpretation_smoke.py"'
        )
        == 2
    )
    assert workflow.count('"src/wellnessbox_rnd/metrics/pro_followup.py"') == 2
    assert "tests/test_pro_followup_effects.py" in workflow
    assert "python scripts/run_pro_personal_group_uncertainty_smoke.py" in workflow
    assert (
        workflow.count('"scripts/run_pro_personal_group_uncertainty_smoke.py"')
        == 2
    )
    assert "python scripts/run_pro_correction_plan_lineage_smoke.py" in workflow
    assert workflow.count('"scripts/run_pro_correction_plan_lineage_smoke.py"') == 2
    assert workflow.count('"src/wellnessbox_rnd/metrics/pro_group_effects.py"') == 2
    assert workflow.count('"src/wellnessbox_rnd/metrics/statistics.py"') == 2
    assert "tests/test_pro_group_effects.py" in workflow
    assert "python scripts/run_counseling_fallback_frozen_api_e2e_smoke.py" in workflow
    assert (
        workflow.count('"scripts/run_counseling_fallback_frozen_api_e2e_smoke.py"')
        == 2
    )
    assert "a24b6c3308cc76627c3ca29807db1705e32c2178" in workflow
    assert "yeohj0710/wellnessbox" in workflow
    assert "WELLNESSBOX_EVIDENCE_ROOT" in workflow
    assert "637e5c1d67d2569709bd7c7dd4d65b04b314ad97" in workflow
    assert "_evidence/wellnessbox-op110" in workflow
    assert "python scripts/run_order_plan_context_integration_smoke.py" in workflow
    assert workflow.count(
        '"data/samples/api_recommend_diet_lifestyle_lab_request_v1.json"'
    ) == 2
    assert workflow.count(
        '"data/samples/api_recommend_consent_hash_request_v1.json"'
    ) == 2
    assert 'python -m pip install -e ".[dev,interim]"' in workflow
    assert workflow.count('"data/rules/safety_rules.json"') == 2
    assert workflow.count('"src/wellnessbox_rnd/safety/**"') == 2
