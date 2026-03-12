import re

from wellnessbox_rnd.domain.catalog import canonicalize_catalog_term, get_catalog_index
from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.domain.models import SafetyRuleMetadata
from wellnessbox_rnd.knowledge.runtime_db import (
    DoseLimitRecord,
    RuntimeKnowledgeDB,
    build_citations_for_rule,
    find_triggered_interaction_rules,
    load_runtime_knowledge_db,
)
from wellnessbox_rnd.safety.rules import get_safety_rule_set
from wellnessbox_rnd.schemas.recommendation import (
    RecommendationStatus,
    RuleReference,
    SafetySummary,
    Severity,
    SupplementInput,
)

_DOSE_PATTERN = re.compile(r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>iu|mg|mcg|g)\b", re.IGNORECASE)


def assess_safety(intake: NormalizedIntake) -> SafetySummary:
    rules = get_safety_rule_set()
    runtime_knowledge_db = load_runtime_knowledge_db()
    warnings: list[str] = []
    blocked_reasons: list[str] = []
    excluded_ingredients: set[str] = set(intake.avoid_ingredient_set)
    rule_refs: list[RuleReference] = []

    for input_rule in rules.input_requirements:
        if _required_input_missing(input_rule.input_key, intake):
            blocked_reasons.append(input_rule.blocked_reason)
            rule_refs.append(_build_rule_ref(input_rule.metadata))

    for medication_rule in rules.medication_rules:
        if set(medication_rule.medications).intersection(intake.medication_set):
            excluded_ingredients.update(medication_rule.excluded_ingredients)
            _append_unique_text(warnings, medication_rule.metadata.warning_text)
            rule_refs.append(_build_rule_ref(medication_rule.metadata))

    if intake.request.user_profile.pregnant and rules.pregnancy_rule is not None:
        excluded_ingredients.update(rules.pregnancy_rule.excluded_ingredients)
        _append_unique_text(warnings, rules.pregnancy_rule.metadata.warning_text)
        rule_refs.append(_build_rule_ref(rules.pregnancy_rule.metadata))

    for condition_rule in rules.condition_rules:
        if set(condition_rule.conditions).intersection(intake.condition_set):
            excluded_ingredients.update(condition_rule.excluded_ingredients)
            _append_unique_text(warnings, condition_rule.metadata.warning_text)
            rule_refs.append(_build_rule_ref(condition_rule.metadata))

    for dose_limit, observed_amount in _find_triggered_dose_limits(intake, runtime_knowledge_db):
        excluded_ingredients.add(dose_limit.ingredient_key)
        triggered_warning = _format_dose_limit_warning(
            warning_text=dose_limit.warning_text,
            observed_amount=observed_amount,
            max_daily_amount=dose_limit.max_daily_amount,
            unit=dose_limit.unit,
        )
        _append_unique_text(warnings, triggered_warning)
        if dose_limit.severity == Severity.BLOCKER:
            _append_unique_text(blocked_reasons, triggered_warning)
        rule_refs.append(
            RuleReference(
                rule_id=dose_limit.rule_id,
                message=dose_limit.message,
                severity=dose_limit.severity,
                source=dose_limit.source_kind,
                reference_ids=dose_limit.reference_ids,
                claim_ids=dose_limit.claim_ids,
                citations=build_citations_for_rule(
                    runtime_knowledge_db,
                    reference_ids=dose_limit.reference_ids,
                    claim_ids=dose_limit.claim_ids,
                ),
            )
        )

    duplicate_ingredients = _recognized_current_duplicates(intake)
    if (
        duplicate_ingredients
        and rules.duplicate_policy == "exclude"
        and rules.duplicate_overlap_rule is not None
    ):
        excluded_ingredients.update(duplicate_ingredients)
        _append_unique_text(warnings, rules.duplicate_overlap_rule.metadata.warning_text)
        rule_refs.append(_build_rule_ref(rules.duplicate_overlap_rule.metadata))

    for knowledge_rule in find_triggered_interaction_rules(
        runtime_knowledge_db,
        medication_keys=intake.medication_set,
        ingredient_keys=intake.current_ingredient_set,
    ):
        matched_ingredients = sorted(
            set(knowledge_rule.ingredient_keys).intersection(intake.current_ingredient_set)
        )
        excluded_ingredients.update(matched_ingredients)
        _append_unique_text(warnings, knowledge_rule.warning_text)
        if knowledge_rule.severity == Severity.BLOCKER:
            _append_unique_text(blocked_reasons, knowledge_rule.warning_text)
        rule_refs.append(
            RuleReference(
                rule_id=knowledge_rule.rule_id,
                message=knowledge_rule.message,
                severity=knowledge_rule.severity,
                source=knowledge_rule.source_kind,
                reference_ids=knowledge_rule.reference_ids,
                claim_ids=knowledge_rule.claim_ids,
                citations=build_citations_for_rule(
                    runtime_knowledge_db,
                    reference_ids=knowledge_rule.reference_ids,
                    claim_ids=knowledge_rule.claim_ids,
                ),
            )
        )

    status = _derive_status(rule_refs, blocked_reasons)
    return SafetySummary(
        status=status,
        warnings=warnings,
        blocked_reasons=blocked_reasons,
        excluded_ingredients=sorted(excluded_ingredients),
        rule_refs=rule_refs,
    )


