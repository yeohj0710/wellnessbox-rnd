from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.domain.models import IngredientCatalogItem
from wellnessbox_rnd.knowledge.candidate_signals import (
    CandidateSignalRuleBase,
    CandidateSignalScoringRegistry,
    NumericCandidateSignalRule,
)
from wellnessbox_rnd.knowledge.goal_priors import get_goal_prior_index
from wellnessbox_rnd.knowledge.runtime_db import load_runtime_knowledge_db
from wellnessbox_rnd.schemas.recommendation import (
    CandidateScoreBreakdown,
    CandidateScoreSignal,
    RecommendationGoal,
)


def score_candidate(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
    safety_review: bool,
) -> CandidateScoreBreakdown:
    goal_priors = get_goal_prior_index()
    goal_alignment = sum(
        prior.prior_score
        for goal in intake.goal_set
        if (prior := goal_priors.get((item.key, goal))) is not None
    )
    symptom_signals = _symptom_signals(item, intake)
    lifestyle_signals = _lifestyle_signals(item, intake)
    laboratory_signals = _laboratory_signals(item, intake)
    dietary_signals = _dietary_signals(item, intake)
    wearable_signals = _wearable_signals(item, intake)
    cgm_signals = _cgm_signals(item, intake)
    genetic_signals = _genetic_signals(item, intake)
    symptom_alignment = sum(signal.points for signal in symptom_signals)
    lifestyle_alignment = sum(signal.points for signal in lifestyle_signals)
    laboratory_alignment = sum(signal.points for signal in laboratory_signals)
    dietary_alignment = sum(signal.points for signal in dietary_signals)
    wearable_adjustment = sum(signal.points for signal in wearable_signals)
    cgm_adjustment = sum(signal.points for signal in cgm_signals)
    genetic_adjustment = sum(signal.points for signal in genetic_signals)
    evidence_readiness = _evidence_readiness_score(item, intake)
    budget_adjustment = _budget_adjustment(
        item.budget_tier.value,
        intake.request.preferences.budget_level.value,
    )
    safety_adjustment = -4.0 if safety_review else 0.0
    conservative_adjustment = _conservative_adjustment(
        conservative_profile=item.conservative_profile,
        intake=intake,
        safety_review=safety_review,
    )
    total = (
        item.default_priority
        + goal_alignment
        + symptom_alignment
        + lifestyle_alignment
        + laboratory_alignment
        + dietary_alignment
        + wearable_adjustment
        + cgm_adjustment
        + genetic_adjustment
        + evidence_readiness
        + budget_adjustment
        + safety_adjustment
        + conservative_adjustment
    )

    return CandidateScoreBreakdown(
        goal_alignment=goal_alignment,
        symptom_alignment=symptom_alignment,
        lifestyle_alignment=lifestyle_alignment,
        laboratory_alignment=laboratory_alignment,
        dietary_alignment=dietary_alignment,
        wearable_adjustment=wearable_adjustment,
        cgm_adjustment=cgm_adjustment,
        genetic_adjustment=genetic_adjustment,
        evidence_readiness=evidence_readiness,
        budget_adjustment=budget_adjustment,
        safety_adjustment=safety_adjustment,
        conservative_adjustment=conservative_adjustment,
        learned_effect_bonus=0.0,
        applied_signals=sorted(
            [
                *symptom_signals,
                *laboratory_signals,
                *lifestyle_signals,
                *dietary_signals,
                *wearable_signals,
                *cgm_signals,
                *genetic_signals,
            ],
            key=lambda signal: (signal.source, signal.rule_id, signal.code),
        ),
        total=total,
    )


def _base_signal(
    *,
    source: str,
    code: str,
    observed_value: float | str,
    points: float,
    rule_id: str,
) -> CandidateScoreSignal:
    registry = _candidate_signal_registry()
    return CandidateScoreSignal(
        source=source,
        code=code,
        observed_value=observed_value,
        points=points,
        rule_id=rule_id,
        scoring_version=registry.scoring_version,
        reference_ids=[registry.policy_reference_id],
        claim_ids=[registry.policy_claim_id],
        limitation=(
            "Deterministic candidate-ordering context only; not diagnosis, dose advice, "
            "or efficacy probability."
        ),
    )


def _rule_signal(
    *,
    rule: CandidateSignalRuleBase,
    source: str,
    code: str,
    observed_value: float | str,
    points: float,
    unit: str | None = None,
) -> CandidateScoreSignal:
    return CandidateScoreSignal(
        source=source,
        code=code,
        observed_value=observed_value,
        unit=unit,
        points=round(points, 6),
        rule_id=rule.rule_id,
        scoring_version=_candidate_signal_registry().scoring_version,
        reference_ids=list(rule.reference_ids),
        claim_ids=list(rule.claim_ids),
        limitation=rule.limitation,
    )


