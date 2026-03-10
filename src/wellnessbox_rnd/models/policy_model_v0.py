from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import NextAction, RecommendationRequest

if TYPE_CHECKING:
    from wellnessbox_rnd.synthetic.longitudinal import SyntheticCohortRecord


class PolicyModelArtifact(BaseModel):
    model_name: str = "policy_model_v0"
    cohort_version: str
    seed: int
    alpha: float
    class_labels: list[str] = Field(default_factory=list)
    feature_names: list[str] = Field(default_factory=list)
    intercepts: list[float] = Field(default_factory=list)
    weights: list[list[float]] = Field(default_factory=list)
    target_name: str = "next_action"


class PolicyFeatureVectorizer:
    def __init__(self, feature_names: list[str]) -> None:
        self.feature_names = feature_names
        self._index = {name: idx for idx, name in enumerate(feature_names)}

    @classmethod
    def fit(cls, feature_rows: list[dict[str, float]]) -> PolicyFeatureVectorizer:
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


def build_policy_feature_dict(record: SyntheticCohortRecord) -> dict[str, float]:
    return build_runtime_policy_feature_dict(
        request=record.request,
        follow_up_step=record.follow_up_step,
        day_index=record.day_index,
        baseline_recommendations=record.baseline_recommendations,
        expected_effect_proxy=record.expected_effect_proxy,
        adherence_proxy=record.adherence_proxy,
        risk_tier=record.labels.risk_tier,
        adverse_event=record.labels.adverse_event,
        closed_loop_state=record.labels.closed_loop_state,
        safety_status=record.labels.safety_status.value,
    )


def build_runtime_policy_feature_dict(
    *,
    request: RecommendationRequest,
    follow_up_step: int,
    day_index: int,
    baseline_recommendations: list[str],
    expected_effect_proxy: float,
    adherence_proxy: float,
    risk_tier: str,
    adverse_event: bool,
    closed_loop_state: str,
    safety_status: str,
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
        "expected_effect_proxy": expected_effect_proxy,
        "adherence_proxy": adherence_proxy,
        "adverse_event": float(adverse_event),
    }

    features[f"sex::{profile.biological_sex.value}"] = 1.0
    features[f"activity::{lifestyle.activity_level.value}"] = 1.0
    features[f"budget::{preferences.budget_level.value}"] = 1.0
    features[f"risk::{risk_tier}"] = 1.0
    features[f"closed_loop_state::{closed_loop_state}"] = 1.0
    features[f"safety_status::{safety_status}"] = 1.0

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


def predict_policy_scores(
    artifact: PolicyModelArtifact,
    record: SyntheticCohortRecord,
) -> dict[str, float]:
    feature_row = build_policy_feature_dict(record)
    return predict_policy_scores_from_feature_dict(artifact, feature_row)


def predict_policy_scores_from_feature_dict(
    artifact: PolicyModelArtifact,
    feature_row: dict[str, float],
) -> dict[str, float]:
    vectorizer = PolicyFeatureVectorizer(feature_names=artifact.feature_names)
    vector = vectorizer.transform([feature_row])[0]
    scores: dict[str, float] = {}
    for label, intercept, weights in zip(
        artifact.class_labels,
        artifact.intercepts,
        artifact.weights,
        strict=True,
    ):
        score = intercept + sum(
            weight * value for weight, value in zip(weights, vector, strict=True)
        )
        scores[label] = round(float(score), 6)
    return scores


def predict_policy_action(
    artifact: PolicyModelArtifact,
    record: SyntheticCohortRecord,
) -> NextAction:
    scores = predict_policy_scores(artifact, record)
    selected_label = max(
        sorted(scores.items()),
        key=lambda item: item[1],
    )[0]
    return NextAction(selected_label)


def load_policy_model_artifact(path: str | Path) -> PolicyModelArtifact:
    return PolicyModelArtifact.model_validate_json(Path(path).read_text(encoding="utf-8"))
