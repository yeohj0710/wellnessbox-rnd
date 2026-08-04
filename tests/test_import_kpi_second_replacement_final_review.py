from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import pytest

from scripts import import_kpi_second_replacement_final_review as importer

SOURCE = importer.COMPLETED_DIR / importer.RETURN_ZIP_NAME


def _package(path: Path, *, mutate) -> Path:
    with zipfile.ZipFile(SOURCE) as source:
        rows = list(
            csv.DictReader(
                io.StringIO(source.read(importer.REVIEW_CSV_NAME).decode("utf-8-sig"))
            )
        )
        identity = source.read(importer.IDENTITY_NAME)
    mutate(rows)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=importer.CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(importer.REVIEW_CSV_NAME, output.getvalue().encode("utf-8-sig"))
        archive.writestr(importer.IDENTITY_NAME, identity)
    return path


def test_validate_return_accepts_two_completed_decisions() -> None:
    result, snapshots = importer.validate_return(SOURCE)

    assert result["status"] == "READY_TO_APPLY_ALL_REPLACEMENTS"
    assert result["source_zip_sha256"] == (
        "c825822ebf43d6583f0b16c631985dfab7cd5e578fef94ff4b9e304f3f13521a"
    )
    assert result["decision_counts"] == {"ACCEPT": 1, "EDIT": 1, "REJECT": 0}
    assert result["replacement_required_count"] == 0
    assert set(snapshots) == {
        importer.RETURN_ZIP_NAME,
        importer.REVIEW_CSV_NAME,
        importer.IDENTITY_NAME,
    }


def test_validate_return_rejects_changed_source_field(tmp_path: Path) -> None:
    def mutate(rows: list[dict[str, str]]) -> None:
        rows[0]["prompt"] += " changed"

    with pytest.raises(ValueError, match="second_final_source_field_changed"):
        importer.validate_return(_package(tmp_path / "changed.zip", mutate=mutate))


def test_validate_return_rejects_answer_outside_vocabulary(tmp_path: Path) -> None:
    def mutate(rows: list[dict[str, str]]) -> None:
        rows[0][importer.CSV_FIELDS[19]] = "not_in_vocabulary"

    with pytest.raises(ValueError, match="second_final_answer_outside_vocabulary"):
        importer.validate_return(_package(tmp_path / "outside.zip", mutate=mutate))


def test_validate_return_rejects_overlapping_intervals(tmp_path: Path) -> None:
    def mutate(rows: list[dict[str, str]]) -> None:
        rows[1][importer.CSV_FIELDS[21]] = rows[0][importer.CSV_FIELDS[21]]

    with pytest.raises(ValueError, match="second_final_intervals_overlap"):
        importer.validate_return(_package(tmp_path / "overlap.zip", mutate=mutate))
