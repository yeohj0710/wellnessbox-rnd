import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from wellnessbox_rnd.domain.catalog import (
    canonicalize_catalog_term,
    canonicalize_exact_catalog_term,
    get_catalog_index,
)
from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.domain.models import SafetyRuleMetadata
from wellnessbox_rnd.knowledge.runtime_db import (
    DoseLimitRecord,
    InteractionRuleRecord,
    RuntimeKnowledgeDB,
    build_citations_for_rule,
    find_triggered_interaction_rules,
    load_runtime_knowledge_db,
)
from wellnessbox_rnd.safety.rules import get_safety_rule_set
from wellnessbox_rnd.schemas.recommendation import (
    DoseAmount,
    IngredientDoseAggregate,
    RecommendationStatus,
    RuleReference,
    SafetySummary,
    Severity,
    SupplementIngredientInput,
    SupplementInput,
    normalize_supplement_ingredient_name,
)

_DOSE_PATTERN = re.compile(
    r"(?<![\d.,])"
    r"(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"\s*(?P<unit>mcg|mg|ng|iu|g)\b",
    re.IGNORECASE,
)
_COMPOUND_INGREDIENT_SEPARATOR = re.compile(
    r"\s*(?:\+|&|/|;|(?<!\d),(?!\d)|\band\b|\bwith\b|\bplus\b)\s*",
    re.IGNORECASE,
)
_AMBIGUOUS_DOSE_CONTEXT = re.compile(
    r"(?:"
    r"\b(?:twice|thrice|bid|tid|qid)\b"
    r"|\b(?:two|three|four|[2-9])\s*(?:x|times?)\b"
    r"|\bq\d+\s*h\b"
    r"|\bevery\s+\d+\s*hours?\b"
    r"|\b\d+\s+doses?\b"
    r"|(?<!\w)\d[\d,.]*\s*(?:[-–—~]|\bto\b)\s*\d"
    r")",
    re.IGNORECASE,
)

_MASS_UNITS = {"ng", "mcg", "mg", "g"}


@dataclass(frozen=True)
class _DoseObservation:
    ingredient_key: str
    amount: float
    unit: str
    evidence_source: str


@dataclass(frozen=True)
class _DoseLimitApplication:
    rule: DoseLimitRecord
    observed_amount: float | None
    reason: Literal["dose_evidence_incomplete", "upper_limit_exceeded"]


@dataclass
class _IngredientDoseAggregateState:
    product_names: set[str] = field(default_factory=set)
    product_observations: list[tuple[int, list[_DoseObservation], bool]] = field(
        default_factory=list
    )


