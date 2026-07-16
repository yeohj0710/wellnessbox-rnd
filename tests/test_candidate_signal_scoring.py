from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.domain.catalog import get_catalog_index
from wellnessbox_rnd.domain.intake import (
    calculate_normalized_input_sha256_v1,
    normalize_request,
)
from wellnessbox_rnd.efficacy.service import score_candidate
from wellnessbox_rnd.ingestion.reference_ingestion import KnowledgeBaseArtifact
from wellnessbox_rnd.knowledge.candidate_signals import (
    load_candidate_signal_registry,
    validate_candidate_signal_registry,
)
from wellnessbox_rnd.knowledge.runtime_db import (
    RuntimeKnowledgeDB,
    build_runtime_knowledge_db,
    validate_runtime_knowledge_db,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    BiologicalSex,
    DataSourceConsents,
    InputAvailability,
    NormalizedSensorGeneticSnapshot,
    RecommendationGoal,
    RecommendationRequest,
    UserProfile,
)
from wellnessbox_rnd.schemas.recommendation_contracts import (
    build_recommendation_set_contract_v1,
    validate_recommendation_set_contract_v1,
)

client = TestClient(app)


def _artifact() -> KnowledgeBaseArtifact:
    return KnowledgeBaseArtifact.model_validate_json(
        Path("data/knowledge/reference_knowledge_base_v1.json").read_text(
            encoding="utf-8"
        )
    )


def _request(
    goals: list[RecommendationGoal],
    **updates: object,
) -> RecommendationRequest:
    return RecommendationRequest(
        user_profile=UserProfile(
            age=41,
            biological_sex=BiologicalSex.FEMALE,
            pregnant=False,
        ),
        goals=goals,
        **updates,
    )


def _score(ingredient_key: str, request: RecommendationRequest):
    intake = normalize_request(request)
    return score_candidate(
        get_catalog_index()[ingredient_key],
        intake,
        safety_review=False,
    )


def _consents(*sources: str) -> DataSourceConsents:
    return DataSourceConsents.model_validate(
        {
            "survey": {"use_for_recommendation": True},
            **{
                source: {"use_for_recommendation": True}
                for source in sources
            },
        }
    )


def test_candidate_signal_registry_is_evidence_linked_and_runtime_persisted() -> None:
    registry = load_candidate_signal_registry()
    runtime_db = build_runtime_knowledge_db()
    stored = RuntimeKnowledgeDB.model_validate_json(
        Path("data/knowledge/runtime_knowledge_db_v1.json").read_text(encoding="utf-8")
    )

    assert validate_candidate_signal_registry(
        registry,
        reference_artifact=_artifact(),
    ) == []
    assert len(registry.all_rules()) == 10
    assert runtime_db.candidate_signal_scoring == registry
    assert validate_runtime_knowledge_db(runtime_db) == []
    assert stored.model_dump(mode="json") == runtime_db.model_dump(mode="json")


def test_candidate_signal_registry_rejects_forged_claim_and_unowned_reference() -> None:
    registry = load_candidate_signal_registry().model_copy(deep=True)
    artifact = _artifact().model_copy(deep=True)
    rule = registry.cgm_rules[0]
    rule.reference_ids.append("REF-NCCIH-COQ10-HEART-001")
    claim = next(
        item
        for item in artifact.parsed_claims
        if item.claim_id == "CLM-CDC-SOLUBLE-FIBER-001"
    )
    claim.normalized_claim_type = "candidate_signal_policy"

    issues = validate_candidate_signal_registry(
        registry,
        reference_artifact=artifact,
    )

    assert (
        "unclaimed_candidate_signal_reference:CS-CGM-TIR-FIBER-001:"
        "REF-NCCIH-COQ10-HEART-001" in issues
    )
    assert any(
        issue.startswith(
            "unexpected_candidate_signal_policy_claim:CS-CGM-TIR-FIBER-001:"
            "CLM-CDC-SOLUBLE-FIBER-001"
        )
        for issue in issues
    )


