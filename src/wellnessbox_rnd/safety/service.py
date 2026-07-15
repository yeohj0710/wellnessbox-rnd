import re

from wellnessbox_rnd.domain.catalog import (
    canonicalize_catalog_term,
    canonicalize_exact_catalog_term,
    get_catalog_index,
)
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
    DoseAmount,
    RecommendationStatus,
    RuleReference,
    SafetySummary,
    Severity,
    SupplementIngredientInput,
    SupplementInput,
    normalize_supplement_ingredient_name,
)

_DOSE_PATTERN = re.compile(
    r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>mcg|mg|ng|iu|g)\b",
    re.IGNORECASE,
)


def assess_safety(intake: NormalizedIntake) -> SafetySummary:
    rules = get_safety_rule_set()
    runtime_knowledge_db = load_runtime_knowledge_db()
    warnings: list[str] = []
    blocked_reasons: list[str] = []
    excluded_ingredients: set[str] = set(intake.avoid_ingredient_set)
    rule_refs: list[RuleReference] = []

    for risk_flag_rule in rules.risk_flag_rules:
        if set(risk_flag_rule.risk_flags).intersection(intake.risk_flag_set):
            _append_unique_text(blocked_reasons, risk_flag_rule.blocked_reason)
            _append_unique_text(warnings, risk_flag_rule.metadata.warning_text)
            rule_refs.append(_build_rule_ref(risk_flag_rule.metadata))

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

    for allergy_rule in rules.allergy_rules:
        if set(allergy_rule.allergies).intersection(intake.allergy_set):
            excluded_ingredients.update(allergy_rule.excluded_ingredients)
            _append_unique_text(warnings, allergy_rule.metadata.warning_text)
            rule_refs.append(_build_rule_ref(allergy_rule.metadata))

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

    for supplement in intake.normalized_current_supplements:
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
    ingredient_observations = _extract_ingredient_daily_dose_observations(
        supplement=supplement,
        limits_by_ingredient=limits_by_ingredient,
    )
    for ingredient in supplement.ingredients:
        if (
            isinstance(ingredient, SupplementIngredientInput)
            and ingredient.daily_dose is not None
        ):
            continue
        observation = _build_dose_observation(
            source_text=normalize_supplement_ingredient_name(ingredient),
            limits_by_ingredient=limits_by_ingredient,
            evidence_source="ingredient_line",
        )
        if observation is None:
            continue
        ingredient_observations.append(observation)

    if ingredient_observations:
        return ingredient_observations

    product_daily_dose_observation = _extract_product_daily_dose_observation(
        supplement=supplement,
        limits_by_ingredient=limits_by_ingredient,
    )
    if product_daily_dose_observation is not None:
        return [product_daily_dose_observation]

    title_observation = _build_dose_observation(
        source_text=supplement.name,
        limits_by_ingredient=limits_by_ingredient,
        evidence_source="title",
    )
    if title_observation is None:
        return []
    return [title_observation]


def _extract_ingredient_daily_dose_observations(
    *,
    supplement: SupplementInput,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> list[tuple[str, float]]:
    observations: list[tuple[str, float]] = []
    for ingredient in supplement.ingredients:
        if not isinstance(ingredient, SupplementIngredientInput):
            continue
        if ingredient.daily_dose is None:
            continue
        ingredient_key = canonicalize_catalog_term(ingredient.name)
        if ingredient_key is None or ingredient_key not in limits_by_ingredient:
            continue
        observation = _build_structured_dose_observation(
            ingredient_key=ingredient_key,
            dose=ingredient.daily_dose,
            limits_by_ingredient=limits_by_ingredient,
        )
        if observation is not None:
            observations.append(observation)
    return observations


def _extract_product_daily_dose_observation(
    *,
    supplement: SupplementInput,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> tuple[str, float] | None:
    ingredient_key = _single_product_dose_ingredient_key(
        supplement=supplement,
        limits_by_ingredient=limits_by_ingredient,
    )
    if ingredient_key is None:
        return None

    if supplement.daily_dose is not None:
        return _build_structured_dose_observation(
            ingredient_key=ingredient_key,
            dose=supplement.daily_dose,
            limits_by_ingredient=limits_by_ingredient,
        )
    if supplement.dose is None:
        return None

    parsed_dose = _parse_supplement_amount(supplement.dose)
    if parsed_dose is None:
        return None
    amount, unit = parsed_dose
    return _build_normalized_dose_observation(
        ingredient_key=ingredient_key,
        amount=amount,
        unit=unit,
        limits_by_ingredient=limits_by_ingredient,
    )


def _single_product_dose_ingredient_key(
    *,
    supplement: SupplementInput,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> str | None:
    declared_ingredient_keys = {
        canonicalize_exact_catalog_term(normalize_supplement_ingredient_name(ingredient))
        or normalize_supplement_ingredient_name(ingredient)
        for ingredient in supplement.ingredients
        if normalize_supplement_ingredient_name(ingredient)
    }
    if declared_ingredient_keys:
        if len(declared_ingredient_keys) != 1:
            return None
        ingredient_key = next(iter(declared_ingredient_keys))
        if ingredient_key not in limits_by_ingredient:
            return None
        return ingredient_key
    else:
        title_ingredient_key = canonicalize_exact_catalog_term(supplement.name)
        if title_ingredient_key and title_ingredient_key in limits_by_ingredient:
            return title_ingredient_key
    return None


def _build_structured_dose_observation(
    *,
    ingredient_key: str,
    dose: DoseAmount,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> tuple[str, float] | None:
    return _build_normalized_dose_observation(
        ingredient_key=ingredient_key,
        amount=dose.amount,
        unit=dose.unit.value,
        limits_by_ingredient=limits_by_ingredient,
    )


def _build_normalized_dose_observation(
    *,
    ingredient_key: str,
    amount: float,
    unit: str,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> tuple[str, float] | None:
    dose_limit = limits_by_ingredient[ingredient_key]
    if not _dose_evidence_source_allowed(dose_limit, "structured_dose"):
        return None

    normalized_amount = _convert_amount_unit(
        amount=amount,
        unit=unit,
        target_unit=dose_limit.unit,
        ingredient_key=ingredient_key,
    )
    if normalized_amount is None:
        return None
    return ingredient_key, normalized_amount


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
        "ng": 0.000001,
        "mcg": 0.001,
        "mg": 1.0,
        "g": 1000.0,
    }
    if normalized_unit in mass_scale_to_mg and normalized_target in mass_scale_to_mg:
        source_mg = amount * mass_scale_to_mg[normalized_unit]
        return source_mg / mass_scale_to_mg[normalized_target]

    if ingredient_key == "vitamin_d3":
        if normalized_unit in mass_scale_to_mg and normalized_target == "iu":
            source_mcg = amount * mass_scale_to_mg[normalized_unit] / mass_scale_to_mg["mcg"]
            return source_mcg * 40.0
        if normalized_unit == "iu" and normalized_target in mass_scale_to_mg:
            source_mcg = amount / 40.0
            source_mg = source_mcg * mass_scale_to_mg["mcg"]
            return source_mg / mass_scale_to_mg[normalized_target]
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
