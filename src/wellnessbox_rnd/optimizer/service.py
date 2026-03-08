from wellnessbox_rnd.domain.catalog import list_catalog_items
from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.efficacy.service import score_candidate
from wellnessbox_rnd.schemas.recommendation import (
    RecommendationCandidate,
    RecommendationGoal,
    RecommendationStatus,
    SafetySummary,
)


def select_recommendations(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
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
    return (
        f"{display_name} was selected for {goal_text} because the current baseline linked it to "
        f"{tag_text}. This is a deterministic baseline ranking, not a medical diagnosis. "
        f"Follow-up focus: {follow_up_focus}."
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
