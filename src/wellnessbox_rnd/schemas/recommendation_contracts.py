from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import (
    CandidatePreselectionScore,
    CandidateScoreBreakdown,
    DecisionUncertainty,
    LearnedRerankingDecision,
    NextAction,
    RecommendationGoal,
    RecommendationReasonBreakdown,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationStatus,
    RuleReference,
)

RECOMMENDATION_SET_CONTRACT_SCHEMA_VERSION_V1 = "recommendation_set_contract_v1"
RECOMMENDATION_SET_CONTRACT_DIAGNOSTICS_SCHEMA_VERSION_V1 = (
    "recommendation_set_contract_v1_decision_diagnostics_v1"
)
_SCORE_TOLERANCE = 1e-6


class RecommendationSelectionItemV1(BaseModel):
    ingredient_key: str
    expected_support_goals: list[RecommendationGoal] = Field(default_factory=list)
    rule_refs: list[str] = Field(default_factory=list)
    catalog_priority: float
    score_breakdown: CandidateScoreBreakdown
    reason_breakdown: RecommendationReasonBreakdown
    additive_component_total: float


class RecommendationSetContractV1(BaseModel):
    schema_version: Literal[
        "recommendation_set_contract_v1",
        "recommendation_set_contract_v1_decision_diagnostics_v1",
    ] = RECOMMENDATION_SET_CONTRACT_SCHEMA_VERSION_V1
    request_id: str
    response_status: RecommendationStatus
    decision_uncertainty: DecisionUncertainty | None = None
    learned_reranking_decision: LearnedRerankingDecision | None = None
    preselection_scores: list[CandidatePreselectionScore] | None = None
    safety_rule_refs: list[RuleReference] = Field(default_factory=list)
    next_action: NextAction
    selection_limit: int = Field(ge=1)
    normalized_focus_goals: list[RecommendationGoal] = Field(default_factory=list)
    excluded_ingredient_keys: list[str] = Field(default_factory=list)
    selected_recommendations: list[RecommendationSelectionItemV1] = Field(default_factory=list)


def build_recommendation_set_contract_v1(
    request: RecommendationRequest,
    response: RecommendationResponse,
) -> RecommendationSetContractV1:
    from wellnessbox_rnd.domain.catalog import list_catalog_items

    catalog_by_key = {item.key: item for item in list_catalog_items()}
    return RecommendationSetContractV1(
        schema_version=RECOMMENDATION_SET_CONTRACT_DIAGNOSTICS_SCHEMA_VERSION_V1,
        request_id=response.request_id,
        response_status=response.status,
        decision_uncertainty=response.decision_uncertainty,
        learned_reranking_decision=response.learned_reranking_decision,
        preselection_scores=list(response.candidate_pool_trace.preselection_scores),
        safety_rule_refs=list(response.safety_summary.rule_refs),
        next_action=response.next_action,
        selection_limit=request.preferences.max_products,
        normalized_focus_goals=list(response.normalized_focus_goals),
        excluded_ingredient_keys=list(response.safety_summary.excluded_ingredients),
        selected_recommendations=[
            RecommendationSelectionItemV1(
                ingredient_key=item.ingredient_key,
                expected_support_goals=list(item.expected_support_goals),
                rule_refs=list(item.rule_refs),
                catalog_priority=catalog_by_key[item.ingredient_key].default_priority,
                score_breakdown=item.score_breakdown,
                reason_breakdown=item.reason_breakdown,
                additive_component_total=_score_component_total(
                    item.score_breakdown,
                    catalog_priority=catalog_by_key[item.ingredient_key].default_priority,
                ),
            )
            for item in response.recommendations
        ],
    )


