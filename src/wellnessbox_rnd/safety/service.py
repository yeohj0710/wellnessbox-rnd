from wellnessbox_rnd.domain.catalog import get_catalog_index
from wellnessbox_rnd.domain.intake import NormalizedIntake
from wellnessbox_rnd.domain.models import SafetyRuleMetadata
from wellnessbox_rnd.safety.rules import get_safety_rule_set
from wellnessbox_rnd.schemas.recommendation import (
    RecommendationStatus,
    RuleReference,
    SafetySummary,
    Severity,
)


def assess_safety(intake: NormalizedIntake) -> SafetySummary:
    rules = get_safety_rule_set()
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
            warnings.append(medication_rule.metadata.warning_text)
            rule_refs.append(_build_rule_ref(medication_rule.metadata))

    if intake.request.user_profile.pregnant and rules.pregnancy_rule is not None:
        excluded_ingredients.update(rules.pregnancy_rule.excluded_ingredients)
        warnings.append(rules.pregnancy_rule.metadata.warning_text)
        rule_refs.append(_build_rule_ref(rules.pregnancy_rule.metadata))

    for condition_rule in rules.condition_rules:
        if set(condition_rule.conditions).intersection(intake.condition_set):
            excluded_ingredients.update(condition_rule.excluded_ingredients)
            warnings.append(condition_rule.metadata.warning_text)
            rule_refs.append(_build_rule_ref(condition_rule.metadata))

    duplicate_ingredients = _recognized_current_duplicates(intake)
    if (
        duplicate_ingredients
        and rules.duplicate_policy == "exclude"
        and rules.duplicate_overlap_rule is not None
    ):
        excluded_ingredients.update(duplicate_ingredients)
        warnings.append(rules.duplicate_overlap_rule.metadata.warning_text)
        rule_refs.append(_build_rule_ref(rules.duplicate_overlap_rule.metadata))

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


def _derive_status(
    rule_refs: list[RuleReference],
    blocked_reasons: list[str],
) -> RecommendationStatus:
    if blocked_reasons or any(rule.severity == Severity.BLOCKER for rule in rule_refs):
        return RecommendationStatus.BLOCKED
    if any(rule.severity == Severity.WARNING for rule in rule_refs):
        return RecommendationStatus.NEEDS_REVIEW
    return RecommendationStatus.OK
