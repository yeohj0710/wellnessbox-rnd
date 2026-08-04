from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import finalize_kpi_replacement_staging as finalizer


def test_build_attaches_openai_review_after_anthropic_primary() -> None:
    result = finalizer.build_finalized_staging()
    kpi4 = result["responses"]["KPI-4"]
    primary = kpi4["validated_record"]
    review = kpi4["openai_second_opinion"]["validated_record"]

    assert result["status"] == "READY_FOR_FINAL_REVIEW_PACKAGE"
    assert primary["drafting_agent_family"] == "anthropic"
    assert review["reviewing_agent_family"] == "openai"
    assert review["drafting_agent_family"] == "anthropic"
    assert review["case_count"] == 7
    assert review["role_conversion_provenance"] == {
        "source_zip_sha256": (
            "99ef845a5d2451889ecf2d16aa40de65263f38919d389d64337b418e560ff43d"
        ),
        "original_response_role": "primary",
        "original_agent_field": "drafting_agent",
        "original_source_field": "draft_source",
        "applied_response_role": "independent_ai_review",
        "conversion_reason": "blind_openai_response_registered_after_anthropic_primary",
        "source_submission_precedes_anthropic_primary_import": True,
        "content_regenerated_for_role_conversion": False,
        "registration_order_only": True,
        "original_provenance_preserved": True,
    }
    assert review["reviewed_at_semantics"] == (
        "role_registration_time_not_response_generation_time"
    )
    assert result["review_plans"]["KPI-4"]["case_count"] == 7


def test_apply_writes_only_after_success(tmp_path: Path) -> None:
    staging_path = tmp_path / "staging.json"
    staging_path.write_bytes(finalizer.STAGING_PATH.read_bytes())

    report = finalizer.apply_finalized_staging(staging_path)
    stored = json.loads(staging_path.read_text(encoding="utf-8"))

    assert report["status"] == "READY_FOR_FINAL_REVIEW_PACKAGE"
    assert stored["status"] == "READY_FOR_FINAL_REVIEW_PACKAGE"


def test_source_hash_mismatch_is_blocked(tmp_path: Path) -> None:
    report = json.loads(finalizer.OPENAI_INTAKE_REPORT.read_text(encoding="utf-8"))
    report["source_zip_sha256"] = "0" * 64
    report_path = tmp_path / "intake.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="openai_submission_zip_sha256_mismatch"):
        finalizer.build_finalized_staging(intake_report_path=report_path)
