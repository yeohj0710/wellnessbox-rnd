import json
import re
from pathlib import Path

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas import (
    build_recommendation_set_contract_v1,
    summarize_recommendation_set_contract_v1,
    validate_recommendation_set_contract_v1,
)
from wellnessbox_rnd.schemas.recommendation import (
    LearnedRerankingDecision,
    RecommendationGoal,
    RecommendationRequest,
    RecommendationStatus,
)
from wellnessbox_rnd.schemas.recommendation_contracts import RecommendationSetContractV1


def test_recommendation_plan_id_accepts_explicit_value_and_derives_stable_default() -> None:
    payload = json.loads(
        Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
            encoding="utf-8"
        )
    )
    payload["plan_id"] = "plan_user_supplied_001"
    explicit = RecommendationRequest.model_validate(payload)
    assert explicit.plan_id == "plan_user_supplied_001"
    assert recommend(explicit).plan_id == explicit.plan_id

    payload.pop("plan_id")
    payload["request_id"] = "stable-plan-request"
    first = RecommendationRequest.model_validate(payload)
    second = RecommendationRequest.model_validate(payload)
    assert first.plan_id == second.plan_id
    assert re.fullmatch(r"plan_[a-f0-9]{32}", first.plan_id)


def test_recommendation_set_contract_validates_start_plan_fixture() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)

    contract = build_recommendation_set_contract_v1(request, response)

    assert validate_recommendation_set_contract_v1(contract) == []
    assert [item.ingredient_key for item in contract.selected_recommendations] == [
        "magnesium_glycinate",
        "l_theanine",
    ]


def test_recommendation_set_contract_flags_duplicate_and_limit_overflow() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    duplicate_item = contract.selected_recommendations[0]
    mutated = contract.model_copy(
        update={
            "selection_limit": 1,
            "selected_recommendations": contract.selected_recommendations + [duplicate_item],
        }
    )

    issues = validate_recommendation_set_contract_v1(mutated)

    assert "selection_limit_exceeded" in issues
    assert "duplicate_selected_ingredient_keys" in issues