def _symptom_signals(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> list[CandidateScoreSignal]:
    registry = _candidate_signal_registry()
    return [
        _base_signal(
            source="symptom",
            code=code,
            observed_value=intake.symptom_severity_by_code[code].value,
            points=registry.symptom_points_per_match,
            rule_id=registry.symptom_rule_id,
        )
        for code in sorted(set(item.supported_symptoms) & intake.symptom_set)
    ]


def _lifestyle_signals(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> list[CandidateScoreSignal]:
    registry = _candidate_signal_registry()
    observed_values: dict[str, float | str] = {
        "sleep_deficit": intake.normalized_lifestyle.sleep_hours
        if intake.normalized_lifestyle.sleep_hours is not None
        else "derived",
        "high_stress": intake.normalized_lifestyle.stress_level
        if intake.normalized_lifestyle.stress_level is not None
        else "derived",
        "low_activity": intake.normalized_lifestyle.activity_level.value,
    }
    return [
        _base_signal(
            source="lifestyle",
            code=code,
            observed_value=observed_values.get(code, "present"),
            points=registry.lifestyle_signal_points_per_match,
            rule_id=registry.lifestyle_rule_id,
        )
        for code in sorted(set(item.preferred_signals) & intake.signal_flags)
    ]


def _rule_applies_to_item_and_goal(
    rule: CandidateSignalRuleBase,
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> bool:
    return rule.ingredient_key == item.key and bool(set(rule.goal_keys) & intake.goal_set)


def _laboratory_signals(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> list[CandidateScoreSignal]:
    signals: list[CandidateScoreSignal] = []
    for rule in _candidate_signal_registry().laboratory_rules:
        if not _rule_applies_to_item_and_goal(rule, item, intake):
            continue
        matched_codes = sorted(
            code
            for code in rule.observation_codes
            if intake.laboratory_range_status_by_code.get(code) == rule.range_status
        )
        if not matched_codes:
            continue
        code = matched_codes[0]
        observation = intake.latest_laboratory_observation_by_code[code]
        signals.append(
            _rule_signal(
                rule=rule,
                source="laboratory",
                code=code,
                observed_value=observation.value,
                unit=observation.unit,
                points=rule.points,
            )
        )
    return signals


def _dietary_signals(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> list[CandidateScoreSignal]:
    signals: list[CandidateScoreSignal] = []
    for rule in _candidate_signal_registry().dietary_rules:
        if not _rule_applies_to_item_and_goal(rule, item, intake):
            continue
        matches = sorted(set(rule.dietary_patterns) & intake.dietary_pattern_set)
        if matches:
            signals.append(
                _rule_signal(
                    rule=rule,
                    source="dietary_pattern",
                    code=matches[0],
                    observed_value=matches[0],
                    points=rule.points,
                )
            )
    return signals


def _numeric_below_points(
    rule: NumericCandidateSignalRule,
    value: float,
) -> float:
    return min(rule.max_points, max(0.0, rule.threshold - value) * rule.points_per_unit)


def _wearable_signals(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> list[CandidateScoreSignal]:
    snapshot = intake.sensor_genetic_snapshot
    if snapshot is None or not snapshot.wearable_available:
        return []
    signals: list[CandidateScoreSignal] = []
    for rule in _candidate_signal_registry().wearable_rules:
        if not _rule_applies_to_item_and_goal(rule, item, intake):
            continue
        value = getattr(snapshot, rule.metric)
        if value is None:
            continue
        points = _numeric_below_points(rule, float(value))
        if points > 0:
            signals.append(
                _rule_signal(
                    rule=rule,
                    source="wearable",
                    code=rule.metric,
                    observed_value=float(value),
                    unit="hours" if rule.metric == "sleep_hours" else None,
                    points=points,
                )
            )
    return signals


def _cgm_signals(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> list[CandidateScoreSignal]:
    snapshot = intake.sensor_genetic_snapshot
    if snapshot is None or not snapshot.cgm_available:
        return []
    signals: list[CandidateScoreSignal] = []
    for rule in _candidate_signal_registry().cgm_rules:
        if not _rule_applies_to_item_and_goal(rule, item, intake):
            continue
        if rule.requires_nonpregnant and intake.request.user_profile.pregnant:
            continue
        if (
            snapshot.time_in_range_low_mg_dl != rule.range_low_mg_dl
            or snapshot.time_in_range_high_mg_dl != rule.range_high_mg_dl
        ):
            continue
        if not (set(rule.condition_keys) & intake.condition_set):
            continue
        value = getattr(snapshot, rule.metric)
        if value is None:
            continue
        points = _numeric_below_points(rule, float(value))
        if points > 0:
            signals.append(
                _rule_signal(
                    rule=rule,
                    source="cgm",
                    code=rule.metric,
                    observed_value=float(value),
                    unit="percent",
                    points=points,
                )
            )
    return signals


def _genetic_signals(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> list[CandidateScoreSignal]:
    snapshot = intake.sensor_genetic_snapshot
    if snapshot is None or not snapshot.genetic_available:
        return []
    signals: list[CandidateScoreSignal] = []
    for rule in _candidate_signal_registry().genetic_rules:
        if not _rule_applies_to_item_and_goal(rule, item, intake):
            continue
        matches = sorted(set(rule.genetic_tags) & set(snapshot.genetic_tags))
        if matches:
            signals.append(
                _rule_signal(
                    rule=rule,
                    source="genetic",
                    code=matches[0],
                    observed_value=matches[0],
                    points=rule.points,
                )
            )
    return signals


def _candidate_signal_registry() -> CandidateSignalScoringRegistry:
    registry = load_runtime_knowledge_db().candidate_signal_scoring
    if registry is None:
        raise ValueError("runtime candidate signal scoring registry is missing")
    return registry


def estimate_follow_up_window_days(intake: NormalizedIntake) -> int:
    if intake.request.input_availability.cgm:
        return 10
    if intake.request.input_availability.wearable:
        return 14
    return 21


def _evidence_readiness_score(item: IngredientCatalogItem, intake: NormalizedIntake) -> float:
    score = 2.0
    if intake.sensor_genetic_snapshot is not None:
        if intake.request.input_availability.survey:
            score += 2.0
        return score
    if item.follow_up_focus == "post_meal_response" and intake.request.input_availability.cgm:
        score += 5.0
    elif item.follow_up_focus == "sleep_quality" and intake.request.input_availability.wearable:
        score += 4.0
    elif (
        item.follow_up_focus == "activity_and_heart_metrics"
        and intake.request.input_availability.wearable
        and any(goal.value == "heart_health" for goal in intake.goal_set)
    ):
        score += 4.0
    elif intake.request.input_availability.survey:
        score += 2.0
    score += _cgm_evidence_bonus(item, intake)
    score += _genetic_evidence_bonus(item, intake)
    return score


def _budget_adjustment(item_budget: str, user_budget: str) -> float:
    if user_budget == "low":
        return {"low": 2.0, "medium": -1.0, "high": -5.0}[item_budget]
    if user_budget == "medium":
        return {"low": 1.0, "medium": 1.0, "high": -2.0}[item_budget]
    return {"low": 0.0, "medium": 1.0, "high": 1.0}[item_budget]


def _conservative_adjustment(
    conservative_profile: str,
    intake: NormalizedIntake,
    safety_review: bool,
) -> float:
    if conservative_profile == "baseline":
        base_adjustment = 1.0
    elif conservative_profile == "interaction_sensitive":
        base_adjustment = -1.0
    else:
        base_adjustment = 0.0

    if not safety_review:
        return base_adjustment

    if conservative_profile == "baseline":
        safety_adjustment = 3.0
    elif conservative_profile == "interaction_sensitive":
        safety_adjustment = -4.0
    else:
        has_review_risk = intake.request.user_profile.pregnant or bool(intake.condition_set)
        safety_adjustment = -1.0 if has_review_risk else 0.0

    return base_adjustment + safety_adjustment


def _genetic_evidence_bonus(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> float:
    if not intake.request.input_availability.genetic:
        return 0.0

    if item.key == "vitamin_d3":
        bonus = 0.0
        if "genetic_micronutrient_context" in intake.signal_flags:
            bonus += 8.0
        if "genetic_low_sun_context" in intake.signal_flags:
            bonus += 4.0
        if "genetic_bone_context" in intake.signal_flags:
            bonus += 2.0
        return bonus
    if item.key == "calcium_citrate" and "genetic_bone_context" in intake.signal_flags:
        return 4.0
    if item.key == "soluble_fiber" and "genetic_glycemic_context" in intake.signal_flags:
        return 2.0
    if item.key == "soluble_fiber" and "genetic_gut_context" in intake.signal_flags:
        return 2.0
    if item.key == "zinc" and "genetic_immunity_context" in intake.signal_flags:
        return 1.0
    if (
        item.key == "vitamin_b_complex"
        and "genetic_energy_metabolism_context" in intake.signal_flags
    ):
        return 4.0
    if (
        item.key == "coq10"
        and "genetic_cardiometabolic_context" in intake.signal_flags
        and RecommendationGoal.HEART_HEALTH in intake.goal_set
    ):
        return 2.0
    if item.key == "omega3" and "genetic_cardiometabolic_context" in intake.signal_flags:
        return 10.0
    if item.key == "l_theanine" and "genetic_recovery_context" in intake.signal_flags:
        return 4.0
    if (
        item.key == "magnesium_glycinate"
        and "genetic_recovery_context" in intake.signal_flags
    ):
        return 6.0
    return 0.0


def genetic_context_note(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> str | None:
    if not intake.request.input_availability.genetic:
        return None
    if intake.sensor_genetic_snapshot is not None:
        signals = _genetic_signals(item, intake)
        if not signals:
            return None
        signal = signals[0]
        return (
            f" Consent-authorized genetic context tag {signal.code} added bounded "
            "candidate-ordering "
            f"points under {signal.rule_id}; it was not treated as a diagnosis."
        )

    if item.key == "vitamin_d3":
        if (
            "genetic_bone_context" in intake.signal_flags
            and "genetic_low_sun_context" in intake.signal_flags
        ):
            return (
                " Available genetic context reinforced bone-mineral support confidence "
                "for low sun exposure."
            )
        if "genetic_bone_context" in intake.signal_flags:
            return " Available genetic context reinforced bone-mineral support confidence."
        if "genetic_low_sun_context" in intake.signal_flags:
            return (
                " Available genetic context reinforced micronutrient support confidence "
                "for low sun exposure."
            )
        if "genetic_micronutrient_context" in intake.signal_flags:
            return " Available genetic context reinforced micronutrient support confidence."
    if item.key == "calcium_citrate" and "genetic_bone_context" in intake.signal_flags:
        return " Available genetic context reinforced bone-mineral support confidence."
    if item.key == "soluble_fiber" and "genetic_glycemic_context" in intake.signal_flags:
        return " Available genetic context reinforced glycemic-response support confidence."
    if item.key == "soluble_fiber" and "genetic_gut_context" in intake.signal_flags:
        return " Available genetic context reinforced gut-resilience support confidence."
    if item.key == "zinc" and "genetic_immunity_context" in intake.signal_flags:
        return " Available genetic context reinforced immune-micronutrient support confidence."
    if (
        item.key == "vitamin_b_complex"
        and "genetic_energy_metabolism_context" in intake.signal_flags
    ):
        return " Available genetic context reinforced energy-metabolism support confidence."
    if (
        item.key == "coq10"
        and "genetic_cardiometabolic_context" in intake.signal_flags
        and RecommendationGoal.HEART_HEALTH in intake.goal_set
    ):
        return " Available genetic context reinforced cardiometabolic energy support confidence."
    if item.key == "omega3" and "genetic_cardiometabolic_context" in intake.signal_flags:
        return " Available genetic context reinforced cardiometabolic support confidence."
    if item.key == "l_theanine" and "genetic_recovery_context" in intake.signal_flags:
        return " Available genetic context reinforced neuro-recovery support confidence."
    if (
        item.key == "magnesium_glycinate"
        and "genetic_recovery_context" in intake.signal_flags
    ):
        return " Available genetic context reinforced recovery support confidence."
    return None


def wearable_context_note(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> str | None:
    if not intake.request.input_availability.wearable:
        return None

    if (
        item.follow_up_focus in {"sleep_quality", "calmness_and_sleep_onset"}
        and "wearable_sleep_context" in intake.signal_flags
    ):
        return " Available wearable context reinforced sleep-pattern follow-up confidence."
    if (
        item.follow_up_focus
        in {"daytime_energy", "energy_and_activity", "activity_and_heart_metrics"}
        and "wearable_activity_context" in intake.signal_flags
    ):
        return " Available wearable context reinforced activity-pattern follow-up confidence."
    return None


def cgm_context_note(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> str | None:
    if not intake.request.input_availability.cgm:
        return None

    if item.key == "berberine" and "cgm_post_meal_spike_context" in intake.signal_flags:
        return " Available CGM context reinforced post-meal glucose support confidence."
    if item.key == "soluble_fiber" and "cgm_glucose_context" in intake.signal_flags:
        return " Available CGM context preserved blood-glucose follow-up visibility."
    return None


def _cgm_evidence_bonus(
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
) -> float:
    if not intake.request.input_availability.cgm:
        return 0.0

    if (
        item.key == "berberine"
        and intake.goal_set == {RecommendationGoal.BLOOD_GLUCOSE}
        and "cgm_post_meal_spike_context" in intake.signal_flags
    ):
        return 8.0
    return 0.0
