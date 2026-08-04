from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from scripts import import_kpi_second_replacement_response as importer

SOURCE = importer.SECOND_DIR / importer.RETURN_ZIP_NAME


def _package(path: Path, *, mutate=None) -> Path:
    with zipfile.ZipFile(SOURCE) as source:
        response = json.loads(source.read(importer.RESPONSE_NAME))
        identity = source.read(importer.IDENTITY_NAME)
    if mutate is not None:
        mutate(response)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            importer.RESPONSE_NAME,
            json.dumps(response, ensure_ascii=False),
        )
        archive.writestr(importer.IDENTITY_NAME, identity)
    return path


def test_validate_return_accepts_complete_blind_anthropic_response() -> None:
    staging, snapshots = importer.validate_return(SOURCE)

    assert staging["status"] == "READY_FOR_FINAL_REVIEW_PACKAGE"
    assert staging["source_zip_sha256"] == (
        "0cdd0ec7d8507ab9cd91be12ad0564a19a91d379be82add232a8bebeaa2e6b86"
    )
    assert staging["validated_record"]["reviewing_agent"] == "claude-opus-5"
    assert staging["validated_record"]["reviewing_agent_family"] == "anthropic"
    assert staging["validated_record"]["drafting_agent_family"] == "openai"
    assert staging["review_plan"]["required_detail_ids"] == [
        "kpi1-repl2-001",
        "kpi1-repl2-002",
    ]
    assert set(snapshots) == {
        importer.RETURN_ZIP_NAME,
        importer.RESPONSE_NAME,
        importer.IDENTITY_NAME,
    }


def test_validate_return_rejects_wrong_model(tmp_path: Path) -> None:
    def mutate(response: dict) -> None:
        response["reviewing_agent"] = "gpt-5.6-pro"

    with pytest.raises(ValueError, match="replacement_response_agent_invalid"):
        importer.validate_return(_package(tmp_path / "wrong-model.zip", mutate=mutate))


def test_validate_return_rejects_engine_consultation(tmp_path: Path) -> None:
    def mutate(response: dict) -> None:
        response["engine_output_consulted"] = True

    with pytest.raises(ValueError, match="ai_review_consulted_engine_output"):
        importer.validate_return(_package(tmp_path / "engine.zip", mutate=mutate))


def test_validate_return_rejects_changed_case_set(tmp_path: Path) -> None:
    def mutate(response: dict) -> None:
        response["cases"].pop()

    with pytest.raises(ValueError, match="ai_review_case_set_mismatch"):
        importer.validate_return(_package(tmp_path / "missing.zip", mutate=mutate))


def test_validate_return_rejects_answer_outside_vocabulary(tmp_path: Path) -> None:
    def mutate(response: dict) -> None:
        response["cases"][0]["proposed_answer"] = ["not_in_vocabulary"]

    with pytest.raises(ValueError, match="ai_review_answer_outside_vocabulary"):
        importer.validate_return(_package(tmp_path / "outside.zip", mutate=mutate))