def assess_safety(
    intake: NormalizedIntake,
    *,
    applied_at: datetime | None = None,
) -> SafetySummary:
    effective_applied_at = applied_at or datetime.now(UTC)
    if effective_applied_at.tzinfo is None:
        raise ValueError("applied_at must be timezone-aware")
    effective_applied_at = effective_applied_at.astimezone(UTC)
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

    for interaction_rule in runtime_knowledge_db.interaction_rules:
        if interaction_rule.source_kind != "evidence_linked_policy":
            continue
        if not set(interaction_rule.medication_keys).intersection(intake.medication_set):
            continue
        excluded_ingredients.update(interaction_rule.ingredient_keys)
        _append_unique_text(warnings, interaction_rule.warning_text)
        rule_refs.append(
            _build_interaction_rule_ref(interaction_rule, runtime_knowledge_db)
        )

    special_population_statuses = {
        status
        for status, active in {
            "pregnant": intake.request.user_profile.pregnant,
            "lactating": intake.request.user_profile.lactating,
        }.items()
        if active
    }
    for special_population_rule in rules.special_population_rules:
        if set(special_population_rule.statuses).intersection(special_population_statuses):
            excluded_ingredients.update(special_population_rule.excluded_ingredients)
            _append_unique_text(
                warnings,
                special_population_rule.metadata.warning_text,
            )
            rule_refs.append(_build_rule_ref(special_population_rule.metadata))

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

    ingredient_dose_aggregates = _build_ingredient_dose_aggregates(
        intake,
        runtime_knowledge_db,
    )
    for application in _find_triggered_dose_limits(
        ingredient_dose_aggregates,
        runtime_knowledge_db,
    ):
        dose_limit = application.rule
        excluded_ingredients.add(dose_limit.ingredient_key)
        if application.reason == "dose_evidence_incomplete":
            triggered_warning = _format_incomplete_dose_limit_warning(dose_limit)
            applied_severity = Severity.INFO
        else:
            if application.observed_amount is None:
                raise ValueError("upper-limit application requires an observed amount")
            triggered_warning = _format_dose_limit_warning(
                warning_text=dose_limit.warning_text,
                observed_amount=application.observed_amount,
                max_daily_amount=dose_limit.max_daily_amount,
                unit=dose_limit.unit,
            )
            applied_severity = dose_limit.severity
        _append_unique_text(warnings, triggered_warning)
        if applied_severity == Severity.BLOCKER:
            _append_unique_text(blocked_reasons, triggered_warning)
        rule_refs.append(
            RuleReference(
                rule_id=dose_limit.rule_id,
                rule_version=dose_limit.rule_version,
                application_reason=application.reason,
                message=dose_limit.message,
                severity=applied_severity,
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
            _build_interaction_rule_ref(knowledge_rule, runtime_knowledge_db)
        )

    status = _derive_status(rule_refs, blocked_reasons)
    return SafetySummary(
        applied_at=effective_applied_at,
        status=status,
        warnings=warnings,
        blocked_reasons=blocked_reasons,
        excluded_ingredients=sorted(excluded_ingredients),
        rule_refs=rule_refs,
        duplicate_ingredient_keys=[
            item.ingredient_key
            for item in ingredient_dose_aggregates
            if item.duplicate_across_products
        ],
        ingredient_dose_aggregates=ingredient_dose_aggregates,
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
        rule_version=metadata.version,
        message=metadata.message,
        severity=metadata.severity,
    )


def _build_interaction_rule_ref(
    rule: InteractionRuleRecord,
    runtime_knowledge_db: RuntimeKnowledgeDB,
) -> RuleReference:
    return RuleReference(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        message=rule.message,
        severity=rule.severity,
        source=rule.source_kind,
        reference_ids=rule.reference_ids,
        claim_ids=rule.claim_ids,
        citations=build_citations_for_rule(
            runtime_knowledge_db,
            reference_ids=rule.reference_ids,
            claim_ids=rule.claim_ids,
        ),
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
    aggregates: list[IngredientDoseAggregate],
    runtime_knowledge_db: RuntimeKnowledgeDB,
) -> list[_DoseLimitApplication]:
    limits_by_ingredient = {
        record.ingredient_key: record
        for record in runtime_knowledge_db.dose_limits
        if record.max_daily_amount is not None and record.unit
    }
    triggered: list[_DoseLimitApplication] = []
    for aggregate in aggregates:
        dose_limit = limits_by_ingredient.get(aggregate.ingredient_key)
        if dose_limit is None:
            continue
        if aggregate.dose_input_count == 0:
            continue
        if (
            not aggregate.dose_complete
            or aggregate.total_daily_amount is None
            or aggregate.unit is None
            or aggregate.unit.lower() != dose_limit.unit.lower()
        ):
            triggered.append(
                _DoseLimitApplication(
                    rule=dose_limit,
                    observed_amount=aggregate.total_daily_amount,
                    reason="dose_evidence_incomplete",
                )
            )
            continue
        observed_amount = aggregate.total_daily_amount
        if observed_amount > float(dose_limit.max_daily_amount):
            triggered.append(
                _DoseLimitApplication(
                    rule=dose_limit,
                    observed_amount=observed_amount,
                    reason="upper_limit_exceeded",
                )
            )
    return triggered


def _build_ingredient_dose_aggregates(
    intake: NormalizedIntake,
    runtime_knowledge_db: RuntimeKnowledgeDB,
) -> list[IngredientDoseAggregate]:
    limits_by_ingredient = {
        record.ingredient_key: record
        for record in runtime_knowledge_db.dose_limits
        if record.max_daily_amount is not None and record.unit
    }
    states: dict[str, _IngredientDoseAggregateState] = {}
    for supplement in intake.normalized_current_supplements:
        observations = _extract_supplement_dose_observations(
            supplement=supplement,
            limits_by_ingredient=limits_by_ingredient,
        )
        observations_by_ingredient: dict[str, list[_DoseObservation]] = {}
        for observation in observations:
            observations_by_ingredient.setdefault(
                observation.ingredient_key, []
            ).append(observation)
        occurrence_counts = _supplement_ingredient_occurrence_counts(supplement)
        ingredient_keys = set(occurrence_counts)
        ingredient_keys.update(observations_by_ingredient)
        for ingredient_key in ingredient_keys:
            state = states.setdefault(ingredient_key, _IngredientDoseAggregateState())
            state.product_names.add(supplement.name)
            state.product_observations.append(
                (
                    occurrence_counts.get(ingredient_key, 1),
                    observations_by_ingredient.get(ingredient_key, []),
                    _supplement_has_dose_input_for_ingredient(
                        supplement,
                        ingredient_key,
                    ),
                )
            )

    aggregates: list[IngredientDoseAggregate] = []
    for ingredient_key, state in sorted(states.items()):
        product_count = len(state.product_observations)
        dose_limit = limits_by_ingredient.get(ingredient_key)
        all_observations = [
            observation
            for _, product_observations, _ in state.product_observations
            for observation in product_observations
        ]
        target_unit = _select_aggregate_unit(
            observations=all_observations,
            dose_limit=dose_limit,
        )
        converted_by_product = [
            [
                converted_amount
                for observation in product_observations
                if (
                    converted_amount := _convert_amount_unit(
                        amount=observation.amount,
                        unit=observation.unit,
                        target_unit=target_unit,
                        ingredient_key=ingredient_key,
                    )
                )
                is not None
            ]
            for _, product_observations, _ in state.product_observations
        ]
        converted_amounts = [
            amount
            for product_observations in converted_by_product
            for amount in product_observations
        ]
        dose_observation_count = len(converted_amounts)
        dose_complete = bool(converted_amounts) and all(
            len(converted_observations) >= expected_occurrence_count
            for (expected_occurrence_count, _, _), converted_observations in zip(
                state.product_observations,
                converted_by_product,
                strict=True,
            )
        )
        aggregates.append(
            IngredientDoseAggregate(
                ingredient_key=ingredient_key,
                product_count=product_count,
                product_names=sorted(state.product_names),
                duplicate_across_products=product_count > 1,
                total_daily_amount=sum(converted_amounts) if converted_amounts else None,
                unit=target_unit if converted_amounts else None,
                dose_input_count=sum(
                    int(dose_input_present)
                    for _, _, dose_input_present in state.product_observations
                ),
                dose_observation_count=dose_observation_count,
                dose_complete=dose_complete,
            )
        )
    return aggregates


def _supplement_ingredient_keys(supplement: SupplementInput) -> set[str]:
    return set(_supplement_ingredient_occurrence_counts(supplement))


def _supplement_ingredient_occurrence_counts(
    supplement: SupplementInput,
) -> dict[str, int]:
    occurrence_counts: dict[str, int] = {}
    for ingredient in supplement.ingredients:
        ingredient_keys = _ingredient_keys_from_text(
            normalize_supplement_ingredient_name(ingredient)
        )
        for ingredient_key in ingredient_keys:
            occurrence_counts[ingredient_key] = (
                occurrence_counts.get(ingredient_key, 0) + 1
            )
    if occurrence_counts:
        return occurrence_counts
    for ingredient_key in _ingredient_keys_from_text(supplement.name):
        occurrence_counts[ingredient_key] = occurrence_counts.get(ingredient_key, 0) + 1
    return occurrence_counts


def _select_aggregate_unit(
    *,
    observations: list[_DoseObservation],
    dose_limit: DoseLimitRecord | None,
) -> str | None:
    if dose_limit is not None and dose_limit.unit:
        return dose_limit.unit.lower()
    units = {observation.unit.lower() for observation in observations}
    if not units:
        return None
    if units.issubset(_MASS_UNITS):
        return "mg"
    if len(units) == 1:
        return next(iter(units))
    return None


def _parse_supplement_amount(
    value: str,
    *,
    require_dose_only: bool = False,
) -> tuple[float, str] | None:
    matches = list(_DOSE_PATTERN.finditer(value))
    if len(matches) != 1:
        return None
    match = matches[0]
    if require_dose_only:
        remainder = f"{value[: match.start()]}{value[match.end() :]}"
        if remainder.strip(" \t\r\n()[]{}:;,.\""):
            return None
    amount = float(match.group("amount").replace(",", ""))
    return amount, match.group("unit").lower()


def _ingredient_keys_from_text(value: str) -> list[str]:
    parts = [
        part
        for part in _COMPOUND_INGREDIENT_SEPARATOR.split(value)
        if part.strip()
    ]
    ingredient_keys: list[str] = []
    for part in parts:
        ingredient_text = _strip_dose_text(part)
        ingredient_key = canonicalize_exact_catalog_term(
            ingredient_text
        ) or canonicalize_catalog_term(ingredient_text)
        if ingredient_key is not None:
            ingredient_keys.append(ingredient_key)
    if ingredient_keys:
        return ingredient_keys
    if len(parts) <= 1:
        ingredient_key = canonicalize_catalog_term(value)
        if ingredient_key is not None:
            return [ingredient_key]
    return []


def _supplement_has_dose_input_for_ingredient(
    supplement: SupplementInput,
    ingredient_key: str,
) -> bool:
    for ingredient in supplement.ingredients:
        ingredient_name = normalize_supplement_ingredient_name(ingredient)
        if ingredient_key not in _ingredient_keys_from_text(ingredient_name):
            continue
        if isinstance(ingredient, SupplementIngredientInput):
            if ingredient.daily_dose is not None:
                return True
        if _DOSE_PATTERN.search(ingredient_name) is not None:
            return True

    if supplement.daily_dose is not None or supplement.dose is not None:
        return True
    return (
        ingredient_key in _ingredient_keys_from_text(supplement.name)
        and _DOSE_PATTERN.search(supplement.name) is not None
    )


def _strip_dose_text(value: str) -> str:
    without_doses = _DOSE_PATTERN.sub("", value)
    return without_doses.strip(" \t\r\n()[]{}:;,+&/-")


def _extract_supplement_dose_observations(
    *,
    supplement: SupplementInput,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> list[_DoseObservation]:
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
            evidence_source="ingredient_line",
        )
        if observation is None or not _dose_observation_allowed(
            observation,
            limits_by_ingredient,
        ):
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
        evidence_source="title",
    )
    if title_observation is None or not _dose_observation_allowed(
        title_observation,
        limits_by_ingredient,
    ):
        return []
    return [title_observation]