def validate_recommendation_set_contract_v1(
    contract: RecommendationSetContractV1,
    *,
    require_current_diagnostics: bool = True,
) -> list[str]:
    issues: list[str] = []
    diagnostics_present = (
        contract.decision_uncertainty is not None
        and contract.learned_reranking_decision is not None
        and contract.preselection_scores is not None
    )
    diagnostics_partially_present = (
        contract.decision_uncertainty is not None
        or contract.learned_reranking_decision is not None
        or contract.preselection_scores is not None
    )
    diagnostics_version = (
        contract.schema_version
        == RECOMMENDATION_SET_CONTRACT_DIAGNOSTICS_SCHEMA_VERSION_V1
    )
    if diagnostics_version and not diagnostics_present:
        issues.append("required_decision_diagnostics_missing")
    if not diagnostics_version and diagnostics_partially_present:
        issues.append("legacy_contract_cannot_contain_decision_diagnostics")
    if require_current_diagnostics and not diagnostics_version:
        issues.append("current_contract_requires_diagnostics_schema")
    selected_keys = [item.ingredient_key for item in contract.selected_recommendations]
    if len(selected_keys) > contract.selection_limit:
        issues.append("selection_limit_exceeded")
    if len(selected_keys) != len(set(selected_keys)):
        issues.append("duplicate_selected_ingredient_keys")
    learned_selected = any(
        "OPT-LEARNED-001" in item.rule_refs
        or abs(item.score_breakdown.learned_effect_bonus) > _SCORE_TOLERANCE
        for item in contract.selected_recommendations
    )
    if (
        contract.learned_reranking_decision is not None
        and contract.learned_reranking_decision.learned_reranking_applied != learned_selected
    ):
        issues.append("learned_decision_selection_mismatch")
    issues.extend(_validate_decision_uncertainty_contract(contract, selected_keys))
    if contract.preselection_scores is not None:
        for traced in contract.preselection_scores:
            issues.extend(
                validate_candidate_preselection_score_contract(
                    traced,
                    safety_rule_refs=contract.safety_rule_refs,
                )
            )

    normalized_focus_goal_values = {goal.value for goal in contract.normalized_focus_goals}
    excluded_keys = set(contract.excluded_ingredient_keys)

    for item in contract.selected_recommendations:
        if item.ingredient_key in excluded_keys:
            issues.append(f"selected_key_is_excluded::{item.ingredient_key}")
        unsupported_goals = [
            goal.value
            for goal in item.expected_support_goals
            if goal.value not in normalized_focus_goal_values
        ]
        if unsupported_goals:
            issues.append(
                f"candidate_goal_outside_request::{item.ingredient_key}::{','.join(sorted(unsupported_goals))}"
            )
        if not any(rule_ref.startswith("OPT-") for rule_ref in item.rule_refs):
            issues.append(f"missing_optimizer_rule_ref::{item.ingredient_key}")
        if "OPT-BASELINE-001" not in item.rule_refs:
            issues.append(f"missing_baseline_optimizer_rule_ref::{item.ingredient_key}")
        learned_marker_present = "OPT-LEARNED-001" in item.rule_refs
        learned_bonus_present = abs(item.score_breakdown.learned_effect_bonus) > _SCORE_TOLERANCE
        if learned_bonus_present and not learned_marker_present:
            issues.append(f"learned_bonus_rule_marker_mismatch::{item.ingredient_key}")
        expected_total = _score_component_total(
            item.score_breakdown,
            catalog_priority=item.catalog_priority,
        )
        if abs(item.additive_component_total - expected_total) > _SCORE_TOLERANCE:
            issues.append(f"stored_component_total_mismatch::{item.ingredient_key}")
        if abs(item.score_breakdown.total - expected_total) > _SCORE_TOLERANCE:
            issues.append(f"score_total_mismatch::{item.ingredient_key}")
        if abs(item.reason_breakdown.score_total - expected_total) > _SCORE_TOLERANCE:
            issues.append(f"reason_score_total_mismatch::{item.ingredient_key}")
        reason_terms = {term.term: term.points for term in item.reason_breakdown.score_terms}
        for term, expected_points in _score_term_values(
            item.score_breakdown,
            catalog_priority=item.catalog_priority,
        ).items():
            actual_points = reason_terms.get(term)
            if actual_points is None or abs(actual_points - expected_points) > _SCORE_TOLERANCE:
                issues.append(f"reason_score_term_mismatch::{item.ingredient_key}::{term}")
        missing_reason_rule_refs = sorted(set(item.rule_refs) - set(item.reason_breakdown.rule_ids))
        if missing_reason_rule_refs:
            issues.append(
                f"reason_missing_candidate_rule_refs::{item.ingredient_key}::"
                f"{','.join(missing_reason_rule_refs)}"
            )
        issues.extend(
            _validate_reason_evidence_contract(
                item,
                safety_rule_refs=contract.safety_rule_refs,
            )
        )

    return issues


