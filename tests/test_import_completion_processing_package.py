from __future__ import annotations

import io
import json
import zipfile

from scripts.import_completion_processing_package import _wizard_checks, safe_member_name


def _wizard_archive(*, finished: bool, preserve_h003_no_go: bool = True) -> zipfile.ZipFile:
    progress = {
        "schema_version": "completion_wizard_progress_v1",
        "total_steps": 13,
        "finished_steps": 13 if finished else 3,
        "all_finished": finished,
        "steps": [
            {
                "step_id": f"STEP-{index}",
                "verdict": "done",
                "detail": "done",
            }
            for index in range(1, 14)
        ],
    }
    progress["steps"][3]["step_id"] = "H-003"
    progress["steps"][5]["step_id"] = "TRAIN"
    progress["steps"][6]["step_id"] = "PROMOTION"
    progress["steps"][5]["verdict"] = "skipped_gate_closed"
    progress["steps"][5]["detail"] = "TRAIN NO-GO preserved"
    if preserve_h003_no_go:
        progress["steps"][3]["verdict"] = "done"
        progress["steps"][3]["detail"] = "H-003 reviewed"
    else:
        progress["steps"][5]["verdict"] = "done"
        progress["steps"][5]["detail"] = "TRAIN reopened"
    if not finished:
        progress["steps"][0]["verdict"] = "todo"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "wellnessbox-rnd/artifacts/final_session/completion_wizard_progress_v1.json",
            json.dumps(progress),
        )
    buffer.seek(0)
    return zipfile.ZipFile(buffer)


def test_wizard_checks_require_all_steps_and_h003_no_go() -> None:
    with _wizard_archive(finished=True) as archive:
        assert _wizard_checks(archive=archive) == {"status": "READY", "problems": []}

    with _wizard_archive(finished=False) as archive:
        result = _wizard_checks(archive=archive)
        assert result["status"] == "REJECTED"
        assert "wizard_not_all_finished" in result["problems"]


def test_wizard_checks_reject_h003_gate_reopening() -> None:
    with _wizard_archive(finished=True, preserve_h003_no_go=False) as archive:
        result = _wizard_checks(archive=archive)
        assert result["status"] == "REJECTED"
        assert "training_no_go_gate_not_preserved" in result["problems"]


def test_archive_member_paths_cannot_escape() -> None:
    assert safe_member_name("wellnessbox-rnd/data/file.json")
    assert not safe_member_name("../outside.json")
    assert not safe_member_name("wellnessbox-rnd\\outside.json")
