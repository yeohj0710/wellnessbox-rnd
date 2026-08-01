from __future__ import annotations

from wellnessbox_rnd.evals.adaptive_answer_key_review import (
    build_adaptive_review_plan,
    register_independent_ai_review,
)
from wellnessbox_rnd.evals.answer_key_workbench import (
    CaseDraft,
    Decision,
    Workbench,
)


def _workbench(case_count: int = 100) -> Workbench:
    return Workbench(
        "KPI-1",
        [
            CaseDraft(
                case_id=f"case-{index:03}",
                prompt=f"상황 {index}",
                draft_answer=[f"answer-{index % 7}"],
                draft_source="independent_reference",
                drafting_agent="codex",
                blinded_from=["engine/policy.json"],
            )
            for index in range(case_count)
        ],
    )


def _reviews(workbench: Workbench) -> list[dict]:
    return [
        {
            "case_id": draft.case_id,
            "proposed_answer": list(draft.draft_answer),
            "confidence": 0.95,
            "flags": [],
        }
        for draft in workbench.drafts
    ]


def _register(workbench: Workbench, cases: list[dict] | None = None) -> None:
    register_independent_ai_review(
        workbench,
        reviewing_agent="claude",
        blinded_from=["engine/policy.json"],
        cases=cases or _reviews(workbench),
    )


def test_all_agreements_require_only_five_detailed_reviews() -> None:
    workbench = _workbench()
    _register(workbench)

    plan = build_adaptive_review_plan(workbench)

    assert plan["status"] == "REVIEW_REQUIRED"
    assert plan["agreement_count"] == 100
    assert plan["disagreement_count"] == 0
    assert plan["sample_target_count"] == 5
    assert len(plan["required_detail_ids"]) == 5


def test_every_disagreement_and_flag_is_required() -> None:
    workbench = _workbench()
    reviews = _reviews(workbench)
    reviews[0]["proposed_answer"] = ["different"]
    reviews[1]["flags"] = ["clinical_uncertainty"]
    _register(workbench, reviews)

    plan = build_adaptive_review_plan(workbench)

    assert reviews[0]["case_id"] in plan["required_detail_ids"]
    assert reviews[1]["case_id"] in plan["required_detail_ids"]
    assert plan["disagreement_count"] == 1
    assert plan["flagged_count"] == 1


def test_one_sample_correction_expands_to_twenty() -> None:
    workbench = _workbench()
    _register(workbench)
    initial = build_adaptive_review_plan(workbench)
    corrected_id = initial["sampled_agreement_ids"][0]
    workbench.decisions[corrected_id] = Decision(
        case_id=corrected_id,
        action="edited",
        final_answer=["corrected"],
        decided_by="여형준",
        decided_at="2026-08-01T01:00:00Z",
    )

    expanded = build_adaptive_review_plan(workbench)

    assert expanded["sample_correction_count"] == 1
    assert expanded["sample_target_count"] == 20
    assert len(expanded["sampled_agreement_ids"]) == 20


def test_two_sample_corrections_require_every_agreement() -> None:
    workbench = _workbench()
    _register(workbench)
    initial = build_adaptive_review_plan(workbench)
    for case_id in initial["sampled_agreement_ids"][:2]:
        workbench.decisions[case_id] = Decision(
            case_id=case_id,
            action="edited",
            final_answer=["corrected"],
            decided_by="여형준",
            decided_at="2026-08-01T01:00:00Z",
        )

    expanded = build_adaptive_review_plan(workbench)

    assert expanded["sample_correction_count"] == 2
    assert expanded["escalation"] == "full_agreement_review"
    assert len(expanded["required_detail_ids"]) == 100


def test_same_provider_family_cannot_review_its_own_draft() -> None:
    workbench = _workbench()

    try:
        register_independent_ai_review(
            workbench,
            reviewing_agent="OpenAI GPT-5",
            blinded_from=["engine/policy.json"],
            cases=_reviews(workbench),
        )
    except ValueError as exc:
        assert str(exc) == "ai_review_agent_matches_drafting_agent_family"
    else:
        raise AssertionError("same-family review was accepted")
