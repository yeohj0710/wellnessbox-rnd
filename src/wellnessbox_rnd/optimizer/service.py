from pathlib import Path

from wellnessbox_rnd.domain.catalog import get_catalog_index, list_catalog_items
from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.domain.models import IngredientCatalogItem
from wellnessbox_rnd.efficacy.service import (
    cgm_context_note,
    genetic_context_note,
    score_candidate,
    wearable_context_note,
)
from wellnessbox_rnd.knowledge.goal_priors import get_goal_prior_index
from wellnessbox_rnd.models import (
    build_runtime_efficacy_feature_dict,
    load_efficacy_model_artifact,
    predict_effect_proxy_from_feature_dict,
    validate_efficacy_model_artifact_for_runtime,
)
from wellnessbox_rnd.schemas.recommendation import (
    CandidatePoolExclusion,
    CandidatePoolItem,
    CandidatePoolTrace,
    CandidatePreselectionScore,
    CandidateRankingSnapshot,
    CandidateScoreBreakdown,
    LearnedRerankingDecision,
    RecommendationCandidate,
    RecommendationGoal,
    RecommendationReasonBreakdown,
    RecommendationReasonEvidenceLink,
    RecommendationReasonInputSignal,
    RecommendationReasonScoreTerm,
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
    selected, _, _, _ = select_recommendations_with_diagnostics(
        intake,
        safety_summary,
        enable_learned_reranking=enable_learned_reranking,
        learned_efficacy_artifact_path=learned_efficacy_artifact_path,
    )
    return selected


def select_recommendations_with_diagnostics(
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    *,
    enable_learned_reranking: bool = False,
    learned_efficacy_artifact_path: str | None = None,
) -> tuple[
    list[RecommendationCandidate],
    LearnedRerankingDecision,
    CandidateRankingSnapshot,
    list[CandidatePreselectionScore],
]:
    candidates: list[RecommendationCandidate] = []
    safety_review = safety_summary.status == RecommendationStatus.NEEDS_REVIEW
    _, _, post_safety_pool = _partition_candidate_pool(
        intake=intake,
        safety_summary=safety_summary,
    )
    catalog_by_key = get_catalog_index()

    for pool_item in post_safety_pool:
        item = catalog_by_key[pool_item.ingredient_key]

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
                reason_breakdown=build_recommendation_reason_breakdown(
                    item=item,
                    intake=intake,
                    breakdown=breakdown,
                    optimizer_rule_ids=["OPT-BASELINE-001"],
                    safety_summary=safety_summary,
                ),
                follow_up_focus=item.follow_up_focus,
            )
        )

    candidates, learned_decision = _apply_learned_efficacy_reranking(
        intake=intake,
        safety_summary=safety_summary,
        candidates=candidates,
        enable_learned_reranking=enable_learned_reranking,
        learned_efficacy_artifact_path=learned_efficacy_artifact_path,
    )
    ranking_snapshot, preselection_scores = _build_candidate_ranking_diagnostics(
        candidates
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

    return selected, learned_decision, ranking_snapshot, preselection_scores


def _build_candidate_ranking_diagnostics(
    candidates: list[RecommendationCandidate],
) -> tuple[CandidateRankingSnapshot, list[CandidatePreselectionScore]]:
    catalog_by_key = get_catalog_index()
    ranked = sorted(
        candidates,
        key=lambda item: (
            -_marginal_selection_score(item, set()),
            -item.score_breakdown.total,
            -item.score_breakdown.goal_alignment,
            item.ingredient_key,
        ),
    )
    preselection_scores = [
        CandidatePreselectionScore(
            rank=index,
            ingredient_key=candidate.ingredient_key,
            expected_support_goals=candidate.expected_support_goals,
            rule_refs=candidate.rule_refs,
            selection_score=round(_marginal_selection_score(candidate, set()), 6),
            score_total=candidate.score_breakdown.total,
            goal_alignment=candidate.score_breakdown.goal_alignment,
            catalog_priority=catalog_by_key[candidate.ingredient_key].default_priority,
            score_breakdown=candidate.score_breakdown,
            reason_breakdown=candidate.reason_breakdown,
        )
        for index, candidate in enumerate(ranked, start=1)
    ]
    if not ranked:
        return (
            CandidateRankingSnapshot(
                calculation_version="candidate_ranking_snapshot_v1",
                candidate_count=0,
            ),
            preselection_scores,
        )
    top_score = round(_marginal_selection_score(ranked[0], set()), 6)
    if len(ranked) == 1:
        return (
            CandidateRankingSnapshot(
                calculation_version="candidate_ranking_snapshot_v1",
                candidate_count=1,
                top_candidate_key=ranked[0].ingredient_key,
                top_selection_score=top_score,
            ),
            preselection_scores,
        )
    runner_up_score = round(_marginal_selection_score(ranked[1], set()), 6)
    return (
        CandidateRankingSnapshot(
            calculation_version="candidate_ranking_snapshot_v1",
            candidate_count=len(ranked),
            top_candidate_key=ranked[0].ingredient_key,
            runner_up_candidate_key=ranked[1].ingredient_key,
            top_selection_score=top_score,
            runner_up_selection_score=runner_up_score,
            top_two_score_margin=round(top_score - runner_up_score, 6),
        ),
        preselection_scores,
    )


def build_candidate_pool_trace(
    *,
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
    selected_candidates: list[RecommendationCandidate],
    preselection_scores: list[CandidatePreselectionScore],
    global_blocked: bool | None = None,
) -> CandidatePoolTrace:
    pre_safety, excluded, post_safety = _partition_candidate_pool(
        intake=intake,
        safety_summary=safety_summary,
    )

    is_global_blocked = (
        safety_summary.status == RecommendationStatus.BLOCKED
        if global_blocked is None
        else global_blocked
    )
    return CandidatePoolTrace(
        pre_safety_candidates=pre_safety,
        excluded_candidates=excluded,
        post_safety_candidates=post_safety,
        preselection_scores=preselection_scores,
        selected_candidate_keys=(
            [] if is_global_blocked else [item.ingredient_key for item in selected_candidates]
        ),
        applied_safety_rule_ids=sorted({item.rule_id for item in safety_summary.rule_refs}),
        global_blocked=is_global_blocked,
    )


def _partition_candidate_pool(
    *,
    intake: NormalizedIntake,
    safety_summary: SafetySummary,
) -> tuple[list[CandidatePoolItem], list[CandidatePoolExclusion], list[CandidatePoolItem]]:
    pre_safety: list[CandidatePoolItem] = []
    excluded: list[CandidatePoolExclusion] = []
    post_safety: list[CandidatePoolItem] = []
    safety_excluded = set(safety_summary.excluded_ingredients)

    for item in list_catalog_items():
        matched_goals = sorted(
            set(item.supported_goals) & intake.goal_set,
            key=lambda goal: goal.value,
        )
        if not matched_goals:
            continue
        pool_item = CandidatePoolItem(
            ingredient_key=item.key,
            display_name=item.display_name,
            matched_goals=matched_goals,
        )
        pre_safety.append(pool_item)
        reasons: list[str] = []
        if item.key in safety_excluded:
            reasons.append("safety_summary_excluded")
        if item.key in intake.avoid_ingredient_set:
            reasons.append("user_avoidance")
        if item.key in intake.current_ingredient_set:
            reasons.append("current_regimen_overlap")
        if reasons:
            excluded.append(
                CandidatePoolExclusion(
                    **pool_item.model_dump(mode="python"),
                    exclusion_reasons=reasons,
                )
            )
        else:
            post_safety.append(pool_item)

    return pre_safety, excluded, post_safety


def build_recommendation_reason_breakdown(
    *,
    item: IngredientCatalogItem,
    intake: NormalizedIntake,
    breakdown: CandidateScoreBreakdown,
    optimizer_rule_ids: list[str],
    safety_summary: SafetySummary,
) -> RecommendationReasonBreakdown:
    fallback_safety_limitation = (
        "Safety-review status applies a conservative ranking adjustment; "
        "it is not efficacy evidence."
    )
    applied_by_term: dict[str, list[str]] = {}
    source_to_term = {
        "symptom": "symptom_alignment",
        "laboratory": "laboratory_alignment",
        "lifestyle": "lifestyle_alignment",
        "dietary_pattern": "dietary_alignment",
        "wearable": "wearable_adjustment",
        "cgm": "cgm_adjustment",
        "genetic": "genetic_adjustment",
    }
    input_signals = [
        RecommendationReasonInputSignal(
            source="goal",
            code=goal.value,
            observed_value="requested",
        )
        for goal in sorted(
            set(item.supported_goals) & intake.goal_set,
            key=lambda goal: goal.value,
        )
    ]
    for signal in breakdown.applied_signals:
        input_signals.append(
            RecommendationReasonInputSignal(
                source=signal.source,
                code=signal.code,
                observed_value=signal.observed_value,
                unit=signal.unit,
            )
        )
        applied_by_term.setdefault(source_to_term[signal.source], []).append(signal.rule_id)
    safety_reason_rules = (
        list(safety_summary.rule_refs) if breakdown.safety_adjustment != 0.0 else []
    )
    if breakdown.safety_adjustment != 0.0:
        if safety_reason_rules:
            for rule in safety_reason_rules:
                input_signals.append(
                    RecommendationReasonInputSignal(
                        source="safety",
                        code=rule.rule_id,
                        observed_value=safety_summary.status.value,
                    )
                )
                applied_by_term.setdefault("safety_adjustment", []).append(rule.rule_id)
        else:
            input_signals.append(
                RecommendationReasonInputSignal(
                    source="safety",
                    code="safety_review_status",
                    observed_value=safety_summary.status.value,
                )
            )

    term_values = {
        "catalog_priority": item.default_priority,
        "goal_alignment": breakdown.goal_alignment,
        "symptom_alignment": breakdown.symptom_alignment,
        "lifestyle_alignment": breakdown.lifestyle_alignment,
        "laboratory_alignment": breakdown.laboratory_alignment,
        "dietary_alignment": breakdown.dietary_alignment,
        "wearable_adjustment": breakdown.wearable_adjustment,
        "cgm_adjustment": breakdown.cgm_adjustment,
        "genetic_adjustment": breakdown.genetic_adjustment,
        "evidence_readiness": breakdown.evidence_readiness,
        "budget_adjustment": breakdown.budget_adjustment,
        "safety_adjustment": breakdown.safety_adjustment,
        "conservative_adjustment": breakdown.conservative_adjustment,
        "learned_effect_bonus": breakdown.learned_effect_bonus,
    }
    baseline_terms = {
        "catalog_priority",
        "evidence_readiness",
        "budget_adjustment",
        "safety_adjustment",
        "conservative_adjustment",
    }
    score_terms = []
    for term, points in term_values.items():
        rule_ids = sorted(set(applied_by_term.get(term, [])))
        if term in baseline_terms:
            rule_ids = sorted(set(rule_ids) | {"OPT-BASELINE-001"})
        if term == "learned_effect_bonus" and "OPT-LEARNED-001" in optimizer_rule_ids:
            rule_ids = ["OPT-LEARNED-001"]
        score_terms.append(
            RecommendationReasonScoreTerm(
                term=term,
                points=points,
                rule_ids=rule_ids,
            )
        )

    goal_priors = get_goal_prior_index()
    reference_ids: set[str] = set()
    claim_ids: set[str] = set()
    limitations: set[str] = set()
    evidence_links: list[RecommendationReasonEvidenceLink] = []
    for goal in sorted(
        set(item.supported_goals) & intake.goal_set,
        key=lambda value: value.value,
    ):
        prior = goal_priors[(item.key, goal)]
        reference_ids.update(prior.reference_ids)
        claim_ids.update(prior.claim_ids)
        limitations.update(prior.limitations)
        evidence_links.append(
            RecommendationReasonEvidenceLink(
                evidence_source="goal_prior",
                code=goal.value,
                reference_ids=list(prior.reference_ids),
                claim_ids=list(prior.claim_ids),
                limitations=list(prior.limitations),
            )
        )
    signal_rule_ids: set[str] = set()
    for signal in breakdown.applied_signals:
        signal_rule_ids.add(signal.rule_id)
        reference_ids.update(signal.reference_ids)
        claim_ids.update(signal.claim_ids)
        limitations.add(signal.limitation)
        evidence_links.append(
            RecommendationReasonEvidenceLink(
                evidence_source="input_signal",
                code=signal.code,
                rule_id=signal.rule_id,
                reference_ids=list(signal.reference_ids),
                claim_ids=list(signal.claim_ids),
                limitations=[signal.limitation],
            )
        )

    safety_rule_ids: set[str] = set()
    if breakdown.safety_adjustment != 0.0:
        if safety_reason_rules:
            for rule in safety_reason_rules:
                safety_rule_ids.add(rule.rule_id)
                reference_ids.update(rule.reference_ids)
                claim_ids.update(rule.claim_ids)
                limitations.add(rule.message)
                evidence_links.append(
                    RecommendationReasonEvidenceLink(
                        evidence_source="safety_rule",
                        code=rule.rule_id,
                        rule_id=rule.rule_id,
                        reference_ids=list(rule.reference_ids),
                        claim_ids=list(rule.claim_ids),
                        limitations=[rule.message],
                    )
                )
        else:
            limitations.add(fallback_safety_limitation)
            evidence_links.append(
                RecommendationReasonEvidenceLink(
                    evidence_source="safety_rule",
                    code="safety_review_status",
                    rule_id="OPT-BASELINE-001",
                    limitations=[fallback_safety_limitation],
                )
            )

    return RecommendationReasonBreakdown(
        input_signals=input_signals,
        score_terms=score_terms,
        evidence_links=evidence_links,
        rule_ids=sorted(set(optimizer_rule_ids) | signal_rule_ids | safety_rule_ids),
        reference_ids=sorted(reference_ids),
        claim_ids=sorted(claim_ids),
        limitations=sorted(limitations),
        score_total=breakdown.total,
    )


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
    overlap_penalty = 4.0 * (len(candidate.expected_support_goals) - len(uncovered_goals))
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
) -> tuple[list[RecommendationCandidate], LearnedRerankingDecision]:
    if not enable_learned_reranking:
        return candidates, LearnedRerankingDecision(
            status="not_requested",
            requested=False,
            eligible=False,
            artifact_validated=False,
            learned_reranking_applied=False,
            deterministic_baseline_used=True,
            fallback_applied=False,
        )
    if not _eligible_for_learned_reranking(intake, safety_summary, candidates):
        return candidates, LearnedRerankingDecision(
            status="not_eligible",
            requested=True,
            eligible=False,
            artifact_validated=False,
            learned_reranking_applied=False,
            deterministic_baseline_used=True,
            fallback_applied=False,
            issues=["eligibility_policy_not_met"],
        )
    if learned_efficacy_artifact_path is None:
        return candidates, LearnedRerankingDecision(
            status="fallback_missing_path",
            requested=True,
            eligible=True,
            artifact_validated=False,
            learned_reranking_applied=False,
            deterministic_baseline_used=True,
            fallback_applied=True,
            issues=["artifact_path_not_supplied"],
        )

    artifact_path = Path(learned_efficacy_artifact_path)
    if not artifact_path.is_file():
        return candidates, LearnedRerankingDecision(
            status="fallback_missing_file",
            requested=True,
            eligible=True,
            artifact_validated=False,
            learned_reranking_applied=False,
            deterministic_baseline_used=True,
            fallback_applied=True,
            issues=["artifact_file_missing"],
        )

    try:
        artifact = load_efficacy_model_artifact(artifact_path)
    except (OSError, ValueError):
        return candidates, LearnedRerankingDecision(
            status="fallback_invalid_artifact",
            requested=True,
            eligible=True,
            artifact_validated=False,
            learned_reranking_applied=False,
            deterministic_baseline_used=True,
            fallback_applied=True,
            issues=["artifact_load_or_schema_failed"],
        )
    artifact_issues = validate_efficacy_model_artifact_for_runtime(artifact)
    if artifact_issues:
        return candidates, LearnedRerankingDecision(
            status="fallback_suspicious_artifact",
            requested=True,
            eligible=True,
            artifact_validated=False,
            learned_reranking_applied=False,
            deterministic_baseline_used=True,
            fallback_applied=True,
            issues=artifact_issues,
        )
    top_deterministic_total = max(candidate.score_breakdown.total for candidate in candidates)
    reranked: list[RecommendationCandidate] = []

    try:
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
                        "reason_breakdown": build_recommendation_reason_breakdown(
                            item=get_catalog_index()[candidate.ingredient_key],
                            intake=intake,
                            breakdown=updated_breakdown,
                            optimizer_rule_ids=updated_rule_refs,
                            safety_summary=safety_summary,
                        ),
                        "rationale": (
                            f"{candidate.rationale} A learned efficacy tie-breaker was "
                            "applied after deterministic safety filtering and only among "
                            "near-tied low-risk candidates."
                        ),
                    }
                )
            )
    except Exception:
        return candidates, LearnedRerankingDecision(
            status="fallback_artifact_runtime_error",
            requested=True,
            eligible=True,
            artifact_validated=True,
            learned_reranking_applied=False,
            deterministic_baseline_used=True,
            fallback_applied=True,
            issues=["artifact_prediction_failed"],
        )

    return reranked, LearnedRerankingDecision(
        status="applied",
        requested=True,
        eligible=True,
        artifact_validated=True,
        learned_reranking_applied=True,
        deterministic_baseline_used=False,
        fallback_applied=False,
    )


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