def test_candidate_signal_registry_rejects_unpinned_thresholds_and_genetic_tags() -> None:
    registry = load_candidate_signal_registry().model_copy(deep=True)
    registry.wearable_rules[0].claim_ids.remove("CLM-CDC-ADULT-SLEEP-001")
    registry.wearable_rules[0].reference_ids.remove("REF-CDC-ADULT-SLEEP-001")
    registry.genetic_rules[0].claim_ids.remove(
        "CLM-MC-CANDIDATE-SIGNAL-CYP1A2-001"
    )
    registry.genetic_rules[0].genetic_tags = ["invented_genetic_tag"]
    registry.wearable_rules[0].limitation = (
        "This diagnoses insomnia and proves magnesium efficacy."
    )

    issues = validate_candidate_signal_registry(
        registry,
        reference_artifact=_artifact(),
    )

    assert (
        "candidate_signal_rule_contract_mismatch:CS-WEARABLE-SLEEP-MAGNESIUM-001"
        in issues
    )
    assert (
        "candidate_signal_rule_contract_mismatch:CS-GENE-CYP1A2-LTHEANINE-001"
        in issues
    )
    assert (
        "candidate_signal_rule_limitation_mismatch:CS-WEARABLE-SLEEP-MAGNESIUM-001"
        in issues
    )


def test_symptom_lifestyle_lab_and_dietary_terms_are_separate_and_auditable() -> None:
    lab_request = _request(
        [RecommendationGoal.BLOOD_GLUCOSE],
        symptoms=["post_meal_spike_concern"],
        laboratory_observations=[
            {
                "code": "hba1c",
                "value": 6.1,
                "unit": "%",
                "reference_range": {"low": 4.0, "high": 5.6},
                "measured_at": "2026-07-16T00:00:00Z",
            }
        ],
        lifestyle={"activity_level": "sedentary"},
    )
    fiber = _score("soluble_fiber", lab_request)
    diet_request = _request(
        [RecommendationGoal.ENERGY_SUPPORT],
        dietary_patterns=["Vegan"],
    )
    b_complex = _score("vitamin_b_complex", diet_request)

    assert fiber.symptom_alignment == 8.0
    assert fiber.lifestyle_alignment == 6.0
    assert fiber.laboratory_alignment == 4.0
    assert {signal.source for signal in fiber.applied_signals} == {
        "symptom",
        "laboratory",
        "lifestyle",
    }
    lab_signal = next(
        signal for signal in fiber.applied_signals if signal.source == "laboratory"
    )
    assert (lab_signal.observed_value, lab_signal.unit, lab_signal.points) == (
        6.1,
        "%",
        4.0,
    )
    assert lab_signal.claim_ids == [
        "CLM-MC-CANDIDATE-SIGNAL-POLICY-001",
        "CLM-CDC-SOLUBLE-FIBER-001",
    ]
    assert b_complex.dietary_alignment == 3.0
    assert b_complex.applied_signals[0].observed_value == "vegan"


def test_wearable_sleep_value_produces_bounded_numeric_points() -> None:
    request = _request(
        [RecommendationGoal.SLEEP_SUPPORT],
        input_availability=InputAvailability(wearable=True),
        data_source_consents=_consents("wearable"),
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            wearable_available=True,
            sleep_hours=5.5,
        ),
    )

    magnesium = _score("magnesium_glycinate", request)
    l_theanine = _score("l_theanine", request)

    assert magnesium.wearable_adjustment == 3.0
    assert l_theanine.wearable_adjustment == 2.25
    signal = next(
        value for value in magnesium.applied_signals if value.source == "wearable"
    )
    assert (signal.observed_value, signal.unit, signal.points) == (5.5, "hours", 3.0)
    assert signal.rule_id == "CS-WEARABLE-SLEEP-MAGNESIUM-001"


