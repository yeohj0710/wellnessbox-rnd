from uuid import uuid4

from wellnessbox_rnd.domain.intake import NormalizedIntake, normalize_request
from wellnessbox_rnd.efficacy.service import estimate_follow_up_window_days
from wellnessbox_rnd.metrics.metadata import build_engine_metadata
from wellnessbox_rnd.optimizer.service import select_recommendations
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import (
    DecisionSummary,
    MissingInfoImportance,
    NextAction,
    RecommendationCandidate,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationStatus,
    SafetySummary,
)


def recommend(request: RecommendationRequest) -> RecommendationResponse:
    intake = normalize_request(request)
    safety_summary = assess_safety(intake)

    if safety_summary.status == RecommendationStatus.BLOCKED:
        return RecommendationResponse(
            request_id=request.request_id,
            decision_id=str(uuid4()),
            status=RecommendationStatus.BLOCKED,
            decision_summary=DecisionSummary(
                headline="recommendation blocked",
                summary=(
                    "The minimum intake contract was not satisfied, so the deterministic baseline "
                    "did not generate recommendation candidates."
                ),
                confidence_band="low",
            ),
            normalized_focus_goals=request.goals,
            safety_summary=safety_summary,
            safety_flags=safety_summary.warnings + safety_summary.blocked_reasons,
            recommendations=[],
            next_action=NextAction.COLLECT_MORE_INPUT,
            follow_up_window_days=21,
            follow_up_questions=[item.question for item in intake.missing_information],
            missing_information=intake.missing_information,
            limitations=_build_limitations(),
            metadata=build_engine_metadata(mode="deterministic_baseline_v1"),
        )

    recommendations = select_recommendations(intake, safety_summary)
    next_action = _decide_next_action(intake, safety_summary, recommendations)
    status = safety_summary.status
    if not recommendations:
        status = RecommendationStatus.NEEDS_REVIEW

    decision_summary = _build_decision_summary(
        intake=intake,
        status=status,
        recommendation_names=[item.display_name for item in recommendations],
    )

    return RecommendationResponse(
        request_id=request.request_id,
        decision_id=str(uuid4()),
        status=status,
        decision_summary=decision_summary,
        normalized_focus_goals=request.goals,
        safety_summary=safety_summary,
        safety_flags=safety_summary.warnings + safety_summary.blocked_reasons,
        recommendations=recommendations,
        next_action=next_action,
        follow_up_window_days=estimate_follow_up_window_days(intake),
        follow_up_questions=[item.question for item in intake.missing_information],
        missing_information=intake.missing_information,
        limitations=_build_limitations(),
        metadata=build_engine_metadata(mode="deterministic_baseline_v1"),
    )


def _decide_next_action(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> NextAction:
    if not recommendations:
        return NextAction.NEEDS_HUMAN_REVIEW
    if safety_summary.status == RecommendationStatus.NEEDS_REVIEW:
        return NextAction.NEEDS_HUMAN_REVIEW
    if any(item.importance == MissingInfoImportance.HIGH for item in intake.missing_information):
        return NextAction.COLLECT_MORE_INPUT
    if len(intake.missing_information) >= 2:
        return NextAction.COLLECT_MORE_INPUT
    return NextAction.START_PLAN


def _build_decision_summary(
    intake: NormalizedIntake,
    status: RecommendationStatus,
    recommendation_names: list[str],
) -> DecisionSummary:
    goal_text = ", ".join(
        goal.value for goal in sorted(intake.goal_set, key=lambda goal: goal.value)
    )
    candidate_text = ", ".join(recommendation_names) if recommendation_names else "no candidates"

    if status == RecommendationStatus.NEEDS_REVIEW:
        headline = "conservative review required"
        summary = (
            f"For goals [{goal_text}], the baseline prioritized {candidate_text}, but safety "
            "review, human review, or additional intake clarification should come first."
        )
        confidence = "medium"
    else:
        headline = "deterministic baseline result"
        summary = (
            f"For goals [{goal_text}], the baseline prioritized {candidate_text}. This is a "
            "rule-and-score ranking result and should be treated as conservative support "
            "guidance rather than diagnosis."
        )
        confidence = "medium" if intake.missing_information else "high"

    return DecisionSummary(
        headline=headline,
        summary=summary,
        confidence_band=confidence,
    )


def _build_limitations() -> list[str]:
    return [
        "Current catalog is a demo placeholder and not the production product SSOT.",
        "Current recommendation logic is deterministic baseline only.",
        "LLM is not used for core recommendation decisions.",
    ]
