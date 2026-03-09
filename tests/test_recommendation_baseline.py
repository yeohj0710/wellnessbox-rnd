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


def test_genetic_context_is_explicit_when_multiple_missing_items_still_require_follow_up(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 37,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support", "stress_support"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": None,
                "stress_level": 3,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "collect_more_input"
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_multiple_missing_items"
    )
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "genetic context" in response.next_action_rationale.summary.lower()


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

    assert response.status.value == "ok"
    assert response.next_action.value == "collect_more_input"
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_multiple_missing_items"
    )
    assert any(item.evidence_type == "rule" for item in response.safety_evidence)
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber",
        "vitamin_d3",
    ]
    assert "omega3" not in [item.ingredient_key for item in response.recommendations]
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "cgm context" in response.decision_summary.summary.lower()


def test_pregnancy_renal_baseline_review_starts_with_explicit_glucose_detail() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 33,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["general_wellness", "blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
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
                "wearable": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber",
        "vitamin_d3",
    ]
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
    }


def test_pregnancy_renal_baseline_review_starts_with_unrelated_current_supplement() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["general_wellness", "blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [{"name": "Vitamin C", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber",
        "vitamin_d3",
    ]
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    }


def test_glucose_sleep_fallback_starts_with_explicit_post_meal_spike(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 41,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["blood_glucose", "sleep_support"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": None,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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
    assert (
        response.next_action_rationale.reason_code == "start_plan_glucose_sleep_fallback"
    )
    assert {item.ingredient_key for item in response.recommendations} == {
        "soluble_fiber",
        "magnesium_glycinate",
    }
    assert "post-meal spike" in response.next_action_rationale.summary.lower()


def test_glucose_sleep_fallback_starts_when_only_glucose_context_is_missing() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 42,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["blood_glucose", "sleep_support"],
            "symptoms": ["post_meal_spike_concern", "difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.9,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code == "start_plan_glucose_sleep_fallback"
    )
    assert {item.ingredient_key for item in response.recommendations} == {
        "soluble_fiber",
        "magnesium_glycinate",
    }


def test_pregnancy_renal_genetic_glucose_fallback_starts_with_soluble_fiber_only() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 32,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_renal_genetic_glucose_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
    }
    assert "genetic glycemic context" in response.next_action_rationale.summary.lower()


def test_pregnancy_renal_genetic_glucose_fallback_supports_low_budget_without_cgm() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 33,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_renal_genetic_glucose_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
    }


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


def test_duplicate_only_heart_context_missing_can_start_when_wearable_signal_is_clear() -> None:
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

    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_duplicate_heart_fallback"
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


def test_genetic_context_is_explicit_when_multimodal_fallback_allows_plan_start(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 52,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "energy_support"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.6,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_energy_fallback"
    )
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "genetic cardiometabolic context" in response.next_action_rationale.summary.lower()


def test_wearable_heart_fallback_can_start_when_activity_context_replaces_heart_follow_up() -> None:
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
            "current_supplements": [],
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_wearable_heart_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "coq10",
    ]
    assert "wearable activity context" in response.next_action_rationale.summary.lower()


def test_wearable_heart_fallback_can_start_with_genetic_context_when_rules_are_still_clear(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 49,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_wearable_heart_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "coq10",
    ]
    assert "genetic context" in response.decision_summary.summary.lower()


def test_duplicate_heart_fallback_can_start_when_only_duplicate_overlap_remains() -> None:
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_duplicate_heart_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "coq10",
    ]
    assert "duplicate filtering" in response.next_action_rationale.summary.lower()


def test_duplicate_heart_fallback_with_genetic_context() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 59,
                "biological_sex": "female",
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
                "sleep_hours": 6.9,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_duplicate_heart_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "coq10",
    ]
    assert "genetic context" in response.decision_summary.summary.lower()


def test_duplicate_heart_symptom_fallback_can_start_with_explicit_low_activity_only(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 57,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {
                    "name": "Nordic Naturals Ultimate Omega Lemon Flavor Soft Gels",
                    "ingredients": [],
                }
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_duplicate_heart_symptom_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert "duplicate filtering" in response.next_action_rationale.summary.lower()


def test_duplicate_heart_symptom_fallback_can_start_with_alias_overlap() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 55,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Omega-3 Fish Oil", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 6.6,
                "stress_level": 2,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_duplicate_heart_symptom_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]

def test_multimodal_heart_energy_fallback_can_start_when_wearable_and_genetic_contexts_are_clear(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 44,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "energy_support"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.7,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_energy_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "coq10",
        "omega3",
    ]
    assert "wearable activity context" in response.next_action_rationale.summary.lower()
    assert "genetic cardiometabolic context" in response.next_action_rationale.summary.lower()


def test_multimodal_heart_energy_fallback_allows_missing_primary_symptom_when_signals_are_clear(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 45,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "energy_support"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.8,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_energy_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "coq10",
        "omega3",
    ]
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "wearable context" in response.decision_summary.summary.lower()


def test_duplicate_heart_energy_fallback_can_start_when_only_duplicate_overlap_remains(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 49,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Qunol Ultra CoQ10 200 mg Ubiquinone Softgels", "ingredients": []}
            ],
            "lifestyle": {
                "sleep_hours": 6.0,
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
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_duplicate_heart_energy_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_b_complex",
        "omega3",
    ]
    assert "duplicate filtering" in response.next_action_rationale.summary.lower()


def test_duplicate_heart_energy_fallback_can_start_with_alias_overlap() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 53,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["heart_health", "energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Coenzyme Q10", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 6.4,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
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
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_duplicate_heart_energy_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_b_complex",
        "omega3",
    ]
    assert "wearable activity context" in response.next_action_rationale.summary.lower()


def test_multimodal_heart_fallback_can_start_when_wearable_and_genetic_contexts_cover_heart_support(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 57,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "coq10",
    ]
    assert "genetic cardiometabolic context" in response.next_action_rationale.summary.lower()