def _required_input_missing(input_key: str, intake: NormalizedIntake) -> bool:
    value = getattr(intake.request.input_availability, input_key, None)
    return value is False


def _recognized_current_duplicates(intake: NormalizedIntake) -> set[str]:
    catalog_keys = set(get_catalog_index())
    return intake.current_ingredient_set.intersection(catalog_keys)


def _build_rule_ref(metadata: SafetyRuleMetadata) -> RuleReference:
    return RuleReference(
        rule_id=metadata.rule_id,
        message=metadata.message,
        severity=metadata.severity,
    )


def _append_unique_text(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _derive_status(
    rule_refs: list[RuleReference],
    blocked_reasons: list[str],
) -> RecommendationStatus:
    if blocked_reasons or any(rule.severity == Severity.BLOCKER for rule in rule_refs):
        return RecommendationStatus.BLOCKED
    if any(rule.severity == Severity.WARNING for rule in rule_refs):
        return RecommendationStatus.NEEDS_REVIEW
    return RecommendationStatus.OK


def _find_triggered_dose_limits(
    intake: NormalizedIntake,
    runtime_knowledge_db: RuntimeKnowledgeDB,
) -> list[tuple[DoseLimitRecord, float]]:
    limits_by_ingredient = {
        record.ingredient_key: record
        for record in runtime_knowledge_db.dose_limits
        if record.max_daily_amount is not None and record.unit
    }
    observed_amounts: dict[str, float] = {}

    for supplement in intake.request.current_supplements:
        for ingredient_key, normalized_amount in _extract_supplement_dose_observations(
            supplement=supplement,
            limits_by_ingredient=limits_by_ingredient,
        ):
            observed_amounts[ingredient_key] = (
                observed_amounts.get(ingredient_key, 0.0) + normalized_amount
            )

    triggered: list[tuple[DoseLimitRecord, float]] = []
    for ingredient_key, observed_amount in observed_amounts.items():
        dose_limit = limits_by_ingredient[ingredient_key]
        if observed_amount > float(dose_limit.max_daily_amount):
            triggered.append((dose_limit, observed_amount))
    return triggered


def _parse_supplement_amount(value: str) -> tuple[float, str] | None:
    match = _DOSE_PATTERN.search(value)
    if match is None:
        return None
    return float(match.group("amount")), match.group("unit").lower()


def _extract_supplement_dose_observations(
    *,
    supplement: SupplementInput,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> list[tuple[str, float]]:
    structured_dose_observations = _extract_structured_supplement_dose_observations(
        supplement=supplement,
        limits_by_ingredient=limits_by_ingredient,
    )
    if structured_dose_observations:
        return structured_dose_observations

    ingredient_observations: list[tuple[str, float]] = []
    for ingredient_text in supplement.ingredients:
        observation = _build_dose_observation(
            source_text=ingredient_text,
            limits_by_ingredient=limits_by_ingredient,
            evidence_source="ingredient_line",
        )
        if observation is None:
            continue
        ingredient_observations.append(observation)

    if ingredient_observations:
        return ingredient_observations

    title_observation = _build_dose_observation(
        source_text=supplement.name,
        limits_by_ingredient=limits_by_ingredient,
        evidence_source="title",
    )
    if title_observation is None:
        return []
    return [title_observation]


def _extract_structured_supplement_dose_observations(
    *,
    supplement: SupplementInput,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> list[tuple[str, float]]:
    if not supplement.dose:
        return []

    candidate_ingredient_keys = {
        canonicalize_catalog_term(ingredient_text)
        for ingredient_text in supplement.ingredients
    }
    candidate_ingredient_keys = {
        ingredient_key
        for ingredient_key in candidate_ingredient_keys
        if ingredient_key and ingredient_key in limits_by_ingredient
    }
    if not candidate_ingredient_keys:
        title_ingredient_key = canonicalize_catalog_term(supplement.name)
        if title_ingredient_key and title_ingredient_key in limits_by_ingredient:
            candidate_ingredient_keys = {title_ingredient_key}

    if len(candidate_ingredient_keys) != 1:
        return []

    ingredient_key = next(iter(candidate_ingredient_keys))
    if not _dose_evidence_source_allowed(
        limits_by_ingredient[ingredient_key],
        "structured_dose",
    ):
        return []

    parsed_dose = _parse_supplement_amount(supplement.dose)
    if parsed_dose is None:
        return []

    amount, unit = parsed_dose
    normalized_amount = _convert_amount_unit(
        amount=amount,
        unit=unit,
        target_unit=limits_by_ingredient[ingredient_key].unit,
        ingredient_key=ingredient_key,
    )
    if normalized_amount is None:
        return []
    return [(ingredient_key, normalized_amount)]


def _build_dose_observation(
    *,
    source_text: str,
    limits_by_ingredient: dict[str, DoseLimitRecord],
    evidence_source: str,
) -> tuple[str, float] | None:
    ingredient_key = canonicalize_catalog_term(source_text)
    if ingredient_key is None or ingredient_key not in limits_by_ingredient:
        return None
    if not _dose_evidence_source_allowed(limits_by_ingredient[ingredient_key], evidence_source):
        return None

    parsed_dose = _parse_supplement_amount(source_text)
    if parsed_dose is None:
        return None

    amount, unit = parsed_dose
    normalized_amount = _convert_amount_unit(
        amount=amount,
        unit=unit,
        target_unit=limits_by_ingredient[ingredient_key].unit,
        ingredient_key=ingredient_key,
    )
    if normalized_amount is None:
        return None
    return ingredient_key, normalized_amount


def _dose_evidence_source_allowed(dose_limit: DoseLimitRecord, evidence_source: str) -> bool:
    return evidence_source in dose_limit.allowed_evidence_sources


def _convert_amount_unit(
    *,
    amount: float,
    unit: str,
    target_unit: str | None,
    ingredient_key: str,
) -> float | None:
    if target_unit is None:
        return None
    normalized_target = target_unit.lower()
    normalized_unit = unit.lower()
    if normalized_unit == normalized_target:
        return amount

    mass_scale_to_mg = {
        "mcg": 0.001,
        "mg": 1.0,
        "g": 1000.0,
    }
    if normalized_unit in mass_scale_to_mg and normalized_target in mass_scale_to_mg:
        source_mg = amount * mass_scale_to_mg[normalized_unit]
        return source_mg / mass_scale_to_mg[normalized_target]

    if ingredient_key == "vitamin_d3":
        if normalized_unit == "mcg" and normalized_target == "iu":
            return amount * 40.0
        if normalized_unit == "iu" and normalized_target == "mcg":
            return amount / 40.0
    return None


def _format_dose_limit_warning(
    *,
    warning_text: str,
    observed_amount: float,
    max_daily_amount: float | None,
    unit: str | None,
) -> str:
    if max_daily_amount is None or unit is None:
        return warning_text
    observed_display = f"{observed_amount:g}"
    limit_display = f"{max_daily_amount:g}"
    return (
        f"{warning_text} Estimated current intake was {observed_display} {unit}"
        f" against a structured limit of {limit_display} {unit}."
    )
