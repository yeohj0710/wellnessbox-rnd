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
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_multiple_missing_items"
    )
    assert len(response.follow_up_questions) >= 2
    assert any(item.code == "missing_sleep_hours" for item in response.missing_information)
    assert response.missing_information[-1].code == "missing_current_supplements"


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
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert len(response.limitation_details) == 3
    assert "not a medical diagnosis" in response.recommendations[0].rationale
    assert response.recommendations[0].score_breakdown.total > 0


def test_conservative_review_prefers_lower_risk_goal_covering_candidates() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 31,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["general_wellness", "blood_glucose"],
            "symptoms": [],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": True,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "needs_review"
    assert response.next_action_rationale.reason_code == "needs_review_due_to_safety"
    assert any(item.evidence_type == "rule" for item in response.safety_evidence)
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber",
        "vitamin_d3",
    ]
    assert "omega3" not in [item.ingredient_key for item in response.recommendations]


def test_duplicate_overlap_adds_safety_rule_without_forcing_review() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 47,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [{"name": "lisinopril", "dose": "10mg"}],
            "current_supplements": [
                {"name": "Omega 3 Softgel", "ingredients": ["omega3"]}
            ],
            "lifestyle": {
                "sleep_hours": 6.0,
                "stress_level": 3,
                "activity_level": "sedentary",
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert "omega3" in response.safety_summary.excluded_ingredients
    assert "SAFETY-DUP-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert [item.ingredient_key for item in response.recommendations] == [
        "coq10",
        "vitamin_b_complex",
    ]


def test_catalog_alias_blocks_avoid_ingredient_by_canonical_key() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 47,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "lisinopril", "dose": "10mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.3,
                "stress_level": 2,
                "activity_level": "sedentary",
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
                "max_products": 1,
                "avoid_ingredients": ["omega-3"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.safety_summary.excluded_ingredients == ["omega3"]
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]


def test_catalog_alias_recognizes_current_supplement_name_without_ingredient_list() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 47,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [{"name": "lisinopril", "dose": "10mg"}],
            "current_supplements": [{"name": "Coenzyme Q10", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 6.2,
                "stress_level": 2,
                "activity_level": "sedentary",
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert "coq10" in response.safety_summary.excluded_ingredients
    assert "SAFETY-DUP-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_b_complex",
        "omega3",
    ]


def test_heart_context_missing_stays_collect_more_input_even_with_current_supplements() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 52,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Daily Multi", "ingredients": ["vitamin_c"]}
            ],
            "lifestyle": {
                "sleep_hours": 6.5,
                "stress_level": 2,
                "activity_level": "sedentary",
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

    assert response.next_action.value == "collect_more_input"
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_high_priority_missing_info"
    )
    assert response.missing_information[0].code == "missing_heart_context"
    assert response.missing_information[0].importance.value == "high"


def test_glucose_context_missing_stays_collect_more_input_even_with_current_supplements() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 40,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Fiber Powder", "ingredients": ["soluble_fiber"]}
            ],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 3,
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
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_high_priority_missing_info"
    )
    assert response.missing_information[0].code == "missing_glucose_context"
    assert response.missing_information[0].importance.value == "high"
