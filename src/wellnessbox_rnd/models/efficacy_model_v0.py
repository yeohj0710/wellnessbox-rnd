from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

if TYPE_CHECKING:
    from wellnessbox_rnd.synthetic.longitudinal import SyntheticCohortRecord


class EfficacyModelArtifact(BaseModel):
    model_name: str = "efficacy_model_v0"
    cohort_version: str
    seed: int
    alpha: float
    feature_names: list[str] = Field(default_factory=list)
    intercept: float
    weights: list[float] = Field(default_factory=list)
    target_name: str = "expected_effect_proxy"


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
        "condition_count": float(len(request.conditions)),
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

    features[f"sex::{profile.biological_sex.value}"] = 1.0
    features[f"activity::{lifestyle.activity_level.value}"] = 1.0
    features[f"budget::{preferences.budget_level.value}"] = 1.0

    for goal in request.goals:
        features[f"goal::{goal.value}"] = 1.0
    for symptom in request.symptoms:
        features[f"symptom::{symptom}"] = 1.0
    for condition in request.conditions:
        features[f"condition::{condition}"] = 1.0
    for medication in request.medications:
        features[f"medication::{medication.name.strip().lower()}"] = 1.0
    for supplement in request.current_supplements:
        for ingredient in supplement.ingredients:
            features[f"current_ingredient::{ingredient}"] = 1.0
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
    return EfficacyModelArtifact.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
