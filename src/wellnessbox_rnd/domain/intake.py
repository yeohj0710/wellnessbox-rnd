from dataclasses import dataclass

from wellnessbox_rnd.domain.catalog import canonicalize_catalog_term
from wellnessbox_rnd.domain.loaders import load_safety_rules
from wellnessbox_rnd.domain.models import GoalContextRule
from wellnessbox_rnd.schemas.recommendation import (
    MissingInfoImportance,
    MissingInformationItem,
    RecommendationGoal,
    RecommendationRequest,
)


@dataclass(frozen=True)
class NormalizedIntake:
    request: RecommendationRequest
    goal_set: set[RecommendationGoal]
    symptom_set: set[str]
    condition_set: set[str]
    medication_set: set[str]
    current_ingredient_set: set[str]
    avoid_ingredient_set: set[str]
    signal_flags: set[str]
    missing_information: list[MissingInformationItem]
    normalization_notes: list[str]


def normalize_request(request: RecommendationRequest) -> NormalizedIntake:
    rules = load_safety_rules()

    goal_set = set(request.goals)
    symptom_set = {_normalize_text(item) for item in request.symptoms}
    condition_set = {_normalize_text(item) for item in request.conditions}
    medication_set = {_normalize_text(item.name) for item in request.medications}
    current_ingredient_set = set()
    for supplement in request.current_supplements:
        current_ingredient_set.update(_normalize_catalog_inputs([supplement.name]))
        current_ingredient_set.update(_normalize_catalog_inputs(supplement.ingredients))

    avoid_ingredient_set = _normalize_catalog_inputs(request.preferences.avoid_ingredients)
    signal_flags = _derive_signal_flags(request)
    missing_information = _collect_missing_information(
        request,
        goal_set,
        rules.goal_context_rules,
    )

    normalization_notes = [
        "Input strings are normalized to lowercase tokens for deterministic matching.",
        "Current ingredient catalog is a demo placeholder and not the production product SSOT.",
    ]
    if request.input_availability.survey:
        normalization_notes.append("Survey input is present, so baseline recommendation can run.")
    else:
        normalization_notes.append(
            "Survey input is missing, so baseline recommendation is blocked."
        )

    return NormalizedIntake(
        request=request,
        goal_set=goal_set,
        symptom_set={item for item in symptom_set if item},
        condition_set={item for item in condition_set if item},
        medication_set={item for item in medication_set if item},
        current_ingredient_set={item for item in current_ingredient_set if item},
        avoid_ingredient_set={item for item in avoid_ingredient_set if item},
        signal_flags=signal_flags,
        missing_information=missing_information,
        normalization_notes=normalization_notes,
    )


def _derive_signal_flags(request: RecommendationRequest) -> set[str]:
    flags: set[str] = set()
    symptom_set = {_normalize_text(item) for item in request.symptoms}
    if request.lifestyle.sleep_hours is not None and request.lifestyle.sleep_hours < 6:
        flags.add("sleep_deficit")
    if request.lifestyle.stress_level is not None and request.lifestyle.stress_level >= 4:
        flags.add("high_stress")
    if request.lifestyle.activity_level.value == "sedentary":
        flags.add("low_activity")
    if request.input_availability.wearable:
        flags.add("wearable_data_available")
        if any(
            goal in request.goals
            for goal in (
                RecommendationGoal.SLEEP_SUPPORT,
                RecommendationGoal.STRESS_SUPPORT,
            )
        ):
            flags.add("wearable_sleep_context")
        if any(
            goal in request.goals
            for goal in (
                RecommendationGoal.HEART_HEALTH,
                RecommendationGoal.ENERGY_SUPPORT,
                RecommendationGoal.GENERAL_WELLNESS,
            )
        ):
            flags.add("wearable_activity_context")
    else:
        flags.add("no_wearable_data")
    if request.input_availability.cgm:
        flags.add("cgm_data_available")
        if RecommendationGoal.BLOOD_GLUCOSE in request.goals:
            flags.add("cgm_glucose_context")
            if "post_meal_spike_concern" in symptom_set:
                flags.add("cgm_post_meal_spike_context")
    else:
        flags.add("no_cgm_data")
    if request.input_availability.genetic:
        flags.add("genetic_data_available")
        if "low_sun_exposure" in symptom_set:
            flags.add("genetic_low_sun_context")
        if RecommendationGoal.BLOOD_GLUCOSE in request.goals:
            flags.add("genetic_glycemic_context")
        if RecommendationGoal.GUT_HEALTH in request.goals:
            flags.add("genetic_gut_context")
        if RecommendationGoal.IMMUNITY_SUPPORT in request.goals:
            flags.add("genetic_immunity_context")
        if RecommendationGoal.BONE_JOINT in request.goals:
            flags.add("genetic_bone_context")
        if (
            RecommendationGoal.ENERGY_SUPPORT in request.goals
            and symptom_set.intersection({"fatigue", "frequent_fatigue"})
        ):
            flags.add("genetic_energy_metabolism_context")
        if any(
            goal in request.goals
            for goal in (
                RecommendationGoal.IMMUNITY_SUPPORT,
                RecommendationGoal.BONE_JOINT,
                RecommendationGoal.GENERAL_WELLNESS,
            )
        ):
            flags.add("genetic_micronutrient_context")
        if any(
            goal in request.goals
            for goal in (
                RecommendationGoal.HEART_HEALTH,
                RecommendationGoal.BLOOD_GLUCOSE,
            )
        ):
            flags.add("genetic_cardiometabolic_context")
        if any(
            goal in request.goals
            for goal in (
                RecommendationGoal.STRESS_SUPPORT,
                RecommendationGoal.SLEEP_SUPPORT,
            )
        ):
            flags.add("genetic_recovery_context")
    else:
        flags.add("no_genetic_data")
    return flags


