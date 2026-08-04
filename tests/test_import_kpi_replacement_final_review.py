from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from scripts import import_kpi_replacement_final_review as importer
from scripts.build_kpi_replacement_final_review_package import (
    CSV_FIELDS,
    IDENTITY_NAME,
    REVIEW_CSV_NAME,
    build_rows,
)


def _package(path: Path, *, mutate=None) -> Path:
    rows, _ = build_rows()
    for index, row in enumerate(rows):
        row["결정"] = "ACCEPT"
        row["시작_시각"] = f"2026-08-04T10:{index // 6:02}:{(index % 6) * 10:02}+09:00"
        row["종료_시각"] = f"2026-08-04T10:{index // 6:02}:{(index % 6) * 10 + 2:02}+09:00"
    if mutate is not None:
        mutate(rows)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    identity = (
        importer.STAGING_PATH.parent / "responses" / IDENTITY_NAME
    ).read_bytes()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(REVIEW_CSV_NAME, "\ufeff" + stream.getvalue())
        archive.writestr(IDENTITY_NAME, identity)
    return path


def test_validate_return_preserves_rejects_and_edits(tmp_path: Path) -> None:
    def mutate(rows: list[dict[str, str]]) -> None:
        rows[0]["결정"] = "EDIT"
        rows[0]["수정_정답"] = rows[0]["권고_정답"].split("|")[0]
        rows[1]["결정"] = "REJECT"

    result, snapshots = importer.validate_return(
        _package(tmp_path / "completed.zip", mutate=mutate)
    )

    assert result["decision_counts"] == {"ACCEPT": 63, "EDIT": 1, "REJECT": 1}
    assert result["replacement_required_case_ids"] == ["kpi1-repl-002"]
    assert result["status"] == "IMPORTED_ADDITIONAL_REPLACEMENTS_REQUIRED"
    assert set(snapshots) == {
        importer.SOURCE_ZIP_NAME,
        REVIEW_CSV_NAME,
        IDENTITY_NAME,
    }


def test_validate_return_rejects_changed_source_field(tmp_path: Path) -> None:
    def mutate(rows: list[dict[str, str]]) -> None:
        rows[0]["prompt"] += " changed"

    with pytest.raises(ValueError, match="source_field_changed"):
        importer.validate_return(_package(tmp_path / "changed.zip", mutate=mutate))


def test_validate_return_rejects_overlapping_intervals(tmp_path: Path) -> None:
    def mutate(rows: list[dict[str, str]]) -> None:
        rows[1]["시작_시각"] = rows[0]["시작_시각"]
        rows[1]["종료_시각"] = rows[0]["종료_시각"]

    with pytest.raises(ValueError, match="intervals_overlap"):
        importer.validate_return(_package(tmp_path / "overlap.zip", mutate=mutate))


def test_validate_return_rejects_edit_outside_vocabulary(tmp_path: Path) -> None:
    def mutate(rows: list[dict[str, str]]) -> None:
        rows[0]["결정"] = "EDIT"
        rows[0]["수정_정답"] = "not_in_vocabulary"

    with pytest.raises(ValueError, match="answer_outside_vocabulary"):
        importer.validate_return(_package(tmp_path / "outside.zip", mutate=mutate))


def test_validate_return_requires_matching_identity(tmp_path: Path) -> None:
    source = _package(tmp_path / "identity.zip")
    replacement = tmp_path / "changed.zip"
    with zipfile.ZipFile(source) as archive, zipfile.ZipFile(replacement, "w") as out:
        out.writestr(REVIEW_CSV_NAME, archive.read(REVIEW_CSV_NAME))
        identity = json.loads(archive.read(IDENTITY_NAME))
        identity["selected_reviewer_identity_ref"] = "registry:op039:sha256:bad"
        out.writestr(IDENTITY_NAME, json.dumps(identity))
    with pytest.raises(ValueError, match="identity_selection_not_registered"):
        importer.validate_return(replacement)
