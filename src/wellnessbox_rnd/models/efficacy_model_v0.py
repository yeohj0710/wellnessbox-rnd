from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wellnessbox_rnd.domain.catalog import canonicalize_catalog_term, get_catalog_index
from wellnessbox_rnd.domain.intake import build_normalized_health_context_feature_dict
from wellnessbox_rnd.schemas.recommendation import (
    ActivityLevel,
    BiologicalSex,
    BudgetLevel,
    LaboratoryRangeStatus,
    RecommendationGoal,
    RecommendationRequest,
    count_current_condition_inputs,
    is_current_condition_input,
    normalize_health_input_code,
    normalize_medication_classification_key,
    normalize_supplement_ingredient_name,
)

if TYPE_CHECKING:
    from wellnessbox_rnd.synthetic.longitudinal import SyntheticCohortRecord


class EfficacyModelArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    cohort_version: str = Field(min_length=1)
    seed: int = Field(ge=0)
    alpha: float
    feature_names: list[str] = Field(default_factory=list)
    intercept: float
    weights: list[float] = Field(default_factory=list)
    target_name: str

    @field_validator("cohort_version")
    @classmethod
    def require_nonblank_cohort_version(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("cohort_version must not be blank")
        return value.strip()


_RUNTIME_SCALAR_FEATURE_NAMES = {
    "adherence_proxy",
    "age_scaled",
    "alcohol_scaled",
    "allergy_count",
    "avoid_count",
    "baseline_recommendation_count",
    "caffeine_mg_per_day_missing",
    "caffeine_mg_per_day_scaled",
    "cgm_available",
    "condition_count",
    "current_supplement_count",
    "day_index_scaled",
    "dietary_pattern_count",
    "exercise_minutes_per_week_missing",
    "exercise_minutes_per_week_scaled",
    "follow_up_step",
    "genetic_available",
    "goal_count",
    "laboratory_observation_count",
    "max_products_scaled",
    "medication_count",
    "nhis_available",
    "pregnant",
    "sleep_hours_missing",
    "sleep_hours_scaled",
    "smoker",
    "stress_level_missing",
    "stress_level_scaled",
    "symptom_count",
    "wearable_available",
}
_RUNTIME_DYNAMIC_FEATURE_PREFIXES = (
    "activity::",
    "allergy::",
    "baseline_candidate::",
    "budget::",
    "condition::",
    "current_ingredient::",
    "dietary_pattern::",
    "goal::",
    "laboratory::",
    "laboratory_status::",
    "laboratory_unit::",
    "medication::",
    "medication_classification::",
    "sex::",
    "symptom::",
)
_MAX_ABSOLUTE_RUNTIME_COEFFICIENT = 10.0


def validate_efficacy_model_artifact_for_runtime(
    artifact: EfficacyModelArtifact,
) -> list[str]:
    issues: list[str] = []
    if artifact.model_name != "efficacy_model_v0":
        issues.append("unexpected_model_name")
    if artifact.target_name != "expected_effect_proxy":
        issues.append("unexpected_target_name")
    if not artifact.feature_names:
        issues.append("empty_feature_names")
    if len(artifact.feature_names) > 4096:
        issues.append("feature_count_exceeds_runtime_limit")
    if any(not value.strip() for value in artifact.feature_names):
        issues.append("empty_feature_name")
    if any(value != value.strip() for value in artifact.feature_names):
        issues.append("feature_name_has_surrounding_whitespace")
    if any(value.endswith("::") for value in artifact.feature_names):
        issues.append("malformed_dynamic_feature_name")
    if len(set(artifact.feature_names)) != len(artifact.feature_names):
        issues.append("duplicate_feature_name")
    if any(
        feature_name not in _RUNTIME_SCALAR_FEATURE_NAMES
        and not feature_name.startswith(_RUNTIME_DYNAMIC_FEATURE_PREFIXES)
        for feature_name in artifact.feature_names
    ):
        issues.append("unsupported_runtime_feature")
    closed_feature_values = {
        "activity::": {item.value for item in ActivityLevel},
        "budget::": {item.value for item in BudgetLevel},
        "goal::": {item.value for item in RecommendationGoal},
        "sex::": {item.value for item in BiologicalSex},
    }
    if any(
        feature_name.removeprefix(prefix) not in allowed_values
        for feature_name in artifact.feature_names
        for prefix, allowed_values in closed_feature_values.items()
        if feature_name.startswith(prefix)
    ):
        issues.append("unsupported_closed_domain_feature")
    if any(
        feature_name.rsplit("::", maxsplit=1)[-1]
        not in {item.value for item in LaboratoryRangeStatus}
        for feature_name in artifact.feature_names
        if feature_name.startswith("laboratory_status::")
    ):
        issues.append("unsupported_laboratory_status_feature")
    if not any(
        feature_name.startswith("baseline_candidate::") for feature_name in artifact.feature_names
    ):
        issues.append("missing_candidate_specific_feature")
    catalog_keys = set(get_catalog_index())
    if any(
        feature_name.removeprefix("baseline_candidate::") not in catalog_keys
        for feature_name in artifact.feature_names
        if feature_name.startswith("baseline_candidate::")
    ):
        issues.append("unsupported_candidate_feature")
    if len(artifact.feature_names) != len(artifact.weights):
        issues.append("feature_weight_dimension_mismatch")
    if not math.isfinite(artifact.alpha) or artifact.alpha <= 0.0:
        issues.append("invalid_regularization_alpha")
    if not math.isfinite(artifact.intercept):
        issues.append("nonfinite_intercept")
    elif abs(artifact.intercept) > _MAX_ABSOLUTE_RUNTIME_COEFFICIENT:
        issues.append("intercept_exceeds_runtime_limit")
    if any(not math.isfinite(value) for value in artifact.weights):
        issues.append("nonfinite_weight")
    elif any(abs(value) > _MAX_ABSOLUTE_RUNTIME_COEFFICIENT for value in artifact.weights):
        issues.append("weight_exceeds_runtime_limit")
    return issues


class EfficacyFeatureVectorizer:
    def __init__(self, feature_names: list[str]) -> None:
        self.feature_names = feature_names
        self._index = {name: idx for idx, name in enumerate(feature_names)}

    @classmethod
    def fit(cls, feature_rows: list[dict[str, float]]) -> EfficacyFeatureVectorizer:
        names = sorted({key for row in feature_rows for key in row})
        return cls(feature_names=names)

    def transform(self, feature_rows: list[dict[str, float]]) -> list[list[float]]:
        matrix: list[list[float]] = []
        for row in feature_rows:
            vector = [0.0] * len(self.feature_names)
            for key, value in row.items():
                idx = self._index.get(key)
                if idx is not None:
                    vector[idx] = float(value)
            matrix.append(vector)
        return matrix


def build_efficacy_feature_dict(record: SyntheticCohortRecord) -> dict[str, float]:
    return build_runtime_efficacy_feature_dict(
        request=record.request,
        follow_up_step=record.follow_up_step,
        day_index=record.day_index,
        baseline_recommendations=record.baseline_recommendations,
        adherence_proxy=record.adherence_proxy,
    )


def build_runtime_efficacy_feature_dict(
    *,
    request: RecommendationRequest,
    follow_up_step: int,
    day_index: int,
    baseline_recommendations: list[str],
    adherence_proxy: float,
) -> dict[str, float]:
    profile = request.user_profile
    lifestyle = request.lifestyle
    availability = request.input_availability
    preferences = request.preferences

    features: dict[str, float] = {
        "age_scaled": profile.age / 100.0,
        "pregnant": float(profile.pregnant),
        "follow_up_step": float(follow_up_step),
        "day_index_scaled": day_index / 30.0,
        "goal_count": float(len(request.goals)),
        "symptom_count": float(len(request.symptoms)),
        "condition_count": float(count_current_condition_inputs(request.conditions)),
        "medication_count": float(len(request.medications)),
        "current_supplement_count": float(len(request.current_supplements)),
        "max_products_scaled": preferences.max_products / 5.0,
        "avoid_count": float(len(preferences.avoid_ingredients)),
        "sleep_hours_scaled": (
            0.0 if lifestyle.sleep_hours is None else lifestyle.sleep_hours / 10.0
        ),
        "sleep_hours_missing": float(lifestyle.sleep_hours is None),
        "stress_level_scaled": (
            0.0 if lifestyle.stress_level is None else lifestyle.stress_level / 5.0
        ),
        "stress_level_missing": float(lifestyle.stress_level is None),
        "smoker": float(lifestyle.smoker),
        "alcohol_scaled": lifestyle.alcohol_per_week / 10.0,
        "wearable_available": float(availability.wearable),
        "cgm_available": float(availability.cgm),
        "genetic_available": float(availability.genetic),
        "nhis_available": float(availability.nhis),
        "baseline_recommendation_count": float(len(baseline_recommendations)),
        "adherence_proxy": adherence_proxy,
    }
    features.update(build_normalized_health_context_feature_dict(request))

    features[f"sex::{profile.biological_sex.value}"] = 1.0
    features[f"activity::{lifestyle.activity_level.value}"] = 1.0
    features[f"budget::{preferences.budget_level.value}"] = 1.0

    for goal in request.goals:
        features[f"goal::{goal.value}"] = 1.0
    for symptom in request.symptoms:
        features[f"symptom::{normalize_health_input_code(symptom)}"] = 1.0
    for condition in request.conditions:
        if not is_current_condition_input(condition):
            continue
        features[f"condition::{normalize_health_input_code(condition)}"] = 1.0
    for medication in request.medications:
        features[f"medication::{medication.name.strip().lower()}"] = 1.0
        if medication.classification is not None:
            classification_key = normalize_medication_classification_key(medication.classification)
            features[f"medication_classification::{classification_key}"] = 1.0
    for supplement in request.current_supplements:
        for ingredient in supplement.ingredients:
            ingredient_name = normalize_supplement_ingredient_name(ingredient)
            ingredient_key = canonicalize_catalog_term(ingredient_name) or ingredient_name
            features[f"current_ingredient::{ingredient_key}"] = 1.0
    for ingredient in baseline_recommendations:
        features[f"baseline_candidate::{ingredient}"] = 1.0

    return features


def predict_effect_proxy(
    artifact: EfficacyModelArtifact,
    record: SyntheticCohortRecord,
) -> float:
    row = build_efficacy_feature_dict(record)
    return predict_effect_proxy_from_feature_dict(artifact, row)


def predict_effect_proxy_from_feature_dict(
    artifact: EfficacyModelArtifact,
    feature_row: dict[str, float],
) -> float:
    vectorizer = EfficacyFeatureVectorizer(feature_names=artifact.feature_names)
    vector = vectorizer.transform([feature_row])[0]
    prediction = artifact.intercept + sum(
        weight * value for weight, value in zip(artifact.weights, vector, strict=True)
    )
    return max(-1.0, min(1.0, round(prediction, 6)))


def load_efficacy_model_artifact(path: str | Path) -> EfficacyModelArtifact:
    return EfficacyModelArtifact.model_validate_json(Path(path).read_text(encoding="utf-8"))
