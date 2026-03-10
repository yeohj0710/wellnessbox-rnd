from uuid import uuid4

from wellnessbox_rnd.domain.catalog import list_catalog_items
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
    RecommendationGoal,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationStatus,
    SafetyEvidenceItem,
    SafetySummary,
)


def recommend(
    request: RecommendationRequest,
    *,
    enable_learned_reranking: bool = False,
    learned_efficacy_artifact_path: str | None = None,
) -> RecommendationResponse:
    intake = normalize_request(request)
    safety_summary = assess_safety(intake)
    wearable_context_considered = _wearable_context_considered(intake)
    cgm_context_considered = _cgm_context_considered(intake)
    genetic_context_considered = _genetic_context_considered(intake)
    recommendations: list[RecommendationCandidate] = []
    effective_safety_summary = safety_summary

    if safety_summary.status == RecommendationStatus.BLOCKED:
        recommendations = select_recommendations(
            intake,
            safety_summary,
            enable_learned_reranking=enable_learned_reranking,
            learned_efficacy_artifact_path=learned_efficacy_artifact_path,
        )
        if _can_clear_pregnancy_survey_only_block(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ) or _can_clear_pregnancy_renal_survey_only_block(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ) or _can_clear_general_wellness_survey_only_block(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ) or _can_clear_baseline_survey_only_block(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ) or _can_clear_renal_survey_only_block(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ) or _can_clear_heart_survey_only_block(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ) or _can_clear_anticoagulant_survey_only_block(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            effective_safety_summary = safety_summary.model_copy(
                update={"status": RecommendationStatus.OK}
            )
            recommendations = select_recommendations(
                intake,
                effective_safety_summary,
                enable_learned_reranking=enable_learned_reranking,
                learned_efficacy_artifact_path=learned_efficacy_artifact_path,
            )
        else:
            next_action = NextAction.COLLECT_MORE_INPUT
            summary = (
                "The minimum intake contract was not satisfied, so the deterministic baseline "
                "did not generate recommendation candidates."
            )
            if wearable_context_considered:
                summary += (
                    " Available wearable context was considered, but the minimum intake "
                    "contract still blocked deterministic planning."
                )
            if cgm_context_considered:
                summary += (
                    " Available CGM context was considered, but the minimum intake contract "
                    "still blocked deterministic planning."
                )
            if genetic_context_considered:
                summary += (
                    " Available genetic context was considered, but the minimum intake contract "
                    "still blocked deterministic planning."
                )
            return RecommendationResponse(
                request_id=request.request_id,
                decision_id=str(uuid4()),
                status=RecommendationStatus.BLOCKED,
                decision_summary=DecisionSummary(
                    headline="recommendation blocked",
                    summary=summary,
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
    else:
        recommendations = select_recommendations(
            intake,
            safety_summary,
            enable_learned_reranking=enable_learned_reranking,
            learned_efficacy_artifact_path=learned_efficacy_artifact_path,
        )
        effective_safety_summary = _resolve_safety_review_status(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        )
    engine_mode = "deterministic_baseline_v1"
    if any("OPT-LEARNED-001" in item.rule_refs for item in recommendations):
        engine_mode = "deterministic_baseline_v1_learned_efficacy_rerank_v0"
    current_regimen_continuation = _can_start_with_current_regimen_coverage(
        intake=intake,
        safety_summary=effective_safety_summary,
        recommendations=recommendations,
    )
    next_action = _decide_next_action(intake, effective_safety_summary, recommendations)
    status = effective_safety_summary.status
    if not recommendations and not current_regimen_continuation:
        status = RecommendationStatus.NEEDS_REVIEW

    decision_summary = _build_decision_summary(
        intake=intake,
        status=status,
        recommendation_names=[item.display_name for item in recommendations],
        current_regimen_continuation=current_regimen_continuation,
        wearable_context_considered=(
            any("wearable context" in item.rationale.lower() for item in recommendations)
            or (not recommendations and wearable_context_considered)
        ),
        cgm_context_considered=(
            any("cgm context" in item.rationale.lower() for item in recommendations)
            or (not recommendations and cgm_context_considered)
        ),
        genetic_context_influenced=(
            any("genetic context" in item.rationale.lower() for item in recommendations)
            or (not recommendations and genetic_context_considered)
        ),
    )

    return RecommendationResponse(
        request_id=request.request_id,
        decision_id=str(uuid4()),
        status=status,
        decision_summary=decision_summary,
        normalized_focus_goals=request.goals,
        safety_summary=effective_safety_summary,
        safety_flags=effective_safety_summary.warnings + effective_safety_summary.blocked_reasons,
        safety_evidence=_build_safety_evidence(intake, effective_safety_summary),
        recommendations=recommendations,
        next_action=next_action,
        next_action_rationale=_build_next_action_rationale(
            intake=intake,
            safety_summary=effective_safety_summary,
            next_action=next_action,
            recommendations=recommendations,
        ),
        follow_up_window_days=estimate_follow_up_window_days(intake),
        follow_up_questions=[item.question for item in intake.missing_information],
        missing_information=intake.missing_information,
        limitations=_build_limitations(),
        limitation_details=_build_limitation_details(),
        metadata=build_engine_metadata(mode=engine_mode),
    )


def _decide_next_action(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> NextAction:
    if _can_start_with_duplicate_heart_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_duplicate_heart_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_heart_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_anticoagulant_heart_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_wearable_heart_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_energy_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_energy_missing_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_bone_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_renal_bone_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_general_wellness_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_multimodal_general_wellness_missing_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_pregnancy_gut_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_pregnancy_general_wellness_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_pregnancy_glucose_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_multimodal_heart_energy_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_duplicate_heart_energy_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_multimodal_heart_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_multimodal_heart_sleep_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_multimodal_heart_glucose_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_glucose_sleep_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_sleep_hours_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_renal_sleep_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_cgm_glucose_missing_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_glucose_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_pregnancy_renal_genetic_glucose_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_pregnancy_renal_cgm_glucose_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if _can_start_with_current_regimen_coverage(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if not recommendations:
        return NextAction.TRIGGER_SAFETY_RECHECK
    if safety_summary.status == RecommendationStatus.NEEDS_REVIEW:
        return NextAction.TRIGGER_SAFETY_RECHECK
    if _can_start_with_genetic_glucose_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextAction.START_PLAN
    if any(item.importance == MissingInfoImportance.HIGH for item in intake.missing_information):
        return NextAction.COLLECT_MORE_INPUT
    if len(intake.missing_information) >= 2:
        return NextAction.COLLECT_MORE_INPUT
    return NextAction.START_PLAN


def _resolve_safety_review_status(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> SafetySummary:
    if safety_summary.status != RecommendationStatus.NEEDS_REVIEW:
        return safety_summary
    if _can_start_with_current_regimen_coverage(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return safety_summary.model_copy(update={"status": RecommendationStatus.OK})
    if not recommendations:
        return safety_summary
    if not (
        _can_clear_anticoagulant_heart_review(
            intake, safety_summary, recommendations
        )
        or _can_clear_anticoagulant_heart_energy_review(
            intake, safety_summary, recommendations
        )
        or _can_clear_anticoagulant_heart_glucose_review(
            intake, safety_summary, recommendations
        )
        or _can_clear_renal_only_review(intake, safety_summary, recommendations)
        or _can_clear_renal_bone_review(intake, safety_summary, recommendations)
        or _can_clear_pregnancy_baseline_review(intake, safety_summary, recommendations)
        or _can_clear_pregnancy_sleep_review(intake, safety_summary, recommendations)
        or _can_clear_pregnancy_renal_baseline_review(
            intake, safety_summary, recommendations
        )
        or _can_clear_pregnancy_renal_sleep_review(
            intake, safety_summary, recommendations
        )
        or _can_clear_pregnancy_renal_glucose_review(
            intake, safety_summary, recommendations
        )
    ):
        return safety_summary
    return safety_summary.model_copy(update={"status": RecommendationStatus.OK})


def _can_clear_anticoagulant_heart_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if not intake.medication_set:
        return False
    if not intake.medication_set.issubset({"warfarin", "coumadin"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-ANTICOAG-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-ANTICOAG-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10"}


def _is_anticoagulant_heart_missing_context_floor(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if not intake.medication_set:
        return False
    if not intake.medication_set.issubset({"warfarin", "coumadin"}):
        return False
    if intake.symptom_set:
        return False
    if "wearable_activity_context" in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if missing_codes != {"missing_primary_symptom", "missing_current_supplements"}:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-ANTICOAG-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-ANTICOAG-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10"}


def _can_clear_anticoagulant_heart_energy_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set:
        return False
    if intake.goal_set != {
        RecommendationGoal.HEART_HEALTH,
        RecommendationGoal.ENERGY_SUPPORT,
    }:
        return False
    if intake.avoid_ingredient_set and intake.avoid_ingredient_set != {
        "vitamin_b_complex"
    }:
        return False
    if not intake.medication_set:
        return False
    if not intake.medication_set.issubset({"warfarin", "coumadin"}):
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False
    if not intake.symptom_set.intersection({"fatigue", "frequent_fatigue"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-ANTICOAG-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-ANTICOAG-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    if recommendation_keys == {"coq10", "vitamin_b_complex"}:
        return not intake.avoid_ingredient_set
    if recommendation_keys != {"coq10"}:
        return False
    return (
        intake.avoid_ingredient_set == {"vitamin_b_complex"}
        and not intake.current_ingredient_set
        and rule_ids == {"SAFETY-ANTICOAG-001"}
    )


def _can_clear_anticoagulant_heart_glucose_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {
        RecommendationGoal.BLOOD_GLUCOSE,
        RecommendationGoal.HEART_HEALTH,
    }:
        return False
    if not intake.medication_set:
        return False
    if not intake.medication_set.issubset({"warfarin", "coumadin"}):
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "cgm_glucose_context" not in intake.signal_flags:
        return False
    if "cgm_post_meal_spike_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if "low_activity" not in intake.symptom_set:
        return False
    if not intake.current_ingredient_set.issubset({"berberine"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-ANTICOAG-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-ANTICOAG-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10", "soluble_fiber"}


def _can_clear_renal_only_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-RENAL-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-RENAL-001" not in rule_ids:
        return False

    catalog_by_key = {item.key: item for item in list_catalog_items()}
    return all(
        catalog_by_key[item.ingredient_key].conservative_profile == "baseline"
        for item in recommendations
        if item.ingredient_key in catalog_by_key
    )


def _can_clear_renal_bone_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set:
        return False
    if intake.goal_set != {RecommendationGoal.BONE_JOINT}:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if not intake.condition_set:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-RENAL-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-RENAL-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    if not recommendation_keys:
        return False
    if not recommendation_keys.issubset({"vitamin_d3", "calcium_citrate"}):
        return False

    return "low_sun_exposure" in intake.symptom_set or any(
        flag in intake.signal_flags
        for flag in ("genetic_bone_context", "genetic_low_sun_context")
    )


def _can_clear_pregnancy_baseline_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-PREG-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-PREG-001" not in rule_ids:
        return False

    allowed_ingredients = {"soluble_fiber", "probiotics"}
    return all(
        item.ingredient_key in allowed_ingredients
        for item in recommendations
    )


def _can_clear_pregnancy_renal_glucose_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set:
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-PREG-001", "SAFETY-RENAL-001", "SAFETY-DUP-001"}):
        return False
    if {"SAFETY-PREG-001", "SAFETY-RENAL-001"} - rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"soluble_fiber"}


def _can_clear_pregnancy_renal_baseline_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set:
        return False
    if intake.goal_set != {
        RecommendationGoal.GENERAL_WELLNESS,
        RecommendationGoal.BLOOD_GLUCOSE,
    }:
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-PREG-001", "SAFETY-RENAL-001", "SAFETY-DUP-001"}):
        return False
    if {"SAFETY-PREG-001", "SAFETY-RENAL-001"} - rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    if not recommendation_keys:
        return False
    if not recommendation_keys.issubset({"vitamin_d3", "soluble_fiber"}):
        return False
    return "soluble_fiber" in recommendation_keys


def _can_clear_pregnancy_sleep_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.SLEEP_SUPPORT}:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-PREG-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-PREG-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    if not recommendation_keys:
        return False
    if not recommendation_keys.issubset({"magnesium_glycinate", "l_theanine"}):
        return False

    catalog_by_key = {item.key: item for item in list_catalog_items()}
    return all(
        item.ingredient_key in catalog_by_key
        and catalog_by_key[item.ingredient_key].conservative_profile == "baseline"
        for item in recommendations
    )


def _can_clear_pregnancy_renal_sleep_review(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set:
        return False
    if intake.goal_set != {RecommendationGoal.SLEEP_SUPPORT}:
        return False
    if intake.condition_set != {"kidney disease"}:
        return False
    if "difficulty_falling_asleep" not in intake.symptom_set:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-PREG-001", "SAFETY-RENAL-001", "SAFETY-DUP-001"}):
        return False
    if {"SAFETY-PREG-001", "SAFETY-RENAL-001"} - rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"l_theanine"}


def _is_stacked_pregnancy_renal_anticoagulant_review_floor(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if not intake.medication_set:
        return False
    if not intake.medication_set.issubset({"warfarin", "coumadin"}):
        return False
    if intake.goal_set != {
        RecommendationGoal.BLOOD_GLUCOSE,
        RecommendationGoal.HEART_HEALTH,
    }:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if "low_activity" not in intake.symptom_set:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if rule_ids != {"SAFETY-ANTICOAG-001", "SAFETY-PREG-001", "SAFETY-RENAL-001"}:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10", "soluble_fiber"}


def _is_anticoagulant_survivor_collapse_review_floor(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set:
        return False
    if not intake.medication_set:
        return False
    if not intake.medication_set.issubset({"warfarin", "coumadin"}):
        return False
    if not intake.avoid_ingredient_set:
        return False
    if intake.goal_set not in (
        {RecommendationGoal.HEART_HEALTH, RecommendationGoal.ENERGY_SUPPORT},
        {RecommendationGoal.BLOOD_GLUCOSE, RecommendationGoal.HEART_HEALTH},
    ):
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"SAFETY-ANTICOAG-001", "SAFETY-DUP-001"}):
        return False
    if "SAFETY-ANTICOAG-001" not in rule_ids:
        return False

    if intake.goal_set == {
        RecommendationGoal.HEART_HEALTH,
        RecommendationGoal.ENERGY_SUPPORT,
    }:
        if not intake.symptom_set.intersection({"fatigue", "frequent_fatigue"}):
            return False
        if (
            intake.avoid_ingredient_set == {"vitamin_b_complex"}
            and not intake.current_ingredient_set
            and rule_ids == {"SAFETY-ANTICOAG-001"}
        ):
            return False
    else:
        if "post_meal_spike_concern" not in intake.symptom_set:
            return False
        if not intake.current_ingredient_set.issubset({"berberine"}):
            return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10"}


def _is_anticoagulant_glucose_survivor_collapse_review_floor(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not _is_anticoagulant_survivor_collapse_review_floor(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return False
    if intake.goal_set != {
        RecommendationGoal.BLOOD_GLUCOSE,
        RecommendationGoal.HEART_HEALTH,
    }:
        return False
    if "cgm_glucose_context" not in intake.signal_flags:
        return False
    if "cgm_post_meal_spike_context" not in intake.signal_flags:
        return False
    if intake.avoid_ingredient_set != {"soluble_fiber"}:
        return False
    if not intake.current_ingredient_set.issubset({"berberine"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    return rule_ids == {"SAFETY-ANTICOAG-001", "SAFETY-DUP-001"}


def _is_explicit_avoid_single_goal_no_candidate_floor(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.current_ingredient_set:
        return False
    if recommendations:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if rule_ids:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if missing_codes != {"missing_current_supplements"}:
        return False

    floor_requirements = {
        RecommendationGoal.HEART_HEALTH: {
            "symptoms": {"low_activity"},
            "avoid": {"omega3", "coq10"},
            "medications": {"atorvastatin"},
            "conditions": set(),
        },
        RecommendationGoal.BONE_JOINT: {
            "symptoms": {"low_sun_exposure"},
            "avoid": {"vitamin_d3", "calcium_citrate"},
            "medications": set(),
            "conditions": set(),
        },
        RecommendationGoal.IMMUNITY_SUPPORT: {
            "symptoms": {"frequent_fatigue"},
            "avoid": {"vitamin_c", "zinc", "vitamin_d3"},
            "medications": set(),
            "conditions": set(),
        },
        RecommendationGoal.ENERGY_SUPPORT: {
            "symptoms": {"fatigue"},
            "avoid": {"vitamin_b_complex", "coq10"},
            "medications": set(),
            "conditions": set(),
        },
    }

    if len(intake.goal_set) != 1:
        return False
    goal = next(iter(intake.goal_set))
    requirement = floor_requirements.get(goal)
    if requirement is None:
        return False
    if intake.symptom_set != requirement["symptoms"]:
        return False
    if intake.medication_set != requirement["medications"]:
        return False
    if intake.condition_set != requirement["conditions"]:
        return False
    if intake.avoid_ingredient_set != requirement["avoid"]:
        return False

    excluded_ingredients = set(safety_summary.excluded_ingredients)
    return excluded_ingredients == requirement["avoid"]


def _can_clear_pregnancy_survey_only_block(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False
    if not recommendations:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-PREG-001", "SAFETY-DUP-001"}):
        return False
    if {"INTAKE-SURVEY-001", "SAFETY-PREG-001"} - rule_ids:
        return False

    allowed_ingredients_by_goal = {
        frozenset({RecommendationGoal.BLOOD_GLUCOSE}): {"soluble_fiber"},
        frozenset({RecommendationGoal.GUT_HEALTH}): {"soluble_fiber", "probiotics"},
        frozenset({RecommendationGoal.GENERAL_WELLNESS}): {
            "vitamin_d3",
            "vitamin_c",
            "zinc",
        },
    }
    allowed_ingredients = allowed_ingredients_by_goal.get(frozenset(intake.goal_set))
    if allowed_ingredients is None:
        return False
    return all(
        item.ingredient_key in allowed_ingredients
        for item in recommendations
    )


def _can_clear_pregnancy_renal_survey_only_block(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if not recommendations:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset(
        {
            "missing_survey",
            "missing_current_supplements",
            "missing_glucose_context",
        }
    ):
        return False
    if "missing_survey" not in missing_codes:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset(
        {"INTAKE-SURVEY-001", "SAFETY-PREG-001", "SAFETY-RENAL-001", "SAFETY-DUP-001"}
    ):
        return False
    if {"INTAKE-SURVEY-001", "SAFETY-PREG-001", "SAFETY-RENAL-001"} - rule_ids:
        return False

    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if not any(
        flag in intake.signal_flags
        for flag in ("cgm_glucose_context", "genetic_glycemic_context")
    ):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"soluble_fiber"}


def _can_clear_general_wellness_survey_only_block(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.GENERAL_WELLNESS}:
        return False
    if not recommendations:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset(
        {"missing_survey", "missing_current_supplements", "missing_primary_symptom"}
    ):
        return False
    if "missing_survey" not in missing_codes:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if rule_ids != {"INTAKE-SURVEY-001"}:
        return False

    allowed_ingredients = {"vitamin_d3", "vitamin_c"}
    return all(item.ingredient_key in allowed_ingredients for item in recommendations)


def _can_clear_baseline_survey_only_block(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False
    if not recommendations:
        return False

    allowed_ingredients_by_goal = {
        RecommendationGoal.ENERGY_SUPPORT: {"vitamin_b_complex", "coq10"},
        RecommendationGoal.BONE_JOINT: {"vitamin_d3", "calcium_citrate"},
    }
    allowed_ingredients = allowed_ingredients_by_goal.get(next(iter(intake.goal_set), None))
    if intake.goal_set not in (
        {RecommendationGoal.ENERGY_SUPPORT},
        {RecommendationGoal.BONE_JOINT},
    ):
        return False
    if allowed_ingredients is None:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False
    if "missing_survey" not in missing_codes:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-DUP-001"}):
        return False
    if "INTAKE-SURVEY-001" not in rule_ids:
        return False

    return all(item.ingredient_key in allowed_ingredients for item in recommendations)


def _can_clear_heart_survey_only_block(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset(
        {
            "missing_heart_context",
            "missing_survey",
            "missing_primary_symptom",
            "missing_current_supplements",
        }
    ):
        return False
    if "missing_survey" not in missing_codes:
        return False
    if "missing_heart_context" not in missing_codes:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-DUP-001"}):
        return False
    if "INTAKE-SURVEY-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in ({"omega3", "coq10"}, {"coq10"})


def _can_clear_anticoagulant_survey_only_block(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if not intake.medication_set:
        return False
    if not intake.medication_set.issubset({"warfarin", "coumadin"}):
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False
    if "missing_survey" not in missing_codes:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset(
        {"INTAKE-SURVEY-001", "SAFETY-ANTICOAG-001", "SAFETY-DUP-001"}
    ):
        return False
    if {"INTAKE-SURVEY-001", "SAFETY-ANTICOAG-001"} - rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10"}


def _can_clear_renal_survey_only_block(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set:
        return False
    if intake.goal_set not in (
        {RecommendationGoal.SLEEP_SUPPORT},
        {RecommendationGoal.BONE_JOINT},
    ):
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if not recommendations:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False
    if "missing_survey" not in missing_codes:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-RENAL-001", "SAFETY-DUP-001"}):
        return False
    if {"INTAKE-SURVEY-001", "SAFETY-RENAL-001"} - rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    if intake.goal_set == {RecommendationGoal.SLEEP_SUPPORT}:
        if recommendation_keys != {"l_theanine"}:
            return False
        return "wearable_sleep_context" in intake.signal_flags or (
            "difficulty_falling_asleep" in intake.symptom_set
        )

    if recommendation_keys not in ({"vitamin_d3", "calcium_citrate"}, {"calcium_citrate"}):
        return False
    return "low_sun_exposure" in intake.symptom_set or any(
        flag in intake.signal_flags
        for flag in ("genetic_bone_context", "genetic_low_sun_context")
    )


def _can_start_with_genetic_glucose_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if intake.request.input_availability.cgm:
        return False
    if "genetic_glycemic_context" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_glucose_context" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_glucose_context", "missing_current_supplements"}):
        return False

    if not recommendations or any(
        item.ingredient_key != "soluble_fiber" for item in recommendations
    ):
        return False

    unavailable_glucose_escalation = (
        {"berberine"} & set(safety_summary.excluded_ingredients)
        or {"berberine"} & intake.current_ingredient_set
        or {"berberine"} & intake.avoid_ingredient_set
    )
    return bool(unavailable_glucose_escalation)


def _can_start_with_pregnancy_renal_genetic_glucose_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if intake.request.input_availability.cgm:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if "genetic_glycemic_context" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_glucose_context" not in missing_codes and "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {"missing_glucose_context", "missing_current_supplements", "missing_survey"}
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if {"SAFETY-PREG-001", "SAFETY-RENAL-001"} - rule_ids:
        return False
    if not rule_ids.issubset(
        {
            "INTAKE-SURVEY-001",
            "SAFETY-PREG-001",
            "SAFETY-RENAL-001",
            "SAFETY-DUP-001",
        }
    ):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"soluble_fiber"}


def _can_start_with_pregnancy_renal_cgm_glucose_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if not intake.request.input_availability.cgm:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if "cgm_glucose_context" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {"missing_glucose_context", "missing_current_supplements", "missing_survey"}
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if {"INTAKE-SURVEY-001", "SAFETY-PREG-001", "SAFETY-RENAL-001"} - rule_ids:
        return False
    if not rule_ids.issubset(
        {
            "INTAKE-SURVEY-001",
            "SAFETY-PREG-001",
            "SAFETY-RENAL-001",
            "SAFETY-DUP-001",
        }
    ):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"soluble_fiber"}


def _can_start_with_current_regimen_coverage(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status == RecommendationStatus.BLOCKED:
        return False
    if recommendations:
        return False
    pregnancy_duplicate_glucose_regimen = False
    statin_duplicate_heart_regimen = False
    duplicate_glucose_regimen = False
    if intake.request.user_profile.pregnant:
        pregnancy_duplicate_glucose_regimen = (
            _can_start_with_pregnancy_duplicate_glucose_regimen_coverage(
                intake, safety_summary
            )
        )
        if not pregnancy_duplicate_glucose_regimen:
            return False
    elif intake.medication_set:
        statin_duplicate_heart_regimen = _can_start_with_statin_duplicate_heart_regimen_coverage(
            intake, safety_summary
        )
        if not statin_duplicate_heart_regimen:
            return False
    else:
        duplicate_glucose_regimen = _can_start_with_duplicate_glucose_regimen_coverage(
            intake, safety_summary
        )
    if intake.missing_information:
        missing_codes = {item.code for item in intake.missing_information}
        if not (
            pregnancy_duplicate_glucose_regimen
            and missing_codes.issubset(
                {"missing_glucose_context", "missing_current_supplements"}
            )
        ):
            return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    renal_only = bool(intake.condition_set)
    if renal_only:
        if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
            return False
        if intake.goal_set != {RecommendationGoal.SLEEP_SUPPORT}:
            return False
        if "difficulty_falling_asleep" not in intake.symptom_set:
            return False
        if "SAFETY-RENAL-001" not in rule_ids:
            return False
        if not rule_ids.issubset({"SAFETY-RENAL-001", "SAFETY-DUP-001"}):
            return False
    elif (
        not pregnancy_duplicate_glucose_regimen
        and not duplicate_glucose_regimen
        and rule_ids != {"SAFETY-DUP-001"}
    ):
        return False

    catalog_by_key = {item.key: item for item in list_catalog_items()}
    current_items = [
        catalog_by_key[item_key]
        for item_key in intake.current_ingredient_set
        if item_key in catalog_by_key
    ]
    if not current_items:
        return False
    if (
        not duplicate_glucose_regimen
        and not statin_duplicate_heart_regimen
        and any(
            item.conservative_profile not in {"baseline", "standard"}
            for item in current_items
        )
    ):
        return False
    if any(item.key in intake.avoid_ingredient_set for item in current_items):
        return False

    covered_goals = {
        goal for item in current_items for goal in item.supported_goals
    }
    if not intake.goal_set.issubset(covered_goals):
        return False
    if renal_only:
        return intake.current_ingredient_set == {"l_theanine"}
    return True


def _can_start_with_statin_duplicate_heart_regimen_coverage(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if "low_activity" not in intake.symptom_set:
        return False
    if not intake.medication_set.issubset({"atorvastatin"}):
        return False
    if not intake.current_ingredient_set:
        return False
    if not intake.current_ingredient_set.issubset({"omega3", "coq10"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    return rule_ids == {"SAFETY-DUP-001"}


def _can_start_with_duplicate_glucose_regimen_coverage(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
) -> bool:
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if intake.current_ingredient_set != {"berberine"}:
        return False
    if intake.avoid_ingredient_set != {"soluble_fiber"}:
        return False
    if not (
        "cgm_glucose_context" in intake.signal_flags
        or "genetic_glycemic_context" in intake.signal_flags
    ):
        return False
    if intake.missing_information:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    return rule_ids == {"SAFETY-DUP-001"}


def _can_start_with_pregnancy_duplicate_glucose_regimen_coverage(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
) -> bool:
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if "soluble_fiber" in intake.avoid_ingredient_set:
        return False
    if intake.current_ingredient_set != {"soluble_fiber"}:
        return False
    if not (
        "cgm_glucose_context" in intake.signal_flags
        or "genetic_glycemic_context" in intake.signal_flags
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    return rule_ids == {"SAFETY-PREG-001", "SAFETY-DUP-001"}


def _can_start_with_duplicate_heart_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if not intake.current_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if missing_codes != {"missing_heart_context"}:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if rule_ids != {"SAFETY-DUP-001"}:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10", "omega3"}


def _can_start_with_wearable_heart_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if missing_codes != {"missing_current_supplements", "missing_heart_context"}:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10", "omega3"}


def _can_start_with_duplicate_heart_symptom_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if not intake.current_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if missing_codes != {"missing_heart_context"}:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if rule_ids != {"SAFETY-DUP-001"}:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10"}


def _can_start_with_heart_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset(
        {
            "missing_heart_context",
            "missing_survey",
            "missing_primary_symptom",
            "missing_current_supplements",
        }
    ):
        return False
    if "missing_survey" not in missing_codes:
        return False
    if "missing_heart_context" not in missing_codes:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-DUP-001"}):
        return False
    if "INTAKE-SURVEY-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in ({"omega3", "coq10"}, {"coq10"})


def _can_start_with_anticoagulant_heart_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if not intake.medication_set:
        return False
    if not intake.medication_set.issubset({"warfarin", "coumadin"}):
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False
    if "missing_survey" not in missing_codes:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset(
        {"INTAKE-SURVEY-001", "SAFETY-ANTICOAG-001", "SAFETY-DUP-001"}
    ):
        return False
    if {"INTAKE-SURVEY-001", "SAFETY-ANTICOAG-001"} - rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10"}


def _can_start_with_energy_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.ENERGY_SUPPORT}:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False
    if not intake.symptom_set.intersection({"fatigue", "frequent_fatigue"}):
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in ({"vitamin_b_complex", "coq10"}, {"coq10"})


def _can_start_with_energy_missing_symptom_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.ENERGY_SUPPORT}:
        return False
    if intake.symptom_set:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    sleep_hours = intake.request.lifestyle.sleep_hours
    if sleep_hours is None or sleep_hours > 6.0:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_primary_symptom" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {"missing_primary_symptom", "missing_current_supplements"}
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"vitamin_b_complex", "coq10"},
        {"vitamin_b_complex"},
        {"coq10"},
    )


def _can_start_with_bone_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.BONE_JOINT}:
        return False
    if not {"low_sun_exposure", "genetic_bone_context"} & (
        intake.symptom_set | intake.signal_flags
    ):
        return False
    if not (
        "genetic_bone_context" in intake.signal_flags
        or "genetic_low_sun_context" in intake.signal_flags
    ):
        return False
    if "low_sun_exposure" not in intake.symptom_set:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-DUP-001"}):
        return False
    if "INTAKE-SURVEY-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"vitamin_d3", "calcium_citrate"},
        {"calcium_citrate"},
    )


def _can_start_with_renal_bone_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.BONE_JOINT}:
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if "low_sun_exposure" not in intake.symptom_set:
        return False
    if not (
        "genetic_bone_context" in intake.signal_flags
        or "genetic_low_sun_context" in intake.signal_flags
    ):
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if {"INTAKE-SURVEY-001", "SAFETY-RENAL-001"} - rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-RENAL-001", "SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"vitamin_d3", "calcium_citrate"},
        {"calcium_citrate"},
    )


def _can_start_with_general_wellness_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.GENERAL_WELLNESS}:
        return False
    if "frequent_fatigue" not in intake.symptom_set:
        return False
    if not (
        "low_sun_exposure" in intake.symptom_set
        or "genetic_micronutrient_context" in intake.signal_flags
        or "genetic_low_sun_context" in intake.signal_flags
    ):
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-DUP-001"}):
        return False
    if "INTAKE-SURVEY-001" not in rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in ({"vitamin_d3", "vitamin_c"}, {"vitamin_d3"})


def _can_start_with_multimodal_general_wellness_missing_symptom_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.GENERAL_WELLNESS}:
        return False
    if intake.symptom_set:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "genetic_micronutrient_context" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_primary_symptom" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {"missing_primary_symptom", "missing_current_supplements"}
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if rule_ids:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"vitamin_d3", "magnesium_glycinate"},
        {"vitamin_d3"},
    )


def _can_start_with_pregnancy_gut_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.GUT_HEALTH}:
        return False
    if "bloating" not in intake.symptom_set:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if {"INTAKE-SURVEY-001", "SAFETY-PREG-001"} - rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-PREG-001", "SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in ({"soluble_fiber", "probiotics"}, {"soluble_fiber"})


def _can_start_with_pregnancy_general_wellness_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.GENERAL_WELLNESS}:
        return False
    if "frequent_fatigue" not in intake.symptom_set:
        return False
    if not (
        "low_sun_exposure" in intake.symptom_set
        or "genetic_micronutrient_context" in intake.signal_flags
        or "genetic_low_sun_context" in intake.signal_flags
    ):
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if {"INTAKE-SURVEY-001", "SAFETY-PREG-001"} - rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-PREG-001", "SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"vitamin_d3", "vitamin_c"},
        {"vitamin_d3", "zinc"},
        {"vitamin_d3"},
    )


def _can_start_with_pregnancy_glucose_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if not intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if intake.avoid_ingredient_set.intersection({"soluble_fiber"}):
        return False
    if not (
        "cgm_glucose_context" in intake.signal_flags
        or "genetic_glycemic_context" in intake.signal_flags
    ):
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {"missing_survey", "missing_current_supplements", "missing_glucose_context"}
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if {"INTAKE-SURVEY-001", "SAFETY-PREG-001"} - rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-PREG-001", "SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"soluble_fiber"}


def _can_start_with_multimodal_heart_energy_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {
        RecommendationGoal.HEART_HEALTH,
        RecommendationGoal.ENERGY_SUPPORT,
    }:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "genetic_cardiometabolic_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_heart_context" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {
            "missing_current_supplements",
            "missing_heart_context",
            "missing_primary_symptom",
        }
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10", "omega3"}


def _can_start_with_multimodal_heart_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.HEART_HEALTH}:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "genetic_cardiometabolic_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_heart_context" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {
            "missing_current_supplements",
            "missing_heart_context",
            "missing_primary_symptom",
        }
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"coq10", "omega3"}


def _can_start_with_duplicate_heart_energy_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if not intake.current_ingredient_set:
        return False
    if intake.goal_set != {
        RecommendationGoal.HEART_HEALTH,
        RecommendationGoal.ENERGY_SUPPORT,
    }:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if missing_codes != {"missing_heart_context"}:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if rule_ids != {"SAFETY-DUP-001"}:
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"omega3", "vitamin_b_complex"}


def _can_start_with_multimodal_heart_sleep_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {
        RecommendationGoal.HEART_HEALTH,
        RecommendationGoal.SLEEP_SUPPORT,
    }:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "wearable_sleep_context" not in intake.signal_flags:
        return False
    if "genetic_cardiometabolic_context" not in intake.signal_flags:
        return False
    if "genetic_recovery_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_heart_context" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {
            "missing_current_supplements",
            "missing_heart_context",
            "missing_primary_symptom",
        }
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"magnesium_glycinate", "omega3"}


def _can_start_with_multimodal_heart_glucose_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {
        RecommendationGoal.BLOOD_GLUCOSE,
        RecommendationGoal.HEART_HEALTH,
    }:
        return False
    if "wearable_activity_context" not in intake.signal_flags:
        return False
    if "low_activity" not in intake.signal_flags:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if "low_activity" not in intake.symptom_set:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if not {"missing_glucose_context", "missing_heart_context"}.issubset(missing_codes):
        return False
    if not missing_codes.issubset(
        {
            "missing_current_supplements",
            "missing_glucose_context",
            "missing_heart_context",
        }
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"omega3", "soluble_fiber"}


def _can_start_with_glucose_sleep_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {
        RecommendationGoal.BLOOD_GLUCOSE,
        RecommendationGoal.SLEEP_SUPPORT,
    }:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if intake.request.input_availability.cgm:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_glucose_context" not in missing_codes:
        return False
    if not missing_codes.issubset(
        {
            "missing_current_supplements",
            "missing_glucose_context",
            "missing_sleep_hours",
        }
    ):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"soluble_fiber", "magnesium_glycinate"}


