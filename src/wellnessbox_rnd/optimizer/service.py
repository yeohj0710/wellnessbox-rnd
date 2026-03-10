from pathlib import Path

from wellnessbox_rnd.domain.catalog import list_catalog_items
from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.domain.models import IngredientCatalogItem
from wellnessbox_rnd.efficacy.service import (
    cgm_context_note,
    genetic_context_note,
    score_candidate,
    wearable_context_note,
)
from wellnessbox_rnd.models import (
    build_runtime_efficacy_feature_dict,
    load_efficacy_model_artifact,
    predict_effect_proxy_from_feature_dict,
)
from wellnessbox_rnd.schemas.recommendation import (
    RecommendationCandidate,
    RecommendationGoal,
    RecommendationStatus,
    SafetySummary,
)


def select_recommendations(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    *,
    enable_learned_reranking: bool = False,
    learned_efficacy_artifact_path: str | None = None,
) -> list[RecommendationCandidate]:
    candidates: list[RecommendationCandidate] = []
    blocked_keys = (
        set(safety_summary.excluded_ingredients)
        | intake.avoid_ingredient_set
        | intake.current_ingredient_set
    )
    safety_review = safety_summary.status == RecommendationStatus.NEEDS_REVIEW

    for item in list_catalog_items():
        if item.key in blocked_keys:
            continue

        breakdown = score_candidate(item=item, intake=intake, safety_review=safety_review)
        if breakdown.goal_alignment <= 0:
            continue

        explanation = build_candidate_explanation(
            item=item,
            display_name=item.display_name,
            explanation_tags=item.explanation_tags,
            intake=intake,
            follow_up_focus=item.follow_up_focus,
            safety_review=safety_review,
        )
        candidates.append(
            RecommendationCandidate(
                ingredient_key=item.key,
                display_name=item.display_name,
                rationale=explanation,
                expected_support_goals=[
                    goal for goal in item.supported_goals if goal in intake.goal_set
                ],
                rule_refs=["OPT-BASELINE-001"],
                score_breakdown=breakdown,
                follow_up_focus=item.follow_up_focus,
            )
        )

    candidates = _apply_learned_efficacy_reranking(
        intake=intake,
        safety_summary=safety_summary,
        candidates=candidates,
        enable_learned_reranking=enable_learned_reranking,
        learned_efficacy_artifact_path=learned_efficacy_artifact_path,
    )

    selected: list[RecommendationCandidate] = []
    covered_goals: set[RecommendationGoal] = set()
    remaining = candidates.copy()

    while remaining and len(selected) < intake.request.preferences.max_products:
        remaining.sort(
            key=lambda item: (
                -_marginal_selection_score(item, covered_goals),
                -item.score_breakdown.total,
                -item.score_breakdown.goal_alignment,
                item.ingredient_key,
            )
        )
        chosen = remaining.pop(0)
        selected.append(chosen)
        covered_goals.update(chosen.expected_support_goals)

    return selected


def build_candidate_explanation(
    item: IngredientCatalogItem,
    display_name: str,
    explanation_tags: list[str],
    intake: NormalizedIntake,
    follow_up_focus: str,
    safety_review: bool,
) -> str:
    goal_text = ", ".join(
        goal.value for goal in sorted(intake.goal_set, key=lambda goal: goal.value)
    )
    tag_text = ", ".join(explanation_tags[:2]) if explanation_tags else "general support"
    caution_text = (
        " Conservative review signals were present, so extra safety margin was applied."
        if safety_review
        else ""
    )
    wearable_text = wearable_context_note(item, intake) or ""
    cgm_text = cgm_context_note(item, intake) or ""
    genetic_text = genetic_context_note(item, intake) or ""
    return (
        f"{display_name} was selected for {goal_text} because the current baseline linked it to "
        f"{tag_text}. This is a deterministic baseline ranking, not a medical diagnosis. "
        f"Follow-up focus: {follow_up_focus}."
        f"{wearable_text}"
        f"{cgm_text}"
        f"{genetic_text}"
        f"{caution_text}"
    )


def _marginal_selection_score(
    candidate: RecommendationCandidate,
    covered_goals: set[RecommendationGoal],
) -> float:
    uncovered_goals = [
        goal for goal in candidate.expected_support_goals if goal not in covered_goals
    ]
    coverage_bonus = sum(_goal_coverage_bonus(goal) for goal in uncovered_goals)
    overlap_penalty = 4.0 * (
        len(candidate.expected_support_goals) - len(uncovered_goals)
    )
    return candidate.score_breakdown.total + coverage_bonus - overlap_penalty


def _goal_coverage_bonus(goal: RecommendationGoal) -> float:
    if goal == RecommendationGoal.GENERAL_WELLNESS:
        return 4.0
    return 12.0


def _apply_learned_efficacy_reranking(
    *,
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    candidates: list[RecommendationCandidate],
    enable_learned_reranking: bool,
    learned_efficacy_artifact_path: str | None,
) -> list[RecommendationCandidate]:
    if not enable_learned_reranking:
        return candidates
    if not _eligible_for_learned_reranking(intake, safety_summary, candidates):
        return candidates
    if learned_efficacy_artifact_path is None:
        return candidates

    artifact_path = Path(learned_efficacy_artifact_path)
    if not artifact_path.exists():
        return candidates

    artifact = load_efficacy_model_artifact(artifact_path)
    top_deterministic_total = max(
        candidate.score_breakdown.total for candidate in candidates
    )
    reranked: list[RecommendationCandidate] = []

    for candidate in candidates:
        deterministic_gap = top_deterministic_total - candidate.score_breakdown.total
        if deterministic_gap > 1.0:
            reranked.append(candidate)
            continue

        feature_row = build_runtime_efficacy_feature_dict(
            request=intake.request,
            follow_up_step=0,
            day_index=0,
            baseline_recommendations=[candidate.ingredient_key],
            adherence_proxy=_runtime_adherence_proxy(intake),
        )
        predicted_effect = predict_effect_proxy_from_feature_dict(artifact, feature_row)
        learned_effect_bonus = round(predicted_effect * 15.0, 6)
        updated_breakdown = candidate.score_breakdown.model_copy(
            update={
                "learned_effect_bonus": learned_effect_bonus,
                "total": candidate.score_breakdown.total + learned_effect_bonus,
            }
        )
        updated_rule_refs = list(candidate.rule_refs)
        if "OPT-LEARNED-001" not in updated_rule_refs:
            updated_rule_refs.append("OPT-LEARNED-001")
        reranked.append(
            candidate.model_copy(
                update={
                    "rule_refs": updated_rule_refs,
                    "score_breakdown": updated_breakdown,
                    "rationale": (
                        f"{candidate.rationale} A learned efficacy tie-breaker was applied "
                        "after deterministic safety filtering and only among near-tied "
                        "low-risk candidates."
                    ),
                }
            )
        )

    return reranked


def _eligible_for_learned_reranking(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    candidates: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if not candidates:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set or intake.medication_set:
        return False
    return intake.goal_set == {RecommendationGoal.GENERAL_WELLNESS}


def _runtime_adherence_proxy(intake: NormalizedIntake) -> float:
    proxy = 0.68
    if intake.request.preferences.budget_level.value == "low":
        proxy += 0.05
    if intake.request.preferences.max_products > 2:
        proxy -= 0.05
    if intake.current_ingredient_set:
        proxy += 0.04
    return max(0.55, min(0.85, round(proxy, 3)))