def _collect_missing_information(
    request: RecommendationRequest,
    goals: set[RecommendationGoal],
    goal_context_rules: dict[str, GoalContextRule],
) -> list[MissingInformationItem]:
    items: list[MissingInformationItem] = []

    if not request.input_availability.survey:
        items.append(
            MissingInformationItem(
                code="missing_survey",
                question="Please complete the baseline survey first.",
                reason="The minimum input contract is not satisfied.",
                importance=MissingInfoImportance.HIGH,
            )
        )

    if not request.symptoms:
        items.append(
            MissingInformationItem(
                code="missing_primary_symptom",
                question="Please name the main symptom or support goal you want to prioritize.",
                reason="Symptom detail helps deterministic ranking stay conservative but useful.",
                importance=MissingInfoImportance.MEDIUM,
            )
        )

    if RecommendationGoal.SLEEP_SUPPORT in goals and request.lifestyle.sleep_hours is None:
        items.append(
            MissingInformationItem(
                code="missing_sleep_hours",
                question="Please share your average sleep hours.",
                reason="Sleep duration is a strong baseline signal for sleep-related ranking.",
                importance=MissingInfoImportance.MEDIUM,
            )
        )

    if RecommendationGoal.BLOOD_GLUCOSE in goals and not request.input_availability.cgm:
        items.append(
            _build_goal_context_item(
                code="missing_glucose_context",
                goal=RecommendationGoal.BLOOD_GLUCOSE,
                goal_context_rules=goal_context_rules,
                fallback_question=(
                    "Please share glucose context such as CGM or lab values if available."
                ),
                fallback_reason=(
                    "Blood glucose goals need more context for a safer baseline ranking."
                ),
                fallback_importance=MissingInfoImportance.HIGH,
            )
        )

    if RecommendationGoal.HEART_HEALTH in goals and not request.medications:
        items.append(
            _build_goal_context_item(
                code="missing_heart_context",
                goal=RecommendationGoal.HEART_HEALTH,
                goal_context_rules=goal_context_rules,
                fallback_question=(
                    "Please share heart-related labs or current medication information."
                ),
                fallback_reason="Heart-related goals benefit from medication and lab context.",
                fallback_importance=MissingInfoImportance.HIGH,
            )
        )

    if not request.current_supplements:
        items.append(
            MissingInformationItem(
                code="missing_current_supplements",
                question="Please list any supplements you are already taking.",
                reason="Current supplement data helps avoid overlap.",
                importance=MissingInfoImportance.LOW,
            )
        )

    return sorted(items, key=_missing_info_sort_key)


def _build_goal_context_item(
    code: str,
    goal: RecommendationGoal,
    goal_context_rules: dict[str, GoalContextRule],
    fallback_question: str,
    fallback_reason: str,
    fallback_importance: MissingInfoImportance,
) -> MissingInformationItem:
    rule = goal_context_rules.get(goal.value)
    if rule is None:
        return MissingInformationItem(
            code=code,
            question=fallback_question,
            reason=fallback_reason,
            importance=fallback_importance,
        )
    return MissingInformationItem(
        code=code,
        question=rule.question,
        reason=rule.reason,
        importance=rule.importance,
    )


def _missing_info_sort_key(item: MissingInformationItem) -> tuple[int, str]:
    priority = {
        MissingInfoImportance.HIGH: 0,
        MissingInfoImportance.MEDIUM: 1,
        MissingInfoImportance.LOW: 2,
    }
    return (priority[item.importance], item.code)


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_catalog_inputs(values: list[str]) -> set[str]:
    normalized_values: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        normalized_values.add(canonicalize_catalog_term(value) or normalized)
    return normalized_values
