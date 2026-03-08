from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest


def test_ranking_prefers_sleep_stress_candidates_in_deterministic_order() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["stress_support", "sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.5,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 1,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": True,
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

    assert [item.ingredient_key for item in response.recommendations] == [
        "magnesium_glycinate",
        "l_theanine",
    ]


def test_missing_info_handling_collects_follow_up_questions() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 36,
                "biological_sex": "male",
                "pregnant": False,
            },
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

    assert response.next_action.value == "collect_more_input"
    assert len(response.follow_up_questions) >= 2
    assert any(item.code == "missing_sleep_hours" for item in response.missing_information)


def test_explanation_format_contains_guardrail_language() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 29,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["immunity_support"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.5,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 1,
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

    assert response.decision_summary.headline == "deterministic baseline result"
    assert "not a medical diagnosis" in response.recommendations[0].rationale
    assert response.recommendations[0].score_breakdown.total > 0
