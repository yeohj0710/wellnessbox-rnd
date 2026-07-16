import hashlib
import json
from dataclasses import dataclass
from typing import Any

from wellnessbox_rnd.domain.catalog import canonicalize_catalog_term
from wellnessbox_rnd.domain.loaders import load_safety_rules
from wellnessbox_rnd.domain.models import GoalContextRule
from wellnessbox_rnd.schemas.recommendation import (
    ConditionInput,
    ConditionStatus,
    DataSource,
    DietaryPatternInput,
    InputAvailability,
    LaboratoryObservationInput,
    LaboratoryRangeStatus,
    LifestyleInput,
    MedicationInput,
    MissingInfoImportance,
    MissingInformationItem,
    NormalizedSensorGeneticSnapshot,
    RecommendationGoal,
    RecommendationRequest,
    RiskSignalSource,
    SupplementIngredientInput,
    SupplementInput,
    SymptomInput,
    SymptomSeverity,
    UrgentRiskSignal,
    classify_laboratory_observation,
    normalize_dietary_pattern_code,
    normalize_health_input_code,
    normalize_laboratory_observation_code,
    normalize_laboratory_unit,
    normalize_medication_classification_code,
    normalize_medication_classification_key,
    normalize_supplement_ingredient_name,
)

_GLUCOSE_LAB_CODES = {
    "fasting glucose",
    "fasting_glucose",
    "glucose",
    "hba1c",
    "hemoglobin a1c",
    "hemoglobin_a1c",
    "postprandial glucose",
    "postprandial_glucose",
}
_HEART_LAB_CODES = {
    "hdl",
    "hdl cholesterol",
    "hdl_cholesterol",
    "ldl",
    "ldl cholesterol",
    "ldl_cholesterol",
    "total cholesterol",
    "total_cholesterol",
    "triglycerides",
}


@dataclass(frozen=True)
class NormalizedIntake:
    request: RecommendationRequest
    declared_input_availability: InputAvailability
    effective_input_availability: InputAvailability
    recommendation_authorized_input_source_set: set[str]
    storage_authorized_input_source_set: set[str]
    goal_set: set[RecommendationGoal]
    normalized_symptoms: list[SymptomInput]
    symptom_set: set[str]
    symptom_severity_by_code: dict[str, SymptomSeverity]
    normalized_conditions: list[ConditionInput]
    condition_set: set[str]
    condition_status_by_code: dict[str, ConditionStatus]
    normalized_allergies: list[str]
    allergy_set: set[str]
    normalized_risk_signals: list[UrgentRiskSignal]
    risk_flag_set: set[str]
    risk_signal_source_by_code: dict[str, RiskSignalSource]
    normalized_medications: list[MedicationInput]
    medication_set: set[str]
    medication_classification_set: set[str]
    normalized_current_supplements: list[SupplementInput]
    current_supplement_product_set: set[str]
    current_ingredient_set: set[str]
    normalized_dietary_patterns: list[DietaryPatternInput]
    dietary_pattern_set: set[str]
    normalized_lifestyle: LifestyleInput
    normalized_laboratory_observations: list[LaboratoryObservationInput]
    latest_laboratory_observation_by_code: dict[str, LaboratoryObservationInput]
    laboratory_range_status_by_code: dict[str, LaboratoryRangeStatus]
    sensor_genetic_snapshot: NormalizedSensorGeneticSnapshot | None
    avoid_ingredient_set: set[str]
    signal_flags: set[str]
    missing_information: list[MissingInformationItem]
    normalization_notes: list[str]


