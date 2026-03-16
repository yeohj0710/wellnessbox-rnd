import json
from pathlib import Path

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas import (
    build_next_action_workflow_event_v1,
    summarize_next_action_workflow_contract_v1,
    validate_next_action_workflow_event_v1,
)
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest


def _load_request(filename: str) -> RecommendationRequest:
    return RecommendationRequest.model_validate(
        json.loads((Path("data/samples") / filename).read_text(encoding="utf-8"))
    )


def test_next_action_workflow_contract_validates_start_plan_fixture() -> None:
    request = _load_request("api_recommend_start_plan_request_v1.json")
    response = recommend(request)

    event = build_next_action_workflow_event_v1(response)

    assert event.next_action.value == "start_plan"
    assert event.projected_workflow_state == "recommendation_ready"
    assert validate_next_action_workflow_event_v1(event) == []


def test_next_action_workflow_contract_validates_structured_safety_recheck_fixture() -> None:
    request = _load_request("api_recommend_structured_safety_block_request_v1.json")
    response = recommend(request)

    event = build_next_action_workflow_event_v1(response)

    assert event.next_action.value == "trigger_safety_recheck"
    assert event.projected_workflow_state == "safety_review"
    assert "SAFETY-DOSE-VITD3-001" in event.safety_rule_ids
    assert validate_next_action_workflow_event_v1(event) == []


def test_next_action_workflow_contract_flags_collect_more_input_without_missing_codes() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {"age": 36, "biological_sex": "male", "pregnant": False},
            "goals": ["sleep_support"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": None,
                "stress_level": 4,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        }
    )
    response = recommend(request)
    event = build_next_action_workflow_event_v1(response).model_copy(
        update={"missing_information_codes": []}
    )

    issues = validate_next_action_workflow_event_v1(event)

    assert "collect_more_input_requires_missing_information" in issues


def test_next_action_workflow_contract_summary_keeps_state_machine_connection() -> None:
    request = _load_request("api_recommend_start_plan_request_v1.json")
    response = recommend(request)
    event = build_next_action_workflow_event_v1(response)

    report = summarize_next_action_workflow_contract_v1(event)

    assert report["issue_count"] == 0
    assert report["connection_map"]["follow_up_state_machine"] == [
        "next_action",
        "projected_workflow_state",
        "reason_code",
    ]