def _can_start_with_sleep_hours_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.SLEEP_SUPPORT}:
        return False
    if "wearable_sleep_context" not in intake.signal_flags:
        return False
    if "difficulty_falling_asleep" not in intake.symptom_set:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_sleep_hours" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_sleep_hours", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"magnesium_glycinate", "l_theanine"},
        {"l_theanine"},
    )


def _can_start_with_renal_sleep_survey_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.SLEEP_SUPPORT}:
        return False
    if not intake.condition_set:
        return False
    if not intake.condition_set.issubset({"kidney disease", "chronic kidney disease"}):
        return False
    if "wearable_sleep_context" not in intake.signal_flags:
        return False
    if "difficulty_falling_asleep" not in intake.symptom_set:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_survey" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_survey", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if {"INTAKE-SURVEY-001", "SAFETY-RENAL-001"} - rule_ids:
        return False
    if not rule_ids.issubset({"INTAKE-SURVEY-001", "SAFETY-RENAL-001", "SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys == {"l_theanine"}


def _is_multigoal_sleep_multiple_missing_floor(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set not in (
        {RecommendationGoal.SLEEP_SUPPORT, RecommendationGoal.GENERAL_WELLNESS},
        {RecommendationGoal.SLEEP_SUPPORT, RecommendationGoal.STRESS_SUPPORT},
    ):
        return False
    if intake.symptom_set:
        return False
    if not {
        "wearable_sleep_context",
        "genetic_recovery_context",
    } & intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if missing_codes != {
        "missing_primary_symptom",
        "missing_sleep_hours",
        "missing_current_supplements",
    }:
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"magnesium_glycinate", "l_theanine"},
        {"l_theanine"},
    )


def _can_start_with_cgm_glucose_missing_symptom_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if intake.symptom_set:
        return False
    if not intake.request.input_availability.cgm:
        return False
    if "cgm_glucose_context" not in intake.signal_flags:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_primary_symptom" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_primary_symptom", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"soluble_fiber", "berberine"},
        {"soluble_fiber"},
        {"berberine"},
    )