def normalize_request(request: RecommendationRequest) -> NormalizedIntake:
    rules = load_safety_rules()

    declared_input_availability = request.input_availability.model_copy(deep=True)
    effective_input_availability = _build_effective_input_availability(request)
    recommendation_authorized_input_source_set = {
        source.value
        for source in DataSource
        if getattr(effective_input_availability, source.value)
    }
    storage_authorized_input_source_set = {
        source.value
        for source in DataSource
        if getattr(declared_input_availability, source.value)
        and getattr(
            request.data_source_consents,
            source.value,
        ).allow_persistent_storage
    }
    consent_gated_laboratory_observations = [
        observation
        for observation in request.laboratory_observations
        if observation.source.value in recommendation_authorized_input_source_set
    ]
    consent_gated_sensor_snapshot = _consent_gate_sensor_snapshot(
        request.sensor_genetic_snapshot,
        effective_input_availability,
    )
    request = request.model_copy(
        update={
            "input_availability": effective_input_availability,
            "laboratory_observations": consent_gated_laboratory_observations,
            "sensor_genetic_snapshot": consent_gated_sensor_snapshot,
        }
    )

    goal_set = set(request.goals)
    normalized_symptoms, symptom_set, symptom_severity_by_code = (
        _normalize_symptom_inputs(request.symptoms)
    )
    normalized_conditions, condition_set, condition_status_by_code = (
        _normalize_condition_inputs(request.conditions)
    )
    normalized_allergies = _normalize_string_inputs(request.allergies)
    allergy_set = set(normalized_allergies)
    normalized_risk_signals, risk_flag_set, risk_signal_source_by_code = (
        _normalize_risk_signals(request.risk_flags)
    )
    normalized_medications, medication_set, medication_classification_set = (
        _normalize_medication_inputs(request.medications)
    )
    (
        normalized_current_supplements,
        current_supplement_product_set,
        current_ingredient_set,
    ) = _normalize_supplement_inputs(request.current_supplements)
    normalized_dietary_patterns, dietary_pattern_set = _normalize_dietary_patterns(
        request.dietary_patterns
    )
    normalized_lifestyle = request.lifestyle.model_copy()
    (
        normalized_laboratory_observations,
        latest_laboratory_observation_by_code,
        laboratory_range_status_by_code,
    ) = _normalize_laboratory_observations(request.laboratory_observations)

    avoid_ingredient_set = _normalize_catalog_inputs(request.preferences.avoid_ingredients)
    signal_flags = _derive_signal_flags(request, symptom_set=symptom_set)
    missing_information = _collect_missing_information(
        request,
        goal_set,
        rules.goal_context_rules,
    )

    normalization_notes = [
        "Input strings are normalized to lowercase tokens for deterministic matching.",
        "Current ingredient catalog is a demo placeholder and not the production product SSOT.",
    ]
    denied_sources = sorted(
        source.value
        for source in DataSource
        if getattr(declared_input_availability, source.value)
        and not getattr(effective_input_availability, source.value)
    )
    if denied_sources:
        normalization_notes.append(
            "Data sources without recommendation-use consent were excluded: "
            + ", ".join(denied_sources)
            + "."
        )
    if request.input_availability.survey:
        normalization_notes.append("Survey input is present, so baseline recommendation can run.")
    else:
        normalization_notes.append(
            "Survey input is missing, so baseline recommendation is blocked."
        )

    return NormalizedIntake(
        request=request,
        declared_input_availability=declared_input_availability,
        effective_input_availability=effective_input_availability,
        recommendation_authorized_input_source_set=(
            recommendation_authorized_input_source_set
        ),
        storage_authorized_input_source_set=storage_authorized_input_source_set,
        goal_set=goal_set,
        normalized_symptoms=normalized_symptoms,
        symptom_set=symptom_set,
        symptom_severity_by_code=symptom_severity_by_code,
        normalized_conditions=normalized_conditions,
        condition_set=condition_set,
        condition_status_by_code=condition_status_by_code,
        normalized_allergies=normalized_allergies,
        allergy_set={item for item in allergy_set if item},
        normalized_risk_signals=normalized_risk_signals,
        risk_flag_set=risk_flag_set,
        risk_signal_source_by_code=risk_signal_source_by_code,
        normalized_medications=normalized_medications,
        medication_set={item for item in medication_set if item},
        medication_classification_set={
            item for item in medication_classification_set if item
        },
        normalized_current_supplements=normalized_current_supplements,
        current_supplement_product_set={
            item for item in current_supplement_product_set if item
        },
        current_ingredient_set={item for item in current_ingredient_set if item},
        normalized_dietary_patterns=normalized_dietary_patterns,
        dietary_pattern_set={item for item in dietary_pattern_set if item},
        normalized_lifestyle=normalized_lifestyle,
        normalized_laboratory_observations=normalized_laboratory_observations,
        latest_laboratory_observation_by_code=latest_laboratory_observation_by_code,
        laboratory_range_status_by_code=laboratory_range_status_by_code,
        sensor_genetic_snapshot=consent_gated_sensor_snapshot,
        avoid_ingredient_set={item for item in avoid_ingredient_set if item},
        signal_flags=signal_flags,
        missing_information=missing_information,
        normalization_notes=normalization_notes,
    )