def test_recommendation_set_contract_flags_score_total_and_goal_mismatch() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    broken_item = contract.selected_recommendations[0].model_copy(
        update={
            "expected_support_goals": [RecommendationGoal.GENERAL_WELLNESS],
            "score_breakdown": contract.selected_recommendations[0].score_breakdown.model_copy(
                update={"total": contract.selected_recommendations[0].score_breakdown.total + 1.0}
            ),
        }
    )
    mutated = contract.model_copy(
        update={
            "selected_recommendations": [
                broken_item,
                contract.selected_recommendations[1],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(mutated)

    assert any(issue.startswith("score_total_mismatch::magnesium_glycinate") for issue in issues)
    assert any(
        issue.startswith("candidate_goal_outside_request::magnesium_glycinate") for issue in issues
    )


def test_recommendation_set_contract_flags_reason_score_and_rule_mismatch() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    original = contract.selected_recommendations[0]
    broken_terms = [
        term.model_copy(update={"points": term.points + 1.0})
        if term.term == "goal_alignment"
        else term
        for term in original.reason_breakdown.score_terms
    ]
    broken_reason = original.reason_breakdown.model_copy(
        update={
            "score_terms": broken_terms,
            "score_total": original.reason_breakdown.score_total + 1.0,
            "rule_ids": [],
        }
    )
    broken_item = original.model_copy(update={"reason_breakdown": broken_reason})
    mutated = contract.model_copy(
        update={
            "selected_recommendations": [
                broken_item,
                contract.selected_recommendations[1],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(mutated)

    assert "reason_score_total_mismatch::magnesium_glycinate" in issues
    assert "reason_score_term_mismatch::magnesium_glycinate::goal_alignment" in issues
    assert any(
        issue.startswith("reason_missing_candidate_rule_refs::magnesium_glycinate")
        for issue in issues
    )


def test_recommendation_set_contract_rejects_forged_evidence_ownership() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 41,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
        }
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)
    original = contract.selected_recommendations[0]
    reason_payload = original.reason_breakdown.model_dump(mode="json")
    goal_link = next(
        link for link in reason_payload["evidence_links"] if link["evidence_source"] == "goal_prior"
    )
    goal_link["reference_ids"].append("REF-FAKE-001")
    goal_link["claim_ids"].append("CLM-FAKE-001")
    reason_payload["reference_ids"].append("REF-FAKE-001")
    reason_payload["claim_ids"].append("CLM-FAKE-001")
    forged_reason = original.reason_breakdown.model_validate(reason_payload)
    forged_item = original.model_copy(update={"reason_breakdown": forged_reason})
    forged_contract = contract.model_copy(
        update={
            "selected_recommendations": [
                forged_item,
                *contract.selected_recommendations[1:],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(forged_contract)

    assert f"reason_goal_prior_evidence_mismatch::{original.ingredient_key}" in issues


def test_recommendation_set_contract_rejects_unmarked_learned_bonus() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    original = contract.selected_recommendations[0]
    updated_breakdown = original.score_breakdown.model_copy(
        update={
            "learned_effect_bonus": 1.0,
            "total": original.score_breakdown.total + 1.0,
        }
    )
    updated_terms = [
        term.model_copy(update={"points": 1.0}) if term.term == "learned_effect_bonus" else term
        for term in original.reason_breakdown.score_terms
    ]
    updated_reason = original.reason_breakdown.model_copy(
        update={
            "score_terms": updated_terms,
            "score_total": original.reason_breakdown.score_total + 1.0,
        }
    )
    forged_item = original.model_copy(
        update={
            "score_breakdown": updated_breakdown,
            "reason_breakdown": updated_reason,
            "additive_component_total": original.additive_component_total + 1.0,
        }
    )
    forged_contract = contract.model_copy(
        update={
            "selected_recommendations": [
                forged_item,
                *contract.selected_recommendations[1:],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(forged_contract)

    assert f"learned_bonus_rule_marker_mismatch::{original.ingredient_key}" in issues


def test_recommendation_set_contract_accepts_marked_zero_learned_bonus() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    original = contract.selected_recommendations[0]
    reason_payload = original.reason_breakdown.model_dump(mode="json")
    reason_payload["rule_ids"].append("OPT-LEARNED-001")
    learned_term = next(
        term for term in reason_payload["score_terms"] if term["term"] == "learned_effect_bonus"
    )
    learned_term["rule_ids"] = ["OPT-LEARNED-001"]
    marked_reason = original.reason_breakdown.model_validate(reason_payload)
    marked_item = original.model_copy(
        update={
            "rule_refs": [*original.rule_refs, "OPT-LEARNED-001"],
            "reason_breakdown": marked_reason,
        }
    )
    assert contract.preselection_scores is not None
    original_trace = contract.preselection_scores[0]
    marked_trace = original_trace.model_copy(
        update={
            "rule_refs": [*original_trace.rule_refs, "OPT-LEARNED-001"],
            "reason_breakdown": marked_reason,
        }
    )
    learned_decision_payload = contract.learned_reranking_decision.model_dump(mode="json")
    learned_decision_payload.update(
        {
            "status": "applied",
            "requested": True,
            "eligible": True,
            "artifact_validated": True,
            "learned_reranking_applied": True,
            "deterministic_baseline_used": False,
            "fallback_applied": False,
        }
    )
    marked_contract = contract.model_copy(
        update={
            "selected_recommendations": [
                marked_item,
                *contract.selected_recommendations[1:],
            ],
            "learned_reranking_decision": LearnedRerankingDecision.model_validate(
                learned_decision_payload
            ),
            "preselection_scores": [
                marked_trace,
                *contract.preselection_scores[1:],
            ],
        }
    )

    assert validate_recommendation_set_contract_v1(marked_contract) == []


def test_recommendation_set_contract_rejects_component_signal_sum_mismatch() -> None:
    request = RecommendationRequest.model_validate(
        {
            "user_profile": {
                "age": 41,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "symptoms": ["difficulty_falling_asleep"],
        }
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    original = contract.selected_recommendations[0]
    updated_breakdown = original.score_breakdown.model_copy(
        update={
            "symptom_alignment": original.score_breakdown.symptom_alignment + 1.0,
            "total": original.score_breakdown.total + 1.0,
        }
    )
    updated_terms = [
        term.model_copy(update={"points": term.points + 1.0})
        if term.term == "symptom_alignment"
        else term
        for term in original.reason_breakdown.score_terms
    ]
    updated_reason = original.reason_breakdown.model_copy(
        update={
            "score_terms": updated_terms,
            "score_total": original.reason_breakdown.score_total + 1.0,
        }
    )
    forged_item = original.model_copy(
        update={
            "score_breakdown": updated_breakdown,
            "reason_breakdown": updated_reason,
            "additive_component_total": original.additive_component_total + 1.0,
        }
    )
    forged_contract = contract.model_copy(
        update={
            "selected_recommendations": [
                forged_item,
                *contract.selected_recommendations[1:],
            ]
        }
    )

    issues = validate_recommendation_set_contract_v1(forged_contract)

    assert f"score_signal_component_mismatch::{original.ingredient_key}::symptom" in issues


def test_recommendation_set_contract_summary_reports_connection_map() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    response = recommend(request)
    contract = build_recommendation_set_contract_v1(request, response)

    report = summarize_recommendation_set_contract_v1(contract)

    assert report["issue_count"] == 0
    assert "optimization" in report["connection_map"]
    assert "selected_recommendations.rule_refs" in report["connection_map"]["optimization"]
    assert "decision_uncertainty" in report["connection_map"]["recommendation"]


def test_recommendation_set_contract_rejects_learned_decision_selection_mismatch() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    applied_payload = contract.learned_reranking_decision.model_dump(mode="json")
    applied_payload.update(
        {
            "status": "applied",
            "requested": True,
            "eligible": True,
            "artifact_validated": True,
            "learned_reranking_applied": True,
            "deterministic_baseline_used": False,
            "fallback_applied": False,
        }
    )
    mutated = contract.model_copy(
        update={
            "learned_reranking_decision": LearnedRerankingDecision.model_validate(applied_payload)
        }
    )

    assert "learned_decision_selection_mismatch" in (
        validate_recommendation_set_contract_v1(mutated)
    )


def test_recommendation_set_contract_revalidates_status_against_uncertainty() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))

    mutated = contract.model_copy(update={"response_status": RecommendationStatus.NEEDS_REVIEW})

    assert "decision_uncertainty_response_context_mismatch" in (
        validate_recommendation_set_contract_v1(mutated)
    )


def test_recommendation_set_contract_revalidates_selection_count() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    assert len(contract.selected_recommendations) > 1

    mutated = contract.model_copy(
        update={"selected_recommendations": contract.selected_recommendations[:1]}
    )

    assert "decision_uncertainty_selection_count_mismatch" in (
        validate_recommendation_set_contract_v1(mutated)
    )


def test_recommendation_set_contract_v1_accepts_legacy_payload_without_diagnostics() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    payload = build_recommendation_set_contract_v1(
        request,
        recommend(request),
    ).model_dump(mode="json")
    del payload["decision_uncertainty"]
    del payload["learned_reranking_decision"]
    del payload["preselection_scores"]
    payload["schema_version"] = "recommendation_set_contract_v1"

    legacy_contract = RecommendationSetContractV1.model_validate(payload)

    assert (
        validate_recommendation_set_contract_v1(
            legacy_contract,
            require_current_diagnostics=False,
        )
        == []
    )


def test_diagnostics_contract_rejects_downgrade_by_field_removal() -> None:
    request = RecommendationRequest.model_validate(
        json.loads(
            Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    contract = build_recommendation_set_contract_v1(request, recommend(request))

    missing_both = contract.model_copy(
        update={
            "decision_uncertainty": None,
            "learned_reranking_decision": None,
            "preselection_scores": None,
        }
    )
    missing_learned = contract.model_copy(
        update={"learned_reranking_decision": None}
    )

    assert "required_decision_diagnostics_missing" in (
        validate_recommendation_set_contract_v1(missing_both)
    )
    assert "required_decision_diagnostics_missing" in (
        validate_recommendation_set_contract_v1(missing_learned)
    )

    downgraded = contract.model_copy(
        update={
            "schema_version": "recommendation_set_contract_v1",
            "decision_uncertainty": None,
            "learned_reranking_decision": None,
            "preselection_scores": None,
        }
    )
    assert "current_contract_requires_diagnostics_schema" in (
        validate_recommendation_set_contract_v1(downgraded)
    )


def test_diagnostics_contract_reconciles_snapshot_with_preselection_scores() -> None:
    request_payload = json.loads(
        Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
            encoding="utf-8"
        )
    )
    request_payload["preferences"]["max_products"] = 1
    request = RecommendationRequest.model_validate(request_payload)
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    uncertainty = contract.decision_uncertainty
    assert uncertainty is not None
    forged_snapshot = uncertainty.candidate_ranking_snapshot.model_copy(
        update={
            "candidate_count": 1,
            "runner_up_candidate_key": None,
            "runner_up_selection_score": None,
            "top_two_score_margin": None,
        }
    )
    forged_uncertainty = uncertainty.model_copy(
        update={
            "candidate_ranking_snapshot": forged_snapshot,
        }
    )
    forged = contract.model_copy(update={"decision_uncertainty": forged_uncertainty})

    assert "decision_uncertainty_candidate_count_mismatch" in (
        validate_recommendation_set_contract_v1(forged)
    )


def test_diagnostics_contract_reports_missing_goal_prior_without_key_error() -> None:
    request_payload = json.loads(
        Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
            encoding="utf-8"
        )
    )
    request_payload["preferences"]["max_products"] = 1
    request = RecommendationRequest.model_validate(request_payload)
    contract = build_recommendation_set_contract_v1(request, recommend(request))
    assert contract.preselection_scores is not None
    traced = contract.preselection_scores[0].model_copy(
        update={"expected_support_goals": [RecommendationGoal.HEART_HEALTH]}
    )
    mutated = contract.model_copy(
        update={
            "preselection_scores": [traced, *contract.preselection_scores[1:]]
        }
    )

    issues = validate_recommendation_set_contract_v1(mutated)

    assert any(issue.startswith("missing_goal_prior::") for issue in issues)
