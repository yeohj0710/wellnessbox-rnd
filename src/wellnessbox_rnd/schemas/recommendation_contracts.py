from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import (
    CandidateScoreBreakdown,
    NextAction,
    RecommendationGoal,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationStatus,
)

RECOMMENDATION_SET_CONTRACT_SCHEMA_VERSION_V1 = "recommendation_set_contract_v1"
_SCORE_TOLERANCE = 1e-6


class RecommendationSelectionItemV1(BaseModel):
    ingredient_key: str
    expected_support_goals: list[RecommendationGoal] = Field(default_factory=list)
    rule_refs: list[str] = Field(default_factory=list)
    catalog_priority: float
    score_breakdown: CandidateScoreBreakdown
    additive_component_total: float


class RecommendationSetContractV1(BaseModel):
    schema_version: str = RECOMMENDATION_SET_CONTRACT_SCHEMA_VERSION_V1
    request_id: str
    response_status: RecommendationStatus
    next_action: NextAction
    selection_limit: int
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
        request_id=response.request_id,
        response_status=response.status,
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
) -> list[str]:
    issues: list[str] = []
    selected_keys = [item.ingredient_key for item in contract.selected_recommendations]
    if len(selected_keys) > contract.selection_limit:
        issues.append("selection_limit_exceeded")
    if len(selected_keys) != len(set(selected_keys)):
        issues.append("duplicate_selected_ingredient_keys")

    normalized_focus_goal_values = {
        goal.value for goal in contract.normalized_focus_goals
    }
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
        expected_total = _score_component_total(
            item.score_breakdown,
            catalog_priority=item.catalog_priority,
        )
        if abs(item.additive_component_total - expected_total) > _SCORE_TOLERANCE:
            issues.append(f"stored_component_total_mismatch::{item.ingredient_key}")
        if abs(item.score_breakdown.total - expected_total) > _SCORE_TOLERANCE:
            issues.append(f"score_total_mismatch::{item.ingredient_key}")

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
        ],
        "connection_map": {
            "recommendation": [
                "selected_recommendations.ingredient_key",
                "selected_recommendations.expected_support_goals",
                "selected_recommendations.score_breakdown",
            ],
            "optimization": [
                "selection_limit",
                "selected_recommendations.rule_refs",
            "selected_recommendations.catalog_priority",
            "selected_recommendations.additive_component_total",
            ],
            "safety": ["excluded_ingredient_keys"],
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
    selected_keys = [
        item["ingredient_key"] for item in example_event["selected_recommendations"]
    ]
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
    lines.extend(
        f"- `{constraint}`" for constraint in report["optimization_constraints_checked"]
    )
    lines.extend(
        [
            "",
            "## connection map",
            "- recommendation: "
            + ", ".join(f"`{item}`" for item in report["connection_map"]["recommendation"]),
            "- optimization: "
            + ", ".join(f"`{item}`" for item in report["connection_map"]["optimization"]),
            "- safety: "
            + ", ".join(f"`{item}`" for item in report["connection_map"]["safety"]),
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
        + score_breakdown.evidence_readiness
        + score_breakdown.budget_adjustment
        + score_breakdown.safety_adjustment
        + score_breakdown.conservative_adjustment
        + score_breakdown.learned_effect_bonus,
        6,
    )


__all__ = [
    "RECOMMENDATION_SET_CONTRACT_SCHEMA_VERSION_V1",
    "RecommendationSelectionItemV1",
    "RecommendationSetContractV1",
    "build_recommendation_set_contract_v1",
    "render_recommendation_set_contract_markdown_v1",
    "summarize_recommendation_set_contract_v1",
    "validate_recommendation_set_contract_v1",
    "write_recommendation_set_contract_report_v1",
]
