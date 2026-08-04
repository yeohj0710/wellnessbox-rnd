from __future__ import annotations

import hashlib
import json
import zipfile

from scripts import build_kpi_second_replacement_final_review_package as builder


def test_final_review_rows_cover_only_the_two_remaining_cases() -> None:
    rows, summary = builder.build_rows()

    assert [row["case_id"] for row in rows] == [
        "kpi1-repl2-001",
        "kpi1-repl2-002",
    ]
    assert summary["case_count"] == 2
    assert summary["required_review_count"] == 2
    assert summary["recommendation_counts"] == {"A": 0, "B": 2}
    assert all(row["권고_선택"] == "B" for row in rows)
    assert all(row["권고_정답"] == row["참조안_B"] for row in rows)
    assert all(not row["결정"] and not row["수정_정답"] for row in rows)
    assert all(not row["보조안_C"] for row in rows)


def test_final_review_package_is_deterministic_and_minimal() -> None:
    assert builder.main() == 0
    first_hash = hashlib.sha256(builder.PACKAGE_PATH.read_bytes()).hexdigest()
    assert builder.main() == 0
    assert hashlib.sha256(builder.PACKAGE_PATH.read_bytes()).hexdigest() == first_hash
    with zipfile.ZipFile(builder.PACKAGE_PATH) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {
            builder.REVIEW_CSV_NAME,
            builder.IDENTITY_NAME,
            "START_HERE.txt",
            "MAKE_RETURN_ZIP.cmd",
            "SUMMARY.json",
        }
        summary = json.loads(archive.read("SUMMARY.json"))
    assert summary["case_count"] == 2
