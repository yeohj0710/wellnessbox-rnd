from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.domain.intake import (
    build_normalized_input_snapshot_v1,
    calculate_normalized_input_sha256_v1,
    normalize_request,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

FIXTURE_PATH = Path("data/samples/api_recommend_consent_hash_request_v1.json")
client = TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "request_id": "consent-hash-case-a",
        "user_profile": {
            "age": 42,
            "biological_sex": "female",
            "pregnant": False,
            "height_cm": 165,
            "weight_kg": 61,
        },
        "goals": ["blood_glucose", "general_wellness"],
        "symptoms": ["post_meal_spike_concern", "fatigue"],
        "conditions": [],
        "allergies": [" Peanut ", "fish"],
        "risk_flags": [],
        "medications": [],
        "current_supplements": [
            {
                "name": "Daily Mix",
                "ingredients": [
                    {"name": "Vitamin D3"},
                    {"name": "Magnesium"},
                ],
            }
        ],
        "dietary_patterns": ["Low Sodium", "mediterranean diet"],
        "laboratory_observations": [
            {
                "code": "HBA1C",
                "value": 5.8,
                "unit": "%",
                "reference_range": {"low": 4.0, "high": 5.6},
                "measured_at": "2026-07-14T09:30:00+09:00",
            },
            {
                "code": "Fasting Glucose",
                "value": 101,
                "unit": "MG/DL",
                "reference_range": {"low": 70, "high": 99},
                "measured_at": "2026-07-14T09:30:00+09:00",
            },
        ],
        "lifestyle": {
            "sleep_hours": 6.5,
            "stress_level": 3,
            "activity_level": "lightly_active",
            "exercise_minutes_per_week": 120,
            "smoker": False,
            "alcohol_per_week": 1,
            "caffeine_mg_per_day": 180,
        },
        "input_availability": {
            "survey": True,
            "nhis": True,
            "wearable": True,
            "cgm": True,
            "genetic": True,
        },
        "data_source_consents": {
            "survey": {
                "use_for_recommendation": True,
                "allow_persistent_storage": True,
            },
            "nhis": {
                "use_for_recommendation": False,
                "allow_persistent_storage": False,
            },
            "wearable": {
                "use_for_recommendation": True,
                "allow_persistent_storage": False,
            },
            "cgm": {
                "use_for_recommendation": False,
                "allow_persistent_storage": True,
            },
            "genetic": {
                "use_for_recommendation": False,
                "allow_persistent_storage": False,
            },
        },
        "preferences": {
            "budget_level": "medium",
            "max_products": 2,
            "avoid_ingredients": ["Ginseng"],
        },
    }


def test_data_source_consents_separate_use_and_storage_for_all_five_sources() -> None:
    request = RecommendationRequest.model_validate(_payload())
    intake = normalize_request(request)

    assert request.data_source_consents.model_dump(mode="json") == {
        "survey": {
            "use_for_recommendation": True,
            "allow_persistent_storage": True,
        },
        "nhis": {
            "use_for_recommendation": False,
            "allow_persistent_storage": False,
        },
        "wearable": {
            "use_for_recommendation": True,
            "allow_persistent_storage": False,
        },
        "cgm": {
            "use_for_recommendation": False,
            "allow_persistent_storage": True,
        },
        "genetic": {
            "use_for_recommendation": False,
            "allow_persistent_storage": False,
        },
    }
    assert intake.recommendation_authorized_input_source_set == {
        "survey",
        "wearable",
    }
    assert intake.storage_authorized_input_source_set == {"survey", "cgm"}
    assert intake.effective_input_availability.model_dump() == {
        "survey": True,
        "nhis": False,
        "wearable": True,
        "cgm": False,
        "genetic": False,
    }
    assert "wearable_data_available" in intake.signal_flags
    assert "cgm_data_available" not in intake.signal_flags
    assert "genetic_data_available" not in intake.signal_flags


def test_consent_denial_removes_optional_source_influence_from_recommendation() -> None:
    denied_payload = _payload()
    absent_payload = deepcopy(denied_payload)
    absent_payload["input_availability"]["cgm"] = False  # type: ignore[index]

    denied_response = recommend(RecommendationRequest.model_validate(denied_payload))
    absent_response = recommend(RecommendationRequest.model_validate(absent_payload))

    assert denied_response.next_action == absent_response.next_action
    assert denied_response.missing_information == absent_response.missing_information
    assert denied_response.recommendations == absent_response.recommendations


