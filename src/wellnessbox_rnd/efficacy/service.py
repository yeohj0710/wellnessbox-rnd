from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.domain.models import IngredientCatalogItem
from wellnessbox_rnd.schemas.recommendation import (
    CandidateScoreBreakdown,
    RecommendationGoal,
)


def score_candidate(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
    safety_review: bool,
) -> CandidateScoreBreakdown:
    goal_alignment = sum(
        _goal_alignment_weight(goal)
        for goal in item.supported_goals
        if goal in intake.goal_set
    )
    symptom_alignment = 8.0 * len(set(item.supported_symptoms) & intake.symptom_set)
    lifestyle_alignment = 6.0 * len(set(item.preferred_signals) & intake.signal_flags)
    evidence_readiness = _evidence_readiness_score(item, intake)
    budget_adjustment = _budget_adjustment(
        item.budget_tier.value,
        intake.request.preferences.budget_level.value,
    )
    safety_adjustment = -4.0 if safety_review else 0.0
    conservative_adjustment = _conservative_adjustment(
        conservative_profile=item.conservative_profile,
        intake=intake,
        safety_review=safety_review,
    )
    total = (
        item.default_priority
        + goal_alignment
        + symptom_alignment
        + lifestyle_alignment
        + evidence_readiness
        + budget_adjustment
        + safety_adjustment
        + conservative_adjustment
    )

    return CandidateScoreBreakdown(
        goal_alignment=goal_alignment,
        symptom_alignment=symptom_alignment,
        lifestyle_alignment=lifestyle_alignment,
        evidence_readiness=evidence_readiness,
        budget_adjustment=budget_adjustment,
        safety_adjustment=safety_adjustment,
        conservative_adjustment=conservative_adjustment,
        learned_effect_bonus=0.0,
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
    score += _cgm_evidence_bonus(item, intake)
    score += _genetic_evidence_bonus(item, intake)
    return score


def _budget_adjustment(item_budget: str, user_budget: str) -> float:
    if user_budget == "low":
        return {"low": 2.0, "medium": -1.0, "high": -5.0}[item_budget]
    if user_budget == "medium":
        return {"low": 1.0, "medium": 1.0, "high": -2.0}[item_budget]
    return {"low": 0.0, "medium": 1.0, "high": 1.0}[item_budget]


def _goal_alignment_weight(goal: RecommendationGoal) -> float:
    if goal == RecommendationGoal.GENERAL_WELLNESS:
        return 18.0
    return 35.0


def _conservative_adjustment(
    conservative_profile: str,
    intake: NormalizedIntake,
    safety_review: bool,
) -> float:
    if conservative_profile == "baseline":
        base_adjustment = 1.0
    elif conservative_profile == "interaction_sensitive":
        base_adjustment = -1.0
    else:
        base_adjustment = 0.0

    if not safety_review:
        return base_adjustment

    if conservative_profile == "baseline":
        safety_adjustment = 3.0
    elif conservative_profile == "interaction_sensitive":
        safety_adjustment = -4.0
    else:
        has_review_risk = intake.request.user_profile.pregnant or bool(intake.condition_set)
        safety_adjustment = -1.0 if has_review_risk else 0.0

    return base_adjustment + safety_adjustment


def _genetic_evidence_bonus(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> float:
    if not intake.request.input_availability.genetic:
        return 0.0

    if item.key == "vitamin_d3":
        bonus = 0.0
        if "genetic_micronutrient_context" in intake.signal_flags:
            bonus += 8.0
        if "genetic_low_sun_context" in intake.signal_flags:
            bonus += 4.0
        if "genetic_bone_context" in intake.signal_flags:
            bonus += 2.0
        return bonus
    if item.key == "calcium_citrate" and "genetic_bone_context" in intake.signal_flags:
        return 4.0
    if item.key == "soluble_fiber" and "genetic_glycemic_context" in intake.signal_flags:
        return 2.0
    if item.key == "soluble_fiber" and "genetic_gut_context" in intake.signal_flags:
        return 2.0
    if item.key == "zinc" and "genetic_immunity_context" in intake.signal_flags:
        return 1.0
    if (
        item.key == "vitamin_b_complex"
        and "genetic_energy_metabolism_context" in intake.signal_flags
    ):
        return 4.0
    if (
        item.key == "coq10"
        and "genetic_cardiometabolic_context" in intake.signal_flags
        and RecommendationGoal.HEART_HEALTH in intake.goal_set
    ):
        return 2.0
    if item.key == "omega3" and "genetic_cardiometabolic_context" in intake.signal_flags:
        return 10.0
    if item.key == "l_theanine" and "genetic_recovery_context" in intake.signal_flags:
        return 4.0
    if (
        item.key == "magnesium_glycinate"
        and "genetic_recovery_context" in intake.signal_flags
    ):
        return 6.0
    return 0.0


def genetic_context_note(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> str | None:
    if not intake.request.input_availability.genetic:
        return None

    if item.key == "vitamin_d3":
        if (
            "genetic_bone_context" in intake.signal_flags
            and "genetic_low_sun_context" in intake.signal_flags
        ):
            return (
                " Available genetic context reinforced bone-mineral support confidence "
                "for low sun exposure."
            )
        if "genetic_bone_context" in intake.signal_flags:
            return " Available genetic context reinforced bone-mineral support confidence."
        if "genetic_low_sun_context" in intake.signal_flags:
            return (
                " Available genetic context reinforced micronutrient support confidence "
                "for low sun exposure."
            )
        if "genetic_micronutrient_context" in intake.signal_flags:
            return " Available genetic context reinforced micronutrient support confidence."
    if item.key == "calcium_citrate" and "genetic_bone_context" in intake.signal_flags:
        return " Available genetic context reinforced bone-mineral support confidence."
    if item.key == "soluble_fiber" and "genetic_glycemic_context" in intake.signal_flags:
        return " Available genetic context reinforced glycemic-response support confidence."
    if item.key == "soluble_fiber" and "genetic_gut_context" in intake.signal_flags:
        return " Available genetic context reinforced gut-resilience support confidence."
    if item.key == "zinc" and "genetic_immunity_context" in intake.signal_flags:
        return " Available genetic context reinforced immune-micronutrient support confidence."
    if (
        item.key == "vitamin_b_complex"
        and "genetic_energy_metabolism_context" in intake.signal_flags
    ):
        return " Available genetic context reinforced energy-metabolism support confidence."
    if (
        item.key == "coq10"
        and "genetic_cardiometabolic_context" in intake.signal_flags
        and RecommendationGoal.HEART_HEALTH in intake.goal_set
    ):
        return " Available genetic context reinforced cardiometabolic energy support confidence."
    if item.key == "omega3" and "genetic_cardiometabolic_context" in intake.signal_flags:
        return " Available genetic context reinforced cardiometabolic support confidence."
    if item.key == "l_theanine" and "genetic_recovery_context" in intake.signal_flags:
        return " Available genetic context reinforced neuro-recovery support confidence."
    if (
        item.key == "magnesium_glycinate"
        and "genetic_recovery_context" in intake.signal_flags
    ):
        return " Available genetic context reinforced recovery support confidence."
    return None


def wearable_context_note(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> str | None:
    if not intake.request.input_availability.wearable:
        return None

    if (
        item.follow_up_focus in {"sleep_quality", "calmness_and_sleep_onset"}
        and "wearable_sleep_context" in intake.signal_flags
    ):
        return " Available wearable context reinforced sleep-pattern follow-up confidence."
    if (
        item.follow_up_focus
        in {"daytime_energy", "energy_and_activity", "activity_and_heart_metrics"}
        and "wearable_activity_context" in intake.signal_flags
    ):
        return " Available wearable context reinforced activity-pattern follow-up confidence."
    return None


def cgm_context_note(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> str | None:
    if not intake.request.input_availability.cgm:
        return None

    if item.key == "berberine" and "cgm_post_meal_spike_context" in intake.signal_flags:
        return " Available CGM context reinforced post-meal glucose support confidence."
    if item.key == "soluble_fiber" and "cgm_glucose_context" in intake.signal_flags:
        return " Available CGM context preserved blood-glucose follow-up visibility."
    return None


def _cgm_evidence_bonus(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> float:
    if not intake.request.input_availability.cgm:
        return 0.0

    if (
        item.key == "berberine"
        and intake.goal_set == {RecommendationGoal.BLOOD_GLUCOSE}
        and "cgm_post_meal_spike_context" in intake.signal_flags
    ):
        return 8.0
    return 0.0
