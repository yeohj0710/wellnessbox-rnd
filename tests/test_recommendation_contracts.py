import json
from pathlib import Path

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas import (
    build_recommendation_set_contract_v1,
    summarize_recommendation_set_contract_v1,
    validate_recommendation_set_contract_v1,
)
from wellnessbox_rnd.schemas.recommendation import RecommendationGoal, RecommendationRequest


def test_recommendation_set_contract_validates_start_plan_fixture() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)

    contract = build_recommendation_set_contract_v1(request, response)

    assert validate_recommendation_set_contract_v1(contract) == []
    assert [item.ingredient_key for item in contract.selected_recommendations] == [
        "magnesium_glycinate",
        "l_theanine",
    ]


def test_recommendation_set_contract_flags_duplicate_and_limit_overflow() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    duplicate_item = contract.selected_recommendations[0]
    mutated = contract.model_copy(
        update={
            "selection_limit": 1,
            "selected_recommendations": contract.selected_recommendations
            + [duplicate_item],
        }
    )

    issues = validate_recommendation_set_contract_v1(mutated)

    assert "selection_limit_exceeded" in issues
    assert "duplicate_selected_ingredient_keys" in issues


def test_recommendation_set_contract_flags_score_total_and_goal_mismatch() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    broken_item = contract.selected_recommendations[0].model_copy(
        update={
            "expected_support_goals": [RecommendationGoal.GENERAL_WELLNESS],
            "score_breakdown": contract.selected_recommendations[0].score_breakdown.model_copy(
                update={"total": contract.selected_recommendations[0].score_breakdown.total + 1.0}
            ),
        }
    )
    mutated = contract.model_copy(
        update={
            "selected_recommendations": [
                broken_item,
                contract.selected_recommendations[1],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(mutated)

    assert any(issue.startswith("score_total_mismatch::magnesium_glycinate") for issue in issues)
    assert any(
        issue.startswith("candidate_goal_outside_request::magnesium_glycinate")
        for issue in issues
    )


def test_recommendation_set_contract_flags_reason_score_and_rule_mismatch() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    original = contract.selected_recommendations[0]
    broken_terms = [
        term.model_copy(update={"points": term.points + 1.0})
        if term.term == "goal_alignment"
        else term
        for term in original.reason_breakdown.score_terms
    ]
    broken_reason = original.reason_breakdown.model_copy(
        update={
            "score_terms": broken_terms,
            "score_total": original.reason_breakdown.score_total + 1.0,
            "rule_ids": [],
        }
    )
    broken_item = original.model_copy(update={"reason_breakdown": broken_reason})
    mutated = contract.model_copy(
        update={
            "selected_recommendations": [
                broken_item,
                contract.selected_recommendations[1],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(mutated)

    assert "reason_score_total_mismatch::magnesium_glycinate" in issues
    assert (
        "reason_score_term_mismatch::magnesium_glycinate::goal_alignment" in issues
    )
    assert any(
        issue.startswith("reason_missing_candidate_rule_refs::magnesium_glycinate")
        for issue in issues
    )


def test_recommendation_set_contract_rejects_forged_evidence_ownership() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 41,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
        }
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    original = contract.selected_recommendations[0]
    reason_payload = original.reason_breakdown.model_dump(mode="json")
    goal_link = next(
        link
        for link in reason_payload["evidence_links"]
        if link["evidence_source"] == "goal_prior"
    )
    goal_link["reference_ids"].append("REF-FAKE-001")
    goal_link["claim_ids"].append("CLM-FAKE-001")
    reason_payload["reference_ids"].append("REF-FAKE-001")
    reason_payload["claim_ids"].append("CLM-FAKE-001")
    forged_reason = original.reason_breakdown.model_validate(reason_payload)
    forged_item = original.model_copy(update={"reason_breakdown": forged_reason})
    forged_contract = contract.model_copy(
        update={
            "selected_recommendations": [
                forged_item,
                *contract.selected_recommendations[1:],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(forged_contract)

    assert (
        f"reason_goal_prior_evidence_mismatch::{original.ingredient_key}" in issues
    )


def test_recommendation_set_contract_rejects_unmarked_learned_bonus() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    original = contract.selected_recommendations[0]
    updated_breakdown = original.score_breakdown.model_copy(
        update={
            "learned_effect_bonus": 1.0,
            "total": original.score_breakdown.total + 1.0,
        }
    )
    updated_terms = [
        term.model_copy(update={"points": 1.0})
        if term.term == "learned_effect_bonus"
        else term
        for term in original.reason_breakdown.score_terms
    ]
    updated_reason = original.reason_breakdown.model_copy(
        update={
            "score_terms": updated_terms,
            "score_total": original.reason_breakdown.score_total + 1.0,
        }
    )
    forged_item = original.model_copy(
        update={
            "score_breakdown": updated_breakdown,
            "reason_breakdown": updated_reason,
            "additive_component_total": original.additive_component_total + 1.0,
        }
    )
    forged_contract = contract.model_copy(
        update={
            "selected_recommendations": [
                forged_item,
                *contract.selected_recommendations[1:],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(forged_contract)

    assert f"learned_bonus_rule_marker_mismatch::{original.ingredient_key}" in issues


def test_recommendation_set_contract_accepts_marked_zero_learned_bonus() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    original = contract.selected_recommendations[0]
    reason_payload = original.reason_breakdown.model_dump(mode="json")
    reason_payload["rule_ids"].append("OPT-LEARNED-001")
    learned_term = next(
        term
        for term in reason_payload["score_terms"]
        if term["term"] == "learned_effect_bonus"
    )
    learned_term["rule_ids"] = ["OPT-LEARNED-001"]
    marked_reason = original.reason_breakdown.model_validate(reason_payload)
    marked_item = original.model_copy(
        update={
            "rule_refs": [*original.rule_refs, "OPT-LEARNED-001"],
            "reason_breakdown": marked_reason,
        }
    )
    marked_contract = contract.model_copy(
        update={
            "selected_recommendations": [
                marked_item,
                *contract.selected_recommendations[1:],
            ]
        }
    )

    assert validate_recommendation_set_contract_v1(marked_contract) == []


def test_recommendation_set_contract_rejects_component_signal_sum_mismatch() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 41,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
        }
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    original = contract.selected_recommendations[0]
    updated_breakdown = original.score_breakdown.model_copy(
        update={
            "symptom_alignment": original.score_breakdown.symptom_alignment + 1.0,
            "total": original.score_breakdown.total + 1.0,
        }
    )
    updated_terms = [
        term.model_copy(update={"points": term.points + 1.0})
        if term.term == "symptom_alignment"
        else term
        for term in original.reason_breakdown.score_terms
    ]
    updated_reason = original.reason_breakdown.model_copy(
        update={
            "score_terms": updated_terms,
            "score_total": original.reason_breakdown.score_total + 1.0,
        }
    )
    forged_item = original.model_copy(
        update={
            "score_breakdown": updated_breakdown,
            "reason_breakdown": updated_reason,
            "additive_component_total": original.additive_component_total + 1.0,
        }
    )
    forged_contract = contract.model_copy(
        update={
            "selected_recommendations": [
                forged_item,
                *contract.selected_recommendations[1:],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(forged_contract)

    assert (
        f"score_signal_component_mismatch::{original.ingredient_key}::symptom"
        in issues
    )


def test_recommendation_set_contract_summary_reports_connection_map() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)

    report = summarize_recommendation_set_contract_v1(contract)

    assert report["issue_count"] == 0
    assert "optimization" in report["connection_map"]
    assert "selected_recommendations.rule_refs" in report["connection_map"]["optimization"]