def test_genetic_consent_denial_removes_structured_variants_from_hash_and_score() -> None:
    denied_payload = _payload()
    denied_payload["sensor_genetic_snapshot"] = {
        "genetic_available": True,
        "genetic_tags": ["lpl_triglyceride_risk"],
        "genetic_variants": [
            {
                "gene_symbol": "LPL",
                "variant_id": "rs328",
                "genotype": "C/G",
                "interpretation": "increased_risk",
                "interpretation_criterion": "panel-v1",
                "testing_laboratory": "Example Genomics",
                "tested_on": "2026-06-30",
            }
        ],
    }
    absent_payload = deepcopy(denied_payload)
    absent_payload["sensor_genetic_snapshot"] = {"genetic_available": False}

    denied_request = RecommendationRequest.model_validate(denied_payload)
    absent_request = RecommendationRequest.model_validate(absent_payload)
    denied_intake = normalize_request(denied_request)
    absent_intake = normalize_request(absent_request)

    assert denied_intake.sensor_genetic_snapshot is not None
    assert denied_intake.sensor_genetic_snapshot.genetic_variants == []
    assert denied_intake.sensor_genetic_snapshot.genetic_tags == []
    assert calculate_normalized_input_sha256_v1(
        denied_intake
    ) == calculate_normalized_input_sha256_v1(absent_intake)
    assert recommend(denied_request).recommendations == recommend(absent_request).recommendations


def test_legacy_request_materializes_explicit_non_persistent_source_scopes() -> None:
    payload = _payload()
    payload.pop("data_source_consents")

    request = RecommendationRequest.model_validate(payload)

    assert request.data_source_consents.model_dump(mode="json") == {
        source: {
            "use_for_recommendation": True,
            "allow_persistent_storage": False,
        }
        for source in ("survey", "nhis", "wearable", "cgm", "genetic")
    }


def test_partial_explicit_consent_block_denies_every_omitted_source() -> None:
    payload = _payload()
    payload["data_source_consents"] = {
        "survey": {
            "use_for_recommendation": True,
            "allow_persistent_storage": False,
        }
    }

    request = RecommendationRequest.model_validate(payload)

    assert request.data_source_consents.survey.use_for_recommendation is True
    for source in ("nhis", "wearable", "cgm", "genetic"):
        consent = getattr(request.data_source_consents, source)
        assert consent.use_for_recommendation is False
        assert consent.allow_persistent_storage is False


def test_survey_consent_denial_fails_closed_at_model_and_api_boundaries() -> None:
    payload = _payload()
    payload["data_source_consents"]["survey"][  # type: ignore[index]
        "use_for_recommendation"
    ] = False

    with pytest.raises(ValidationError, match="survey use_for_recommendation consent"):
        RecommendationRequest.model_validate(payload)

    response = client.post("/v1/recommend", json=payload)
    assert response.status_code == 422


def test_denied_nhis_laboratory_content_cannot_change_normalized_input_or_result() -> None:
    first_payload = _payload()
    second_payload = deepcopy(first_payload)
    for observation in first_payload["laboratory_observations"]:  # type: ignore[union-attr]
        observation["source"] = "nhis"
    for observation in second_payload["laboratory_observations"]:  # type: ignore[union-attr]
        observation["source"] = "nhis"
        observation["value"] = float(observation["value"]) * 10

    first_request = RecommendationRequest.model_validate(first_payload)
    second_request = RecommendationRequest.model_validate(second_payload)
    first = normalize_request(first_request)
    second = normalize_request(second_request)

    assert first.normalized_laboratory_observations == []
    assert second.normalized_laboratory_observations == []
    assert build_normalized_input_snapshot_v1(first) == build_normalized_input_snapshot_v1(
        second
    )
    assert calculate_normalized_input_sha256_v1(
        first
    ) == calculate_normalized_input_sha256_v1(second)
    assert recommend(first_request).recommendations == recommend(second_request).recommendations


def test_unavailable_nhis_laboratory_content_cannot_enter_normalized_input() -> None:
    payload = _payload()
    payload["input_availability"]["nhis"] = False  # type: ignore[index]
    payload["data_source_consents"]["nhis"][  # type: ignore[index]
        "use_for_recommendation"
    ] = True
    for observation in payload["laboratory_observations"]:  # type: ignore[union-attr]
        observation["source"] = "nhis"

    intake = normalize_request(RecommendationRequest.model_validate(payload))

    assert "nhis" not in intake.recommendation_authorized_input_source_set
    assert intake.normalized_laboratory_observations == []


def test_denied_laboratory_record_cannot_trigger_conflict_validation() -> None:
    payload = _payload()
    survey_observation = deepcopy(payload["laboratory_observations"][0])  # type: ignore[index]
    survey_observation["source"] = "survey"
    denied_observation = deepcopy(survey_observation)
    denied_observation["source"] = "nhis"
    denied_observation["value"] = 9.9
    payload["laboratory_observations"] = [survey_observation, denied_observation]

    request = RecommendationRequest.model_validate(payload)
    intake = normalize_request(request)

    assert [item.source.value for item in intake.normalized_laboratory_observations] == [
        "survey"
    ]
    assert client.post("/v1/recommend", json=payload).status_code == 200

    payload["data_source_consents"]["nhis"][  # type: ignore[index]
        "use_for_recommendation"
    ] = True
    with pytest.raises(ValidationError, match="conflicting laboratory observations"):
        RecommendationRequest.model_validate(payload)