def test_cgm_value_requires_consent_diabetes_context_and_goal() -> None:
    snapshot = NormalizedSensorGeneticSnapshot(
        cgm_available=True,
        time_in_range_pct=55.0,
        time_in_range_low_mg_dl=70.0,
        time_in_range_high_mg_dl=180.0,
        mean_glucose_mg_dl=148.0,
    )
    authorized = _request(
        [RecommendationGoal.BLOOD_GLUCOSE],
        conditions=["type 2 diabetes"],
        input_availability=InputAvailability(cgm=True),
        data_source_consents=_consents("cgm"),
        sensor_genetic_snapshot=snapshot,
    )
    no_diabetes = authorized.model_copy(update={"conditions": []})
    wrong_range = authorized.model_copy(
        update={
            "sensor_genetic_snapshot": snapshot.model_copy(
                update={
                    "time_in_range_low_mg_dl": 80.0,
                    "time_in_range_high_mg_dl": 140.0,
                }
            )
        }
    )
    pregnant = authorized.model_copy(
        update={
            "user_profile": authorized.user_profile.model_copy(
                update={"pregnant": True}
            )
        }
    )
    denied_consents = DataSourceConsents.model_validate(
        {
            "survey": {"use_for_recommendation": True},
            "cgm": {"use_for_recommendation": False},
        }
    )
    denied = authorized.model_copy(update={"data_source_consents": denied_consents})

    fiber = _score("soluble_fiber", authorized)
    berberine = _score("berberine", authorized)
    denied_intake = normalize_request(denied)

    assert fiber.cgm_adjustment == 3.0
    assert berberine.cgm_adjustment == 1.5
    assert _score("soluble_fiber", no_diabetes).cgm_adjustment == 0.0
    assert _score("soluble_fiber", wrong_range).cgm_adjustment == 0.0
    assert _score("soluble_fiber", pregnant).cgm_adjustment == 0.0
    assert denied_intake.sensor_genetic_snapshot is not None
    assert denied_intake.sensor_genetic_snapshot.time_in_range_pct is None
    assert score_candidate(
        get_catalog_index()["soluble_fiber"],
        denied_intake,
        safety_review=False,
    ).cgm_adjustment == 0.0


def test_genetic_tag_is_converted_to_numeric_points_and_unknown_tag_is_zero() -> None:
    base = _request(
        [RecommendationGoal.HEART_HEALTH],
        input_availability=InputAvailability(genetic=True),
        data_source_consents=_consents("genetic"),
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            genetic_available=True,
            genetic_tags=["lpl_triglyceride_risk"],
        ),
    )
    unknown = base.model_copy(
        update={
            "sensor_genetic_snapshot": NormalizedSensorGeneticSnapshot(
                genetic_available=True,
                genetic_tags=["unknown_research_tag"],
            )
        }
    )

    omega3 = _score("omega3", base)

    assert omega3.genetic_adjustment == 4.0
    signal = next(
        value for value in omega3.applied_signals if value.source == "genetic"
    )
    assert signal.observed_value == "lpl_triglyceride_risk"
    assert _score("omega3", unknown).genetic_adjustment == 0.0


def test_genetic_tag_does_not_spill_into_unscoped_candidate_or_rationale() -> None:
    request = _request(
        [RecommendationGoal.SLEEP_SUPPORT],
        input_availability=InputAvailability(genetic=True),
        data_source_consents=_consents("genetic"),
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            genetic_available=True,
            genetic_tags=["cyp1a2_slow_metabolizer"],
        ),
        preferences={"max_products": 5},
    )

    response = recommend(request)
    magnesium = next(
        item
        for item in response.recommendations
        if item.ingredient_key == "magnesium_glycinate"
    )
    l_theanine = next(
        item for item in response.recommendations if item.ingredient_key == "l_theanine"
    )

    assert magnesium.score_breakdown.genetic_adjustment == 0.0
    assert "genetic tag" not in magnesium.rationale.casefold()
    assert l_theanine.score_breakdown.genetic_adjustment == 4.0
    assert "CS-GENE-CYP1A2-LTHEANINE-001" in l_theanine.rationale
    assert "genetic context" in response.decision_summary.summary.casefold()


def test_numeric_signal_scores_reconcile_with_recommendation_contract() -> None:
    request = _request(
        [RecommendationGoal.SLEEP_SUPPORT],
        input_availability=InputAvailability(wearable=True),
        data_source_consents=_consents("wearable"),
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            wearable_available=True,
            sleep_hours=5.5,
        ),
        preferences={"max_products": 5},
    )
    response = recommend(request)

    contract = build_recommendation_set_contract_v1(request, response)

    assert validate_recommendation_set_contract_v1(contract) == []


