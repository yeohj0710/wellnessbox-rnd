from __future__ import annotations

import hashlib
import zipfile

from scripts import build_kpi_second_replacement_handoff as builder
from scripts.build_kpi_replacement_handoff import build_candidates


def test_second_replacement_cases_are_new_and_blinded() -> None:
    candidates, request = builder.build_candidates_and_request()
    first_prompts = {
        draft.prompt for draft in build_candidates()["KPI-1"]
    }

    assert candidates["count"] == 2
    assert candidates["replaces_rejected_case_ids"] == [
        "kpi1-repl-022",
        "kpi1-repl-027",
    ]
    assert [case["case_id"] for case in candidates["cases"]] == [
        "kpi1-repl2-001",
        "kpi1-repl2-002",
    ]
    assert not first_prompts.intersection(
        case["prompt"] for case in candidates["cases"]
    )
    assert request["requested_role"] == "review"
    assert request["required_provider_family"] == "anthropic"
    assert request["blindness_contract"]["allowed_model_ids"] == [
        "claude-opus-5"
    ]
    assert request["packet"]["case_count"] == 2


def test_second_replacement_package_is_deterministic() -> None:
    assert builder.main() == 0
    first_hash = hashlib.sha256(builder.PACKAGE_PATH.read_bytes()).hexdigest()
    assert builder.main() == 0
    assert hashlib.sha256(builder.PACKAGE_PATH.read_bytes()).hexdigest() == first_hash
    with zipfile.ZipFile(builder.PACKAGE_PATH) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {
            "kpi1_second_replacement_candidates_v1.json",
            "kpi1_anthropic_review_request.json",
            "reviewer_identity_selection.json",
            "START_HERE.txt",
            "MAKE_RETURN_ZIP.cmd",
        }
