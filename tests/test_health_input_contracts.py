from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.models.efficacy_model_v0 import build_runtime_efficacy_feature_dict
from wellnessbox_rnd.models.policy_model_v0 import build_runtime_policy_feature_dict
from wellnessbox_rnd.schemas.recommendation import (
    ConditionInput,
    ConditionStatus,
    RecommendationRequest,
    RecommendationStatus,
    RiskSignalSource,
    SymptomSeverity,
    UserProfile,
)
from wellnessbox_rnd.simulation import closed_loop_v0
from wellnessbox_rnd.synthetic import (
    longitudinal,
    rich_longitudinal_v2,
    rich_longitudinal_v3,
    rich_longitudinal_v4,
)

client = TestClient(app)
FIXTURE_PATH = Path("data/samples/api_recommend_structured_health_input_request_v1.json")


def _structured_request() -> RecommendationRequest:
    return RecommendationRequest.model_validate_json(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_user_profile_structures_height_and_weight_with_bounds() -> None:
    profile = UserProfile(
        age=52,
        biological_sex="male",
        pregnant=False,
        height_cm=176.5,
        weight_kg=82.4,
    )

    assert profile.height_cm == 176.5
    assert profile.weight_kg == 82.4
    with pytest.raises(ValidationError):
        UserProfile(
            age=52,
            biological_sex="male",
            height_cm=0,
            weight_kg=82.4,
        )


def test_structured_health_inputs_preserve_status_severity_and_signal_source() -> None:
    intake = normalize_request(_structured_request())

    assert intake.symptom_set == {"chest_pressure"}
    assert intake.symptom_severity_by_code == {
        "chest_pressure": SymptomSeverity.CRITICAL
    }
    assert intake.normalized_symptoms[0].duration_days == 0
    assert intake.condition_set == {"hypertension"}
    assert intake.condition_status_by_code == {
        "hypertension": ConditionStatus.ACTIVE,
        "resolved_condition": ConditionStatus.RESOLVED,
    }
    assert intake.normalized_conditions[0].display_name == "Hypertension"
    assert intake.risk_flag_set == {"red_flag_chest_pain"}
    assert intake.risk_signal_source_by_code == {
        "red_flag_chest_pain": RiskSignalSource.SELF_REPORT
    }
    assert intake.normalized_risk_signals[1].present is False
    assert (
        intake.normalized_risk_signals[1].source
        == RiskSignalSource.IMPORTED_RECORD
    )


def test_legacy_strings_and_structured_objects_share_one_normalized_code_path() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["symptoms"] = [" Chest   Pressure "]
    payload["conditions"] = [" Hypertension "]
    payload["risk_flags"] = [" Red_Flag_Chest_Pain "]

    intake = normalize_request(RecommendationRequest.model_validate(payload))

    assert intake.symptom_set == {"chest pressure"}
    assert intake.symptom_severity_by_code == {
        "chest pressure": SymptomSeverity.UNSPECIFIED
    }
    assert intake.condition_status_by_code == {
        "hypertension": ConditionStatus.ACTIVE
    }
    assert intake.risk_signal_source_by_code == {
        "red_flag_chest_pain": RiskSignalSource.LEGACY
    }


def test_structured_urgent_signal_stops_api_recommendations() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    response = client.post("/v1/recommend", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "blocked"
    assert body["recommendations"] == []
    assert body["next_action"] == "trigger_safety_recheck"
    assert any(
        item["rule_id"] == "SAFETY-URGENT-SYMPTOM-001"
        for item in body["safety_summary"]["rule_refs"]
    )


def test_structured_codes_remain_stable_in_existing_model_feature_paths() -> None:
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
        risk_tier="high",
        adverse_event=False,
        closed_loop_state="baseline",
        safety_status="blocked",
    )

    for features in (efficacy_features, policy_features):
        assert features["symptom::chest_pressure"] == 1.0
        assert features["condition::hypertension"] == 1.0
        assert "condition::resolved_condition" not in features
        assert features["condition_count"] == 1.0
        assert all("code=" not in key for key in features)


def test_resolved_condition_does_not_activate_risk_or_learned_model_guards() -> None:
    request = _structured_request().model_copy(
        update={
            "conditions": [
                ConditionInput(code="resolved_condition", status=ConditionStatus.RESOLVED)
            ],
            "risk_flags": [],
            "medications": [],
        }
    )
    response = SimpleNamespace(
        status=RecommendationStatus.OK,
        safety_summary=SimpleNamespace(rule_refs=[]),
        recommendations=[object(), object()],
    )
    record = SimpleNamespace(
        trajectory_step=1,
        labels=SimpleNamespace(risk_tier="low"),
        request=request,
    )

    assert longitudinal._risk_tier(request=request, response=response) == "low"
    assert rich_longitudinal_v2._risk_tier(request, response) == "low"
    assert closed_loop_v0._can_apply_learned_effect_guard(
        record=record,
        response=response,
    ) == (True, None)
    assert closed_loop_v0._policy_guard_reason(record=record, response=response) is None
    assert rich_longitudinal_v3._is_effect_enrichment_target(record) is True
    assert rich_longitudinal_v4._is_effect_enrichment_target(record) is True

    active_request = request.model_copy(
        update={
            "conditions": [
                ConditionInput(code="active_condition", status=ConditionStatus.ACTIVE)
            ]
        }
    )
    active_record = SimpleNamespace(
        trajectory_step=1,
        labels=SimpleNamespace(risk_tier="low"),
        request=active_request,
    )

    assert rich_longitudinal_v2._risk_tier(active_request, response) == "high"
    assert closed_loop_v0._policy_guard_reason(
        record=active_record,
        response=response,
    ) == "serious_condition_requires_deterministic_policy"


def test_openapi_exposes_structured_health_input_contract_and_example() -> None:
    body = client.get("/openapi.json").json()

    profile_properties = body["components"]["schemas"]["UserProfile"]["properties"]
    assert "height_cm" in profile_properties
    assert "weight_kg" in profile_properties
    assert "ConditionInput" in body["components"]["schemas"]
    assert "SymptomInput" in body["components"]["schemas"]
    assert "UrgentRiskSignal" in body["components"]["schemas"]
    examples = body["paths"]["/v1/recommend"]["post"]["requestBody"]["content"][
        "application/json"
    ]["examples"]
    assert "structured_health_profile_and_urgent_signal" in examples