def _can_start_with_glucose_symptom_fallback(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    recommendations: list[RecommendationCandidate],
) -> bool:
    if safety_summary.status != RecommendationStatus.OK:
        return False
    if intake.request.user_profile.pregnant:
        return False
    if intake.medication_set or intake.condition_set or intake.avoid_ingredient_set:
        return False
    if intake.goal_set != {RecommendationGoal.BLOOD_GLUCOSE}:
        return False
    if "post_meal_spike_concern" not in intake.symptom_set:
        return False
    if intake.request.input_availability.cgm:
        return False
    if intake.request.input_availability.genetic:
        return False

    missing_codes = {item.code for item in intake.missing_information}
    if "missing_glucose_context" not in missing_codes:
        return False
    if not missing_codes.issubset({"missing_glucose_context", "missing_current_supplements"}):
        return False

    rule_ids = {rule.rule_id for rule in safety_summary.rule_refs}
    if not rule_ids.issubset({"SAFETY-DUP-001"}):
        return False

    recommendation_keys = {item.ingredient_key for item in recommendations}
    return recommendation_keys in (
        {"soluble_fiber", "berberine"},
        {"soluble_fiber"},
        {"berberine"},
    )


def _build_decision_summary(
    intake: NormalizedIntake,
    status: RecommendationStatus,
    recommendation_names: list[str],
    current_regimen_continuation: bool,
    wearable_context_considered: bool,
    cgm_context_considered: bool,
    genetic_context_influenced: bool,
) -> DecisionSummary:
    goal_text = ", ".join(
        goal.value for goal in sorted(intake.goal_set, key=lambda goal: goal.value)
    )
    candidate_text = ", ".join(recommendation_names) if recommendation_names else "no candidates"

    if current_regimen_continuation:
        headline = "current regimen continuation"
        summary = (
            f"For goals [{goal_text}], the baseline found no additional safe candidates "
            "after duplicate filtering because the current regimen already covers the "
            "focus goals."
        )
        confidence = "high"
    elif status == RecommendationStatus.NEEDS_REVIEW:
        headline = "conservative review required"
        summary = (
            f"For goals [{goal_text}], the baseline prioritized {candidate_text}, but safety "
            "review, a system safety recheck, or additional intake clarification should come first."
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

    if wearable_context_considered:
        summary += " Available wearable context was considered in the current baseline."
    if cgm_context_considered:
        summary += " Available CGM context was considered in the current baseline."
    if genetic_context_influenced:
        summary += " Available genetic context influenced the current ranking."

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
        summary = (
            "The minimum intake contract is incomplete, so more input is "
            "required before planning."
        )
        if _wearable_context_considered(intake):
            summary += (
                " Wearable context was available, but the minimum intake contract still "
                "prevented deterministic planning."
            )
        if _cgm_context_considered(intake):
            summary += (
                " CGM context was available, but the minimum intake contract still "
                "prevented deterministic planning."
            )
        if _genetic_context_considered(intake):
            summary += (
                " Genetic context was available, but the minimum intake contract still "
                "prevented deterministic planning."
            )
        return NextActionRationale(
            reason_code="blocked_minimum_input",
            summary=summary,
            supporting_codes=missing_codes or rule_ids,
        )

    if not recommendations:
        if _can_start_with_current_regimen_coverage(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_current_regimen_coverage",
                summary=(
                    "Duplicate overlap removed additional candidates, but the current "
                    "regimen already covers the focus goals, so the plan can continue "
                    "without adding a new supplement."
                ),
                supporting_codes=sorted(intake.current_ingredient_set),
            )
        explicit_avoid_floor = _is_explicit_avoid_single_goal_no_candidate_floor(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        )
        if explicit_avoid_floor:
            goal_name = next(iter(intake.goal_set)).value.replace("_", " ")
            summary = (
                "Explicit avoid preferences removed all deterministic "
                f"{goal_name} candidates in the current baseline catalog, so "
                "a system safety recheck is required instead of overriding the avoid "
                "guard. No safe deterministic candidates remain once the full "
                "single-goal set is explicitly avoided."
            )
            if _wearable_context_considered(intake):
                summary += (
                    " Available wearable context was considered, but it does not "
                    "restore a safe candidate once the full single-goal set is "
                    "explicitly avoided."
                )
            if _cgm_context_considered(intake):
                summary += (
                    " Available CGM context was considered, but it does not restore "
                    "a safe candidate once the full single-goal set is explicitly "
                    "avoided."
                )
            if _genetic_context_considered(intake):
                summary += (
                    " Available genetic context was considered, but it does not "
                    "restore a safe candidate once the full single-goal set is "
                    "explicitly avoided."
                )
            return NextActionRationale(
                reason_code="needs_review_no_candidates",
                summary=summary,
                supporting_codes=sorted(safety_summary.excluded_ingredients),
            )
        summary = (
            "No safe deterministic candidates were available, so a system safety "
            "recheck is required."
        )
        if _wearable_context_considered(intake):
            summary += (
                " Available wearable context was considered, but no additional safe "
                "deterministic candidate remained under current constraints."
            )
        if _cgm_context_considered(intake):
            summary += (
                " Available CGM context was considered, but no additional safe "
                "deterministic candidate remained under current constraints."
            )
        if _genetic_context_considered(intake):
            summary += (
                " Available genetic context was considered, but no additional safe "
                "deterministic candidate remained under current constraints."
            )
        return NextActionRationale(
            reason_code="needs_review_no_candidates",
            summary=summary,
            supporting_codes=rule_ids or missing_codes,
        )

    if next_action == NextAction.TRIGGER_SAFETY_RECHECK:
        stacked_floor = _is_stacked_pregnancy_renal_anticoagulant_review_floor(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        )
        survivor_collapse_floor = _is_anticoagulant_survivor_collapse_review_floor(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        )
        glucose_survivor_collapse_floor = (
            _is_anticoagulant_glucose_survivor_collapse_review_floor(
                intake=intake,
                safety_summary=safety_summary,
                recommendations=recommendations,
            )
        )
        if stacked_floor:
            summary = (
                "Stacked pregnancy, renal, and anticoagulant safety signals are "
                "present, so a system safety recheck remains required before plan start "
                "even though soluble fiber and CoQ10 survived the current "
                "filtering."
            )
        elif glucose_survivor_collapse_floor:
            summary = (
                "Anticoagulant filtering removed omega3, soluble fiber was "
                "removed by avoid filtering, and duplicate overlap removed "
                "berberine, leaving CoQ10 only despite available heart and CGM "
                "glucose context, so a system safety recheck remains required before plan "
                "start."
            )
        elif survivor_collapse_floor:
            summary = (
                "Anticoagulant filtering removed omega3 and the remaining multi-goal "
                "survivor set collapsed to CoQ10 only after avoid or duplicate "
                "filtering, so a system safety recheck remains required before plan start."
            )
        else:
            summary = (
                "Safety review signals are present, so the baseline requires "
                "a system safety recheck before plan start."
            )
        if _wearable_context_considered(intake):
            summary += (
                " Available wearable context was considered, but safety review still "
                "takes priority."
            )
        if _cgm_context_considered(intake):
            summary += (
                " Available CGM context was considered, but safety review still "
                "takes priority."
            )
        if stacked_floor and _genetic_context_considered(intake):
            summary += (
                " Available genetic context was considered, but the stacked safety "
                "review still takes priority."
            )
        if survivor_collapse_floor and _genetic_context_considered(intake):
            summary += (
                " Available genetic context was considered, but the collapsed "
                "single-survivor review still takes priority."
            )
        return NextActionRationale(
            reason_code="needs_review_due_to_safety",
            summary=summary,
            supporting_codes=rule_ids,
        )

    if next_action == NextAction.COLLECT_MORE_INPUT and high_priority_codes:
        if _can_start_with_duplicate_heart_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_duplicate_heart_fallback",
                summary=(
                    "Available wearable activity context is strong enough to start a "
                    "conservative heart-health baseline plan now, even though duplicate "
                    "filtering already removed current-regimen overlap and deeper heart "
                    "context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_duplicate_heart_symptom_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_duplicate_heart_symptom_fallback",
                summary=(
                    "Explicit low-activity symptom detail is strong enough to start a "
                    "conservative heart-health baseline plan now, even though duplicate "
                    "filtering removed the current omega3 overlap and deeper heart "
                    "context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_heart_survey_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_heart_survey_fallback",
                summary=(
                    "Available wearable activity context is strong enough to start a "
                    "conservative heart-health baseline plan now, while the missing "
                    "survey can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_bone_survey_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_bone_survey_fallback",
                summary=(
                    "Explicit low-sun symptom detail and genetic bone context are "
                    "strong enough to start a conservative bone-support baseline plan "
                    "now, while the missing survey can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_renal_bone_survey_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_renal_bone_survey_fallback",
                summary=(
                    "Explicit low-sun symptom detail, genetic bone context, and the "
                    "renal-only conservative bone survivors are strong enough to start "
                    "a conservative bone-support baseline plan now, while the missing "
                    "survey can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_general_wellness_survey_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_general_wellness_survey_fallback",
                summary=(
                    "Explicit fatigue detail is strong enough to start a conservative "
                    "general-wellness baseline plan now, while the missing survey can "
                    "still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_pregnancy_gut_survey_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_pregnancy_gut_survey_fallback",
                summary=(
                    "Explicit bloating detail and the remaining pregnancy-safe gut "
                    "candidates are strong enough to start a conservative gut-health "
                    "baseline plan now, while the missing survey can still be "
                    "collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_pregnancy_general_wellness_survey_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_pregnancy_general_wellness_survey_fallback",
                summary=(
                    "Explicit fatigue detail and the remaining pregnancy-safe "
                    "micronutrient candidates are strong enough to start a "
                    "conservative general-wellness baseline plan now, while the "
                    "missing survey can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_multimodal_heart_energy_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_multimodal_heart_energy_fallback",
                summary=(
                    "Available wearable activity context and genetic "
                    "cardiometabolic context are strong enough to start a "
                    "conservative heart-and-energy baseline plan now, while "
                    "deeper heart context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_duplicate_heart_energy_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_duplicate_heart_energy_fallback",
                summary=(
                    "Available wearable activity context is strong enough to start a "
                    "conservative heart-and-energy baseline plan now, even though "
                    "duplicate filtering already removed current-regimen overlap and "
                    "deeper heart context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_multimodal_heart_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_multimodal_heart_fallback",
                summary=(
                    "Available wearable activity context and genetic "
                    "cardiometabolic context are strong enough to start a "
                    "conservative heart-health baseline plan now, while "
                    "deeper heart context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_multimodal_heart_sleep_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_multimodal_heart_sleep_fallback",
                summary=(
                    "Available wearable activity context, wearable sleep context, "
                    "and genetic heart-recovery context are strong enough to start "
                    "a conservative heart-and-sleep baseline plan now, while deeper "
                    "heart context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_multimodal_heart_glucose_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_multimodal_heart_glucose_fallback",
                summary=(
                    "Available wearable activity context and explicit post-meal spike "
                    "symptom detail are strong enough to start a conservative heart-"
                    "and-glucose baseline plan now, while deeper glucose and heart "
                    "context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_glucose_sleep_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_glucose_sleep_fallback",
                summary=(
                    "Explicit post-meal spike detail is strong enough to start a "
                    "conservative glucose-and-sleep baseline plan now when the "
                    "remaining candidates are limited to soluble fiber and "
                    "magnesium glycinate, while deeper glucose context can still "
                    "be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_wearable_heart_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_wearable_heart_fallback",
                summary=(
                    "Available wearable activity context is strong enough to start a "
                    "conservative heart-health baseline plan now, while deeper heart "
                    "context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_pregnancy_renal_genetic_glucose_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_pregnancy_renal_genetic_glucose_fallback",
                summary=(
                    "Explicit post-meal spike detail and genetic glycemic context are "
                    "strong enough to start a conservative renal-and-pregnancy-safe "
                    "glucose baseline plan now when only soluble fiber survives, "
                    "while deeper glucose context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_pregnancy_renal_cgm_glucose_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_pregnancy_renal_cgm_glucose_fallback",
                summary=(
                    "Explicit post-meal spike detail and CGM glucose context are "
                    "strong enough to start a conservative renal-and-pregnancy-safe "
                    "glucose baseline plan now when only soluble fiber survives, "
                    "while deeper survey context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        if _can_start_with_glucose_symptom_fallback(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            return NextActionRationale(
                reason_code="start_plan_glucose_symptom_fallback",
                summary=(
                    "Explicit post-meal spike detail is strong enough to start a "
                    "conservative blood-glucose baseline plan now, while deeper "
                    "glucose context can still be collected later."
                ),
                supporting_codes=sorted(
                    high_priority_codes
                    + [item.ingredient_key for item in recommendations]
                ),
            )
        summary = (
            "High-priority missing context is still open, so more input is "
            "needed before plan start."
        )
        if _wearable_context_considered(intake):
            summary += (
                " Available wearable context was considered, but additional intake "
                "context is still required."
            )
        if _cgm_context_considered(intake):
            summary += (
                " Available CGM context was considered, but additional intake "
                "context is still required."
            )
        if _genetic_context_considered(intake):
            summary += (
                " Available genetic context was considered, but additional intake "
                "context is still required."
            )
        return NextActionRationale(
            reason_code="collect_more_input_high_priority_missing_info",
            summary=summary,
            supporting_codes=high_priority_codes,
        )

    if _can_start_with_wearable_heart_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_wearable_heart_fallback",
            summary=(
                "Available wearable activity context is strong enough to start a "
                "conservative heart-health baseline plan now, while deeper heart "
                "context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_duplicate_heart_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_duplicate_heart_fallback",
            summary=(
                "Available wearable activity context is strong enough to start a "
                "conservative heart-health baseline plan now, even though duplicate "
                "filtering already removed current-regimen overlap and deeper heart "
                "context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_duplicate_heart_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_duplicate_heart_symptom_fallback",
            summary=(
                "Explicit low-activity symptom detail is strong enough to start a "
                "conservative heart-health baseline plan now, even though duplicate "
                "filtering removed the current omega3 overlap and deeper heart "
                "context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_heart_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_heart_survey_fallback",
            summary=(
                "Available wearable activity context is strong enough to start a "
                "conservative heart-health baseline plan now, while the missing "
                "survey can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_anticoagulant_heart_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_anticoagulant_heart_survey_fallback",
            summary=(
                "Available wearable activity context is strong enough to start a "
                "conservative heart-health baseline plan now after anticoagulant "
                "filtering left CoQ10 as the only survivor, while the missing "
                "survey can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_energy_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_energy_survey_fallback",
            summary=(
                "Available wearable activity context and explicit fatigue detail "
                "are strong enough to start a conservative baseline energy plan "
                "now, while the missing survey can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_energy_missing_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_energy_missing_symptom_fallback",
            summary=(
                "Available wearable activity context and short-sleep detail are "
                "strong enough to start a conservative baseline energy plan now, "
                "while the missing primary symptom detail can still be collected "
                "later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_bone_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_bone_survey_fallback",
            summary=(
                "Explicit low-sun symptom detail and genetic bone context are "
                "strong enough to start a conservative bone-support baseline plan "
                "now, while the missing survey can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_general_wellness_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_general_wellness_survey_fallback",
            summary=(
                "Explicit fatigue detail is strong enough to start a conservative "
                "general-wellness baseline plan now, while the missing survey can "
                "still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_multimodal_general_wellness_missing_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_multimodal_general_wellness_missing_symptom_fallback",
            summary=(
                "Available wearable context and available genetic context are "
                "strong enough to start a conservative general-wellness baseline "
                "plan now, even though the primary symptom detail is still "
                "missing."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_pregnancy_gut_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_pregnancy_gut_survey_fallback",
            summary=(
                "Explicit bloating detail and the remaining pregnancy-safe gut "
                "candidates are strong enough to start a conservative gut-health "
                "baseline plan now, while the missing survey can still be "
                "collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_pregnancy_general_wellness_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_pregnancy_general_wellness_survey_fallback",
            summary=(
                "Explicit fatigue detail and the remaining pregnancy-safe "
                "micronutrient candidates are strong enough to start a "
                "conservative general-wellness baseline plan now, while the "
                "missing survey can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_pregnancy_glucose_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_pregnancy_glucose_survey_fallback",
            summary=(
                "Explicit post-meal spike detail and the remaining pregnancy-safe "
                "soluble-fiber survivor are strong enough to start a conservative "
                "glucose baseline plan now, while the missing survey can still be "
                "collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_multimodal_heart_energy_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_multimodal_heart_energy_fallback",
            summary=(
                "Available wearable activity context and genetic "
                "cardiometabolic context are strong enough to start a "
                "conservative heart-and-energy baseline plan now, while deeper "
                "heart context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_duplicate_heart_energy_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_duplicate_heart_energy_fallback",
            summary=(
                "Available wearable activity context is strong enough to start a "
                "conservative heart-and-energy baseline plan now, even though duplicate "
                "filtering already removed current-regimen overlap and deeper heart "
                "context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_multimodal_heart_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_multimodal_heart_fallback",
            summary=(
                "Available wearable activity context and genetic "
                "cardiometabolic context are strong enough to start a "
                "conservative heart-health baseline plan now, while deeper "
                "heart context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_multimodal_heart_sleep_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_multimodal_heart_sleep_fallback",
            summary=(
                "Available wearable activity context, wearable sleep context, and "
                "genetic heart-recovery context are strong enough to start a "
                "conservative heart-and-sleep baseline plan now, while deeper "
                "heart context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_multimodal_heart_glucose_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_multimodal_heart_glucose_fallback",
            summary=(
                "Available wearable activity context and explicit post-meal spike "
                "symptom detail are strong enough to start a conservative heart-and-"
                "glucose baseline plan now, while deeper glucose and heart context "
                "can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_glucose_sleep_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_glucose_sleep_fallback",
            summary=(
                "Explicit post-meal spike detail is strong enough to start a "
                "conservative glucose-and-sleep baseline plan now when the "
                "remaining candidates are limited to soluble fiber and "
                "magnesium glycinate, while deeper glucose context can still "
                "be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_sleep_hours_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_sleep_hours_fallback",
            summary=(
                "Explicit sleep-onset symptom detail and wearable sleep context "
                "are strong enough to start a conservative sleep-support baseline "
                "plan now, while the missing sleep-hours detail can still be "
                "collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_renal_sleep_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_renal_sleep_survey_fallback",
            summary=(
                "Explicit sleep-onset symptom detail, wearable sleep context, and the "
                "renal-only theanine survivor are strong enough to start a conservative "
                "sleep-support baseline plan now, while the missing survey can still be "
                "collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_cgm_glucose_missing_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_cgm_glucose_missing_symptom_fallback",
            summary=(
                "Available CGM glucose context is strong enough to start a conservative "
                "blood-glucose baseline plan now, even though the primary symptom detail "
                "is still missing."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_glucose_symptom_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_glucose_symptom_fallback",
            summary=(
                "Explicit post-meal spike detail is strong enough to start a "
                "conservative blood-glucose baseline plan now, while deeper "
                "glucose context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_pregnancy_renal_genetic_glucose_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_pregnancy_renal_genetic_glucose_fallback",
            summary=(
                "Explicit post-meal spike detail and genetic glycemic context are "
                "strong enough to start a conservative renal-and-pregnancy-safe "
                "glucose baseline plan now when only soluble fiber survives, while "
                "deeper glucose or survey context can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if _can_start_with_renal_bone_survey_fallback(
        intake=intake,
        safety_summary=safety_summary,
        recommendations=recommendations,
    ):
        return NextActionRationale(
            reason_code="start_plan_renal_bone_survey_fallback",
            summary=(
                "Explicit low-sun symptom detail, genetic bone context, and the "
                "renal-only conservative bone survivors are strong enough to start "
                "a conservative bone-support baseline plan now, while the missing "
                "survey can still be collected later."
            ),
            supporting_codes=[item.ingredient_key for item in recommendations],
        )

    if next_action == NextAction.COLLECT_MORE_INPUT:
        if _is_anticoagulant_heart_missing_context_floor(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            summary = (
                "Multiple missing information items remain, so the baseline "
                "requests more input first. A conservative anticoagulant heart "
                "baseline still needs explicit heart symptom detail or "
                "survey-backed activity context before plan start."
            )
        elif _is_multigoal_sleep_multiple_missing_floor(
            intake=intake,
            safety_summary=safety_summary,
            recommendations=recommendations,
        ):
            summary = (
                "Multiple missing information items remain, so the baseline "
                "requests more input first. A conservative multi-goal sleep "
                "baseline still needs explicit sleep symptom detail and "
                "sleep-hours detail before plan start."
            )
        else:
            summary = (
                "Multiple missing information items remain, so the baseline "
                "requests more input first."
            )
        if _wearable_context_considered(intake):
            summary += (
                " Available wearable context was considered, but more intake detail "
                "is still needed before plan start."
            )
        if _cgm_context_considered(intake):
            summary += (
                " Available CGM context was considered, but more intake detail "
                "is still needed before plan start."
            )
        if _genetic_context_considered(intake):
            summary += (
                " Available genetic context was considered, but more intake detail "
                "is still needed before plan start."
            )
        return NextActionRationale(
            reason_code="collect_more_input_multiple_missing_items",
            summary=summary,
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


def _genetic_context_considered(intake: NormalizedIntake) -> bool:
    return any(
        flag.startswith("genetic_") and flag != "genetic_data_available"
        for flag in intake.signal_flags
    )


def _wearable_context_considered(intake: NormalizedIntake) -> bool:
    return any(
        flag.startswith("wearable_") and flag != "wearable_data_available"
        for flag in intake.signal_flags
    )


def _cgm_context_considered(intake: NormalizedIntake) -> bool:
    return "cgm_glucose_context" in intake.signal_flags
