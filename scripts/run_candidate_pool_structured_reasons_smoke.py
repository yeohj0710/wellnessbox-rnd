from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from pydantic import ValidationError

from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    CandidatePoolTrace,
    RecommendationReasonBreakdown,
    RecommendationRequest,
)
from wellnessbox_rnd.schemas.recommendation_contracts import (
    build_recommendation_set_contract_v1,
    validate_recommendation_set_contract_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data/original_plan/evidence/op045_op046_candidate_pool_structured_reasons_smoke_v1.json"
)
SOURCE_PATHS = [
    "scripts/run_candidate_pool_structured_reasons_smoke.py",
    "src/wellnessbox_rnd/schemas/recommendation.py",
    "src/wellnessbox_rnd/schemas/recommendation_contracts.py",
    "src/wellnessbox_rnd/optimizer/service.py",
    "src/wellnessbox_rnd/orchestration/recommendation_service.py",
]


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify candidate-pool preservation and structured reasons."
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

    warfarin_request = _request(
        goals=["heart_health"],
        medications=[{"name": "warfarin"}],
    )
    warfarin_response = recommend(warfarin_request)
    trace = warfarin_response.candidate_pool_trace
    pre_keys = {item.ingredient_key for item in trace.pre_safety_candidates}
    excluded_keys = {item.ingredient_key for item in trace.excluded_candidates}
    post_keys = {item.ingredient_key for item in trace.post_safety_candidates}
    selected_keys = set(trace.selected_candidate_keys)
    omega3_exclusion = next(
        item for item in trace.excluded_candidates if item.ingredient_key == "omega3"
    )
    if pre_keys != excluded_keys | post_keys or excluded_keys & post_keys:
        raise RuntimeError("candidate_pool_partition_mismatch")
    if not selected_keys.issubset(post_keys):
        raise RuntimeError("selected_candidates_outside_post_safety_pool")
    if omega3_exclusion.exclusion_reasons != ["safety_summary_excluded"]:
        raise RuntimeError("omega3_safety_exclusion_missing")
    coq10 = next(
        item
        for item in warfarin_response.recommendations
        if item.ingredient_key == "coq10"
    )
    safety_inputs = [
        item
        for item in coq10.reason_breakdown.input_signals
        if item.source == "safety"
    ]
    safety_links = [
        item
        for item in coq10.reason_breakdown.evidence_links
        if item.evidence_source == "safety_rule"
    ]
    safety_term = next(
        item
        for item in coq10.reason_breakdown.score_terms
        if item.term == "safety_adjustment"
    )
    if [item.code for item in safety_inputs] != ["SAFETY-ANTICOAG-001"]:
        raise RuntimeError("structured_safety_input_missing")
    if not safety_links or safety_links[0].reference_ids != ["REF-NIH-ODS-OMEGA3-001"]:
        raise RuntimeError("structured_safety_evidence_missing")
    if "SAFETY-ANTICOAG-001" not in safety_term.rule_ids:
        raise RuntimeError("structured_safety_score_rule_missing")

    exclusion_response = recommend(
        _request(
            goals=["sleep_support"],
            current_supplements=[{"name": "L-Theanine", "ingredients": []}],
            preferences={
                "max_products": 5,
                "avoid_ingredients": ["magnesium_glycinate"],
            },
        )
    )
    exclusion_reasons = {
        item.ingredient_key: item.exclusion_reasons
        for item in exclusion_response.candidate_pool_trace.excluded_candidates
    }
    if "user_avoidance" not in exclusion_reasons.get("magnesium_glycinate", []):
        raise RuntimeError("user_avoidance_exclusion_missing")
    if "current_regimen_overlap" not in exclusion_reasons.get("l_theanine", []):
        raise RuntimeError("current_regimen_exclusion_missing")

    blocked_payload = json.loads(
        (
            PROJECT_ROOT
            / "data/samples/api_recommend_structured_health_input_request_v1.json"
        ).read_text(encoding="utf-8")
    )
    blocked_response = recommend(RecommendationRequest.model_validate(blocked_payload))
    blocked_trace = blocked_response.candidate_pool_trace
    if (
        not blocked_trace.global_blocked
        or blocked_trace.selected_candidate_keys
        or blocked_response.recommendations
    ):
        raise RuntimeError("global_block_retained_selection")

    reason_request = _request(
        goals=["sleep_support"],
        symptoms=["difficulty_falling_asleep"],
        lifestyle={
            "sleep_hours": 5.0,
            "stress_level": 4,
            "activity_level": "lightly_active",
        },
    )
    reason_response = recommend(reason_request)
    candidate = next(
        item
        for item in reason_response.recommendations
        if item.ingredient_key == "magnesium_glycinate"
    )
    reason = candidate.reason_breakdown
    term_points = {item.term: item.points for item in reason.score_terms}
    input_signals = {(item.source, item.code) for item in reason.input_signals}
    expected_inputs = {
        ("goal", "sleep_support"),
        ("symptom", "difficulty_falling_asleep"),
        ("lifestyle", "high_stress"),
        ("lifestyle", "sleep_deficit"),
    }
    if not expected_inputs.issubset(input_signals):
        raise RuntimeError("structured_reason_input_signal_missing")
    if len(term_points) != 14:
        raise RuntimeError("structured_reason_score_term_count_mismatch")
    if abs(sum(term_points.values()) - reason.score_total) > 1e-6:
        raise RuntimeError("structured_reason_score_total_mismatch")
    if abs(reason.score_total - candidate.score_breakdown.total) > 1e-6:
        raise RuntimeError("structured_reason_candidate_total_mismatch")
    if not reason.reference_ids or not reason.claim_ids or not reason.limitations:
        raise RuntimeError("structured_reason_evidence_ids_missing")
    linked_reference_ids = {
        value for link in reason.evidence_links for value in link.reference_ids
    }
    linked_claim_ids = {value for link in reason.evidence_links for value in link.claim_ids}
    if linked_reference_ids != set(reason.reference_ids):
        raise RuntimeError("structured_reason_reference_association_mismatch")
    if linked_claim_ids != set(reason.claim_ids):
        raise RuntimeError("structured_reason_claim_association_mismatch")

    contract = build_recommendation_set_contract_v1(reason_request, reason_response)
    contract_issues = validate_recommendation_set_contract_v1(contract)
    if contract_issues:
        raise RuntimeError(f"recommendation_contract_invalid:{contract_issues}")

    trace_fail_closed = False
    trace_payload = trace.model_dump(mode="json")
    trace_payload["post_safety_candidates"] = []
    try:
        CandidatePoolTrace.model_validate(trace_payload)
    except ValidationError:
        trace_fail_closed = True

    trace_identity_fail_closed = False
    trace_identity_payload = trace.model_dump(mode="json")
    trace_identity_payload["post_safety_candidates"][0]["display_name"] = "mutated"
    try:
        CandidatePoolTrace.model_validate(trace_identity_payload)
    except ValidationError:
        trace_identity_fail_closed = True

    reason_fail_closed = False
    reason_payload = reason.model_dump(mode="json")
    reason_payload["score_total"] += 1.0
    try:
        RecommendationReasonBreakdown.model_validate(reason_payload)
    except ValidationError:
        reason_fail_closed = True

    reason_completeness_fail_closed = False
    incomplete_reason_payload = reason.model_dump(mode="json")
    removed_term = incomplete_reason_payload["score_terms"].pop()
    incomplete_reason_payload["score_total"] -= removed_term["points"]
    try:
        RecommendationReasonBreakdown.model_validate(incomplete_reason_payload)
    except ValidationError:
        reason_completeness_fail_closed = True
    if not all(
        (
            trace_fail_closed,
            trace_identity_fail_closed,
            reason_fail_closed,
            reason_completeness_fail_closed,
        )
    ):
        raise RuntimeError("candidate_pool_or_reason_contract_failed_open")

    report = {
        "schema_version": "op045_op046_candidate_pool_structured_reasons_smoke_v1",
        "requirement_stages": {"OP-045": "IMPLEMENTED", "OP-046": "IMPLEMENTED"},
        "cases": {
            "safety_partition": {
                "pre_safety_candidate_keys": sorted(pre_keys),
                "excluded_candidate_keys": sorted(excluded_keys),
                "post_safety_candidate_keys": sorted(post_keys),
                "selected_candidate_keys": sorted(selected_keys),
                "omega3_exclusion_reasons": omega3_exclusion.exclusion_reasons,
                "applied_safety_rule_ids": trace.applied_safety_rule_ids,
                "selected_candidate_safety_reason": {
                    "ingredient_key": coq10.ingredient_key,
                    "input_signals": [
                        item.model_dump(mode="json") for item in safety_inputs
                    ],
                    "score_term": safety_term.model_dump(mode="json"),
                    "evidence_links": [
                        item.model_dump(mode="json") for item in safety_links
                    ],
                },
            },
            "explicit_exclusion_sources": exclusion_reasons,
            "global_block": {
                "pre_safety_candidate_count": len(blocked_trace.pre_safety_candidates),
                "selected_candidate_keys": blocked_trace.selected_candidate_keys,
                "global_blocked": blocked_trace.global_blocked,
                "applied_safety_rule_ids": blocked_trace.applied_safety_rule_ids,
            },
            "structured_reason": {
                "ingredient_key": candidate.ingredient_key,
                "input_signals": sorted(f"{source}:{code}" for source, code in input_signals),
                "score_terms": term_points,
                "score_total": reason.score_total,
                "rule_ids": reason.rule_ids,
                "reference_ids": reason.reference_ids,
                "claim_ids": reason.claim_ids,
                "limitations": reason.limitations,
                "evidence_links": [
                    item.model_dump(mode="json") for item in reason.evidence_links
                ],
            },
            "contract_bridge": {
                "issue_count": len(contract_issues),
                "selected_count": len(contract.selected_recommendations),
            },
            "schema_fail_closed": {
                "candidate_pool_partition": trace_fail_closed,
                "candidate_identity": trace_identity_fail_closed,
                "structured_reason_total": reason_fail_closed,
                "structured_reason_completeness": reason_completeness_fail_closed,
            },
        },
        "checks": [
            "pre_safety_pool_is_exact_partition_of_excluded_and_post_safety_candidates",
            "selected_candidates_are_subset_of_post_safety_candidates",
            "safety_user_avoidance_and_current_regimen_exclusions_are_distinguished",
            "global_safety_block_preserves_pool_and_clears_selection",
            "input_signals_score_terms_and_evidence_ids_are_separated",
            "safety_adjustment_preserves_trigger_rule_and_evidence",
            "evidence_ids_are_associated_with_goal_or_input_signal",
            "fourteen_score_terms_reconcile_to_candidate_total",
            "recommendation_contract_cross_checks_structured_reason",
            "candidate_pool_and_reason_schema_mismatches_fail_closed",
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
