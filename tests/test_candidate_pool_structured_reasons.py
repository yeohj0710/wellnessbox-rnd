from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.domain.catalog import get_catalog_index
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    CandidatePoolTrace,
    RecommendationReasonBreakdown,
    RecommendationRequest,
)

client = TestClient(app)


def _request(*, goals: list[str], **updates: object) -> RecommendationRequest:
    payload: dict[str, object] = {
        "user_profile": {
            "age": 41,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": goals,
        "symptoms": [],
        "conditions": [],
        "allergies": [],
        "risk_flags": [],
        "medications": [],
        "current_supplements": [],
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


def _keys(items) -> list[str]:
    return [item.ingredient_key for item in items]


def test_candidate_pool_preserves_pre_excluded_post_and_selected_sets() -> None:
    response = recommend(
        _request(
            goals=["heart_health"],
            medications=[{"name": "warfarin"}],
        )
    )
    trace = response.candidate_pool_trace

    assert "omega3" in _keys(trace.pre_safety_candidates)
    omega3 = next(
        item for item in trace.excluded_candidates if item.ingredient_key == "omega3"
    )
    assert omega3.exclusion_reasons == ["safety_summary_excluded"]
    assert "omega3" not in _keys(trace.post_safety_candidates)
    assert set(_keys(trace.pre_safety_candidates)) == set(
        _keys(trace.excluded_candidates)
    ) | set(_keys(trace.post_safety_candidates))
    assert set(trace.selected_candidate_keys) == {
        item.ingredient_key for item in response.recommendations
    }
    assert set(trace.selected_candidate_keys).issubset(
        _keys(trace.post_safety_candidates)
    )
    assert "SAFETY-ANTICOAG-001" in trace.applied_safety_rule_ids
    assert trace.global_blocked is False
    coq10 = next(
        item for item in response.recommendations if item.ingredient_key == "coq10"
    )
    safety_input = next(
        item
        for item in coq10.reason_breakdown.input_signals
        if item.source == "safety"
    )
    safety_link = next(
        item
        for item in coq10.reason_breakdown.evidence_links
        if item.evidence_source == "safety_rule"
    )
    safety_term = next(
        item
        for item in coq10.reason_breakdown.score_terms
        if item.term == "safety_adjustment"
    )
    assert safety_input.code == "SAFETY-ANTICOAG-001"
    assert safety_link.rule_id == "SAFETY-ANTICOAG-001"
    assert safety_link.reference_ids == ["REF-NIH-ODS-OMEGA3-001"]
    assert "SAFETY-ANTICOAG-001" in safety_term.rule_ids


def test_candidate_pool_keeps_user_avoidance_and_current_regimen_categories() -> None:
    response = recommend(
        _request(
            goals=["sleep_support"],
            current_supplements=[{"name": "L-Theanine", "ingredients": []}],
            preferences={
                "max_products": 5,
                "avoid_ingredients": ["magnesium_glycinate"],
            },
        )
    )
    exclusions = {
        item.ingredient_key: item.exclusion_reasons
        for item in response.candidate_pool_trace.excluded_candidates
    }

    assert "user_avoidance" in exclusions["magnesium_glycinate"]
    assert "current_regimen_overlap" in exclusions["l_theanine"]
    assert response.candidate_pool_trace.post_safety_candidates == []


def test_global_block_preserves_pool_but_never_claims_a_selection() -> None:
    payload = json.loads(
        Path("data/samples/api_recommend_structured_health_input_request_v1.json").read_text(
            encoding="utf-8"
        )
    )
    response = recommend(RecommendationRequest.model_validate(payload))
    trace = response.candidate_pool_trace

    assert response.recommendations == []
    assert trace.global_blocked is True
    assert trace.selected_candidate_keys == []
    assert trace.pre_safety_candidates
    assert "SAFETY-URGENT-SYMPTOM-001" in trace.applied_safety_rule_ids


def test_structured_reason_separates_inputs_terms_and_evidence_ids() -> None:
    response = recommend(
        _request(
            goals=["sleep_support"],
            symptoms=["difficulty_falling_asleep"],
            lifestyle={
                "sleep_hours": 5.0,
                "stress_level": 4,
                "activity_level": "lightly_active",
            },
        )
    )
    candidate = next(
        item
        for item in response.recommendations
        if item.ingredient_key == "magnesium_glycinate"
    )
    reason = candidate.reason_breakdown
    terms = {item.term: item for item in reason.score_terms}

    assert {(item.source, item.code) for item in reason.input_signals}.issuperset(
        {
            ("goal", "sleep_support"),
            ("symptom", "difficulty_falling_asleep"),
            ("lifestyle", "high_stress"),
            ("lifestyle", "sleep_deficit"),
        }
    )
    assert set(terms) == {
        "catalog_priority",
        "goal_alignment",
        "symptom_alignment",
        "lifestyle_alignment",
        "laboratory_alignment",
        "dietary_alignment",
        "wearable_adjustment",
        "cgm_adjustment",
        "genetic_adjustment",
        "evidence_readiness",
        "budget_adjustment",
        "safety_adjustment",
        "conservative_adjustment",
        "learned_effect_bonus",
    }
    assert terms["catalog_priority"].points == get_catalog_index()[
        "magnesium_glycinate"
    ].default_priority
    assert reason.score_total == pytest.approx(candidate.score_breakdown.total)
    assert sum(item.points for item in reason.score_terms) == pytest.approx(
        reason.score_total
    )
    assert "OPT-BASELINE-001" in reason.rule_ids
    assert "CS-SYMPTOM-MATCH-001" in reason.rule_ids
    assert "REF-MC-GOAL-PRIOR-001" in reason.reference_ids
    assert "CLM-MC-GOAL-PRIOR-POLICY-001" in reason.claim_ids
    assert reason.limitations
    goal_link = next(
        item
        for item in reason.evidence_links
        if item.evidence_source == "goal_prior" and item.code == "sleep_support"
    )
    symptom_link = next(
        item
        for item in reason.evidence_links
        if item.evidence_source == "input_signal"
        and item.code == "difficulty_falling_asleep"
    )
    assert "REF-MC-GOAL-PRIOR-001" in goal_link.reference_ids
    assert symptom_link.rule_id == "CS-SYMPTOM-MATCH-001"
    assert set(reason.reference_ids) == {
        value for item in reason.evidence_links for value in item.reference_ids
    }


def test_candidate_trace_and_reason_contracts_fail_closed_on_mismatch() -> None:
    response = recommend(_request(goals=["sleep_support"]))
    trace_payload = response.candidate_pool_trace.model_dump(mode="json")
    trace_payload["post_safety_candidates"] = []

    with pytest.raises(ValidationError, match="partition"):
        CandidatePoolTrace.model_validate(trace_payload)

    identity_payload = response.candidate_pool_trace.model_dump(mode="json")
    identity_payload["post_safety_candidates"][0]["display_name"] = "mutated"
    with pytest.raises(ValidationError, match="identity"):
        CandidatePoolTrace.model_validate(identity_payload)

    reason_payload = response.recommendations[0].reason_breakdown.model_dump(mode="json")
    reason_payload["score_total"] += 1.0
    with pytest.raises(ValidationError, match="score total mismatch"):
        RecommendationReasonBreakdown.model_validate(reason_payload)

    incomplete_reason_payload = (
        response.recommendations[0].reason_breakdown.model_dump(mode="json")
    )
    removed_term = incomplete_reason_payload["score_terms"].pop()
    incomplete_reason_payload["score_total"] -= removed_term["points"]
    with pytest.raises(ValidationError, match="every score term"):
        RecommendationReasonBreakdown.model_validate(incomplete_reason_payload)

    invalid_id_payload = response.recommendations[0].reason_breakdown.model_dump(
        mode="json"
    )
    invalid_id_payload["reference_ids"][0] = " "
    with pytest.raises(ValidationError):
        RecommendationReasonBreakdown.model_validate(invalid_id_payload)

    unexpected_field_payload = response.candidate_pool_trace.model_dump(mode="json")
    unexpected_field_payload["unexpected"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CandidatePoolTrace.model_validate(unexpected_field_payload)

    duplicate_link_payload = response.recommendations[0].reason_breakdown.model_dump(
        mode="json"
    )
    duplicate_link_payload["evidence_links"].append(
        duplicate_link_payload["evidence_links"][0]
    )
    with pytest.raises(ValidationError, match="evidence links must be unique"):
        RecommendationReasonBreakdown.model_validate(duplicate_link_payload)


def test_api_and_openapi_expose_candidate_pool_and_structured_reasons() -> None:
    request = _request(goals=["sleep_support"])
    response = client.post("/v1/recommend", json=request.model_dump(mode="json"))
    body = response.json()
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert response.status_code == 200
    assert body["candidate_pool_trace"]["pre_safety_candidates"]
    assert body["recommendations"][0]["reason_breakdown"]["score_terms"]
    assert "CandidatePoolTrace" in schemas
    assert "RecommendationReasonBreakdown" in schemas
