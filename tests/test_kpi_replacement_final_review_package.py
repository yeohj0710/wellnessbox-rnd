from __future__ import annotations

import json
import zipfile

from scripts import build_kpi_replacement_final_review_package as builder


def test_review_rows_cover_the_minimum_required_set_with_recommendations() -> None:
    rows, summary = builder.build_rows()

    assert len(rows) == 65
    assert summary["total_case_count"] == 65
    assert summary["required_review_count"] == 65
    assert summary["supporting_option_c_not_independent_review_evidence"] is True
    assert {row["indicator_id"] for row in rows} == {"KPI-1", "KPI-4", "KPI-5"}
    assert len({row["case_id"] for row in rows}) == 65
    assert all(row["권고_선택"] in {"A", "B", "C"} for row in rows)
    assert all(row["권고_정답"] for row in rows)
    assert all(not row["결정"] for row in rows)
    assert all(not row["수정_정답"] for row in rows)


def test_recommendation_is_one_of_the_visible_reference_answers() -> None:
    rows, _ = builder.build_rows()

    for row in rows:
        source = {
            "A": row["참조안_A"],
            "B": row["참조안_B"],
            "C": row["보조안_C"],
        }[row["권고_선택"]]
        assert source
        assert row["권고_정답"] == source


def test_generated_package_contains_only_review_files() -> None:
    assert builder.main() == 0
    with zipfile.ZipFile(builder.FINAL_REVIEW_ZIP) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {
            builder.REVIEW_CSV_NAME,
            builder.IDENTITY_NAME,
            "START_HERE.txt",
            "MAKE_RETURN_ZIP.cmd",
            "SUMMARY.json",
        }
        summary = json.loads(archive.read("SUMMARY.json"))
        identity = json.loads(archive.read(builder.IDENTITY_NAME))
    assert summary["required_review_count"] == 65
    assert identity["selected_reviewer_identity_ref"]
    assert identity["confirmed_at"]
