from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    DecisionUncertainty,
    LearnedRerankingDecision,
    RecommendationRequest,
)
from wellnessbox_rnd.training import load_synthetic_records

client = TestClient(app)
DATASET_PATH = "data/synthetic/synthetic_longitudinal_v1.jsonl"


def _request(*, goals: list[str], **updates: object) -> RecommendationRequest:
    payload: dict[str, object] = {
        "user_profile": {
            "age": 41,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": goals,
        "symptoms": ["difficulty_falling_asleep"],
        "conditions": [],
        "allergies": [],
        "risk_flags": [],
        "medications": [],
        "current_supplements": [{"name": "Vitamin C", "ingredients": []}],
        "dietary_patterns": [],
        "laboratory_observations": [],
        "lifestyle": {
            "sleep_hours": 7.0,
            "stress_level": 2,
            "activity_level": "lightly_active",
        },
        "preferences": {"max_products": 5},
    }
    payload.update(updates)
    return RecommendationRequest.model_validate(payload)


def _general_wellness_request() -> RecommendationRequest:
    records = load_synthetic_records(DATASET_PATH)
    request = next(
        record.request
        for record in records
        if record.user_id == "syn-user-009" and record.follow_up_step == 0
    )
    payload = request.model_dump(mode="json")
    payload["preferences"]["max_products"] = 5
    return RecommendationRequest.model_validate(payload)


def _write_artifact(path: Path, **updates: object) -> Path:
    payload: dict[str, object] = {
        "model_name": "efficacy_model_v0",
        "cohort_version": "test_fixture_v1",
        "seed": 1,
        "alpha": 0.1,
        "feature_names": ["baseline_candidate::vitamin_c"],
        "intercept": 0.0,
        "weights": [0.0],
        "target_name": "expected_effect_proxy",
    }
    payload.update(updates)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_decision_uncertainty_reconciles_components_and_band() -> None:
    response = recommend(_request(goals=["sleep_support"]))
    uncertainty = response.decision_uncertainty

    assert uncertainty.calculation_version == "decision_uncertainty_v1"
    assert uncertainty.score_scope.endswith("not_clinical_probability")
    assert uncertainty.raw_uncertainty_score == pytest.approx(
        sum(item.points for item in uncertainty.components)
    )
    assert uncertainty.uncertainty_score == min(1.0, uncertainty.raw_uncertainty_score)
    assert uncertainty.additional_input_conditions == []


def test_candidate_margin_uses_preselection_pool_when_output_limit_is_one() -> None:
    request = _general_wellness_request()
    request_payload = request.model_dump(mode="json")
    request_payload["preferences"]["max_products"] = 1

    one_product = recommend(RecommendationRequest.model_validate(request_payload))
    full_selection = recommend(request)
    one_snapshot = one_product.decision_uncertainty.candidate_ranking_snapshot
    full_snapshot = full_selection.decision_uncertainty.candidate_ranking_snapshot

    assert len(one_product.recommendations) == 1
    assert one_snapshot == full_snapshot
    assert one_snapshot.candidate_count > 1
    assert one_snapshot.top_two_score_margin == pytest.approx(0.7)
    assert any(
        item.code == "candidate_score_margin:top_two" and item.points == 0.20
        for item in one_product.decision_uncertainty.components
    )


def test_ranking_snapshot_is_reconciled_with_independent_score_trace() -> None:
    request_payload = _general_wellness_request().model_dump(mode="json")
    request_payload["preferences"]["max_products"] = 1
    response = recommend(RecommendationRequest.model_validate(request_payload))
    payload = response.model_dump(mode="json")
    uncertainty = payload["decision_uncertainty"]
    snapshot = uncertainty["candidate_ranking_snapshot"]
    margin_component = next(
        item
        for item in uncertainty["components"]
        if item["source"] == "candidate_score_margin"
    )
    snapshot.update(
        {
            "candidate_count": 1,
            "runner_up_candidate_key": None,
            "runner_up_selection_score": None,
            "top_two_score_margin": None,
        }
    )
    uncertainty["components"].remove(margin_component)
    uncertainty["raw_uncertainty_score"] -= margin_component["points"]
    uncertainty["uncertainty_score"] -= margin_component["points"]
    uncertainty["uncertainty_band"] = "low"

    with pytest.raises(ValidationError, match="candidate count mismatch"):
        type(response).model_validate(payload)


def test_unselected_candidate_score_trace_preserves_full_breakdown() -> None:
    request_payload = _general_wellness_request().model_dump(mode="json")
    request_payload["preferences"]["max_products"] = 1
    response = recommend(RecommendationRequest.model_validate(request_payload))
    payload = response.model_dump(mode="json")
    unselected_score = payload["candidate_pool_trace"]["preselection_scores"][1]
    unselected_score["score_total"] -= 10.0
    unselected_score["goal_alignment"] = 0.0
    unselected_score["selection_score"] = unselected_score["score_total"] + 4.0

    with pytest.raises(ValidationError, match="preserved candidate score total mismatch"):
        type(response).model_validate(payload)


def test_unselected_candidate_score_trace_uses_external_catalog_registry() -> None:
    request_payload = _general_wellness_request().model_dump(mode="json")
    request_payload["preferences"]["max_products"] = 1
    response = recommend(RecommendationRequest.model_validate(request_payload))
    payload = response.model_dump(mode="json")
    traced = payload["candidate_pool_trace"]["preselection_scores"][1]
    delta = -0.05
    traced["catalog_priority"] += delta
    traced["score_total"] += delta
    traced["selection_score"] += delta
    traced["score_breakdown"]["total"] += delta
    traced["reason_breakdown"]["score_total"] += delta
    catalog_term = next(
        item
        for item in traced["reason_breakdown"]["score_terms"]
        if item["term"] == "catalog_priority"
    )
    catalog_term["points"] += delta

    with pytest.raises(ValidationError, match="preselection_catalog_priority_mismatch"):
        type(response).model_validate(payload)


def test_preselection_goal_mutation_returns_validation_error_not_key_error() -> None:
    request_payload = _general_wellness_request().model_dump(mode="json")
    request_payload["preferences"]["max_products"] = 1
    response = recommend(RecommendationRequest.model_validate(request_payload))
    payload = response.model_dump(mode="json")
    payload["candidate_pool_trace"]["preselection_scores"][1][
        "expected_support_goals"
    ] = ["heart_health"]

    with pytest.raises(ValidationError, match="must match post-safety candidate goals"):
        type(response).model_validate(payload)


def test_missing_information_is_quantified_as_additional_input_conditions() -> None:
    response = recommend(
        _request(
            goals=["heart_health"],
            symptoms=[],
            current_supplements=[],
        )
    )
    uncertainty = response.decision_uncertainty
    conditions = {item.code: item for item in uncertainty.additional_input_conditions}

    assert conditions["missing_heart_context"].uncertainty_points == 0.20
    assert conditions["missing_primary_symptom"].uncertainty_points == 0.10
    assert conditions["missing_current_supplements"].uncertainty_points == 0.05
    assert {
        item.code for item in uncertainty.components if item.source == "missing_information"
    } == {f"missing_information:{code}" for code in conditions}
    assert uncertainty.raw_uncertainty_score >= 0.35


def test_uncertainty_and_learned_diagnostic_schemas_fail_closed() -> None:
    response = recommend(_request(goals=["sleep_support"]))
    uncertainty_payload = response.decision_uncertainty.model_dump(mode="json")
    uncertainty_payload["raw_uncertainty_score"] += 0.1
    with pytest.raises(ValidationError, match="raw score mismatch"):
        DecisionUncertainty.model_validate(uncertainty_payload)

    learned_payload = response.learned_reranking_decision.model_dump(mode="json")
    learned_payload["status"] = "applied"
    with pytest.raises(ValidationError, match="flags are inconsistent"):
        LearnedRerankingDecision.model_validate(learned_payload)

    response_payload = response.model_dump(mode="json")
    response_payload["decision_uncertainty"]["components"].append(
        {
            "code": "candidate_availability:forged",
            "source": "candidate_availability",
            "points": 0.1,
            "basis_codes": ["forged"],
        }
    )
    response_payload["decision_uncertainty"]["raw_uncertainty_score"] += 0.1
    response_payload["decision_uncertainty"]["uncertainty_score"] += 0.1
    response_payload["decision_uncertainty"]["uncertainty_band"] = "moderate"
    with pytest.raises(ValidationError, match="do not match response decision inputs"):
        type(response).model_validate(response_payload)


def test_missing_learned_path_and_file_return_exact_deterministic_baseline() -> None:
    request = _general_wellness_request()
    baseline = recommend(request)
    missing_path = recommend(request, enable_learned_reranking=True)
    missing_file = recommend(
        request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path="artifacts/models/does_not_exist.json",
    )

    assert missing_path.recommendations == baseline.recommendations
    assert missing_file.recommendations == baseline.recommendations
    assert missing_path.learned_reranking_decision.status == "fallback_missing_path"
    assert missing_file.learned_reranking_decision.status == "fallback_missing_file"
    assert missing_path.metadata.mode == "deterministic_baseline_v1"
    assert missing_file.metadata.mode == "deterministic_baseline_v1"


def test_invalid_and_suspicious_artifacts_fall_back_without_partial_rerank(
    tmp_path: Path,
) -> None:
    request = _general_wellness_request()
    baseline = recommend(request)
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    suspicious = _write_artifact(
        tmp_path / "suspicious.json",
        feature_names=["a", "b"],
        weights=[0.1],
    )

    malformed_response = recommend(
        request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=str(malformed),
    )
    suspicious_response = recommend(
        request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=str(suspicious),
    )

    assert malformed_response.recommendations == baseline.recommendations
    assert suspicious_response.recommendations == baseline.recommendations
    assert malformed_response.learned_reranking_decision.status == "fallback_invalid_artifact"
    assert suspicious_response.learned_reranking_decision.status == "fallback_suspicious_artifact"
    assert "feature_weight_dimension_mismatch" in (
        suspicious_response.learned_reranking_decision.issues
    )


@pytest.mark.parametrize("missing_field", ["model_name", "target_name"])
def test_missing_artifact_identity_fields_are_invalid(
    tmp_path: Path,
    missing_field: str,
) -> None:
    artifact_path = _write_artifact(tmp_path / f"missing-{missing_field}.json")
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    del payload[missing_field]
    artifact_path.write_text(json.dumps(payload), encoding="utf-8")

    response = recommend(
        _general_wellness_request(),
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=str(artifact_path),
    )

    assert response.learned_reranking_decision.status == "fallback_invalid_artifact"


@pytest.mark.parametrize(
    ("updates", "expected_issue"),
    [
        (
            {"feature_names": ["unknown_runtime_feature"], "weights": [0.1]},
            "unsupported_runtime_feature",
        ),
        ({"weights": [1e307]}, "weight_exceeds_runtime_limit"),
        (
            {
                "feature_names": ["baseline_candidate::not_in_catalog"],
                "weights": [0.1],
            },
            "unsupported_candidate_feature",
        ),
        (
            {
                "feature_names": ["baseline_candidate::vitamin_c "],
                "weights": [0.1],
            },
            "feature_name_has_surrounding_whitespace",
        ),
        (
            {
                "feature_names": [
                    "baseline_candidate::vitamin_c",
                    "goal::not_a_goal",
                ],
                "weights": [0.1, 0.1],
            },
            "unsupported_closed_domain_feature",
        ),
        (
            {
                "feature_names": [
                    "baseline_candidate::vitamin_c",
                    "sex::robot",
                ],
                "weights": [0.1, 0.1],
            },
            "unsupported_closed_domain_feature",
        ),
        (
            {
                "feature_names": [
                    "baseline_candidate::vitamin_c",
                    "activity::flying",
                ],
                "weights": [0.1, 0.1],
            },
            "unsupported_closed_domain_feature",
        ),
    ],
)
def test_unsupported_features_and_extreme_weights_are_suspicious(
    tmp_path: Path,
    updates: dict[str, object],
    expected_issue: str,
) -> None:
    artifact_path = _write_artifact(tmp_path / f"{expected_issue}.json", **updates)

    response = recommend(
        _general_wellness_request(),
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=str(artifact_path),
    )

    assert response.learned_reranking_decision.status == "fallback_suspicious_artifact"
    assert expected_issue in response.learned_reranking_decision.issues


def test_blank_cohort_version_is_invalid(tmp_path: Path) -> None:
    artifact_path = _write_artifact(
        tmp_path / "blank-cohort.json",
        cohort_version="   ",
    )

    response = recommend(
        _general_wellness_request(),
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=str(artifact_path),
    )

    assert response.learned_reranking_decision.status == "fallback_invalid_artifact"


def test_non_applied_response_requires_exact_deterministic_mode() -> None:
    response = recommend(_general_wellness_request())
    payload = response.model_dump(mode="json")
    payload["metadata"]["mode"] = "deterministic_baseline_v1_learned_efficacy_rerank_v999"

    with pytest.raises(ValidationError, match="cannot retain learned candidates or mode"):
        type(response).model_validate(payload)


def test_prediction_error_discards_partial_rerank_and_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    request = _general_wellness_request()
    baseline = recommend(request)
    artifact_path = _write_artifact(tmp_path / "valid.json")
    calls = 0

    def _fail_after_one_prediction(*_args) -> float:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise ValueError("injected prediction failure")
        return 0.2

    monkeypatch.setattr(
        "wellnessbox_rnd.optimizer.service.predict_effect_proxy_from_feature_dict",
        _fail_after_one_prediction,
    )
    response = recommend(
        request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=str(artifact_path),
    )

    assert calls > 1
    assert response.recommendations == baseline.recommendations
    assert response.learned_reranking_decision.status == "fallback_artifact_runtime_error"
    assert all("OPT-LEARNED-001" not in item.rule_refs for item in response.recommendations)


def test_api_and_openapi_expose_uncertainty_and_learned_decision() -> None:
    request = _request(goals=["sleep_support"])
    response = client.post("/v1/recommend", json=request.model_dump(mode="json"))
    body = response.json()
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert response.status_code == 200
    assert body["decision_uncertainty"]["calculation_version"] == ("decision_uncertainty_v1")
    assert body["learned_reranking_decision"]["status"] == "not_requested"
    assert "DecisionUncertainty" in schemas
    assert "LearnedRerankingDecision" in schemas