def test_consent_contract_rejects_unknown_sources_and_non_boolean_values() -> None:
    payload = _payload()
    payload["data_source_consents"]["unknown"] = {  # type: ignore[index]
        "use_for_recommendation": True,
        "allow_persistent_storage": False,
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RecommendationRequest.model_validate(payload)

    payload = _payload()
    payload["data_source_consents"]["cgm"]["use_for_recommendation"] = 1  # type: ignore[index]
    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)


def test_same_normalized_input_has_same_snapshot_and_sha256() -> None:
    first_payload = _payload()
    second_payload = deepcopy(first_payload)
    second_payload["request_id"] = "consent-hash-case-b"
    second_payload["goals"] = list(reversed(second_payload["goals"]))  # type: ignore[arg-type]
    second_payload["symptoms"] = [" FATIGUE ", "post_meal_spike_concern"]
    second_payload["allergies"] = ["FISH", "peanut"]
    second_payload["dietary_patterns"] = [" Mediterranean Diet ", "low sodium"]
    second_payload["laboratory_observations"] = list(  # type: ignore[arg-type]
        reversed(second_payload["laboratory_observations"])
    )
    second_payload["current_supplements"][0]["ingredients"] = list(  # type: ignore[index]
        reversed(second_payload["current_supplements"][0]["ingredients"])  # type: ignore[index]
    )

    first = normalize_request(RecommendationRequest.model_validate(first_payload))
    second = normalize_request(RecommendationRequest.model_validate(second_payload))

    assert build_normalized_input_snapshot_v1(first) == build_normalized_input_snapshot_v1(
        second
    )
    assert calculate_normalized_input_sha256_v1(
        first
    ) == calculate_normalized_input_sha256_v1(second)
    assert re.fullmatch(r"[0-9a-f]{64}", calculate_normalized_input_sha256_v1(first))
    assert "request_id" not in json.dumps(
        build_normalized_input_snapshot_v1(first), sort_keys=True
    )


def test_explicit_false_lactation_preserves_legacy_snapshot_and_hash() -> None:
    legacy_payload = _payload()
    explicit_false_payload = deepcopy(legacy_payload)
    explicit_false_payload["user_profile"]["lactating"] = False  # type: ignore[index]

    legacy = normalize_request(RecommendationRequest.model_validate(legacy_payload))
    explicit_false = normalize_request(
        RecommendationRequest.model_validate(explicit_false_payload)
    )

    assert build_normalized_input_snapshot_v1(
        legacy
    ) == build_normalized_input_snapshot_v1(explicit_false)
    assert calculate_normalized_input_sha256_v1(
        legacy
    ) == calculate_normalized_input_sha256_v1(explicit_false)
    assert "lactating" not in build_normalized_input_snapshot_v1(legacy)["user_profile"]


def test_consent_change_changes_normalized_snapshot_hash() -> None:
    first_payload = _payload()
    second_payload = deepcopy(first_payload)
    second_payload["data_source_consents"]["genetic"][  # type: ignore[index]
        "allow_persistent_storage"
    ] = True

    first = normalize_request(RecommendationRequest.model_validate(first_payload))
    second = normalize_request(RecommendationRequest.model_validate(second_payload))

    assert calculate_normalized_input_sha256_v1(
        first
    ) != calculate_normalized_input_sha256_v1(second)


def test_positive_and_negative_zero_have_one_normalized_snapshot_hash() -> None:
    first_payload = _payload()
    second_payload = deepcopy(first_payload)
    first_payload["lifestyle"]["exercise_minutes_per_week"] = 0.0  # type: ignore[index]
    second_payload["lifestyle"]["exercise_minutes_per_week"] = -0.0  # type: ignore[index]

    first = normalize_request(RecommendationRequest.model_validate(first_payload))
    second = normalize_request(RecommendationRequest.model_validate(second_payload))

    assert build_normalized_input_snapshot_v1(first) == build_normalized_input_snapshot_v1(
        second
    )
    assert calculate_normalized_input_sha256_v1(
        first
    ) == calculate_normalized_input_sha256_v1(second)


def test_representative_fixture_and_openapi_example_use_real_consent_contract() -> None:
    request = RecommendationRequest.model_validate_json(FIXTURE_PATH.read_text(encoding="utf-8"))
    intake = normalize_request(request)

    assert calculate_normalized_input_sha256_v1(intake)
    assert intake.recommendation_authorized_input_source_set == {
        "survey",
        "wearable",
    }
    assert intake.storage_authorized_input_source_set == {"survey", "wearable"}

    response = client.post("/v1/recommend", json=json.loads(FIXTURE_PATH.read_text("utf-8")))
    assert response.status_code == 200

    examples = app.openapi()["paths"]["/v1/recommend"]["post"]["requestBody"][
        "content"
    ]["application/json"]["examples"]
    assert "consent_scoped_deterministic_input" in examples
    assert examples["consent_scoped_deterministic_input"]["value"][
        "data_source_consents"
    ] == request.data_source_consents.model_dump(mode="json")
