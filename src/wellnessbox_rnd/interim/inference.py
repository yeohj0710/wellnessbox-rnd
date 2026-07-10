from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import csr_matrix

from wellnessbox_rnd.interim.store import InterimStore


@dataclass(frozen=True)
class ModelRecommendation:
    model_id: str
    ingredients: tuple[str, ...]
    scores: tuple[float, ...]
    evidence_ids: tuple[str, ...]


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _age_band(age: object) -> str:
    number = int(age or 40)
    if number < 30:
        return "20s"
    if number < 40:
        return "30s"
    if number < 50:
        return "40s"
    if number < 60:
        return "50s"
    return "60plus"


def feature_tokens(profile: dict[str, Any], goals: list[str]) -> list[str]:
    preferences = profile.get("preferences") if isinstance(profile.get("preferences"), dict) else {}
    tokens = {
        f"age={profile.get('age_band', _age_band(profile.get('age')))}",
        f"sex={profile.get('sex_at_birth', profile.get('biological_sex', 'unknown'))}",
        "pregnancy="
        + str(
            profile.get(
                "pregnancy_status",
                "pregnant" if profile.get("pregnant") else "not_pregnant",
            )
        ),
        f"budget={preferences.get('monthly_budget_krw', 50000)}",
        f"pill_limit={preferences.get('max_daily_pills', 3)}",
        f"form={preferences.get('preferred_form', 'any')}",
    }
    list_keys = (
        "conditions",
        "medication_classes",
        "allergies",
        "diet_patterns",
        "current_supplements",
        "wearable_features",
        "genetic_features",
        "risk_flags",
    )
    for key in list_keys:
        for item in _list(profile.get(key)):
            value = item.get("name") if isinstance(item, dict) else item
            tokens.add(f"{key}:{value}")
    for goal in goals or [str(value) for value in _list(profile.get("goals"))]:
        tokens.add(f"goals:{goal}")
    for symptom in _list(profile.get("symptoms")):
        if isinstance(symptom, dict):
            tokens.add(f"symptom:{symptom.get('code', 'unknown')}")
            tokens.add(f"symptom_severity:{symptom.get('severity', 'unknown')}")
            if symptom.get("red_flag"):
                tokens.add("symptom:red_flag")
        else:
            tokens.add(f"symptom:{symptom}")
    labs = profile.get("labs") if isinstance(profile.get("labs"), dict) else {}
    for name, status in labs.items():
        tokens.add(f"lab:{name}={status}")
    return sorted(tokens)


def recommend_with_registered_model(
    store: InterimStore, *, profile: dict[str, Any], goals: list[str]
) -> ModelRecommendation:
    rows = store.rows(
        """
        select * from model_versions where version like '%retrained%'
        order by created_at desc, model_id desc limit 1
        """
    )
    if not rows:
        raise RuntimeError("retrained_model_not_registered")
    row = rows[0]
    artifact = Path(row["artifact_uri"])
    if not artifact.exists():
        raise RuntimeError("registered_model_artifact_missing")
    model = joblib.load(artifact)
    vocabulary = model["vocabulary"]
    indices = sorted(
        vocabulary[token] for token in feature_tokens(profile, goals) if token in vocabulary
    )
    matrix = csr_matrix(
        (np.ones(len(indices)), ([0] * len(indices), indices)),
        shape=(1, len(vocabulary)),
    )
    probabilities = model["ingredient_model"].predict_proba(matrix)[0]
    count = int(np.clip(model["count_model"].predict(matrix)[0], 1, 3))
    ranked = np.argsort(-probabilities)[:count]
    evidence_rows = store.rows(
        """
        select ep.evidence_id from evidence_passages ep
        join source_registry sr on sr.source_id=ep.source_id
        where ep.approved_for_safety=1 and sr.retired_at is null
          and sr.metadata_json not like '%\"quarantined\":true%'
        order by ep.evidence_id limit 10
        """
    )
    return ModelRecommendation(
        model_id=str(row["model_id"]),
        ingredients=tuple(str(model["ingredients"][index]) for index in ranked),
        scores=tuple(float(probabilities[index]) for index in ranked),
        evidence_ids=tuple(str(item[0]) for item in evidence_rows),
    )