def summarize_recommendation_set_contract_v1(
    contract: RecommendationSetContractV1,
    *,
    request_fixture_path: str | Path | None = None,
) -> dict[str, object]:
    issues = validate_recommendation_set_contract_v1(contract)
    selected_keys = [item.ingredient_key for item in contract.selected_recommendations]
    return {
        "schema_version": contract.schema_version,
        "request_fixture_path": (
            str(request_fixture_path) if request_fixture_path is not None else None
        ),
        "request_id": contract.request_id,
        "response_status": contract.response_status.value,
        "next_action": contract.next_action.value,
        "selection_limit": contract.selection_limit,
        "selected_count": len(contract.selected_recommendations),
        "unique_selected_count": len(set(selected_keys)),
        "issue_count": len(issues),
        "issues": issues,
        "optimization_constraints_checked": [
            "selection_count_lte_max_products",
            "selected_ingredients_unique",
            "selected_ingredients_not_in_excluded_keys",
            "candidate_goals_subset_of_normalized_focus_goals",
            "candidate_rule_refs_include_optimizer_marker",
            "candidate_score_total_matches_catalog_priority_plus_components",
            "candidate_reason_terms_match_score_breakdown",
            "candidate_reason_total_matches_score_breakdown",
            "candidate_reason_includes_candidate_rule_refs",
            "candidate_score_components_match_applied_signal_points",
            "candidate_goal_score_matches_registered_goal_priors",
            "learned_bonus_matches_learned_rule_marker",
            "learned_decision_matches_selected_candidates",
            "decision_uncertainty_components_reconcile_to_bounded_total",
        ],
        "connection_map": {
            "recommendation": [
                "selected_recommendations.ingredient_key",
                "selected_recommendations.expected_support_goals",
                "selected_recommendations.score_breakdown",
                "selected_recommendations.reason_breakdown",
                "decision_uncertainty",
                "learned_reranking_decision",
            ],
            "optimization": [
                "selection_limit",
                "selected_recommendations.rule_refs",
                "selected_recommendations.catalog_priority",
                "selected_recommendations.additive_component_total",
            ],
            "safety": ["excluded_ingredient_keys", "safety_rule_refs"],
            "follow_up": ["next_action"],
        },
        "example_event": contract.model_dump(mode="json"),
    }