def _extract_ingredient_daily_dose_observations(
    *,
    supplement: SupplementInput,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> list[_DoseObservation]:
    observations: list[_DoseObservation] = []
    for ingredient in supplement.ingredients:
        if not isinstance(ingredient, SupplementIngredientInput):
            continue
        if ingredient.daily_dose is None:
            continue
        ingredient_keys = _ingredient_keys_from_text(ingredient.name)
        if len(ingredient_keys) != 1:
            continue
        ingredient_key = ingredient_keys[0]
        observation = _build_structured_dose_observation(
            ingredient_key=ingredient_key,
            dose=ingredient.daily_dose,
        )
        if _dose_observation_allowed(observation, limits_by_ingredient):
            observations.append(observation)
    return observations


def _extract_product_daily_dose_observation(
    *,
    supplement: SupplementInput,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> _DoseObservation | None:
    ingredient_key = _single_product_dose_ingredient_key(supplement=supplement)
    if ingredient_key is None:
        return None

    if supplement.daily_dose is not None:
        observation = _build_structured_dose_observation(
            ingredient_key=ingredient_key,
            dose=supplement.daily_dose,
        )
        return (
            observation
            if _dose_observation_allowed(observation, limits_by_ingredient)
            else None
        )
    if supplement.dose is None:
        return None

    parsed_dose = _parse_supplement_amount(
        supplement.dose,
        require_dose_only=True,
    )
    if parsed_dose is None:
        return None
    amount, unit = parsed_dose
    observation = _DoseObservation(
        ingredient_key=ingredient_key,
        amount=amount,
        unit=unit,
        evidence_source="structured_dose",
    )
    return (
        observation
        if _dose_observation_allowed(observation, limits_by_ingredient)
        else None
    )


def _single_product_dose_ingredient_key(
    *,
    supplement: SupplementInput,
) -> str | None:
    declared_ingredient_names = [
        normalize_supplement_ingredient_name(ingredient)
        for ingredient in supplement.ingredients
        if normalize_supplement_ingredient_name(ingredient)
    ]
    if declared_ingredient_names:
        resolved_ingredient_keys = [
            _ingredient_keys_from_text(name) for name in declared_ingredient_names
        ]
        if any(len(keys) != 1 for keys in resolved_ingredient_keys):
            return None
        declared_ingredient_keys = {keys[0] for keys in resolved_ingredient_keys}
        if len(declared_ingredient_keys) != 1:
            return None
        return next(iter(declared_ingredient_keys))
    title_ingredient_keys = _ingredient_keys_from_text(supplement.name)
    return title_ingredient_keys[0] if len(title_ingredient_keys) == 1 else None


def _build_structured_dose_observation(
    *,
    ingredient_key: str,
    dose: DoseAmount,
) -> _DoseObservation:
    return _DoseObservation(
        ingredient_key=ingredient_key,
        amount=dose.amount,
        unit=dose.unit.value,
        evidence_source="structured_dose",
    )


def _build_dose_observation(
    *,
    source_text: str,
    evidence_source: str,
) -> _DoseObservation | None:
    if _AMBIGUOUS_DOSE_CONTEXT.search(source_text) is not None:
        return None
    parsed_dose = _parse_supplement_amount(source_text)
    if parsed_dose is None:
        return None

    ingredient_keys = _ingredient_keys_from_text(source_text)
    if len(ingredient_keys) != 1:
        return None
    ingredient_key = ingredient_keys[0]

    amount, unit = parsed_dose
    return _DoseObservation(
        ingredient_key=ingredient_key,
        amount=amount,
        unit=unit,
        evidence_source=evidence_source,
    )


def _dose_observation_allowed(
    observation: _DoseObservation,
    limits_by_ingredient: dict[str, DoseLimitRecord],
) -> bool:
    dose_limit = limits_by_ingredient.get(observation.ingredient_key)
    if dose_limit is None:
        return True
    return _dose_evidence_source_allowed(
        dose_limit,
        observation.evidence_source,
    )


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


def _format_incomplete_dose_limit_warning(dose_limit: DoseLimitRecord) -> str:
    unit_context = f" in {dose_limit.unit}" if dose_limit.unit else ""
    return (
        f"Current dose evidence for {dose_limit.ingredient_key} was missing, partial,"
        f" or not convertible{unit_context}, so the regimen could not be compared"
        " safely with the structured upper limit and was excluded conservatively."
    )