def _build_effective_input_availability(
    request: RecommendationRequest,
) -> InputAvailability:
    return InputAvailability.model_validate(
        {
            source.value: getattr(request.input_availability, source.value)
            and getattr(
                request.data_source_consents,
                source.value,
            ).use_for_recommendation
            for source in DataSource
        }
    )


def _consent_gate_sensor_snapshot(
    snapshot: NormalizedSensorGeneticSnapshot | None,
    availability: InputAvailability,
) -> NormalizedSensorGeneticSnapshot | None:
    if snapshot is None:
        return None
    return snapshot.model_copy(
        update={
            "wearable_available": snapshot.wearable_available and availability.wearable,
            "sleep_hours": snapshot.sleep_hours if availability.wearable else None,
            "steps": snapshot.steps if availability.wearable else None,
            "resting_heart_rate": (
                snapshot.resting_heart_rate if availability.wearable else None
            ),
            "cgm_available": snapshot.cgm_available and availability.cgm,
            "mean_glucose_mg_dl": (
                snapshot.mean_glucose_mg_dl if availability.cgm else None
            ),
            "time_in_range_pct": (
                snapshot.time_in_range_pct if availability.cgm else None
            ),
            "time_in_range_low_mg_dl": (
                snapshot.time_in_range_low_mg_dl if availability.cgm else None
            ),
            "time_in_range_high_mg_dl": (
                snapshot.time_in_range_high_mg_dl if availability.cgm else None
            ),
            "post_meal_spike_concern": (
                snapshot.post_meal_spike_concern if availability.cgm else False
            ),
            "genetic_available": snapshot.genetic_available and availability.genetic,
            "genetic_tags": snapshot.genetic_tags if availability.genetic else [],
        }
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _normalize_json_numbers(value: Any) -> Any:
    if isinstance(value, float) and value == 0.0:
        return 0.0
    if isinstance(value, dict):
        return {key: _normalize_json_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_json_numbers(item) for item in value]
    return value


def _sorted_model_payloads(values: list[Any]) -> list[dict[str, object]]:
    payloads = [value.model_dump(mode="json") for value in values]
    return sorted(payloads, key=_canonical_json)


def _sorted_supplement_payloads(
    values: list[SupplementInput],
) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for value in values:
        payload = value.model_dump(mode="json")
        ingredients = payload.get("ingredients")
        if isinstance(ingredients, list):
            payload["ingredients"] = sorted(ingredients, key=_canonical_json)
        payloads.append(payload)
    return sorted(payloads, key=_canonical_json)


def build_normalized_input_snapshot_v1(
    intake: NormalizedIntake,
) -> dict[str, object]:
    request = intake.request
    snapshot = {
        "schema_version": "normalized_recommendation_input_v1",
        "user_profile": request.user_profile.model_dump(mode="json"),
        "goals": sorted(goal.value for goal in intake.goal_set),
        "symptoms": _sorted_model_payloads(intake.normalized_symptoms),
        "conditions": _sorted_model_payloads(intake.normalized_conditions),
        "allergies": list(intake.normalized_allergies),
        "risk_signals": _sorted_model_payloads(intake.normalized_risk_signals),
        "medications": _sorted_model_payloads(intake.normalized_medications),
        "current_supplements": _sorted_supplement_payloads(
            intake.normalized_current_supplements
        ),
        "dietary_patterns": _sorted_model_payloads(
            intake.normalized_dietary_patterns
        ),
        "laboratory_observations": _sorted_model_payloads(
            intake.normalized_laboratory_observations
        ),
        "lifestyle": intake.normalized_lifestyle.model_dump(mode="json"),
        "input_sources": {
            "declared_availability": intake.declared_input_availability.model_dump(
                mode="json"
            ),
            "effective_availability": intake.effective_input_availability.model_dump(
                mode="json"
            ),
            "consents": request.data_source_consents.model_dump(mode="json"),
            "recommendation_authorized": sorted(
                intake.recommendation_authorized_input_source_set
            ),
            "storage_authorized": sorted(
                intake.storage_authorized_input_source_set
            ),
        },
        "preferences": {
            "budget_level": request.preferences.budget_level.value,
            "max_products": request.preferences.max_products,
            "avoid_ingredients": sorted(intake.avoid_ingredient_set),
        },
    }
    if intake.sensor_genetic_snapshot is not None:
        snapshot["sensor_genetic_snapshot"] = (
            intake.sensor_genetic_snapshot.model_dump(
                mode="json",
                exclude={"normalization_notes"},
            )
        )
    return _normalize_json_numbers(snapshot)


def calculate_normalized_input_sha256_v1(intake: NormalizedIntake) -> str:
    canonical_payload = _canonical_json(build_normalized_input_snapshot_v1(intake))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _derive_signal_flags(
    request: RecommendationRequest,
    *,
    symptom_set: set[str],
) -> set[str]:
    flags: set[str] = set()
    if request.lifestyle.sleep_hours is not None and request.lifestyle.sleep_hours < 6:
        flags.add("sleep_deficit")
    if request.lifestyle.stress_level is not None and request.lifestyle.stress_level >= 4:
        flags.add("high_stress")
    if request.lifestyle.activity_level.value == "sedentary":
        flags.add("low_activity")
    if request.lifestyle.exercise_minutes_per_week is not None:
        flags.add("exercise_context_available")
    if request.lifestyle.caffeine_mg_per_day is not None:
        flags.add("caffeine_context_available")
    if request.dietary_patterns:
        flags.add("dietary_pattern_context_available")
    if request.laboratory_observations:
        flags.add("laboratory_context_available")
    if request.input_availability.wearable:
        flags.add("wearable_data_available")
        snapshot = request.sensor_genetic_snapshot
        if snapshot is not None:
            if snapshot.sleep_hours is not None:
                flags.add("wearable_sleep_context")
            if snapshot.steps is not None or snapshot.resting_heart_rate is not None:
                flags.add("wearable_activity_context")
        else:
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
        snapshot = request.sensor_genetic_snapshot
        has_cgm_observation = snapshot is None or (
            snapshot.mean_glucose_mg_dl is not None
            or snapshot.time_in_range_pct is not None
        )
        if RecommendationGoal.BLOOD_GLUCOSE in request.goals and has_cgm_observation:
            flags.add("cgm_glucose_context")
            if snapshot is not None:
                spike_concern = snapshot.post_meal_spike_concern
            else:
                spike_concern = "post_meal_spike_concern" in symptom_set
            if spike_concern:
                flags.add("cgm_post_meal_spike_context")
    else:
        flags.add("no_cgm_data")
    if request.input_availability.genetic:
        flags.add("genetic_data_available")
        snapshot = request.sensor_genetic_snapshot
        if snapshot is not None:
            return flags
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

    laboratory_codes = {
        normalize_laboratory_observation_code(item)
        for item in request.laboratory_observations
    }

    if (
        RecommendationGoal.BLOOD_GLUCOSE in goals
        and not request.input_availability.cgm
        and not laboratory_codes.intersection(_GLUCOSE_LAB_CODES)
    ):
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

    if (
        RecommendationGoal.HEART_HEALTH in goals
        and not request.medications
        and not laboratory_codes.intersection(_HEART_LAB_CODES)
    ):
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


def _normalize_string_inputs(values: list[str]) -> list[str]:
    normalized_values = {_normalize_text(value) for value in values}
    return sorted(value for value in normalized_values if value)


def _normalize_dietary_patterns(
    values: list[str | DietaryPatternInput],
) -> tuple[list[DietaryPatternInput], set[str]]:
    by_code: dict[str, DietaryPatternInput] = {}
    for value in values:
        code = normalize_dietary_pattern_code(value)
        if not code:
            continue
        normalized = (
            value.model_copy(update={"code": code})
            if isinstance(value, DietaryPatternInput)
            else DietaryPatternInput(code=code)
        )
        current = by_code.get(code)
        if current is None or (
            current.display_name is None and normalized.display_name is not None
        ):
            by_code[code] = normalized
    normalized_inputs = [by_code[code] for code in sorted(by_code)]
    return normalized_inputs, set(by_code)


def _normalize_laboratory_observations(
    values: list[LaboratoryObservationInput],
) -> tuple[
    list[LaboratoryObservationInput],
    dict[str, LaboratoryObservationInput],
    dict[str, LaboratoryRangeStatus],
]:
    normalized_inputs: list[LaboratoryObservationInput] = []
    latest_by_code: dict[str, LaboratoryObservationInput] = {}
    for value in values:
        code = normalize_laboratory_observation_code(value)
        normalized = value.model_copy(
            update={
                "code": code,
                "unit": normalize_laboratory_unit(value.unit),
            }
        )
        normalized_inputs.append(normalized)
        current = latest_by_code.get(code)
        if current is None or normalized.measured_at > current.measured_at:
            latest_by_code[code] = normalized

    range_status_by_code = {
        code: classify_laboratory_observation(value)
        for code, value in latest_by_code.items()
    }
    return normalized_inputs, latest_by_code, range_status_by_code


def build_normalized_health_context_feature_dict(
    request: RecommendationRequest,
) -> dict[str, float]:
    normalized_allergies = _normalize_string_inputs(request.allergies)
    _, dietary_pattern_set = _normalize_dietary_patterns(request.dietary_patterns)
    normalized_laboratory_observations, latest_by_code, status_by_code = (
        _normalize_laboratory_observations(request.laboratory_observations)
    )
    lifestyle = request.lifestyle
    features: dict[str, float] = {
        "allergy_count": float(len(normalized_allergies)),
        "dietary_pattern_count": float(len(dietary_pattern_set)),
        "laboratory_observation_count": float(
            len(normalized_laboratory_observations)
        ),
        "exercise_minutes_per_week_scaled": (
            0.0
            if lifestyle.exercise_minutes_per_week is None
            else lifestyle.exercise_minutes_per_week / 10_080.0
        ),
        "exercise_minutes_per_week_missing": float(
            lifestyle.exercise_minutes_per_week is None
        ),
        "caffeine_mg_per_day_scaled": (
            0.0
            if lifestyle.caffeine_mg_per_day is None
            else lifestyle.caffeine_mg_per_day / 5_000.0
        ),
        "caffeine_mg_per_day_missing": float(
            lifestyle.caffeine_mg_per_day is None
        ),
    }
    for allergy in normalized_allergies:
        features[f"allergy::{allergy}"] = 1.0
    for dietary_pattern in dietary_pattern_set:
        features[f"dietary_pattern::{dietary_pattern}"] = 1.0
    for code, observation in latest_by_code.items():
        features[f"laboratory::{code}"] = 1.0
        features[f"laboratory_unit::{code}::{observation.unit}"] = 1.0
        features[f"laboratory_status::{code}::{status_by_code[code].value}"] = 1.0
    return features


def _normalize_medication_inputs(
    values: list[MedicationInput],
) -> tuple[list[MedicationInput], set[str], set[str]]:
    normalized_inputs: list[MedicationInput] = []
    medication_set: set[str] = set()
    classification_set: set[str] = set()
    for value in values:
        name = _normalize_text(value.name)
        if not name:
            continue
        classification = value.classification
        if classification is not None:
            classification_code = normalize_medication_classification_code(classification)
            classification = classification.model_copy(
                update={
                    "code": classification_code,
                    "system": _normalize_text(classification.system),
                }
            )
            classification_set.add(normalize_medication_classification_key(classification))
        dose = value.dose.strip() if isinstance(value.dose, str) else value.dose
        normalized_inputs.append(
            value.model_copy(
                update={
                    "name": name,
                    "classification": classification,
                    "dose": dose,
                }
            )
        )
        medication_set.add(name)
    return normalized_inputs, medication_set, classification_set


def _normalize_supplement_inputs(
    values: list[SupplementInput],
) -> tuple[list[SupplementInput], set[str], set[str]]:
    normalized_inputs: list[SupplementInput] = []
    product_set: set[str] = set()
    ingredient_set: set[str] = set()
    for value in values:
        product_name = _normalize_text(value.name)
        normalized_ingredients: list[SupplementIngredientInput] = []
        for ingredient in value.ingredients:
            ingredient_name = normalize_supplement_ingredient_name(ingredient)
            if not ingredient_name:
                continue
            normalized_ingredient = (
                ingredient.model_copy(update={"name": ingredient_name})
                if isinstance(ingredient, SupplementIngredientInput)
                else SupplementIngredientInput(name=ingredient_name)
            )
            normalized_ingredients.append(normalized_ingredient)
            ingredient_set.update(_normalize_catalog_inputs([ingredient_name]))

        product_set.add(product_name)
        ingredient_set.update(_normalize_catalog_inputs([product_name]))
        dose = value.dose.strip() if value.dose is not None else None
        normalized_inputs.append(
            value.model_copy(
                update={
                    "name": product_name,
                    "dose": dose,
                    "ingredients": normalized_ingredients,
                }
            )
        )
    return normalized_inputs, product_set, ingredient_set


def _normalize_symptom_inputs(
    values: list[str | SymptomInput],
) -> tuple[list[SymptomInput], set[str], dict[str, SymptomSeverity]]:
    severity_rank = {
        SymptomSeverity.UNSPECIFIED: 0,
        SymptomSeverity.MILD: 1,
        SymptomSeverity.MODERATE: 2,
        SymptomSeverity.SEVERE: 3,
        SymptomSeverity.CRITICAL: 4,
    }
    normalized_inputs: list[SymptomInput] = []
    severity_by_code: dict[str, SymptomSeverity] = {}
    for value in values:
        code = normalize_health_input_code(value)
        if not code:
            continue
        normalized_input = (
            value.model_copy(update={"code": code})
            if isinstance(value, SymptomInput)
            else SymptomInput(code=code, severity=SymptomSeverity.UNSPECIFIED)
        )
        normalized_inputs.append(normalized_input)
        severity = normalized_input.severity
        current = severity_by_code.get(code)
        if current is None or severity_rank[severity] > severity_rank[current]:
            severity_by_code[code] = severity
    return normalized_inputs, set(severity_by_code), severity_by_code


def _normalize_condition_inputs(
    values: list[str | ConditionInput],
) -> tuple[list[ConditionInput], set[str], dict[str, ConditionStatus]]:
    status_rank = {
        ConditionStatus.RESOLVED: 0,
        ConditionStatus.HISTORY: 1,
        ConditionStatus.SUSPECTED: 2,
        ConditionStatus.ACTIVE: 3,
    }
    normalized_inputs: list[ConditionInput] = []
    status_by_code: dict[str, ConditionStatus] = {}
    for value in values:
        code = normalize_health_input_code(value)
        if not code:
            continue
        normalized_input = (
            value.model_copy(update={"code": code})
            if isinstance(value, ConditionInput)
            else ConditionInput(code=code, status=ConditionStatus.ACTIVE)
        )
        normalized_inputs.append(normalized_input)
        status = normalized_input.status
        current = status_by_code.get(code)
        if current is None or status_rank[status] > status_rank[current]:
            status_by_code[code] = status
    active_codes = {
        code
        for code, status in status_by_code.items()
        if status != ConditionStatus.RESOLVED
    }
    return normalized_inputs, active_codes, status_by_code


def _normalize_risk_signals(
    values: list[str | UrgentRiskSignal],
) -> tuple[list[UrgentRiskSignal], set[str], dict[str, RiskSignalSource]]:
    normalized_inputs: list[UrgentRiskSignal] = []
    source_by_code: dict[str, RiskSignalSource] = {}
    for value in values:
        code = normalize_health_input_code(value)
        if not code:
            continue
        normalized_input = (
            value.model_copy(update={"code": code})
            if isinstance(value, UrgentRiskSignal)
            else UrgentRiskSignal(
                code=code,
                present=True,
                source=RiskSignalSource.LEGACY,
            )
        )
        normalized_inputs.append(normalized_input)
        if normalized_input.present:
            source_by_code[code] = normalized_input.source
    return normalized_inputs, set(source_by_code), source_by_code


def _normalize_catalog_inputs(values: list[str]) -> set[str]:
    normalized_values: set[str] = set()
    for value in values:
        normalized = _normalize_text(value)
        if not normalized:
            continue
        normalized_values.add(canonicalize_catalog_term(value) or normalized)
    return normalized_values
