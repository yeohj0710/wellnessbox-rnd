from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.models.efficacy_model_v0 import build_runtime_efficacy_feature_dict
from wellnessbox_rnd.models.policy_model_v0 import build_runtime_policy_feature_dict
from wellnessbox_rnd.schemas.recommendation import (
    LaboratoryObservationInput,
    LaboratoryRangeStatus,
    RecommendationGoal,
    RecommendationRequest,
    UserProfile,
)

FIXTURE_PATH = Path("data/samples/api_recommend_diet_lifestyle_lab_request_v1.json")
client = TestClient(app)


def _structured_request() -> RecommendationRequest:
    return RecommendationRequest.model_validate_json(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_allergies_dietary_patterns_and_lifestyle_are_normalized_without_loss() -> None:
    intake = normalize_request(_structured_request())

    assert intake.normalized_allergies == ["fish", "peanut"]
    assert intake.allergy_set == {"fish", "peanut"}
    assert intake.dietary_pattern_set == {"mediterranean diet", "low sodium"}
    assert [item.code for item in intake.normalized_dietary_patterns] == [
        "low sodium",
        "mediterranean diet",
    ]
    assert intake.normalized_dietary_patterns[0].display_name == "Low-sodium diet"
    assert intake.normalized_dietary_patterns[1].display_name == "Mediterranean diet"
    assert intake.normalized_lifestyle.exercise_minutes_per_week == 95
    assert intake.normalized_lifestyle.caffeine_mg_per_day == 240
    assert "exercise_context_available" in intake.signal_flags
    assert "caffeine_context_available" in intake.signal_flags
    assert "dietary_pattern_context_available" in intake.signal_flags


def test_laboratory_observations_preserve_value_range_and_utc_measurement_time() -> None:
    request = _structured_request()
    older_hba1c = LaboratoryObservationInput.model_validate(
        {
            "code": "HBA1C",
            "value": 5.4,
            "unit": "%",
            "reference_range": {"low": 4.0, "high": 5.6},
            "measured_at": "2026-06-14T09:30:00+09:00",
        }
    )
    request = request.model_copy(
        update={
            "laboratory_observations": [
                older_hba1c,
                *request.laboratory_observations,
            ]
        }
    )

    intake = normalize_request(request)
    hba1c = intake.latest_laboratory_observation_by_code["hba1c"]
    fasting_glucose = intake.latest_laboratory_observation_by_code["fasting glucose"]

    assert hba1c.value == 6.1
    assert hba1c.unit == "%"
    assert hba1c.reference_range.low == 4.0
    assert hba1c.reference_range.high == 5.6
    assert hba1c.measured_at == datetime(2026, 7, 14, 0, 30, tzinfo=UTC)
    assert fasting_glucose.unit == "mg/dL"
    assert intake.laboratory_range_status_by_code == {
        "hba1c": LaboratoryRangeStatus.HIGH,
        "fasting glucose": LaboratoryRangeStatus.HIGH,
    }
    assert "laboratory_context_available" in intake.signal_flags


def test_laboratory_observation_rejects_invalid_ranges_time_and_nonfinite_values() -> None:
    valid = {
        "code": "hba1c",
        "value": 5.4,
        "unit": "%",
        "reference_range": {"low": 4.0, "high": 5.6},
        "measured_at": "2026-07-14T09:30:00+09:00",
    }

    with pytest.raises(ValidationError, match="low cannot exceed high"):
        LaboratoryObservationInput.model_validate(
            {**valid, "reference_range": {"low": 6.0, "high": 5.0}}
        )
    with pytest.raises(ValidationError, match="requires low or high"):
        LaboratoryObservationInput.model_validate(
            {**valid, "reference_range": {"low": None, "high": None}}
        )
    with pytest.raises(ValidationError, match="must include a timezone"):
        LaboratoryObservationInput.model_validate(
            {**valid, "measured_at": datetime(2026, 7, 14, 9, 30)}
        )
    with pytest.raises(ValidationError):
        LaboratoryObservationInput.model_validate({**valid, "value": float("nan")})

    for invalid in (
        {**valid, "value": True},
        {**valid, "reference_range": {"low": False, "high": 5.6}},
    ):
        with pytest.raises(ValidationError, match="must be numeric, not boolean"):
            LaboratoryObservationInput.model_validate(invalid)


def test_new_lifestyle_numeric_fields_reject_boolean_values_at_api_boundary() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["lifestyle"]["exercise_minutes_per_week"] = True

    with pytest.raises(ValidationError, match="must be numeric, not boolean"):
        RecommendationRequest.model_validate(payload)

    response = client.post("/v1/recommend", json=payload)
    assert response.status_code == 422
    assert "must be numeric, not boolean" in response.text

    payload["lifestyle"]["exercise_minutes_per_week"] = 95
    payload["lifestyle"]["caffeine_mg_per_day"] = True
    with pytest.raises(ValidationError, match="must be numeric, not boolean"):
        RecommendationRequest.model_validate(payload)


def test_conflicting_laboratory_observations_at_same_time_are_rejected() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["laboratory_observations"].append(
        {
            "code": "HBA1C",
            "value": 5.2,
            "unit": "%",
            "reference_range": {"low": 4.0, "high": 5.6},
            "measured_at": "2026-07-14T00:30:00Z",
        }
    )

    with pytest.raises(
        ValidationError,
        match="conflicting laboratory observations for the same code and measured_at",
    ):
        RecommendationRequest.model_validate(payload)

    response = client.post("/v1/recommend", json=payload)
    assert response.status_code == 422
    assert "conflicting laboratory observations" in response.text


def test_equivalent_micro_unit_spellings_share_ascii_canonical_units() -> None:
    observations = []
    for unit in ("mcg/L", "\u03bcg/L", "\u00b5g/L"):
        observations.append(
            {
                "code": "ferritin",
                "value": 50,
                "unit": unit,
                "reference_range": {"low": 15, "high": 150},
                "measured_at": "2026-07-14T00:30:00Z",
            }
        )
    for unit in ("umol/L", "\u03bcmol/L", "\u00b5mol/L"):
        observations.append(
            {
                "code": "copper",
                "value": 15,
                "unit": unit,
                "reference_range": {"low": 10, "high": 25},
                "measured_at": "2026-07-14T00:30:00Z",
            }
        )

    request = RecommendationRequest(
        user_profile=UserProfile(age=40, biological_sex="female"),
        goals=[RecommendationGoal.GENERAL_WELLNESS],
        laboratory_observations=observations,
    )
    intake = normalize_request(request)

    assert {
        item.unit for item in intake.normalized_laboratory_observations
    } == {"ug/L", "umol/L"}


def test_diet_lifestyle_and_laboratory_context_reach_existing_model_feature_paths() -> None:
    request = _structured_request()
    efficacy_features = build_runtime_efficacy_feature_dict(
        request=request,
        follow_up_step=0,
        day_index=0,
        baseline_recommendations=[],
        adherence_proxy=1.0,
    )
    policy_features = build_runtime_policy_feature_dict(
        request=request,
        follow_up_step=0,
        day_index=0,
        baseline_recommendations=[],
        expected_effect_proxy=0.0,
        adherence_proxy=1.0,
        risk_tier="low",
        adverse_event=False,
        closed_loop_state="baseline",
        safety_status="ok",
    )

    for features in (efficacy_features, policy_features):
        assert features["allergy::fish"] == 1.0
        assert features["dietary_pattern::mediterranean diet"] == 1.0
        assert features["laboratory::hba1c"] == 1.0
        assert features["laboratory_unit::fasting glucose::mg/dL"] == 1.0
        assert features["laboratory_status::hba1c::high"] == 1.0
        assert features["exercise_minutes_per_week_scaled"] == pytest.approx(
            95 / 10_080
        )
        assert features["caffeine_mg_per_day_scaled"] == pytest.approx(240 / 5_000)


def test_relevant_laboratory_observation_satisfies_glucose_context_request() -> None:
    request = _structured_request()
    missing_codes = {item.code for item in normalize_request(request).missing_information}
    assert "missing_glucose_context" not in missing_codes

    without_labs = request.model_copy(update={"laboratory_observations": []})
    missing_codes = {
        item.code for item in normalize_request(without_labs).missing_information
    }
    assert "missing_glucose_context" in missing_codes


def test_new_lifestyle_fields_are_bounded_and_legacy_defaults_remain_compatible() -> None:
    request = RecommendationRequest(
        user_profile=UserProfile(age=40, biological_sex="female"),
        goals=[RecommendationGoal.GENERAL_WELLNESS],
    )

    assert request.dietary_patterns == []
    assert request.laboratory_observations == []
    assert request.lifestyle.exercise_minutes_per_week is None
    assert request.lifestyle.caffeine_mg_per_day is None

    payload = request.model_dump(mode="json")
    payload["lifestyle"]["exercise_minutes_per_week"] = -1
    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate(payload)


def test_openapi_and_api_expose_structured_diet_lifestyle_lab_contract() -> None:
    openapi = client.get("/openapi.json").json()

    schemas = openapi["components"]["schemas"]
    assert "DietaryPatternInput" in schemas
    assert "LaboratoryObservationInput" in schemas
    assert "LaboratoryReferenceRange" in schemas
    lifestyle_properties = schemas["LifestyleInput"]["properties"]
    assert "exercise_minutes_per_week" in lifestyle_properties
    assert "caffeine_mg_per_day" in lifestyle_properties
    examples = openapi["paths"]["/v1/recommend"]["post"]["requestBody"]["content"][
        "application/json"
    ]["examples"]
    assert "structured_diet_lifestyle_and_laboratory_observations" in examples

    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    response = client.post("/v1/recommend", json=payload)

    assert response.status_code == 200
    missing_codes = {item["code"] for item in response.json()["missing_information"]}
    assert "missing_glucose_context" not in missing_codes
