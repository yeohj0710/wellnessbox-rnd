from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from scripts import build_kpi_original_review_identity_linkage_package as builder
from scripts import import_kpi_original_review_identity_linkage as importer


def _return_zip(path: Path, *, status: str = "CONFIRMED") -> Path:
    form = builder.build_form()
    form["identity_link_status"] = status
    form["confirmed_at"] = "2026-08-04T17:00:00+09:00"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            builder.FORM_NAME,
            json.dumps(form, ensure_ascii=False),
        )
    return path


def test_form_covers_all_remaining_original_decisions() -> None:
    form = builder.build_form()

    assert form["indicator_counts"] == {
        "KPI-1": 51,
        "KPI-3": 100,
        "KPI-4": 93,
        "KPI-5": 91,
    }
    assert form["total_decision_count"] == 335
    assert form["identity_link_status"] == ""
    assert form["confirmed_at"] == ""


def test_package_contains_one_editable_form_and_helpers() -> None:
    assert builder.main() == 0

    with zipfile.ZipFile(builder.PACKAGE_PATH) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {
            builder.FORM_NAME,
            "SUMMARY.json",
            "START_HERE.txt",
            "MAKE_RETURN_ZIP.cmd",
        }


def test_validate_return_accepts_one_confirmation(tmp_path: Path) -> None:
    result, _ = importer.validate_return(_return_zip(tmp_path / "completed.zip"))

    assert result["status"] == "READY_TO_APPLY"
    assert result["total_decision_count"] == 335
    assert result["qualification_stage"] == (
        "pharmacist_candidate_preliminary_safety_review"
    )


def test_validate_return_rejects_nonconfirmation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="identity_link_not_confirmed"):
        importer.validate_return(
            _return_zip(tmp_path / "not-confirmed.zip", status="NOT_CONFIRMED")
        )


def test_validate_return_rejects_immutable_change(tmp_path: Path) -> None:
    path = _return_zip(tmp_path / "changed.zip")
    with zipfile.ZipFile(path) as archive:
        form = json.loads(archive.read(builder.FORM_NAME))
    form["total_decision_count"] = 334
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(builder.FORM_NAME, json.dumps(form, ensure_ascii=False))

    with pytest.raises(ValueError, match="identity_link_immutable_field_changed"):
        importer.validate_return(path)


def test_link_changes_only_identity_fields_and_adds_provenance(tmp_path: Path) -> None:
    result, _ = importer.validate_return(_return_zip(tmp_path / "completed.zip"))
    linked = importer._linked_workbenches(result)

    for indicator_id, workbench in linked.items():
        original = builder.load_workbench(
            builder._workbench_path(builder.ROOT, indicator_id)
        )
        changed = 0
        for case_id, before in original.decisions.items():
            after = workbench.decisions[case_id]
            before_payload = vars(before).copy()
            after_payload = vars(after).copy()
            before_name = before_payload.pop("decided_by")
            before_ref = before_payload.pop("reviewer_identity_ref")
            after_payload.pop("decided_by")
            after_payload.pop("reviewer_identity_ref")
            assert after_payload == before_payload
            if before_name == builder.ANONYMOUS_REVIEWER and not before_ref:
                changed += 1
                assert after.decided_by == result["registered_name"]
                assert after.reviewer_identity_ref == result["reviewer_identity_ref"]
        assert changed == builder.EXPECTED_COUNTS[indicator_id]
        assert workbench.identity_linkages[-1]["decision_scope_sha256"] == (
            result["decision_scope_sha256"]
        )
