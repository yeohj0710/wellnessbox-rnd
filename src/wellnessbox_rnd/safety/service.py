from wellnessbox_rnd.domain.intake import NormalizedIntake
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

    if "survey" in rules.minimum_required_inputs and not intake.request.input_availability.survey:
        blocked_reasons.append("Baseline survey input is required before recommendation can run.")
        rule_refs.append(
            RuleReference(
                rule_id="INTAKE-SURVEY-001",
                message="Survey input is the minimum contract for recommendation.",
                severity=Severity.BLOCKER,
            )
        )

    for medication, ingredients in rules.medication_interactions.items():
        if medication in intake.medication_set:
            excluded_ingredients.update(ingredients)
            warnings.append(
                f"Potential interaction context was detected for {medication}, so related "
                "candidates were excluded."
            )
            rule_refs.append(
                RuleReference(
                    rule_id="SAFETY-ANTICOAG-001",
                    message="Potential medication interaction triggers conservative exclusion.",
                    severity=Severity.WARNING,
                )
            )

    if intake.request.user_profile.pregnant:
        excluded_ingredients.update(rules.pregnancy_exclusions)
        warnings.append(
            "Pregnancy input was detected, so restricted ingredients were excluded conservatively."
        )
        rule_refs.append(
            RuleReference(
                rule_id="SAFETY-PREG-001",
                message="Pregnancy input requires conservative exclusion and human review.",
                severity=Severity.WARNING,
            )
        )

    for condition, ingredients in rules.condition_exclusions.items():
        if condition in intake.condition_set:
            excluded_ingredients.update(ingredients)
            warnings.append(
                rules.condition_review_flags.get(
                    condition,
                    f"Condition context for {condition} requires a conservative review.",
                )
            )
            rule_refs.append(
                RuleReference(
                    rule_id="SAFETY-RENAL-001",
                    message="Condition-specific exclusion was applied conservatively.",
                    severity=Severity.WARNING,
                )
            )

    duplicate_hits = excluded_ingredients.intersection(intake.current_ingredient_set)
    if duplicate_hits:
        warnings.append(
            "Current supplement overlap was detected, so duplicate ingredients were excluded."
        )
        rule_refs.append(
            RuleReference(
                rule_id="SAFETY-DUP-001",
                message="Current supplement overlap is excluded by policy.",
                severity=Severity.INFO,
            )
        )
        excluded_ingredients.update(duplicate_hits)

    status = RecommendationStatus.OK
    if blocked_reasons:
        status = RecommendationStatus.BLOCKED
    elif warnings:
        status = RecommendationStatus.NEEDS_REVIEW

    return SafetySummary(
        status=status,
        warnings=warnings,
        blocked_reasons=blocked_reasons,
        excluded_ingredients=sorted(excluded_ingredients),
        rule_refs=rule_refs,
    )
