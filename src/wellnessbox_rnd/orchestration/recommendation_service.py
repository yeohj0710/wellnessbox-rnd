from uuid import uuid4

from wellnessbox_rnd.domain.intake import NormalizedIntake, normalize_request
from wellnessbox_rnd.efficacy.service import estimate_follow_up_window_days
from wellnessbox_rnd.metrics.metadata import build_engine_metadata
from wellnessbox_rnd.optimizer.service import select_recommendations
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import (
    DecisionSummary,
    LimitationItem,
    MissingInfoImportance,
    NextAction,
    NextActionRationale,
    RecommendationCandidate,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationStatus,
    SafetyEvidenceItem,
    SafetySummary,
)


def recommend(request: RecommendationRequest) -> RecommendationResponse:
    intake = normalize_request(request)
    safety_summary = assess_safety(intake)

    if safety_summary.status == RecommendationStatus.BLOCKED:
        next_action = NextAction.COLLECT_MORE_INPUT
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
            safety_evidence=_build_safety_evidence(intake, safety_summary),
            recommendations=[],
            next_action=next_action,
            next_action_rationale=_build_next_action_rationale(
                intake=intake,
                safety_summary=safety_summary,
                next_action=next_action,
                recommendations=[],
            ),
            follow_up_window_days=21,
            follow_up_questions=[item.question for item in intake.missing_information],
            missing_information=intake.missing_information,
            limitations=_build_limitations(),
            limitation_details=_build_limitation_details(),
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
        safety_evidence=_build_safety_evidence(intake, safety_summary),
        recommendations=recommendations,
        next_action=next_action,
        next_action_rationale=_build_next_action_rationale(
            intake=intake,
            safety_summary=safety_summary,
            next_action=next_action,
            recommendations=recommendations,
        ),
        follow_up_window_days=estimate_follow_up_window_days(intake),
        follow_up_questions=[item.question for item in intake.missing_information],
        missing_information=intake.missing_information,
        limitations=_build_limitations(),
        limitation_details=_build_limitation_details(),
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
    return [item.summary for item in _build_limitation_details()]


def _build_limitation_details() -> list[LimitationItem]:
    return [
        LimitationItem(
            code="demo_catalog_only",
            summary="Current catalog is a demo placeholder and not the production product SSOT.",
        ),
        LimitationItem(
            code="deterministic_baseline_only",
            summary="Current recommendation logic is deterministic baseline only.",
        ),
        LimitationItem(
            code="no_llm_core_decision",
            summary="LLM is not used for core recommendation decisions.",
        ),
    ]


def _build_safety_evidence(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
) -> list[SafetyEvidenceItem]:
    evidence: list[SafetyEvidenceItem] = []
    seen_keys: set[tuple[str, str]] = set()

    for rule_ref in safety_summary.rule_refs:
        _append_safety_evidence(
            evidence=evidence,
            seen_keys=seen_keys,
            item=SafetyEvidenceItem(
                evidence_type="rule",
                code=rule_ref.rule_id,
                summary=rule_ref.message,
            ),
        )

    for ingredient_key in safety_summary.excluded_ingredients:
        if ingredient_key in intake.avoid_ingredient_set:
            item = SafetyEvidenceItem(
                evidence_type="user_preference",
                code=ingredient_key,
                summary=(
                    f"{ingredient_key} was excluded because the user asked to avoid it."
                ),
            )
        elif ingredient_key in intake.current_ingredient_set:
            item = SafetyEvidenceItem(
                evidence_type="excluded_ingredient",
                code=ingredient_key,
                summary=(
                    f"{ingredient_key} was excluded because it overlaps with current "
                    "supplement context or conservative policy."
                ),
            )
        else:
            item = SafetyEvidenceItem(
                evidence_type="excluded_ingredient",
                code=ingredient_key,
                summary=f"{ingredient_key} was excluded by safety policy before ranking.",
            )
        _append_safety_evidence(evidence=evidence, seen_keys=seen_keys, item=item)

    return evidence


def _append_safety_evidence(
    evidence: list[SafetyEvidenceItem],
    seen_keys: set[tuple[str, str]],
    item: SafetyEvidenceItem,
) -> None:
    key = (item.evidence_type, item.code)
    if key in seen_keys:
        return
    seen_keys.add(key)
    evidence.append(item)


def _build_next_action_rationale(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    next_action: NextAction,
    recommendations: list[RecommendationCandidate],
) -> NextActionRationale:
    missing_codes = [item.code for item in intake.missing_information]
    high_priority_codes = [
        item.code
        for item in intake.missing_information
        if item.importance == MissingInfoImportance.HIGH
    ]
    rule_ids = [rule.rule_id for rule in safety_summary.rule_refs]

    if safety_summary.status == RecommendationStatus.BLOCKED:
        return NextActionRationale(
            reason_code="blocked_minimum_input",
            summary=(
                "The minimum intake contract is incomplete, so more input is "
                "required before planning."
            ),
            supporting_codes=missing_codes or rule_ids,
        )

    if not recommendations:
        return NextActionRationale(
            reason_code="needs_review_no_candidates",
            summary="No safe deterministic candidates were available, so human review is required.",
            supporting_codes=rule_ids or missing_codes,
        )

    if next_action == NextAction.NEEDS_HUMAN_REVIEW:
        return NextActionRationale(
            reason_code="needs_review_due_to_safety",
            summary=(
                "Safety review signals are present, so the baseline requires "
                "human review before plan start."
            ),
            supporting_codes=rule_ids,
        )

    if next_action == NextAction.COLLECT_MORE_INPUT and high_priority_codes:
        return NextActionRationale(
            reason_code="collect_more_input_high_priority_missing_info",
            summary=(
                "High-priority missing context is still open, so more input is "
                "needed before plan start."
            ),
            supporting_codes=high_priority_codes,
        )

    if next_action == NextAction.COLLECT_MORE_INPUT:
        return NextActionRationale(
            reason_code="collect_more_input_multiple_missing_items",
            summary=(
                "Multiple missing information items remain, so the baseline "
                "requests more input first."
            ),
            supporting_codes=missing_codes,
        )

    return NextActionRationale(
        reason_code="start_plan_ready",
        summary=(
            "The deterministic baseline has candidates and no blocking review "
            "condition, so the plan can start."
        ),
        supporting_codes=[item.ingredient_key for item in recommendations],
    )
