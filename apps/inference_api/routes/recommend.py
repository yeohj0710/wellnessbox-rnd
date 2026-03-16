from typing import Annotated

from fastapi import APIRouter, Body

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest, RecommendationResponse

router = APIRouter(tags=["recommend"])

_RECOMMEND_REQUEST_EXAMPLES = {
    "structured_current_supplement_dose": {
        "summary": "Structured current supplement dose",
        "description": (
            "Shows the bounded structured input path for current supplement dose capture."
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
            "medications": [],
            "current_supplements": [
                {
                    "name": "Daily Bone Softgel",
                    "dose": "125 mcg",
                    "ingredients": ["Vitamin D3"],
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