def test_multimodal_heart_fallback_can_start_with_non_cardiac_current_regimen_overlap(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 54,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
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
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "coq10",
    ]


def test_multimodal_heart_sleep_fallback_can_start_when_wearable_and_genetic_contexts_are_clear(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 46,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "sleep_support"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.9,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_sleep_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "magnesium_glycinate",
    ]
    assert "wearable sleep context" in response.next_action_rationale.summary.lower()
    assert "genetic heart-recovery context" in (
        response.next_action_rationale.summary.lower()
    )


def test_multimodal_heart_sleep_fallback_can_start_without_missing_current_supplements(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 48,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["heart_health", "sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Daily Multi", "ingredients": ["vitamin_c"]}
            ],
            "lifestyle": {
                "sleep_hours": 5.8,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_sleep_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "magnesium_glycinate",
        "omega3",
    ]
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "genetic context" in response.decision_summary.summary.lower()


def test_multimodal_heart_glucose_fallback_can_start_when_wearable_and_symptom_contexts_are_clear(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 48,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "blood_glucose"],
            "symptoms": ["low_activity", "post_meal_spike_concern"],
            "conditions": [],
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
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_glucose_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "soluble_fiber",
    ]
    assert "wearable activity context" in response.next_action_rationale.summary.lower()
    assert "post-meal spike" in response.next_action_rationale.summary.lower()


def test_multimodal_heart_glucose_fallback_can_start_with_non_overlapping_current_regimen(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 46,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["blood_glucose", "heart_health"],
            "symptoms": ["low_activity", "post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Daily Multi", "ingredients": ["vitamin_c"]}
            ],
            "lifestyle": {
                "sleep_hours": 6.9,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_multimodal_heart_glucose_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "soluble_fiber",
    ]
    assert "wearable context" in response.decision_summary.summary.lower()


def test_genetic_glucose_fallback_can_start_without_cgm_when_berberine_is_avoided() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 44,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["Thorne Berberine 500"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "glycemic-response" in response.recommendations[0].rationale.lower()


def test_genetic_glucose_fallback_can_start_without_cgm_when_berberine_overlaps() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 45,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Berberine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "glycemic-response" in response.recommendations[0].rationale.lower()


def test_long_current_supplement_title_is_canonicalized_before_duplicate_filtering() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 57,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {
                    "name": "Nordic Naturals Ultimate Omega Lemon Flavor Soft Gels",
                    "ingredients": [],
                }
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

    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_duplicate_heart_symptom_fallback"
    )
    assert "omega3" in response.safety_summary.excluded_ingredients
    assert "SAFETY-DUP-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]


def test_long_avoid_title_is_canonicalized_before_candidate_filtering() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["gut_health"],
            "symptoms": ["bloating"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
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
                "avoid_ingredients": [
                    "Renew Life Extra Care Ultimate Flora Probiotic 50 Billion CFU Capsules"
                ],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.safety_summary.excluded_ingredients == ["probiotics"]
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]


def test_genetic_micronutrient_context_changes_top_candidate_for_general_wellness() -> None:
    baseline_request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 44,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["general_wellness"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
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
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )
    genetic_request = baseline_request.model_copy(
        update={
            "input_availability": baseline_request.input_availability.model_copy(
                update={"genetic": True}
            )
        }
    )

    baseline_response = recommend(baseline_request)
    genetic_response = recommend(genetic_request)

    assert [item.ingredient_key for item in baseline_response.recommendations] == ["vitamin_c"]
    assert [item.ingredient_key for item in genetic_response.recommendations] == ["vitamin_d3"]
    assert baseline_response.next_action.value == "start_plan"
    assert genetic_response.next_action.value == "start_plan"


def test_genetic_cardiometabolic_context_changes_top_candidate_for_heart_health() -> None:
    baseline_request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 52,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [{"name": "atorvastatin", "dose": "20mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.7,
                "stress_level": 2,
                "activity_level": "sedentary",
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
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )
    genetic_request = baseline_request.model_copy(
        update={
            "input_availability": baseline_request.input_availability.model_copy(
                update={"genetic": True}
            )
        }
    )

    baseline_response = recommend(baseline_request)
    genetic_response = recommend(genetic_request)

    assert [item.ingredient_key for item in baseline_response.recommendations] == ["coq10"]
    assert [item.ingredient_key for item in genetic_response.recommendations] == ["omega3"]
    assert baseline_response.next_action.value == "start_plan"
    assert genetic_response.next_action.value == "start_plan"


def test_genetic_multi_goal_context_backfills_omega3_and_vitamin_d3() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 52,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "immunity_support"],
            "symptoms": ["low_activity", "frequent_fatigue"],
            "conditions": [],
            "medications": [{"name": "atorvastatin", "dose": "20mg"}],
            "current_supplements": [{"name": "Vitamin C", "ingredients": []}],
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
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert "vitamin_c" in response.safety_summary.excluded_ingredients
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "vitamin_d3",
    ]


def test_cgm_post_meal_context_changes_top_candidate_for_pure_blood_glucose() -> None:
    baseline_request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 46,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )
    cgm_request = baseline_request.model_copy(
        update={
            "input_availability": baseline_request.input_availability.model_copy(
                update={"cgm": True}
            )
        }
    )

    baseline_response = recommend(baseline_request)
    cgm_response = recommend(cgm_request)

    assert [item.ingredient_key for item in baseline_response.recommendations] == [
        "soluble_fiber"
    ]
    assert [item.ingredient_key for item in cgm_response.recommendations] == [
        "berberine"
    ]
    assert baseline_response.next_action.value == "collect_more_input"
    assert cgm_response.next_action.value == "start_plan"


def test_cgm_context_does_not_override_low_budget_for_pure_blood_glucose() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 46,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
                "cgm": True,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]


