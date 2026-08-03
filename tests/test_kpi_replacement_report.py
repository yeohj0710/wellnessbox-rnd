from __future__ import annotations

from scripts.build_kpi_replacement_report import build_report
from wellnessbox_rnd.evals.answer_key_workbench import (
    CaseDraft,
    Workbench,
    decide,
)


def _workbench(indicator_id: str, *, rejected: bool = False) -> Workbench:
    draft = CaseDraft(
        case_id=f"{indicator_id}-case-1",
        prompt="질문",
        draft_answer=["a"],
        draft_source="independent_source",
        drafting_agent="codex",
    )
    decision = decide(
        draft=draft,
        final_answer=None if rejected else ["a"],
        decided_by="검토자",
        decided_at="2026-08-03T12:00:00+09:00",
        note="교체 필요",
        review_duration_seconds=2.0,
    )
    return Workbench(
        indicator_id=indicator_id,
        drafts=[draft],
        decisions={draft.case_id: decision},
        ai_review={
            "cases": {
                draft.case_id: {"proposed_answer": ["b"]},
            }
        },
    )


def test_build_report_preserves_rejected_case_evidence() -> None:
    workbenches = {
        "KPI-1": _workbench("KPI-1", rejected=True),
        "KPI-3": _workbench("KPI-3"),
        "KPI-4": _workbench("KPI-4", rejected=True),
        "KPI-5": _workbench("KPI-5"),
    }

    report = build_report(workbenches, review_zip_sha256="abc")

    assert report["replacement_required_count"] == 2
    assert report["indicator_counts"] == {
        "KPI-1": 1,
        "KPI-3": 0,
        "KPI-4": 1,
        "KPI-5": 0,
    }
    assert report["seal_ready_indicators"] == ["KPI-3", "KPI-5"]
    rejected = report["indicators"][0]["rejected_cases"][0]
    assert rejected["case_id"] == "KPI-1-case-1"
    assert rejected["independent_opinion"] == ["b"]
    assert rejected["review_note"] == "교체 필요"