def write_recommendation_set_contract_report_v1(
    report: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
    output_example_json_path: str | Path | None = None,
) -> None:
    output_json = Path(output_json_path)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    output_md = Path(output_md_path)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(
        render_recommendation_set_contract_markdown_v1(report),
        encoding="utf-8",
    )

    if output_example_json_path is not None:
        output_example_json = Path(output_example_json_path)
        output_example_json.parent.mkdir(parents=True, exist_ok=True)
        output_example_json.write_text(
            json.dumps(report["example_event"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def render_recommendation_set_contract_markdown_v1(report: dict[str, object]) -> str:
    example_event = report["example_event"]
    selected_keys = [item["ingredient_key"] for item in example_event["selected_recommendations"]]
    lines = [
        "# recommendation set contract v1",
        "",
        "## summary",
        f"- request_fixture_path: `{report['request_fixture_path']}`",
        f"- response_status: `{report['response_status']}`",
        f"- next_action: `{report['next_action']}`",
        f"- selection_limit: `{report['selection_limit']}`",
        f"- selected_count: `{report['selected_count']}`",
        f"- issue_count: `{report['issue_count']}`",
        "",
        "## optimization constraints checked",
    ]
    lines.extend(f"- `{constraint}`" for constraint in report["optimization_constraints_checked"])
    lines.extend(
        [
            "",
            "## connection map",
            "- recommendation: "
            + ", ".join(f"`{item}`" for item in report["connection_map"]["recommendation"]),
            "- optimization: "
            + ", ".join(f"`{item}`" for item in report["connection_map"]["optimization"]),
            "- safety: " + ", ".join(f"`{item}`" for item in report["connection_map"]["safety"]),
            "- follow_up: "
            + ", ".join(f"`{item}`" for item in report["connection_map"]["follow_up"]),
            "",
            "## example event",
            f"- selected_ingredient_keys: `{selected_keys}`",
            f"- excluded_ingredient_keys: `{example_event['excluded_ingredient_keys']}`",
            f"- normalized_focus_goals: `{example_event['normalized_focus_goals']}`",
        ]
    )
    if report["issues"]:
        lines.extend(["", "## issues"])
        lines.extend(f"- `{issue}`" for issue in report["issues"])
    return "\n".join(lines) + "\n"


def _score_component_total(
    score_breakdown: CandidateScoreBreakdown,
    *,
    catalog_priority: float,
) -> float:
    return round(
        catalog_priority
        + score_breakdown.goal_alignment
        + score_breakdown.symptom_alignment
        + score_breakdown.lifestyle_alignment
        + score_breakdown.laboratory_alignment
        + score_breakdown.dietary_alignment
        + score_breakdown.wearable_adjustment
        + score_breakdown.cgm_adjustment
        + score_breakdown.genetic_adjustment
        + score_breakdown.evidence_readiness
        + score_breakdown.budget_adjustment
        + score_breakdown.safety_adjustment
        + score_breakdown.conservative_adjustment
        + score_breakdown.learned_effect_bonus,
        6,
    )


def _score_term_values(
    score_breakdown: CandidateScoreBreakdown,
    *,
    catalog_priority: float,
) -> dict[str, float]:
    return {
        "catalog_priority": catalog_priority,
        "goal_alignment": score_breakdown.goal_alignment,
        "symptom_alignment": score_breakdown.symptom_alignment,
        "lifestyle_alignment": score_breakdown.lifestyle_alignment,
        "laboratory_alignment": score_breakdown.laboratory_alignment,
        "dietary_alignment": score_breakdown.dietary_alignment,
        "wearable_adjustment": score_breakdown.wearable_adjustment,
        "cgm_adjustment": score_breakdown.cgm_adjustment,
        "genetic_adjustment": score_breakdown.genetic_adjustment,
        "evidence_readiness": score_breakdown.evidence_readiness,
        "budget_adjustment": score_breakdown.budget_adjustment,
        "safety_adjustment": score_breakdown.safety_adjustment,
        "conservative_adjustment": score_breakdown.conservative_adjustment,
        "learned_effect_bonus": score_breakdown.learned_effect_bonus,
    }


def _validate_reason_evidence_contract(
    item: RecommendationSelectionItemV1,
    *,
    safety_rule_refs: list[RuleReference],
) -> list[str]:
    from wellnessbox_rnd.knowledge.goal_priors import get_goal_prior_index

    issues: list[str] = []
    reason = item.reason_breakdown
    expected_goal_inputs = {(goal.value, "requested", None) for goal in item.expected_support_goals}
    actual_goal_inputs = {
        (signal.code, signal.observed_value, signal.unit)
        for signal in reason.input_signals
        if signal.source == "goal"
    }
    if actual_goal_inputs != expected_goal_inputs:
        issues.append(f"reason_goal_input_mismatch::{item.ingredient_key}")

    expected_scored_inputs = {
        (signal.source, signal.code, signal.observed_value, signal.unit)
        for signal in item.score_breakdown.applied_signals
    }
    actual_scored_inputs = {
        (signal.source, signal.code, signal.observed_value, signal.unit)
        for signal in reason.input_signals
        if signal.source not in {"goal", "safety"}
    }
    if actual_scored_inputs != expected_scored_inputs:
        issues.append(f"reason_scored_input_mismatch::{item.ingredient_key}")

    goal_priors = get_goal_prior_index()
    missing_goal_priors = [
        goal.value
        for goal in item.expected_support_goals
        if (item.ingredient_key, goal) not in goal_priors
    ]
    if missing_goal_priors:
        issues.append(
            f"missing_goal_prior::{item.ingredient_key}::"
            f"{','.join(sorted(missing_goal_priors))}"
        )
    expected_goal_links = {
        (
            goal.value,
            frozenset(goal_priors[(item.ingredient_key, goal)].reference_ids),
            frozenset(goal_priors[(item.ingredient_key, goal)].claim_ids),
            frozenset(goal_priors[(item.ingredient_key, goal)].limitations),
        )
        for goal in item.expected_support_goals
        if (item.ingredient_key, goal) in goal_priors
    }
    actual_goal_links = {
        (
            link.code,
            frozenset(link.reference_ids),
            frozenset(link.claim_ids),
            frozenset(link.limitations),
        )
        for link in reason.evidence_links
        if link.evidence_source == "goal_prior" and link.rule_id is None
    }
    if actual_goal_links != expected_goal_links:
        issues.append(f"reason_goal_prior_evidence_mismatch::{item.ingredient_key}")

    expected_signal_links = {
        (
            signal.code,
            signal.rule_id,
            frozenset(signal.reference_ids),
            frozenset(signal.claim_ids),
            frozenset([signal.limitation]),
        )
        for signal in item.score_breakdown.applied_signals
    }
    actual_signal_links = {
        (
            link.code,
            link.rule_id,
            frozenset(link.reference_ids),
            frozenset(link.claim_ids),
            frozenset(link.limitations),
        )
        for link in reason.evidence_links
        if link.evidence_source == "input_signal"
    }
    if actual_signal_links != expected_signal_links:
        issues.append(f"reason_input_signal_evidence_mismatch::{item.ingredient_key}")

    safety_adjusted = abs(item.score_breakdown.safety_adjustment) > _SCORE_TOLERANCE
    expected_safety_inputs: set[tuple[str, str, None]] = set()
    expected_safety_links: set[tuple[str, str, frozenset[str], frozenset[str], frozenset[str]]] = (
        set()
    )
    safety_rule_ids: set[str] = set()
    if safety_adjusted and safety_rule_refs:
        expected_safety_inputs = {
            (rule.rule_id, RecommendationStatus.NEEDS_REVIEW.value, None)
            for rule in safety_rule_refs
        }
        expected_safety_links = {
            (
                rule.rule_id,
                rule.rule_id,
                frozenset(rule.reference_ids),
                frozenset(rule.claim_ids),
                frozenset([rule.message]),
            )
            for rule in safety_rule_refs
        }
        safety_rule_ids = {rule.rule_id for rule in safety_rule_refs}
    elif safety_adjusted:
        fallback_limitation = (
            "Safety-review status applies a conservative ranking adjustment; "
            "it is not efficacy evidence."
        )
        expected_safety_inputs = {
            (
                "safety_review_status",
                RecommendationStatus.NEEDS_REVIEW.value,
                None,
            )
        }
        expected_safety_links = {
            (
                "safety_review_status",
                "OPT-BASELINE-001",
                frozenset(),
                frozenset(),
                frozenset([fallback_limitation]),
            )
        }
    actual_safety_inputs = {
        (signal.code, str(signal.observed_value), signal.unit)
        for signal in reason.input_signals
        if signal.source == "safety"
    }
    if actual_safety_inputs != expected_safety_inputs:
        issues.append(f"reason_safety_input_mismatch::{item.ingredient_key}")
    actual_safety_links = {
        (
            link.code,
            str(link.rule_id),
            frozenset(link.reference_ids),
            frozenset(link.claim_ids),
            frozenset(link.limitations),
        )
        for link in reason.evidence_links
        if link.evidence_source == "safety_rule"
    }
    if actual_safety_links != expected_safety_links:
        issues.append(f"reason_safety_evidence_mismatch::{item.ingredient_key}")
    expected_safety_adjustment = -4.0 if safety_adjusted else 0.0
    if abs(item.score_breakdown.safety_adjustment - expected_safety_adjustment) > _SCORE_TOLERANCE:
        issues.append(f"safety_adjustment_policy_mismatch::{item.ingredient_key}")

    goal_priors_total = sum(
        goal_priors[(item.ingredient_key, goal)].prior_score
        for goal in item.expected_support_goals
        if (item.ingredient_key, goal) in goal_priors
    )
    if abs(item.score_breakdown.goal_alignment - goal_priors_total) > _SCORE_TOLERANCE:
        issues.append(f"goal_prior_score_mismatch::{item.ingredient_key}")
    source_component_values = {
        "symptom": item.score_breakdown.symptom_alignment,
        "laboratory": item.score_breakdown.laboratory_alignment,
        "lifestyle": item.score_breakdown.lifestyle_alignment,
        "dietary_pattern": item.score_breakdown.dietary_alignment,
        "wearable": item.score_breakdown.wearable_adjustment,
        "cgm": item.score_breakdown.cgm_adjustment,
        "genetic": item.score_breakdown.genetic_adjustment,
    }
    for source, component_value in source_component_values.items():
        signal_total = sum(
            signal.points
            for signal in item.score_breakdown.applied_signals
            if signal.source == source
        )
        if abs(component_value - signal_total) > _SCORE_TOLERANCE:
            issues.append(f"score_signal_component_mismatch::{item.ingredient_key}::{source}")

    source_to_term = {
        "symptom": "symptom_alignment",
        "laboratory": "laboratory_alignment",
        "lifestyle": "lifestyle_alignment",
        "dietary_pattern": "dietary_alignment",
        "wearable": "wearable_adjustment",
        "cgm": "cgm_adjustment",
        "genetic": "genetic_adjustment",
    }
    expected_term_rules: dict[str, set[str]] = {
        term: set()
        for term in _score_term_values(
            item.score_breakdown,
            catalog_priority=item.catalog_priority,
        )
    }
    for term in (
        "catalog_priority",
        "evidence_readiness",
        "budget_adjustment",
        "safety_adjustment",
        "conservative_adjustment",
    ):
        if "OPT-BASELINE-001" in item.rule_refs:
            expected_term_rules[term].add("OPT-BASELINE-001")
    if "OPT-LEARNED-001" in item.rule_refs:
        expected_term_rules["learned_effect_bonus"].add("OPT-LEARNED-001")
    for signal in item.score_breakdown.applied_signals:
        expected_term_rules[source_to_term[signal.source]].add(signal.rule_id)
    if safety_adjusted:
        expected_term_rules["safety_adjustment"].update(safety_rule_ids)
    actual_term_rules = {term.term: set(term.rule_ids) for term in reason.score_terms}
    if actual_term_rules != expected_term_rules:
        issues.append(f"reason_score_term_rule_mismatch::{item.ingredient_key}")

    expected_rule_ids = (
        set(item.rule_refs)
        | {signal.rule_id for signal in item.score_breakdown.applied_signals}
        | safety_rule_ids
    )
    if set(reason.rule_ids) != expected_rule_ids:
        issues.append(f"reason_rule_set_mismatch::{item.ingredient_key}")
    return issues


def validate_candidate_preselection_score_contract(
    traced: CandidatePreselectionScore,
    *,
    safety_rule_refs: list[RuleReference],
) -> list[str]:
    from wellnessbox_rnd.domain.catalog import get_catalog_index

    issues: list[str] = []
    catalog_item = get_catalog_index().get(traced.ingredient_key)
    if catalog_item is None:
        return [f"preselection_candidate_missing_from_catalog::{traced.ingredient_key}"]
    if abs(traced.catalog_priority - catalog_item.default_priority) > _SCORE_TOLERANCE:
        issues.append(f"preselection_catalog_priority_mismatch::{traced.ingredient_key}")
    item = RecommendationSelectionItemV1(
        ingredient_key=traced.ingredient_key,
        expected_support_goals=traced.expected_support_goals,
        rule_refs=traced.rule_refs,
        catalog_priority=traced.catalog_priority,
        score_breakdown=traced.score_breakdown,
        reason_breakdown=traced.reason_breakdown,
        additive_component_total=traced.score_total,
    )
    expected_total = _score_component_total(
        traced.score_breakdown,
        catalog_priority=traced.catalog_priority,
    )
    if abs(traced.score_total - expected_total) > _SCORE_TOLERANCE:
        issues.append(f"preselection_score_total_mismatch::{traced.ingredient_key}")
    reason_terms = {
        term.term: term.points for term in traced.reason_breakdown.score_terms
    }
    if reason_terms != _score_term_values(
        traced.score_breakdown,
        catalog_priority=traced.catalog_priority,
    ):
        issues.append(f"preselection_reason_term_mismatch::{traced.ingredient_key}")
    if not set(traced.rule_refs).issubset(traced.reason_breakdown.rule_ids):
        issues.append(f"preselection_reason_rule_mismatch::{traced.ingredient_key}")
    learned_marker_present = "OPT-LEARNED-001" in traced.rule_refs
    learned_bonus_present = (
        abs(traced.score_breakdown.learned_effect_bonus) > _SCORE_TOLERANCE
    )
    if learned_bonus_present and not learned_marker_present:
        issues.append(f"preselection_learned_marker_mismatch::{traced.ingredient_key}")
    issues.extend(
        _validate_reason_evidence_contract(
            item,
            safety_rule_refs=safety_rule_refs,
        )
    )
    return issues


def _validate_decision_uncertainty_contract(
    contract: RecommendationSetContractV1,
    selected_keys: list[str],
) -> list[str]:
    uncertainty = contract.decision_uncertainty
    if uncertainty is None:
        return []

    issues: list[str] = []
    snapshot = uncertainty.candidate_ranking_snapshot
    score_trace = contract.preselection_scores
    if score_trace is not None:
        if snapshot.candidate_count != len(score_trace):
            issues.append("decision_uncertainty_candidate_count_mismatch")
        if score_trace and (
            snapshot.top_candidate_key != score_trace[0].ingredient_key
            or snapshot.top_selection_score != score_trace[0].selection_score
        ):
            issues.append("decision_uncertainty_top_score_trace_mismatch")
        if len(score_trace) >= 2:
            expected_margin = round(
                score_trace[0].selection_score - score_trace[1].selection_score,
                6,
            )
            if (
                snapshot.runner_up_candidate_key != score_trace[1].ingredient_key
                or snapshot.runner_up_selection_score != score_trace[1].selection_score
                or snapshot.top_two_score_margin != expected_margin
            ):
                issues.append("decision_uncertainty_runner_up_score_trace_mismatch")
        selected_by_key = {
            item.ingredient_key: item for item in contract.selected_recommendations
        }
        for traced in score_trace:
            selected = selected_by_key.get(traced.ingredient_key)
            if selected is not None and (
                abs(traced.score_total - selected.score_breakdown.total) > _SCORE_TOLERANCE
                or abs(
                    traced.goal_alignment - selected.score_breakdown.goal_alignment
                )
                > _SCORE_TOLERANCE
                or traced.score_breakdown != selected.score_breakdown
                or traced.reason_breakdown != selected.reason_breakdown
            ):
                issues.append(
                    f"preselection_score_selection_mismatch::{traced.ingredient_key}"
                )
    if contract.response_status == RecommendationStatus.BLOCKED:
        expected_selected_count = 0
    else:
        expected_selected_count = min(contract.selection_limit, snapshot.candidate_count)
    if len(selected_keys) != expected_selected_count:
        issues.append("decision_uncertainty_selection_count_mismatch")
    if selected_keys and selected_keys[0] != snapshot.top_candidate_key:
        issues.append("decision_uncertainty_top_candidate_mismatch")

    expected_components: dict[str, tuple[str, float, list[str | None]]] = {}
    if contract.response_status == RecommendationStatus.NEEDS_REVIEW:
        expected_components["recommendation_status:needs_review"] = (
            "recommendation_status",
            0.20,
            [RecommendationStatus.NEEDS_REVIEW.value],
        )
    if snapshot.candidate_count == 0 and contract.response_status != RecommendationStatus.BLOCKED:
        expected_components["candidate_availability:no_selection"] = (
            "candidate_availability",
            0.15,
            ["no_selected_candidate"],
        )
    if snapshot.top_two_score_margin is not None:
        margin = snapshot.top_two_score_margin
        margin_points = (
            0.20 if margin < 1.0 else 0.10 if margin < 3.0 else 0.05 if margin < 5.0 else 0.0
        )
        if margin_points:
            expected_components["candidate_score_margin:top_two"] = (
                "candidate_score_margin",
                margin_points,
                [snapshot.top_candidate_key, snapshot.runner_up_candidate_key],
            )
    actual_components = {
        item.code: (item.source, item.points, item.basis_codes)
        for item in uncertainty.components
        if item.source != "missing_information"
    }
    if actual_components != expected_components:
        issues.append("decision_uncertainty_response_context_mismatch")
    return issues


__all__ = [
    "RECOMMENDATION_SET_CONTRACT_DIAGNOSTICS_SCHEMA_VERSION_V1",
    "RECOMMENDATION_SET_CONTRACT_SCHEMA_VERSION_V1",
    "RecommendationSelectionItemV1",
    "RecommendationSetContractV1",
    "build_recommendation_set_contract_v1",
    "render_recommendation_set_contract_markdown_v1",
    "summarize_recommendation_set_contract_v1",
    "validate_candidate_preselection_score_contract",
    "validate_recommendation_set_contract_v1",
    "write_recommendation_set_contract_report_v1",
]
