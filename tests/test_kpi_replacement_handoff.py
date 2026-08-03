from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from scripts import build_kpi_replacement_handoff as builder
from scripts import import_kpi_replacement_responses as importer


def test_replacement_candidates_match_rejected_counts_and_are_new() -> None:
    candidates = builder.build_candidates()

    assert {key: len(value) for key, value in candidates.items()} == builder.COUNTS
    for indicator_id, drafts in candidates.items():
        current_prompts = {
            item.prompt for item in builder._workbench(indicator_id).drafts
        }
        prompts = [item.prompt for item in drafts]
        assert len(prompts) == len(set(prompts))
        assert not set(prompts) & current_prompts
        assert all(item.blinded_from for item in drafts)


def test_kpi1_replacements_do_not_pair_children_with_adult_ages() -> None:
    drafts = builder.build_candidates()["KPI-1"]
    base_keys = {
        re.search(
            r"^영역 (.+?) / 판정 「(.+?)」 /", draft.prompt
        ).groups()
        for draft in drafts
    }

    assert len(base_keys) == 49
    assert len({tuple(draft.draft_answer) for draft in drafts}) == 44

    for draft in drafts:
        if "어린이" not in draft.prompt:
            continue
        age = int(draft.prompt.split("나이 ", 1)[1].split(" /", 1)[0])
        assert age < 18


def test_external_requests_use_actual_replacement_counts() -> None:
    requests = builder.build_requests(builder.build_candidates())

    assert {
        key: value["packet"]["case_count"] for key, value in requests.items()
    } == builder.COUNTS
    for indicator_id, request in requests.items():
        count = builder.COUNTS[indicator_id]
        assert f"{count}개 사례" in request["instructions"][2]
        assert request["required_provider_family"] == "anthropic"
        assert request["requested_role"] == (
            "primary" if indicator_id == "KPI-4" else "review"
        )


def _response_for(request: dict) -> dict:
    response = request["response_skeleton"]
    agent_key = "drafting_agent" if request["requested_role"] == "primary" else "reviewing_agent"
    response[agent_key] = "claude-opus-5"
    vocabulary = request["packet"]["answer_vocabulary"]
    for item in response["cases"]:
        item["proposed_answer"] = [vocabulary[0]]
        item["confidence"] = 0.8
        item["rationale"] = "독립 판단"
    return response


def _completed_zip(tmp_path: Path, *, identity_ref: str | None = None) -> Path:
    requests = builder.build_requests(builder.build_candidates())
    selection = builder._identity_selection()
    selection["selected_reviewer_identity_ref"] = (
        identity_ref or selection["options"][1]["reviewer_identity_ref"]
    )
    selection["confirmed_at"] = "2026-08-03T18:00:00+09:00"
    source = tmp_path / "completed.zip"
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            importer.SELECTION_NAME,
            json.dumps(selection, ensure_ascii=False),
        )
        for indicator_id, request in requests.items():
            archive.writestr(
                builder.RESPONSE_NAMES[indicator_id],
                json.dumps(_response_for(request), ensure_ascii=False),
            )
    return source


def test_completed_replacement_zip_validates_without_writing(
    tmp_path: Path,
) -> None:
    source = _completed_zip(tmp_path)
    before = importer.STAGING_PATH.read_bytes() if importer.STAGING_PATH.is_file() else None

    staging, _ = importer.validate_return(source)

    assert staging["counts"] == builder.COUNTS
    assert staging["status"] == "READY_FOR_KPI4_SECOND_OPINION_AND_FINAL_REVIEW"
    after = importer.STAGING_PATH.read_bytes() if importer.STAGING_PATH.is_file() else None
    assert after == before


def test_unregistered_identity_reference_blocks_replacement_return(
    tmp_path: Path,
) -> None:
    source = _completed_zip(
        tmp_path,
        identity_ref="registry:op039:sha256:" + "0" * 64,
    )

    with pytest.raises(ValueError, match="identity_selection_not_registered"):
        importer.validate_return(source)


def test_generic_provider_name_is_not_an_actual_model() -> None:
    with pytest.raises(ValueError, match="replacement_response_agent_invalid"):
        importer._actual_anthropic_agent(
            {"reviewing_agent": "Claude"}, "reviewing_agent"
        )


def test_apply_stores_validated_staging_and_original_responses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _completed_zip(tmp_path)
    staging_path = tmp_path / "staging.json"
    response_dir = tmp_path / "responses"
    monkeypatch.setattr(importer, "STAGING_PATH", staging_path)
    monkeypatch.setattr(importer, "RESPONSE_DIR", response_dir)

    report = importer.apply_return(source)

    assert report["status"] == "READY_FOR_KPI4_SECOND_OPINION_AND_FINAL_REVIEW"
    assert staging_path.is_file()
    assert sorted(path.name for path in response_dir.iterdir()) == sorted(
        [importer.SELECTION_NAME, *builder.RESPONSE_NAMES.values()]
    )


def test_snapshot_zip_keeps_original_bytes_after_source_replacement(
    tmp_path: Path,
) -> None:
    source = tmp_path / "snapshot.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("value.txt", "original")
    reader = importer.SnapshotZip(source)
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("value.txt", "replacement")

    try:
        assert reader.read("value.txt") == b"original"
    finally:
        reader.close()
