from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import RecommendationGoal

if TYPE_CHECKING:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord


class EffectModelV1Artifact(BaseModel):
    model_name: str = "effect_model_v1"
    cohort_version: str
    seed: int
    alpha: float
    feature_names: list[str] = Field(default_factory=list)
    output_names: list[str] = Field(default_factory=list)
    intercepts: list[float] = Field(default_factory=list)
    weights: list[list[float]] = Field(default_factory=list)
    target_name: str = "delta_z_by_domain"
    policy_proxy_slope: float = 1.0
    policy_proxy_intercept: float = 0.0
    policy_proxy_clip_min: float = -1.0
    policy_proxy_clip_max: float = 1.0


class EffectFeatureVectorizerV1:
    def __init__(self, feature_names: list[str]) -> None:
        self.feature_names = feature_names
        self._index = {name: idx for idx, name in enumerate(feature_names)}

    @classmethod
    def fit(
        cls,
        feature_rows: list[dict[str, float]],
    ) -> EffectFeatureVectorizerV1:
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


def build_effect_feature_dict_v1(
    record: RichSyntheticCohortRecord,
) -> dict[str, float]:
    request = record.request
    profile = request.user_profile
    lifestyle = request.lifestyle
    availability = request.input_availability
    preferences = request.preferences

    features: dict[str, float] = {
        "age": float(profile.age),
        "pregnant": float(profile.pregnant),
        "trajectory_step": float(record.trajectory_step),
        "day_index": float(record.day_index),
        "goal_count": float(len(request.goals)),
        "symptom_count": float(len(request.symptoms)),
        "condition_count": float(len(request.conditions)),
        "medication_count": float(len(request.medications)),
        "current_supplement_count": float(len(request.current_supplements)),
        "max_products": float(preferences.max_products),
        "sleep_hours": float(lifestyle.sleep_hours or 0.0),
        "stress_level": float(lifestyle.stress_level or 0.0),
        "wearable_available": float(availability.wearable),
        "cgm_available": float(availability.cgm),
        "genetic_available": float(availability.genetic),
        "nhis_available": float(availability.nhis),
        "baseline_aggregate_z": float(record.baseline_pro.aggregate_z),
        "adherence_proxy": float(record.adherence_proxy),
        "side_effect_proxy": float(record.side_effect_proxy),
        "regimen_count": float(len(record.regimen)),
        "active_regimen_count": float(
            sum(1 for item in record.regimen if item.regimen_status == "active")
        ),
        "planned_regimen_count": float(
            sum(1 for item in record.regimen if item.regimen_status == "planned")
        ),
        "reduced_regimen_count": float(
            sum(1 for item in record.regimen if item.regimen_status == "reduced")
        ),
        "stopped_regimen_count": float(
            sum(1 for item in record.regimen if item.regimen_status == "stopped")
        ),
        "total_daily_dose": float(
            round(sum(item.daily_dose for item in record.regimen), 3)
        ),
        "risk_tier_low": float(record.labels.risk_tier == "low"),
        "risk_tier_moderate": float(record.labels.risk_tier == "moderate"),
        "risk_tier_high": float(record.labels.risk_tier == "high"),
    }

    for goal in RecommendationGoal:
        features[f"goal::{goal.value}"] = float(goal in request.goals)
        features[f"baseline::{goal.value}"] = float(
            record.baseline_pro.domain_z.get(goal.value, 0.0)
        )

    for regimen_item in record.regimen:
        features[f"regimen::{regimen_item.ingredient_key}"] = 1.0
        features[f"dose::{regimen_item.ingredient_key}"] = float(
            regimen_item.daily_dose
        )
        features[f"schedule::{regimen_item.schedule}"] = 1.0
        features[f"regimen_status::{regimen_item.regimen_status}"] = 1.0

    return features


def predict_domain_deltas_v1(
    artifact: EffectModelV1Artifact,
    record: RichSyntheticCohortRecord,
) -> dict[str, float]:
    feature_row = build_effect_feature_dict_v1(record)
    return predict_domain_deltas_from_feature_dict_v1(artifact, feature_row)


def predict_domain_deltas_from_feature_dict_v1(
    artifact: EffectModelV1Artifact,
    feature_row: dict[str, float],
) -> dict[str, float]:
    vectorizer = EffectFeatureVectorizerV1(feature_names=artifact.feature_names)
    vector = vectorizer.transform([feature_row])[0]
    predictions: dict[str, float] = {}
    for output_name, intercept, weights in zip(
        artifact.output_names,
        artifact.intercepts,
        artifact.weights,
        strict=True,
    ):
        value = intercept + sum(
            weight * feature_value
            for weight, feature_value in zip(weights, vector, strict=True)
        )
        predictions[output_name] = round(float(value), 6)
    return predictions


def predict_aggregate_delta_v1(
    artifact: EffectModelV1Artifact,
    record: RichSyntheticCohortRecord,
) -> float:
    predictions = predict_domain_deltas_v1(artifact, record)
    if not predictions:
        return 0.0
    return round(sum(predictions.values()) / len(predictions), 6)


def calibrate_policy_effect_proxy_from_aggregate_v1(
    artifact: EffectModelV1Artifact,
    aggregate_delta: float,
) -> float:
    value = artifact.policy_proxy_intercept + (
        artifact.policy_proxy_slope * aggregate_delta
    )
    value = max(artifact.policy_proxy_clip_min, min(artifact.policy_proxy_clip_max, value))
    return round(float(value), 6)


def predict_policy_effect_proxy_v1(
    artifact: EffectModelV1Artifact,
    record: RichSyntheticCohortRecord,
) -> float:
    return calibrate_policy_effect_proxy_from_aggregate_v1(
        artifact,
        predict_aggregate_delta_v1(artifact, record),
    )


def load_effect_model_v1_artifact(path: str | Path) -> EffectModelV1Artifact:
    return EffectModelV1Artifact.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )
