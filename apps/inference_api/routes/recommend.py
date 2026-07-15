from typing import Annotated

from fastapi import APIRouter, Body

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest, RecommendationResponse

router = APIRouter(tags=["recommend"])

_RECOMMEND_REQUEST_EXAMPLES = {
    "structured_health_profile_and_urgent_signal": {
        "summary": "Structured health profile and urgent signal",
        "description": (
            "Shows height, weight, condition status, symptom severity, and an explicit "
            "urgent-risk signal that stops recommendation generation."
        ),
        "value": {
            "user_profile": {
                "age": 52,
                "biological_sex": "male",
                "pregnant": False,
                "height_cm": 176.5,
                "weight_kg": 82.4,
            },
            "goals": ["heart_health"],
            "symptoms": [
                {
                    "code": "chest_pressure",
                    "severity": "critical",
                    "duration_days": 0,
                }
            ],
            "conditions": [
                {
                    "code": "hypertension",
                    "status": "active",
                    "display_name": "Hypertension",
                }
            ],
            "risk_flags": [
                {
                    "code": "red_flag_chest_pain",
                    "present": True,
                    "source": "self_report",
                }
            ],
            "medications": [],
            "current_supplements": [],
            "input_availability": {"survey": True},
        },
    },
    "structured_current_supplement_dose": {
        "summary": "Structured medication and current supplement doses",
        "description": (
            "Shows medication classification and numeric dose-unit objects, plus an "
            "ingredient-specific daily supplement dose used by deterministic safety rules."
        ),
        "value": {
            "user_profile": {
                "age": 45,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["bone_joint"],
            "symptoms": ["low_sun_exposure"],
            "conditions": [],
            "medications": [
                {
                    "name": "Metformin",
                    "classification": {
                        "code": "A10BA02",
                        "system": "ATC",
                        "display_name": "Biguanides",
                    },
                    "dose": {"amount": 500, "unit": "mg"},
                }
            ],
            "current_supplements": [
                {
                    "name": "Daily Bone Softgel",
                    "ingredients": [
                        {
                            "name": "Vitamin D3",
                            "daily_dose": {"amount": 125, "unit": "mcg"},
                        }
                    ],
                }
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
                "genetic": False,
            },
            "preferences": {
                "budget_level": "medium",
                "max_products": 2,
                "avoid_ingredients": [],
            },
        },
    },
    "structured_diet_lifestyle_and_laboratory_observations": {
        "summary": "Structured diet, lifestyle, and laboratory observations",
        "description": (
            "Shows normalized allergy and dietary-pattern inputs, explicit weekly exercise "
            "and daily caffeine values, and timestamped laboratory observations with units "
            "and reference ranges."
        ),
        "value": {
            "user_profile": {
                "age": 48,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["blood_glucose"],
            "symptoms": ["post_meal_spike_concern"],
            "conditions": [],
            "allergies": ["fish", "peanut"],
            "medications": [],
            "current_supplements": [],
            "dietary_patterns": [
                {
                    "code": "mediterranean diet",
                    "display_name": "Mediterranean diet",
                },
                "low sodium",
            ],
            "laboratory_observations": [
                {
                    "code": "hba1c",
                    "value": 6.1,
                    "unit": "%",
                    "reference_range": {"low": 4.0, "high": 5.6},
                    "measured_at": "2026-07-14T09:30:00+09:00",
                },
                {
                    "code": "fasting glucose",
                    "value": 102,
                    "unit": "mg/dL",
                    "reference_range": {"low": 70, "high": 99},
                    "measured_at": "2026-07-14T09:30:00+09:00",
                },
            ],
            "lifestyle": {
                "sleep_hours": 6.5,
                "stress_level": 3,
                "activity_level": "lightly_active",
                "exercise_minutes_per_week": 95,
                "smoker": False,
                "alcohol_per_week": 1,
                "caffeine_mg_per_day": 240,
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
        },
    },
    "structured_start_plan_path": {
        "summary": "Structured start plan path",
        "description": (
            "Shows a non-blocked deterministic path with wearable context and a "
            "structured start_plan next action."
        ),
        "value": {
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
        },
    }
}


@router.post("/recommend", response_model=RecommendationResponse)
def recommend_endpoint(
    payload: Annotated[
        RecommendationRequest,
        Body(openapi_examples=_RECOMMEND_REQUEST_EXAMPLES),
    ],
) -> RecommendationResponse:
    return recommend(payload)
