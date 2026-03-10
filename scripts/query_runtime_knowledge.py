from __future__ import annotations

import argparse
import json

from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    ActivityLevel,
    BiologicalSex,
    InputAvailability,
    LifestyleInput,
    MedicationInput,
    RecommendationGoal,
    RecommendationPreferences,
    RecommendationRequest,
    SupplementInput,
    UserProfile,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a sample runtime knowledge-backed safety query."
    )
    parser.add_argument("--medication", action="append", required=True)
    parser.add_argument("--current-ingredient", action="append", required=True)
    args = parser.parse_args()

    request = RecommendationRequest(
        user_profile=UserProfile(
            age=55,
            biological_sex=BiologicalSex.MALE,
            pregnant=False,
        ),
        goals=[RecommendationGoal.HEART_HEALTH],
        symptoms=["low_activity_tolerance"],
        medications=[MedicationInput(name=value) for value in args.medication],
        current_supplements=[
            SupplementInput(name=value)
            for value in args.current_ingredient
        ],
        lifestyle=LifestyleInput(
            sleep_hours=7.0,
            stress_level=2,
            activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        ),
        input_availability=InputAvailability(
            survey=True,
            nhis=False,
            wearable=False,
            cgm=False,
            genetic=False,
        ),
        preferences=RecommendationPreferences(),
    )

    intake = normalize_request(request)
    response = recommend(request)
    payload = {
        "request_medications": sorted(intake.medication_set),
        "request_current_ingredients": sorted(intake.current_ingredient_set),
        "status": response.safety_summary.status,
        "rule_refs": response.safety_summary.model_dump()["rule_refs"],
        "excluded_ingredients": response.safety_summary.excluded_ingredients,
        "blocked_reasons": response.safety_summary.blocked_reasons,
        "next_action": response.next_action,
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