def test_genetic_low_sun_context_adds_explicit_vitamin_d3_rationale_note() -> None:
    baseline_request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["general_wellness"],
            "symptoms": ["low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": True,
                "cgm": True,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "high",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )
    genetic_request = baseline_request.model_copy(
        update={
            "input_availability": baseline_request.input_availability.model_copy(
                update={"genetic": True}
            )
        }
    )

    baseline_response = recommend(baseline_request)
    genetic_response = recommend(genetic_request)

    assert baseline_response.recommendations[0].ingredient_key == "vitamin_d3"
    assert genetic_response.recommendations[0].ingredient_key == "vitamin_d3"
    assert (
        genetic_response.recommendations[0].score_breakdown.evidence_readiness
        > baseline_response.recommendations[0].score_breakdown.evidence_readiness
    )
    assert "genetic context" not in baseline_response.recommendations[0].rationale.lower()
    assert "genetic context" in genetic_response.recommendations[0].rationale.lower()
    assert "low sun exposure" in genetic_response.recommendations[0].rationale.lower()


def test_genetic_cardiometabolic_context_adds_explicit_omega3_rationale_note() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 52,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [{"name": "atorvastatin", "dose": "20mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.7,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 1,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.recommendations[0].ingredient_key == "omega3"
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "cardiometabolic" in response.recommendations[0].rationale.lower()


def test_decision_summary_mentions_genetic_context_for_constrained_immunity_case() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 41,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["immunity_support"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.7,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["vitamin_c"],
            },
        }
    )

    response = recommend(request)

    assert [item.ingredient_key for item in response.recommendations] == [
        "zinc",
        "vitamin_d3",
    ]
    assert "genetic context" in response.decision_summary.summary.lower()


def test_decision_summary_mentions_genetic_context_for_sleep_recovery_case() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 36,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "L-Theanine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": None,
                "stress_level": 3,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": True,
                "cgm": False,
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

    assert [item.ingredient_key for item in response.recommendations] == [
        "magnesium_glycinate"
    ]
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "l_theanine" in response.safety_summary.excluded_ingredients


def test_genetic_energy_metabolism_context_changes_top_candidate_for_energy_support() -> None:
    baseline_request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 45,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.5,
                "stress_level": 2,
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
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )
    genetic_request = baseline_request.model_copy(
        update={
            "input_availability": baseline_request.input_availability.model_copy(
                update={"genetic": True}
            )
        }
    )

    baseline_response = recommend(baseline_request)
    genetic_response = recommend(genetic_request)

    assert [item.ingredient_key for item in baseline_response.recommendations] == ["coq10"]
    assert [item.ingredient_key for item in genetic_response.recommendations] == [
        "vitamin_b_complex"
    ]
    assert "genetic context" in genetic_response.recommendations[0].rationale.lower()
    assert "energy-metabolism" in genetic_response.recommendations[0].rationale.lower()


def test_genetic_recovery_context_adds_explicit_l_theanine_rationale_when_magnesium_is_blocked(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Magnesium Glycinate", "ingredients": []}
            ],
            "lifestyle": {
                "sleep_hours": 5.7,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": True,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["l_theanine"]
    assert "magnesium_glycinate" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "neuro-recovery" in response.recommendations[0].rationale.lower()


def test_genetic_bone_context_adds_explicit_calcium_rationale_when_vitamin_d_is_blocked() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 60,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 1,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["vitamin d"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["calcium_citrate"]
    assert "vitamin_d3" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "bone-mineral" in response.recommendations[0].rationale.lower()


def test_genetic_bone_context_adds_explicit_vitamin_d_rationale_when_calcium_is_blocked() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 61,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Calcium Citrate", "ingredients": []}
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["vitamin_d3"]
    assert "calcium_citrate" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "bone-mineral" in response.recommendations[0].rationale.lower()
    assert "low sun exposure" in response.recommendations[0].rationale.lower()


def test_genetic_immunity_context_changes_top_candidate_for_immunity_support() -> None:
    baseline_request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 37,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["immunity_support"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "lightly_active",
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
                "max_products": 1,
                "avoid_ingredients": ["vitamin d"],
            },
        }
    )
    genetic_request = baseline_request.model_copy(
        update={
            "input_availability": baseline_request.input_availability.model_copy(
                update={"genetic": True}
            )
        }
    )

    baseline_response = recommend(baseline_request)
    genetic_response = recommend(genetic_request)

    assert [item.ingredient_key for item in baseline_response.recommendations] == [
        "vitamin_c"
    ]
    assert [item.ingredient_key for item in genetic_response.recommendations] == [
        "zinc"
    ]
    assert "genetic context" not in baseline_response.decision_summary.summary.lower()
    assert "genetic context" in genetic_response.recommendations[0].rationale.lower()
    assert "immune-micronutrient" in genetic_response.recommendations[0].rationale.lower()


def test_genetic_immunity_context_keeps_explicit_zinc_rationale_when_vitamin_d_is_overlap_blocked(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 38,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["immunity_support"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Vitamin D3", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 6.9,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["zinc"]
    assert "vitamin_d3" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "immune-micronutrient" in response.recommendations[0].rationale.lower()


def test_genetic_cardiometabolic_context_adds_explicit_coq10_rationale_when_omega3_is_blocked(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 58,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "atorvastatin", "dose": "20mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.9,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["omega 3"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert "omega3" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "cardiometabolic energy" in response.recommendations[0].rationale.lower()


def test_genetic_cardiometabolic_context_survives_review_when_omega3_is_excluded() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 66,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose", "heart_health"],
            "symptoms": ["post_meal_spike_concern", "low_activity"],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [{"name": "Berberine", "ingredients": []}],
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
    assert response.next_action.value == "needs_human_review"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber",
        "coq10",
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[1].rationale.lower()
    assert "genetic context" in response.decision_summary.summary.lower()


def test_genetic_glycemic_context_adds_explicit_soluble_fiber_rationale_when_berberine_is_blocked(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 45,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Berberine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "glycemic-response" in response.recommendations[0].rationale.lower()
    assert "genetic context" in response.decision_summary.summary.lower()


def test_genetic_glycemic_context_survives_review_when_only_soluble_fiber_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 32,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_renal_genetic_glucose_fallback"
    )
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "glycemic-response" in response.recommendations[0].rationale.lower()
    assert "genetic context" in response.decision_summary.summary.lower()


def test_genetic_gut_context_adds_explicit_soluble_fiber_rationale_when_probiotics_are_blocked(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 36,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["gut_health"],
            "symptoms": ["bloating"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Probiotics", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "probiotics" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "gut-resilience" in response.recommendations[0].rationale.lower()
    assert "genetic context" in response.decision_summary.summary.lower()


def test_genetic_gut_context_survives_review_when_only_soluble_fiber_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 30,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["gut_health"],
            "symptoms": ["bloating"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Probiotics", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "probiotics" in response.safety_summary.excluded_ingredients
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert "gut-resilience" in response.recommendations[0].rationale.lower()
    assert "genetic context" in response.decision_summary.summary.lower()


def test_genetic_context_is_explicit_when_no_safe_candidates_remain() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 66,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "atorvastatin", "dose": "20mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.5,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["omega-3", "coenzyme q10"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "needs_review"
    assert response.next_action.value == "needs_human_review"
    assert response.recommendations == []
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "genetic context" in response.next_action_rationale.summary.lower()


def test_genetic_context_is_explicit_when_blocked_minimum_input_prevents_planning() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 64,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "atorvastatin", "dose": "20mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.6,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "blocked"
    assert response.next_action.value == "collect_more_input"
    assert response.recommendations == []
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "genetic context" in response.next_action_rationale.summary.lower()


def test_cgm_context_is_explicit_when_missing_info_still_blocks_plan_start() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 48,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose", "heart_health"],
            "symptoms": ["post_meal_spike_concern", "low_activity"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
                "cgm": True,
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
    assert response.next_action.value == "collect_more_input"
    assert "cgm context" in response.decision_summary.summary.lower()
    assert "cgm context" in response.next_action_rationale.summary.lower()


def test_cgm_context_is_explicit_when_no_safe_glucose_candidates_remain() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 46,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Berberine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
                "cgm": True,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["soluble fiber"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "needs_review"
    assert response.next_action.value == "needs_human_review"
    assert response.recommendations == []
    assert "cgm context" in response.decision_summary.summary.lower()
    assert "cgm context" in response.next_action_rationale.summary.lower()


def test_cgm_context_is_explicit_when_blocked_minimum_input_prevents_glucose_planning() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 33,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": True,
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
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "cgm context" in response.decision_summary.summary.lower()
    assert response.next_action_rationale.reason_code == "start_plan_ready"


def test_pregnancy_general_wellness_survey_block_is_cleared_with_safe_micronutrients() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 29,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["general_wellness"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_general_wellness_survey_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_d3",
        "vitamin_c",
    ]
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
    }
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "genetic context" in response.decision_summary.summary.lower()


def test_pregnancy_general_wellness_survey_block_is_cleared_with_duplicate_overlap() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 31,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["general_wellness"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Vitamin C", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 6.9,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_general_wellness_survey_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_d3",
        "zinc",
    ]
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-DUP-001",
        "SAFETY-PREG-001",
    }
    assert "vitamin_c" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.decision_summary.summary.lower()


def test_pregnancy_general_wellness_survey_fallback_starts_single_product_plan_when_budget_is_low(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 30,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["general_wellness"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": True,
                "cgm": True,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["vitamin_d3"]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_general_wellness_survey_fallback"
    )
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
    }


def test_pregnancy_general_wellness_survey_fallback_keeps_single_product_plan_after_overlap(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 32,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["general_wellness"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Vitamin C", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": True,
                "cgm": True,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["vitamin_d3"]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_general_wellness_survey_fallback"
    )
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-DUP-001",
    }
    assert "vitamin_c" in response.safety_summary.excluded_ingredients


def test_wearable_context_is_explicit_when_sleep_hours_fallback_starts_sleep_plan() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": None,
                "stress_level": 3,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
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
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "wearable sleep context" in response.next_action_rationale.summary.lower()
    assert "wearable context" in response.recommendations[0].rationale.lower()


def test_wearable_context_is_explicit_when_no_safe_sleep_candidates_remain() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 38,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "L-Theanine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 5.8,
                "stress_level": 3,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["magnesium glycinate"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "l_theanine" in response.next_action_rationale.supporting_codes


def test_wearable_context_is_explicit_when_anticoagulant_heart_survey_clearance(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 61,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.7,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
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
    assert response.next_action.value == "collect_more_input"
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "wearable context" in response.next_action_rationale.summary.lower()


def test_renal_only_review_is_cleared_when_only_baseline_sleep_candidate_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 58,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.9,
                "stress_level": 3,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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
    assert [item.ingredient_key for item in response.recommendations] == ["l_theanine"]
    assert "magnesium_glycinate" in response.safety_summary.excluded_ingredients
    assert "SAFETY-RENAL-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]


def test_renal_only_review_is_cleared_when_duplicate_filter_leaves_baseline_bone_candidate(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 63,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [{"name": "Calcium Citrate", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["vitamin_d3"]
    assert "calcium_citrate" in response.safety_summary.excluded_ingredients
    assert "SAFETY-RENAL-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "SAFETY-DUP-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]


def test_renal_bone_review_is_cleared_when_conservative_bone_candidates_remain(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 63,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_d3",
        "calcium_citrate",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-RENAL-001"
    ]


def test_renal_bone_review_is_cleared_when_duplicate_filter_leaves_only_calcium(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 62,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [{"name": "Vitamin D3 2000 IU", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "calcium_citrate"
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    ]
    assert "vitamin_d3" in response.safety_summary.excluded_ingredients


def test_pregnancy_review_is_cleared_when_only_fiber_candidate_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 30,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
                "cgm": True,
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
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]


def test_pregnancy_review_is_cleared_when_duplicate_overlap_leaves_only_fiber() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 30,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["gut_health"],
            "symptoms": ["bloating"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Probiotics", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
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
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "probiotics" in response.safety_summary.excluded_ingredients
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "SAFETY-DUP-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]


def test_pregnancy_sleep_review_is_cleared_when_only_baseline_sleep_candidates_remain(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 29,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.4,
                "stress_level": 4,
                "activity_level": "lightly_active",
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "magnesium_glycinate",
        "l_theanine",
    ]
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]


def test_pregnancy_sleep_review_is_cleared_when_duplicate_overlap_leaves_only_theanine(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 29,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Magnesium Glycinate", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 5.4,
                "stress_level": 4,
                "activity_level": "lightly_active",
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["l_theanine"]
    assert "magnesium_glycinate" in response.safety_summary.excluded_ingredients
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "SAFETY-DUP-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]


def test_pregnancy_renal_sleep_review_is_cleared_when_only_theanine_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 33,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.1,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["l_theanine"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
    ]
    assert "genetic context" in response.recommendations[0].rationale.lower()


def test_pregnancy_renal_sleep_review_is_cleared_when_duplicate_overlap_leaves_only_theanine(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [
                {"name": "Magnesium Glycinate Night Powder", "ingredients": []}
            ],
            "lifestyle": {
                "sleep_hours": 5.4,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["l_theanine"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    ]
    assert "magnesium_glycinate" in response.safety_summary.excluded_ingredients


def test_pregnancy_renal_glucose_review_is_cleared_when_only_soluble_fiber_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 32,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "SAFETY-RENAL-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "genetic context" in response.recommendations[0].rationale.lower()


def test_pregnancy_renal_glucose_review_is_cleared_without_cgm_when_only_soluble_fiber_remains(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 32,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "SAFETY-RENAL-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "glycemic-response" in response.recommendations[0].rationale.lower()


def test_pregnancy_renal_glucose_review_is_cleared_for_chronic_kidney_disease() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_renal_genetic_glucose_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]


def test_pregnancy_renal_glucose_review_is_cleared_for_chronic_kidney_disease_low_budget(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "SAFETY-RENAL-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]


def test_anticoagulant_heart_review_clears_when_only_coq10_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 61,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "moderately_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "collect_more_input"
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_multiple_missing_items"
    )
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-ANTICOAG-001"
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients


def test_anticoagulant_heart_review_clears_when_duplicate_overlap_leaves_only_coq10(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 69,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [{"name": "Omega-3", "ingredients": []}],
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
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-ANTICOAG-001",
        "SAFETY-DUP-001",
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients


def test_coumadin_alias_heart_review_clears_when_only_coq10_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 67,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "Coumadin", "dose": "3mg"}],
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
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-ANTICOAG-001"
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients


def test_anticoagulant_combo_goal_still_requires_review() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 69,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health", "energy_support"],
            "symptoms": ["fatigue", "low_activity"],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.4,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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

    assert response.status.value == "needs_review"
    assert response.next_action.value == "needs_human_review"
    assert response.next_action_rationale.reason_code == "needs_review_due_to_safety"
    assert [item.ingredient_key for item in response.recommendations] == [
        "coq10",
        "vitamin_b_complex",
    ]


def test_anticoagulant_heart_review_clears_under_low_budget_single_product_constraints(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 64,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-ANTICOAG-001"
    ]


def test_coumadin_alias_duplicate_overlap_clears_when_only_coq10_survives() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 68,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "Coumadin", "dose": "3mg"}],
            "current_supplements": [{"name": "Omega-3 Softgel", "ingredients": []}],
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
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-ANTICOAG-001",
        "SAFETY-DUP-001",
    ]


def test_anticoagulant_heart_survey_only_block_clears_to_collect_more_input_when_only_coq10_remains(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 68,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "warfarin", "dose": "5mg"}],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
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
    assert response.next_action.value == "collect_more_input"
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_high_priority_missing_info"
    )
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-ANTICOAG-001",
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients


def test_anticoagulant_heart_survey_only_block_clears_with_coumadin_alias_and_duplicate_overlap(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 70,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "Coumadin", "dose": "3mg"}],
            "current_supplements": [
                {"name": "Fish Oil Omega-3 Softgels", "ingredients": []}
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
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
    assert response.next_action.value == "collect_more_input"
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_high_priority_missing_info"
    )
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-ANTICOAG-001",
        "SAFETY-DUP-001",
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients


def test_pregnancy_survey_only_block_is_cleared_when_only_fiber_candidate_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 31,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "cgm context" in response.recommendations[0].rationale.lower()
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_glucose_survey_fallback"
    )


def test_pregnancy_survey_only_block_is_cleared_when_duplicate_overlap_leaves_safe_gut_candidates(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 30,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["gut_health"],
            "symptoms": ["bloating"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Probiotics", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
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
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert "probiotics" in response.safety_summary.excluded_ingredients
    assert "SAFETY-PREG-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert "SAFETY-DUP-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_gut_survey_fallback"
    )


def test_pregnancy_glucose_survey_only_case_can_start_when_cgm_and_genetic_context_are_explicit(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 31,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_glucose_survey_fallback"
    )
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
    }
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "soluble-fiber survivor" in response.next_action_rationale.summary.lower()
    assert "cgm context" in response.decision_summary.summary.lower()


def test_pregnancy_glucose_survey_only_case_can_start_when_duplicate_overlap_leaves_soluble_fiber(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Berberine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": True,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_glucose_survey_fallback"
    )
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-DUP-001",
    }
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "soluble-fiber survivor" in response.next_action_rationale.summary.lower()


def test_pregnancy_renal_genetic_glucose_block_is_cleared() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 33,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_renal_genetic_glucose_fallback"
    )
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
    }
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "conservative" in response.next_action_rationale.summary.lower()
    assert "genetic glycemic context" in response.next_action_rationale.summary.lower()


def test_pregnancy_renal_genetic_duplicate_block_is_cleared() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [{"name": "Berberine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_renal_genetic_glucose_fallback"
    )
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    }
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "conservative" in response.next_action_rationale.summary.lower()
    assert "genetic glycemic context" in response.next_action_rationale.summary.lower()


def test_pregnancy_renal_genetic_glucose_survey_fallback_supports_chronic_kidney_disease(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_renal_genetic_glucose_fallback"
    )
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
    }


def test_pregnancy_renal_genetic_glucose_survey_fallback_supports_low_budget_overlap(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 36,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [{"name": "Berberine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_renal_genetic_glucose_fallback"
    )
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    }


def test_pregnancy_renal_cgm_duplicate_block_is_cleared() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [{"name": "Berberine", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": True,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["soluble_fiber"]
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    }
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "cgm context" in response.decision_summary.summary.lower()
    assert "plan can start" in response.next_action_rationale.summary.lower()


def test_pregnancy_renal_cgm_glucose_survey_fallback_starts_without_overlap() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": True,
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
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
    }
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "cgm context" in response.decision_summary.summary.lower()


def test_pregnancy_renal_cgm_glucose_survey_fallback_supports_low_budget_overlap() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 36,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [{"name": "Berberine Complex", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": True,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert response.next_action_rationale.reason_code == "start_plan_ready"
    assert {ref.rule_id for ref in response.safety_summary.rule_refs} == {
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    }
    assert "berberine" in response.safety_summary.excluded_ingredients
    assert "plan can start" in response.next_action_rationale.summary.lower()


def test_general_wellness_survey_only_block_is_cleared_when_baseline_candidates_are_safe(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 45,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["general_wellness"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.5,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 2,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "collect_more_input"
    assert [item.ingredient_key for item in response.recommendations] == ["vitamin_d3"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "collect_more_input_high_priority_missing_info"
    )


def test_general_wellness_survey_block_keeps_genetic_baseline_support(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 46,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["general_wellness"],
            "symptoms": ["frequent_fatigue", "low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.7,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_d3",
        "vitamin_c",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == ["INTAKE-SURVEY-001"]
    assert "genetic context" in response.recommendations[0].rationale.lower()
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_general_wellness_survey_fallback"
    )


def test_general_wellness_survey_fallback_starts_when_fatigue_detail_is_explicit() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 43,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["general_wellness"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.7,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 1,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_d3",
        "vitamin_c",
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_general_wellness_survey_fallback"
    )
    assert "fatigue detail" in response.next_action_rationale.summary.lower()


def test_general_wellness_survey_fallback_starts_without_genetic_when_low_sun_detail_is_explicit(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 44,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["general_wellness"],
            "symptoms": ["frequent_fatigue", "low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_d3",
        "vitamin_c",
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_general_wellness_survey_fallback"
    )


def test_pregnancy_gut_survey_fallback_starts_when_only_pregnancy_safe_gut_candidates_remain(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 31,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["gut_health"],
            "symptoms": ["bloating"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber",
        "probiotics",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_gut_survey_fallback"
    )
    assert "bloating detail" in response.next_action_rationale.summary.lower()


def test_pregnancy_gut_survey_fallback_starts_when_duplicate_overlap_leaves_only_soluble_fiber(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 29,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["gut_health"],
            "symptoms": ["bloating"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Daily Probiotic", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
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
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber"
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-PREG-001",
        "SAFETY-DUP-001",
    ]
    assert "probiotics" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_pregnancy_gut_survey_fallback"
    )


def test_energy_survey_only_block_is_cleared_when_only_baseline_energy_candidates_remain(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.8,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
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
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_b_complex",
        "coq10",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_energy_survey_fallback"
    )
    assert "wearable activity context" in response.next_action_rationale.summary.lower()
    assert "energy plan" in response.next_action_rationale.summary.lower()


def test_energy_survey_only_block_can_start_when_duplicate_overlap_leaves_only_coq10(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Vitamin B Complex", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 6.0,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
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
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-DUP-001",
    ]
    assert "vitamin_b_complex" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_energy_survey_fallback"
    )


def test_energy_missing_symptom_fallback_starts_when_wearable_context_and_short_sleep_are_explicit(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["energy_support"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.5,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
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
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_b_complex",
        "coq10",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_energy_missing_symptom_fallback"
    )
    assert "wearable activity context" in response.next_action_rationale.summary.lower()
    assert "energy plan" in response.next_action_rationale.summary.lower()


def test_energy_missing_symptom_fallback_starts_single_product_plan_under_low_budget(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 36,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["energy_support"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.4,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": True,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_b_complex"
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_energy_missing_symptom_fallback"
    )
    assert "short-sleep detail" in response.next_action_rationale.summary.lower()


def test_bone_survey_only_block_is_cleared_when_duplicate_overlap_leaves_baseline_support(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 56,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [{"name": "Vitamin D3 2000 IU", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "calcium_citrate"
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-DUP-001",
    ]
    assert "vitamin_d3" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_bone_survey_fallback"
    )
    assert "genetic bone context" in response.next_action_rationale.summary.lower()


def test_bone_survey_only_block_is_cleared_when_baseline_bone_candidates_remain() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 56,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_d3",
        "calcium_citrate",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_bone_survey_fallback"
    )
    assert "low-sun symptom detail" in response.next_action_rationale.summary.lower()


def test_renal_sleep_survey_only_block_is_cleared_when_only_theanine_remains() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 55,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.3,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": False,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["l_theanine"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-RENAL-001",
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_renal_sleep_survey_fallback"
    )
    assert "wearable sleep context" in response.next_action_rationale.summary.lower()


def test_renal_sleep_survey_only_block_can_start_when_duplicate_overlap_leaves_only_theanine(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 57,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [
                {"name": "Magnesium Glycinate Powder", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 5.8,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
                "wearable": True,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == ["l_theanine"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    ]
    assert "magnesium_glycinate" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_renal_sleep_survey_fallback"
    )


def test_renal_bone_survey_only_block_is_cleared_when_duplicate_overlap_leaves_only_calcium(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 58,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [{"name": "Vitamin D3 2000 IU", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "calcium_citrate"
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    ]
    assert "vitamin_d3" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_renal_bone_survey_fallback"
    )


def test_renal_bone_survey_only_block_is_cleared_when_conservative_bone_candidates_remain(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 59,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "vitamin_d3",
        "calcium_citrate",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-RENAL-001",
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_renal_bone_survey_fallback"
    )


def test_sleep_hours_fallback_starts_sleep_plan_when_wearable_sleep_context_is_explicit(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 36,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": None,
                "stress_level": 3,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert [item.ingredient_key for item in response.recommendations] == [
        "magnesium_glycinate",
        "l_theanine",
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_sleep_hours_fallback"
    )
    assert "wearable sleep context" in response.next_action_rationale.summary.lower()


def test_sleep_hours_fallback_starts_sleep_plan_when_duplicate_overlap_leaves_only_theanine(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 37,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Magnesium Glycinate Powder", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": None,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
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
    assert [item.ingredient_key for item in response.recommendations] == ["l_theanine"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-DUP-001"
    ]
    assert "magnesium_glycinate" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_sleep_hours_fallback"
    )


def test_heart_survey_only_block_is_cleared_when_wearable_context_can_anchor_follow_up() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 45,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.5,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
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
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "coq10",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_heart_survey_fallback"
    )


def test_heart_survey_only_block_is_cleared_when_duplicate_overlap_leaves_only_coq10(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 46,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Omega-3 Softgel", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 6.6,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
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
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-DUP-001",
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_heart_survey_fallback"
    )


def test_heart_survey_fallback_can_start_with_alias_overlap_only_coq10() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 47,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "High Potency Fish Oil Omega-3 1200 mg", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 6.7,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
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
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-DUP-001",
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_heart_survey_fallback"
    )


def test_heart_survey_fallback_can_start_when_missing_primary_symptom_is_still_open() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 48,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 6.4,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
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
    assert [item.ingredient_key for item in response.recommendations] == [
        "omega3",
        "coq10",
    ]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001"
    ]
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_heart_survey_fallback"
    )


def test_heart_survey_only_block_clears_when_missing_primary_symptom_and_duplicate_overlap(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 49,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Omega-3 Softgel", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 6.3,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
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
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-DUP-001",
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_heart_survey_fallback"
    )


def test_heart_survey_only_block_clears_when_missing_primary_symptom_and_alias_overlap(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 50,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "High Potency Fish Oil Omega-3 1200 mg", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 6.4,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": False,
                "nhis": True,
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
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "INTAKE-SURVEY-001",
        "SAFETY-DUP-001",
    ]
    assert "omega3" in response.safety_summary.excluded_ingredients
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_heart_survey_fallback"
    )


def test_duplicate_only_current_regimen_coverage_can_continue_stress_plan() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 39,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["stress_support"],
            "symptoms": ["high_stress"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Magnesium Glycinate", "ingredients": []},
                {"name": "L-Theanine", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 5.9,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
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
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "magnesium_glycinate" in response.next_action_rationale.supporting_codes
    assert "l_theanine" in response.next_action_rationale.supporting_codes


def test_duplicate_only_current_regimen_coverage_can_continue_gut_plan() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 38,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["gut_health"],
            "symptoms": ["bloating"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Probiotics", "ingredients": []},
                {"name": "Soluble Fiber", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "probiotics" in response.next_action_rationale.supporting_codes
    assert "soluble_fiber" in response.next_action_rationale.supporting_codes


def test_pregnancy_duplicate_regimen_glucose_plan_with_cgm() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 32,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Psyllium Fiber", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": True,
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
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-PREG-001",
        "SAFETY-DUP-001",
    ]
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "cgm context" in response.decision_summary.summary.lower()
    assert "soluble_fiber" in response.next_action_rationale.supporting_codes


def test_pregnancy_duplicate_regimen_glucose_plan_with_genetic_context() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 34,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Metamucil Psyllium Husk", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 7.1,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-PREG-001",
        "SAFETY-DUP-001",
    ]
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "soluble_fiber" in response.next_action_rationale.supporting_codes


def test_pregnancy_duplicate_regimen_glucose_plan_with_genetic_context_and_low_budget(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 36,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Metamucil Psyllium Husk", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-PREG-001",
        "SAFETY-DUP-001",
    ]
    assert [item.code for item in response.missing_information] == [
        "missing_glucose_context"
    ]
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "soluble_fiber" in response.next_action_rationale.supporting_codes


def test_pregnancy_duplicate_regimen_glucose_plan_with_cgm_and_low_budget(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 35,
                "biological_sex": "female",
                "pregnant": True,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Psyllium Fiber", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": True,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "low",
                "max_products": 1,
                "avoid_ingredients": [],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-PREG-001",
        "SAFETY-DUP-001",
    ]
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "cgm context" in response.decision_summary.summary.lower()
    assert "soluble_fiber" in response.next_action_rationale.supporting_codes


def test_duplicate_only_current_regimen_coverage_allows_immunity_plan_with_avoided_alternatives(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 38,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["immunity_support"],
            "symptoms": ["frequent_fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Vitamin D3", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["vitamin c", "zinc"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "vitamin_d3" in response.next_action_rationale.supporting_codes


def test_duplicate_only_current_regimen_coverage_allows_sleep_plan_with_avoided_alternatives(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 38,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "L-Theanine", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 5.8,
                "stress_level": 3,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": True,
                "cgm": False,
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["magnesium glycinate"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "l_theanine" in response.next_action_rationale.supporting_codes


def test_renal_duplicate_only_current_regimen_coverage_can_continue_sleep_plan() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 46,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": ["kidney disease"],
            "medications": [],
            "current_supplements": [
                {"name": "L-Theanine", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 5.3,
                "stress_level": 4,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
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
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    ]
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "l_theanine" in response.next_action_rationale.supporting_codes


def test_renal_duplicate_only_current_regimen_coverage_can_continue_sleep_plan_with_alias_overlap(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 52,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
            "conditions": ["chronic kidney disease"],
            "medications": [],
            "current_supplements": [
                {"name": "Nighttime Theanine Capsule", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 5.4,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert [ref.rule_id for ref in response.safety_summary.rule_refs] == [
        "SAFETY-RENAL-001",
        "SAFETY-DUP-001",
    ]
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "l_theanine" in response.next_action_rationale.supporting_codes


def test_duplicate_only_current_regimen_coverage_can_continue_bone_plan() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 63,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Vitamin D3", "ingredients": []},
                {"name": "Calcium Citrate", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 7.0,
                "stress_level": 2,
                "activity_level": "lightly_active",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": False,
                "wearable": False,
                "cgm": False,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "genetic context" in response.decision_summary.summary.lower()
    assert "vitamin_d3" in response.next_action_rationale.supporting_codes
    assert "calcium_citrate" in response.next_action_rationale.supporting_codes


def test_duplicate_only_current_regimen_coverage_can_continue_energy_plan_without_medications(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 58,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Vitamin B Complex", "ingredients": []},
                {"name": "Coenzyme Q10", "ingredients": []},
            ],
            "lifestyle": {
                "sleep_hours": 5.8,
                "stress_level": 3,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
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
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "vitamin_b_complex" in response.next_action_rationale.supporting_codes
    assert "coq10" in response.next_action_rationale.supporting_codes


def test_duplicate_only_current_regimen_coverage_can_continue_statin_heart_plan() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 62,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "atorvastatin", "dose": "20mg"}],
            "current_supplements": [
                {"name": "Omega-3", "ingredients": []},
                {"name": "Coenzyme Q10", "ingredients": []},
            ],
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
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "wearable context" in response.decision_summary.summary.lower()
    assert "omega3" in response.next_action_rationale.supporting_codes
    assert "coq10" in response.next_action_rationale.supporting_codes


def test_duplicate_only_current_regimen_coverage_can_continue_statin_heart_plan_with_omega3_only(
) -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 59,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["heart_health"],
            "symptoms": ["low_activity"],
            "conditions": [],
            "medications": [{"name": "atorvastatin", "dose": "20mg"}],
            "current_supplements": [{"name": "Omega 3 Softgel", "ingredients": []}],
            "lifestyle": {
                "sleep_hours": 6.8,
                "stress_level": 2,
                "activity_level": "sedentary",
                "smoker": False,
                "alcohol_per_week": 0,
            },
            "input_availability": {
                "survey": True,
                "nhis": True,
                "wearable": False,
                "cgm": False,
                "genetic": True,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": ["coenzyme q10"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.recommendations == []
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_current_regimen_coverage"
    )
    assert "current regimen already covers the focus goals" in (
        response.decision_summary.summary.lower()
    )
    assert "genetic context" in response.decision_summary.summary.lower()
    assert response.next_action_rationale.supporting_codes == ["omega3"]


def test_long_b_complex_avoid_title_canonicalizes_and_leaves_only_coq10() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 41,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [],
            "lifestyle": {
                "sleep_hours": 5.8,
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
                "avoid_ingredients": ["Garden of Life Vitamin Code Raw B-Complex"],
            },
        }
    )

    response = recommend(request)

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert response.safety_summary.excluded_ingredients == ["vitamin_b_complex"]
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]


def test_long_b_complex_current_supplement_title_canonicalizes_before_duplicate_filtering() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 42,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["energy_support"],
            "symptoms": ["fatigue"],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {
                    "name": "Garden of Life Vitamin Code Raw B-Complex Capsules",
                    "ingredients": [],
                }
            ],
            "lifestyle": {
                "sleep_hours": 5.9,
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

    assert response.status.value == "ok"
    assert response.next_action.value == "start_plan"
    assert "SAFETY-DUP-001" in [ref.rule_id for ref in response.safety_summary.rule_refs]
    assert response.safety_summary.excluded_ingredients == ["vitamin_b_complex"]
    assert [item.ingredient_key for item in response.recommendations] == ["coq10"]


def test_cgm_glucose_missing_primary_symptom_can_start_plan() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 44,
                "biological_sex": "male",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": [],
            "conditions": [],
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
                "wearable": False,
                "cgm": True,
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
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_cgm_glucose_missing_symptom_fallback"
    )
    assert [item.ingredient_key for item in response.recommendations] == [
        "soluble_fiber",
        "berberine",
    ]


def test_cgm_glucose_missing_primary_symptom_can_start_plan_after_duplicate_overlap() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 45,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": [],
            "conditions": [],
            "medications": [],
            "current_supplements": [
                {"name": "Fiber Powder", "ingredients": ["soluble_fiber"]}
            ],
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
                "wearable": False,
                "cgm": True,
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
    assert (
        response.next_action_rationale.reason_code
        == "start_plan_cgm_glucose_missing_symptom_fallback"
    )
    assert "soluble_fiber" in response.safety_summary.excluded_ingredients
    assert [item.ingredient_key for item in response.recommendations] == ["berberine"]
