from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import (
    NextAction,
    RecommendationGoal,
    RecommendationStatus,
)

if TYPE_CHECKING:
    from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord


class PolicyModelV1Artifact(BaseModel):
    model_name: str = "policy_model_v1"
    cohort_version: str
    seed: int
    alpha: float
    class_labels: list[str] = Field(default_factory=list)
    feature_names: list[str] = Field(default_factory=list)
    intercepts: list[float] = Field(default_factory=list)
    weights: list[list[float]] = Field(default_factory=list)
    target_name: str = "next_action"


class PolicyFeatureVectorizerV1:
    def __init__(self, feature_names: list[str]) -> None:
        self.feature_names = feature_names
        self._index = {name: idx for idx, name in enumerate(feature_names)}

    @classmethod
    def fit(
        cls,
        feature_rows: list[dict[str, float]],
    ) -> PolicyFeatureVectorizerV1:
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


def build_policy_feature_dict_v1(
    record: RichSyntheticCohortRecord,
) -> dict[str, float]:
    feature_row = {
        "age": float(record.request.user_profile.age),
        "pregnant": float(record.request.user_profile.pregnant),
        "goal_count": float(len(record.request.goals)),
        "symptom_count": float(len(record.request.symptoms)),
        "condition_count": float(len(record.request.conditions)),
        "medication_count": float(len(record.request.medications)),
        "current_supplement_count": float(len(record.request.current_supplements)),
        "max_products": float(record.request.preferences.max_products),
        "sleep_hours": float(record.request.lifestyle.sleep_hours or 0.0),
        "stress_level": float(record.request.lifestyle.stress_level or 0.0),
        "wearable_available": float(record.request.input_availability.wearable),
        "cgm_available": float(record.request.input_availability.cgm),
        "genetic_available": float(record.request.input_availability.genetic),
        "trajectory_step": float(record.trajectory_step),
        "day_index": float(record.day_index),
        "baseline_aggregate_z": float(record.baseline_pro.aggregate_z),
        "follow_up_aggregate_z": float(record.follow_up_pro.aggregate_z),
        "delta_aggregate_z": float(
            round(
                record.follow_up_pro.aggregate_z - record.baseline_pro.aggregate_z,
                3,
            )
        ),
        "expected_effect_proxy": float(record.expected_effect_proxy),
        "adherence_proxy": float(record.adherence_proxy),
        "side_effect_proxy": float(record.side_effect_proxy),
        "regimen_count": float(len(record.regimen)),
        "regimen_reduced_count": float(
            sum(1 for item in record.regimen if item.regimen_status == "reduced")
        ),
        "regimen_stopped_count": float(
            sum(1 for item in record.regimen if item.regimen_status == "stopped")
        ),
        "risk_tier_low": float(record.labels.risk_tier == "low"),
        "risk_tier_moderate": float(record.labels.risk_tier == "moderate"),
        "risk_tier_high": float(record.labels.risk_tier == "high"),
        "safety_status_ok": float(record.labels.safety_status == RecommendationStatus.OK),
        "safety_status_needs_review": float(
            record.labels.safety_status == RecommendationStatus.NEEDS_REVIEW
        ),
        "safety_status_blocked": float(record.labels.safety_status == RecommendationStatus.BLOCKED),
    }
    for goal in RecommendationGoal:
        feature_row[f"goal::{goal.value}"] = float(goal in record.request.goals)
        feature_row[f"baseline::{goal.value}"] = float(
            record.baseline_pro.domain_z.get(goal.value, 0.0)
        )
        feature_row[f"follow_up::{goal.value}"] = float(
            record.follow_up_pro.domain_z.get(goal.value, 0.0)
        )
        feature_row[f"delta::{goal.value}"] = float(record.delta_z_by_domain.get(goal.value, 0.0))
    return feature_row


def predict_policy_scores_v1(
    artifact: PolicyModelV1Artifact,
    record: RichSyntheticCohortRecord,
) -> dict[str, float]:
    feature_row = build_policy_feature_dict_v1(record)
    return predict_policy_scores_from_feature_dict_v1(artifact, feature_row)


def predict_policy_scores_from_feature_dict_v1(
    artifact: PolicyModelV1Artifact,
    feature_row: dict[str, float],
) -> dict[str, float]:
    vectorizer = PolicyFeatureVectorizerV1(feature_names=artifact.feature_names)
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


def predict_policy_action_v1(
    artifact: PolicyModelV1Artifact,
    record: RichSyntheticCohortRecord,
) -> NextAction:
    scores = predict_policy_scores_v1(artifact, record)
    selected_label = max(
        sorted(scores.items()),
        key=lambda item: item[1],
    )[0]
    return NextAction(selected_label)


def load_policy_model_v1_artifact(path: str | Path) -> PolicyModelV1Artifact:
    return PolicyModelV1Artifact.model_validate_json(Path(path).read_text(encoding="utf-8"))
