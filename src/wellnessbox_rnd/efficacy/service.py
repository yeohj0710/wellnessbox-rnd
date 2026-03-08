from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.domain.models import IngredientCatalogItem
from wellnessbox_rnd.schemas.recommendation import CandidateScoreBreakdown


def score_candidate(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
    safety_review: bool,
) -> CandidateScoreBreakdown:
    goal_alignment = 35.0 * len(set(item.supported_goals) & intake.goal_set)
    symptom_alignment = 8.0 * len(set(item.supported_symptoms) & intake.symptom_set)
    lifestyle_alignment = 6.0 * len(set(item.preferred_signals) & intake.signal_flags)
    evidence_readiness = _evidence_readiness_score(item, intake)
    budget_adjustment = _budget_adjustment(
        item.budget_tier.value,
        intake.request.preferences.budget_level.value,
    )
    safety_adjustment = -4.0 if safety_review else 0.0
    total = (
        item.default_priority
        + goal_alignment
        + symptom_alignment
        + lifestyle_alignment
        + evidence_readiness
        + budget_adjustment
        + safety_adjustment
    )

    return CandidateScoreBreakdown(
        goal_alignment=goal_alignment,
        symptom_alignment=symptom_alignment,
        lifestyle_alignment=lifestyle_alignment,
        evidence_readiness=evidence_readiness,
        budget_adjustment=budget_adjustment,
        safety_adjustment=safety_adjustment,
        total=total,
    )


def estimate_follow_up_window_days(intake: NormalizedIntake) -> int:
    if intake.request.input_availability.cgm:
        return 10
    if intake.request.input_availability.wearable:
        return 14
    return 21


def _evidence_readiness_score(item: IngredientCatalogItem, intake: NormalizedIntake) -> float:
    score = 2.0
    if item.follow_up_focus == "post_meal_response" and intake.request.input_availability.cgm:
        score += 5.0
    elif item.follow_up_focus == "sleep_quality" and intake.request.input_availability.wearable:
        score += 4.0
    elif (
        item.follow_up_focus == "activity_and_heart_metrics"
        and intake.request.input_availability.wearable
        and any(goal.value == "heart_health" for goal in intake.goal_set)
    ):
        score += 4.0
    elif intake.request.input_availability.survey:
        score += 2.0
    return score


def _budget_adjustment(item_budget: str, user_budget: str) -> float:
    if user_budget == "low":
        return {"low": 2.0, "medium": -1.0, "high": -5.0}[item_budget]
    if user_budget == "medium":
        return {"low": 1.0, "medium": 1.0, "high": -2.0}[item_budget]
    return {"low": 0.0, "medium": 1.0, "high": 1.0}[item_budget]