def test_denied_sensor_values_do_not_change_normalized_hash() -> None:
    denied_consents = DataSourceConsents.model_validate(
        {
            "survey": {"use_for_recommendation": True},
            "wearable": {"use_for_recommendation": False},
        }
    )
    first = _request(
        [RecommendationGoal.SLEEP_SUPPORT],
        input_availability=InputAvailability(wearable=True),
        data_source_consents=denied_consents,
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            wearable_available=True,
            sleep_hours=4.0,
            normalization_notes=["wearable_sleep_minutes_converted_to_hours"],
        ),
    )
    second = first.model_copy(
        update={
            "sensor_genetic_snapshot": NormalizedSensorGeneticSnapshot(
                wearable_available=True,
                sleep_hours=8.0,
                normalization_notes=["different_nonclinical_parser_note"],
            )
        }
    )

    assert calculate_normalized_input_sha256_v1(
        normalize_request(first)
    ) == calculate_normalized_input_sha256_v1(normalize_request(second))


def test_candidate_score_total_reconciles_every_visible_term() -> None:
    request = _request(
        [RecommendationGoal.SLEEP_SUPPORT],
        symptoms=["difficulty_falling_asleep"],
        lifestyle={"sleep_hours": 5.0, "stress_level": 4},
        input_availability=InputAvailability(wearable=True),
        data_source_consents=_consents("wearable"),
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            wearable_available=True,
            sleep_hours=5.5,
        ),
    )
    item = get_catalog_index()["magnesium_glycinate"]
    score = _score(item.key, request)

    assert score.total == pytest.approx(
        item.default_priority
        + score.goal_alignment
        + score.symptom_alignment
        + score.lifestyle_alignment
        + score.laboratory_alignment
        + score.dietary_alignment
        + score.wearable_adjustment
        + score.cgm_adjustment
        + score.genetic_adjustment
        + score.evidence_readiness
        + score.budget_adjustment
        + score.safety_adjustment
        + score.conservative_adjustment
        + score.learned_effect_bonus
    )


def test_sensor_snapshot_rejects_out_of_bounds_and_undeclared_source() -> None:
    with pytest.raises(ValidationError):
        NormalizedSensorGeneticSnapshot(
            wearable_available=True,
            sleep_hours=25.0,
        )
    with pytest.raises(ValidationError, match="input_availability.wearable=true"):
        _request(
            [RecommendationGoal.SLEEP_SUPPORT],
            data_source_consents=_consents("wearable"),
            sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
                wearable_available=True,
                sleep_hours=6.0,
            ),
        )
    with pytest.raises(ValidationError, match="explicit data_source_consents"):
        _request(
            [RecommendationGoal.SLEEP_SUPPORT],
            input_availability=InputAvailability(wearable=True),
            sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
                wearable_available=True,
                sleep_hours=6.0,
            ),
        )


def test_api_exposes_sensor_snapshot_and_numeric_score_terms() -> None:
    request = _request(
        [RecommendationGoal.SLEEP_SUPPORT],
        input_availability=InputAvailability(wearable=True),
        data_source_consents=_consents("wearable"),
        sensor_genetic_snapshot=NormalizedSensorGeneticSnapshot(
            wearable_available=True,
            sleep_hours=5.5,
        ),
        preferences={"max_products": 5},
    )

    response = client.post("/v1/recommend", json=request.model_dump(mode="json"))
    body = response.json()
    magnesium = next(
        item
        for item in body["recommendations"]
        if item["ingredient_key"] == "magnesium_glycinate"
    )
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert response.status_code == 200
    assert "NormalizedSensorGeneticSnapshot" in schemas
    assert magnesium["score_breakdown"]["wearable_adjustment"] == 3.0
    assert any(
        signal["rule_id"] == "CS-WEARABLE-SLEEP-MAGNESIUM-001"
        and signal["observed_value"] == 5.5
        for signal in magnesium["score_breakdown"]["applied_signals"]
    )
