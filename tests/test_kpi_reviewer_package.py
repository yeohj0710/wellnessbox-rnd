from __future__ import annotations

import re

from scripts import build_kpi_reviewer_package as package
from wellnessbox_rnd.evals.answer_key_workbench import CaseDraft, Workbench


def test_csv_bytes_has_excel_utf8_bom_and_blank_decision_columns() -> None:
    row = {field: "" for field in package.CSV_FIELDS}
    row.update({"case_id": "case-1", "prompt": "상황", "안_A": "a", "안_B": "b"})

    content = package._csv_bytes([row])

    assert content.startswith(b"\xef\xbb\xbf")
    text = content.decode("utf-8-sig")
    assert "검토_선택,최종_답,검토_메모" in text
    assert "case-1,상황,a" in text


def test_build_rows_includes_only_required_cases(monkeypatch) -> None:
    workbench = Workbench(
        indicator_id="KPI-1",
        drafts=[
            CaseDraft("case-1", "상황 1", ["a"], "source", "근거 A", "codex"),
            CaseDraft("case-2", "상황 2", ["b"], "source", "근거 B", "codex"),
        ],
        decisions={},
        ai_review={
            "reviewing_agent": "claude-opus-5",
            "cases": {
                "case-1": {
                    "proposed_answer": ["b"],
                    "confidence": 0.9,
                    "flags": ["check"],
                    "rationale": "근거 C",
                },
                "case-2": {
                    "proposed_answer": ["b"],
                    "confidence": 0.9,
                    "flags": [],
                    "rationale": "근거 D",
                },
            },
        },
    )
    monkeypatch.setattr(package, "load_workbench", lambda _: workbench)
    monkeypatch.setattr(
        package,
        "build_adaptive_review_plan",
        lambda _: {
            "status": "REVIEW_REQUIRED",
            "case_count": 2,
            "agreement_count": 1,
            "disagreement_count": 1,
            "flagged_count": 1,
            "required_detail_ids": ["case-1"],
        },
    )

    rows, summary = package.build_rows("KPI-1")

    assert [row["case_id"] for row in rows] == ["case-1"]
    assert rows[0]["안_A"] == "a"
    assert rows[0]["안_B"] == "b"
    assert summary["required_review_count"] == 1


def test_instructions_separate_completed_preparation_from_review_work() -> None:
    text = package._instructions_bytes().decode("utf-8")

    assert "안 A와 안 B가 준비돼 있습니다" in text
    assert "추가 외부 작성 작업은 없습니다" in text
    assert "Claude" not in text
    assert "AI" not in text
    assert "SUMMARY.json" not in text
    assert "작성 대상 6개" in text
    assert "kpi_completed_review.zip 하나만 반환" in text


def test_return_zip_script_contains_only_the_six_editable_files() -> None:
    text = package._return_zip_script_bytes().decode("utf-8")
    listed = re.search(r"\$files=@\((.*?)\);", text)

    assert listed is not None
    assert tuple(re.findall(r"'([^']+)'", listed.group(1))) == package.EDITABLE_FILES
    assert "kpi_completed_review.zip" in text
