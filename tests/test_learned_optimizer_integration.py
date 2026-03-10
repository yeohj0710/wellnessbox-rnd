from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.training import load_synthetic_records

DATASET_PATH = "data/synthetic/synthetic_longitudinal_v1.jsonl"
MODEL_ARTIFACT_PATH = "artifacts/models/efficacy_model_v0.json"


def _record(user_id: str):
    records = load_synthetic_records(DATASET_PATH)
    return next(
        record
        for record in records
        if record.user_id == user_id and record.follow_up_step == 0
    )


def test_learned_rerank_can_swap_near_tied_general_wellness_single_product() -> None:
    request = _record("syn-user-009").request

    baseline_response = recommend(request)
    learned_response = recommend(
        request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=MODEL_ARTIFACT_PATH,
    )

    assert baseline_response.recommendations[0].ingredient_key == "vitamin_d3"
    assert learned_response.recommendations[0].ingredient_key == "vitamin_c"
    assert (
        learned_response.metadata.mode
        == "deterministic_baseline_v1_learned_efficacy_rerank_v0"
    )
    assert "OPT-LEARNED-001" in learned_response.recommendations[0].rule_refs
    assert learned_response.recommendations[0].score_breakdown.learned_effect_bonus > 0


def test_learned_rerank_does_not_apply_to_high_risk_anticoagulant_case() -> None:
    request = _record("syn-user-003").request

    response = recommend(
        request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path=MODEL_ARTIFACT_PATH,
    )

    assert response.recommendations[0].ingredient_key == "coq10"
    assert response.metadata.mode == "deterministic_baseline_v1"
    assert all(
        candidate.score_breakdown.learned_effect_bonus == 0.0
        for candidate in response.recommendations
    )


def test_learned_rerank_missing_artifact_falls_back_to_deterministic_selection() -> None:
    request = _record("syn-user-009").request

    baseline_response = recommend(request)
    fallback_response = recommend(
        request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path="artifacts/models/does_not_exist.json",
    )

    assert fallback_response.recommendations[0].ingredient_key == "vitamin_d3"
    assert fallback_response.recommendations == baseline_response.recommendations
    assert fallback_response.metadata.mode == "deterministic_baseline_v1"
