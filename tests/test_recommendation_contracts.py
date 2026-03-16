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
