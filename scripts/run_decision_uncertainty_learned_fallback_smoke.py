from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from wellnessbox_rnd.optimizer import service as optimizer_service
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    DecisionUncertainty,
    LearnedRerankingDecision,
    RecommendationRequest,
    RecommendationStatus,
)
from wellnessbox_rnd.schemas.recommendation_contracts import (
    build_recommendation_set_contract_v1,
    validate_recommendation_set_contract_v1,
)
from wellnessbox_rnd.training import load_synthetic_records

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/original_plan/evidence/op047_op048_decision_uncertainty_learned_fallback_smoke_v1.json"
)
SOURCE_PATHS = [
    "scripts/run_decision_uncertainty_learned_fallback_smoke.py",
    "src/wellnessbox_rnd/schemas/recommendation.py",
    "src/wellnessbox_rnd/schemas/recommendation_contracts.py",
    "src/wellnessbox_rnd/models/efficacy_model_v0.py",
    "src/wellnessbox_rnd/training/efficacy_model_v0.py",
    "src/wellnessbox_rnd/models/__init__.py",
    "src/wellnessbox_rnd/optimizer/service.py",
    "src/wellnessbox_rnd/orchestration/recommendation_service.py",
]


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify quantified uncertainty and learned-artifact fallback."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


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


def _write_artifact(path: Path, **updates: object) -> Path:
    payload: dict[str, object] = {
        "model_name": "efficacy_model_v0",
        "cohort_version": "op047_op048_smoke_v1",
        "seed": 1,
        "alpha": 0.1,
        "feature_names": ["baseline_candidate::vitamin_c"],
        "intercept": 0.0,
        "weights": [0.2],
        "target_name": "expected_effect_proxy",
    }
    payload.update(updates)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _source_sha256() -> str:
    digest = hashlib.sha256()
    for relative_path in SOURCE_PATHS:
        path = PROJECT_ROOT / relative_path
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        normalized_text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        digest.update(normalized_text.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", *SOURCE_PATHS],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def main() -> None:
    args = _args()
    complete_request = _request(goals=["sleep_support"])
    complete_response = recommend(complete_request)
    complete_uncertainty = complete_response.decision_uncertainty
    if (
        abs(
            complete_uncertainty.raw_uncertainty_score
            - sum(item.points for item in complete_uncertainty.components)
        )
        > 1e-6
    ):
        raise RuntimeError("uncertainty_component_sum_mismatch")

    missing_request = _request(
        goals=["heart_health"],
        symptoms=[],
        current_supplements=[],
    )
    missing_response = recommend(missing_request)
    missing_conditions = {
        item.code: item.uncertainty_points
        for item in missing_response.decision_uncertainty.additional_input_conditions
    }
    expected_missing = {
        "missing_heart_context": 0.20,
        "missing_primary_symptom": 0.10,
        "missing_current_supplements": 0.05,
    }
    if missing_conditions != expected_missing:
        raise RuntimeError(
            f"additional_input_weight_mismatch:{missing_conditions}!={expected_missing}"
        )

    records = load_synthetic_records(
        PROJECT_ROOT / "data/synthetic/synthetic_longitudinal_v1.jsonl"
    )
    learned_request = next(
        record.request
        for record in records
        if record.user_id == "syn-user-009" and record.follow_up_step == 0
    )
    learned_request_payload = learned_request.model_dump(mode="json")
    learned_request_payload["preferences"]["max_products"] = 5
    learned_request = RecommendationRequest.model_validate(learned_request_payload)
    baseline = recommend(learned_request)
    one_product_payload = learned_request.model_dump(mode="json")
    one_product_payload["preferences"]["max_products"] = 1
    one_product_response = recommend(RecommendationRequest.model_validate(one_product_payload))
    if (
        one_product_response.decision_uncertainty.candidate_ranking_snapshot
        != baseline.decision_uncertainty.candidate_ranking_snapshot
    ):
        raise RuntimeError("candidate_margin_changed_with_output_limit")
    missing_path = recommend(learned_request, enable_learned_reranking=True)
    missing_file = recommend(
        learned_request,
        enable_learned_reranking=True,
        learned_efficacy_artifact_path="artifacts/models/does_not_exist.json",
    )

    with TemporaryDirectory() as temporary_directory:
        temporary_root = Path(temporary_directory)
        malformed_path = temporary_root / "malformed.json"
        malformed_path.write_text("{", encoding="utf-8")
        suspicious_path = _write_artifact(
            temporary_root / "suspicious.json",
            feature_names=["a", "b"],
            weights=[0.1],
        )
        valid_path = _write_artifact(temporary_root / "valid.json")
        missing_identity_path = _write_artifact(temporary_root / "missing-identity.json")
        missing_identity_payload = json.loads(missing_identity_path.read_text(encoding="utf-8"))
        del missing_identity_payload["model_name"]
        missing_identity_path.write_text(
            json.dumps(missing_identity_payload),
            encoding="utf-8",
        )
        unknown_feature_path = _write_artifact(
            temporary_root / "unknown-feature.json",
            feature_names=["unknown_runtime_feature"],
            weights=[0.1],
        )
        extreme_weight_path = _write_artifact(
            temporary_root / "extreme-weight.json",
            weights=[1e307],
        )
        unknown_candidate_path = _write_artifact(
            temporary_root / "unknown-candidate.json",
            feature_names=["baseline_candidate::not_in_catalog"],
            weights=[0.1],
        )
        whitespace_feature_path = _write_artifact(
            temporary_root / "whitespace-feature.json",
            feature_names=["baseline_candidate::vitamin_c "],
            weights=[0.1],
        )
        blank_cohort_path = _write_artifact(
            temporary_root / "blank-cohort.json",
            cohort_version="   ",
        )
        closed_domain_path = _write_artifact(
            temporary_root / "closed-domain.json",
            feature_names=[
                "baseline_candidate::vitamin_c",
                "goal::not_a_goal",
            ],
            weights=[0.1, 0.1],
        )
        malformed = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(malformed_path),
        )
        suspicious = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(suspicious_path),
        )
        applied = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(valid_path),
        )
        missing_identity = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(missing_identity_path),
        )
        unknown_feature = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(unknown_feature_path),
        )
        extreme_weight = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(extreme_weight_path),
        )
        unknown_candidate = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(unknown_candidate_path),
        )
        whitespace_feature = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(whitespace_feature_path),
        )
        blank_cohort = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(blank_cohort_path),
        )
        closed_domain = recommend(
            learned_request,
            enable_learned_reranking=True,
            learned_efficacy_artifact_path=str(closed_domain_path),
        )

        original_predictor = optimizer_service.predict_effect_proxy_from_feature_dict
        prediction_calls = 0

        def _fail_after_one_prediction(*_args: object) -> float:
            nonlocal prediction_calls
            prediction_calls += 1
            if prediction_calls > 1:
                raise ValueError("injected smoke prediction failure")
            return 0.2

        try:
            optimizer_service.predict_effect_proxy_from_feature_dict = _fail_after_one_prediction
            runtime_error = recommend(
                learned_request,
                enable_learned_reranking=True,
                learned_efficacy_artifact_path=str(valid_path),
            )
        finally:
            optimizer_service.predict_effect_proxy_from_feature_dict = original_predictor

    baseline_keys = [item.ingredient_key for item in baseline.recommendations]
    fallback_responses = [
        missing_path,
        missing_file,
        malformed,
        suspicious,
        missing_identity,
        unknown_feature,
        extreme_weight,
        unknown_candidate,
        whitespace_feature,
        blank_cohort,
        closed_domain,
        runtime_error,
    ]
    for response in fallback_responses:
        if response.recommendations != baseline.recommendations:
            raise RuntimeError("learned_fallback_changed_deterministic_selection")
        if response.metadata.mode != "deterministic_baseline_v1":
            raise RuntimeError("learned_fallback_retained_learned_mode")
        if any("OPT-LEARNED-001" in item.rule_refs for item in response.recommendations):
            raise RuntimeError("learned_fallback_retained_learned_rule")
    expected_fallback_statuses = [
        "fallback_missing_path",
        "fallback_missing_file",
        "fallback_invalid_artifact",
        "fallback_suspicious_artifact",
        "fallback_invalid_artifact",
        "fallback_suspicious_artifact",
        "fallback_suspicious_artifact",
        "fallback_suspicious_artifact",
        "fallback_suspicious_artifact",
        "fallback_invalid_artifact",
        "fallback_suspicious_artifact",
        "fallback_artifact_runtime_error",
    ]
    actual_fallback_statuses = [
        item.learned_reranking_decision.status for item in fallback_responses
    ]
    if actual_fallback_statuses != expected_fallback_statuses:
        raise RuntimeError("learned_fallback_status_mismatch")
    if applied.learned_reranking_decision.status != "applied":
        raise RuntimeError("valid_learned_artifact_not_applied")
    if applied.recommendations[0].ingredient_key != "vitamin_c":
        raise RuntimeError("valid_learned_artifact_did_not_rerank")

    uncertainty_fail_closed = False
    uncertainty_payload = complete_uncertainty.model_dump(mode="json")
    uncertainty_payload["raw_uncertainty_score"] += 0.1
    try:
        DecisionUncertainty.model_validate(uncertainty_payload)
    except ValidationError:
        uncertainty_fail_closed = True

    learned_fail_closed = False
    learned_payload = baseline.learned_reranking_decision.model_dump(mode="json")
    learned_payload["status"] = "applied"
    try:
        LearnedRerankingDecision.model_validate(learned_payload)
    except ValidationError:
        learned_fail_closed = True
    if not uncertainty_fail_closed or not learned_fail_closed:
        raise RuntimeError("uncertainty_or_learned_schema_failed_open")

    ranking_trace_fail_closed = False
    ranking_payload = one_product_response.model_dump(mode="json")
    ranking_payload["decision_uncertainty"]["candidate_ranking_snapshot"][
        "candidate_count"
    ] = 1
    try:
        type(one_product_response).model_validate(ranking_payload)
    except ValidationError:
        ranking_trace_fail_closed = True
    if not ranking_trace_fail_closed:
        raise RuntimeError("ranking_snapshot_score_trace_failed_open")

    score_registry_fail_closed = False
    registry_payload = one_product_response.model_dump(mode="json")
    traced = registry_payload["candidate_pool_trace"]["preselection_scores"][1]
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
    try:
        type(one_product_response).model_validate(registry_payload)
    except ValidationError:
        score_registry_fail_closed = True
    if not score_registry_fail_closed:
        raise RuntimeError("preselection_score_registry_failed_open")

    mode_fail_closed = False
    mode_payload = baseline.model_dump(mode="json")
    mode_payload["metadata"]["mode"] = "deterministic_baseline_v1_learned_efficacy_rerank_v999"
    try:
        type(baseline).model_validate(mode_payload)
    except ValidationError:
        mode_fail_closed = True
    if not mode_fail_closed:
        raise RuntimeError("fallback_engine_mode_failed_open")

    contract = build_recommendation_set_contract_v1(learned_request, applied)
    contract_issues = validate_recommendation_set_contract_v1(contract)
    if contract_issues:
        raise RuntimeError(f"learned_recommendation_contract_invalid:{contract_issues}")
    baseline_contract = build_recommendation_set_contract_v1(learned_request, baseline)
    status_mutation = baseline_contract.model_copy(
        update={"response_status": RecommendationStatus.NEEDS_REVIEW}
    )
    selection_mutation = baseline_contract.model_copy(
        update={"selected_recommendations": baseline_contract.selected_recommendations[:1]}
    )
    status_mutation_issues = validate_recommendation_set_contract_v1(status_mutation)
    selection_mutation_issues = validate_recommendation_set_contract_v1(selection_mutation)
    if "decision_uncertainty_response_context_mismatch" not in status_mutation_issues:
        raise RuntimeError("contract_status_mutation_not_detected")
    if "decision_uncertainty_selection_count_mismatch" not in selection_mutation_issues:
        raise RuntimeError("contract_selection_mutation_not_detected")
    diagnostics_downgrade = baseline_contract.model_copy(
        update={
            "decision_uncertainty": None,
            "learned_reranking_decision": None,
            "preselection_scores": None,
        }
    )
    diagnostics_downgrade_issues = validate_recommendation_set_contract_v1(
        diagnostics_downgrade
    )
    if "required_decision_diagnostics_missing" not in diagnostics_downgrade_issues:
        raise RuntimeError("contract_diagnostics_downgrade_not_detected")
    version_downgrade = baseline_contract.model_copy(
        update={
            "schema_version": "recommendation_set_contract_v1",
            "decision_uncertainty": None,
            "learned_reranking_decision": None,
            "preselection_scores": None,
        }
    )
    version_downgrade_issues = validate_recommendation_set_contract_v1(
        version_downgrade
    )
    if "current_contract_requires_diagnostics_schema" not in version_downgrade_issues:
        raise RuntimeError("contract_version_downgrade_not_detected")

    report = {
        "schema_version": "op047_op048_decision_uncertainty_learned_fallback_smoke_v1",
        "requirement_stages": {"OP-047": "IMPLEMENTED", "OP-048": "IMPLEMENTED"},
        "cases": {
            "complete_input_uncertainty": complete_uncertainty.model_dump(mode="json"),
            "missing_input_uncertainty": missing_response.decision_uncertainty.model_dump(
                mode="json"
            ),
            "preselection_close_ranking_with_one_output": (
                one_product_response.decision_uncertainty.model_dump(mode="json")
            ),
            "learned_fallback": {
                "baseline_candidate_keys": baseline_keys,
                "statuses": actual_fallback_statuses,
                "suspicious_issues": suspicious.learned_reranking_decision.issues,
                "unknown_feature_issues": (unknown_feature.learned_reranking_decision.issues),
                "extreme_weight_issues": (extreme_weight.learned_reranking_decision.issues),
                "unknown_candidate_issues": (
                    unknown_candidate.learned_reranking_decision.issues
                ),
                "whitespace_feature_issues": (
                    whitespace_feature.learned_reranking_decision.issues
                ),
                "closed_domain_issues": (
                    closed_domain.learned_reranking_decision.issues
                ),
                "runtime_prediction_calls": prediction_calls,
            },
            "valid_learned_artifact": {
                "status": applied.learned_reranking_decision.status,
                "selected_candidate_keys": [
                    item.ingredient_key for item in applied.recommendations
                ],
                "engine_mode": applied.metadata.mode,
            },
            "schema_fail_closed": {
                "uncertainty_total": uncertainty_fail_closed,
                "learned_flags": learned_fail_closed,
                "fallback_engine_mode": mode_fail_closed,
                "ranking_snapshot_score_trace": ranking_trace_fail_closed,
                "preselection_score_registry": score_registry_fail_closed,
            },
            "contract_bridge": {
                "issue_count": len(contract_issues),
                "status_mutation_issues": status_mutation_issues,
                "selection_mutation_issues": selection_mutation_issues,
                "diagnostics_downgrade_issues": diagnostics_downgrade_issues,
                "version_downgrade_issues": version_downgrade_issues,
            },
        },
        "checks": [
            "missing_input_importance_is_converted_to_versioned_numeric_points",
            "uncertainty_components_reconcile_to_raw_and_bounded_scores",
            "uncertainty_score_is_not_a_clinical_probability",
            "candidate_margin_uses_preselection_pool_independent_of_output_limit",
            "ranking_snapshot_reconciles_with_independent_preselection_scores",
            "every_preselection_score_reconciles_with_external_registries",
            "missing_path_and_file_preserve_deterministic_selection",
            "invalid_identity_unsupported_features_and_extreme_weights_fall_back",
            "runtime_prediction_error_discards_all_partial_reranking",
            "all_fallback_cases_preserve_the_full_deterministic_recommendations",
            "fallback_clears_learned_rules_bonus_and_engine_mode",
            "valid_artifact_can_apply_only_after_runtime_validation",
            "uncertainty_and_learned_diagnostic_mismatches_fail_closed",
            "non_applied_response_requires_exact_deterministic_engine_mode",
            "recommendation_contract_preserves_diagnostics",
            "recommendation_contract_revalidates_status_and_selection_count",
            "diagnostics_contract_version_rejects_field_removal_downgrade",
        ],
        "source_identity": {
            "commit": _git_commit(),
            "source_sha256": _source_sha256(),
        },
        "production_operation_proven": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
