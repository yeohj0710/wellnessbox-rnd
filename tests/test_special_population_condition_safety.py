import pytest
from pydantic import ValidationError

from wellnessbox_rnd.domain.intake import normalize_request
from wellnessbox_rnd.domain.models import ConditionSafetyRule, SafetyRuleMetadata
from wellnessbox_rnd.knowledge.runtime_db import build_runtime_knowledge_db
from wellnessbox_rnd.safety.service import assess_safety
from wellnessbox_rnd.schemas.recommendation import (
    BiologicalSex,
    RecommendationGoal,
    RecommendationRequest,
    RecommendationStatus,
    Severity,
    UserProfile,
)


def _assess(
    *,
    pregnant: bool = False,
    lactating: bool = False,
    conditions: list[str] | None = None,
):
    request = RecommendationRequest(
        user_profile=UserProfile(
            age=32,
            biological_sex=BiologicalSex.FEMALE,
            pregnant=pregnant,
            lactating=lactating,
        ),
        goals=[RecommendationGoal.GENERAL_WELLNESS],
        conditions=conditions or [],
    )
    return assess_safety(normalize_request(request))


def _rule_ids(summary) -> list[str]:
    return [rule.rule_id for rule in summary.rule_refs]


def test_user_profile_keeps_pregnancy_and_lactation_independent() -> None:
    pregnant = UserProfile(
        age=32,
        biological_sex=BiologicalSex.FEMALE,
        pregnant=True,
    )
    lactating = UserProfile(
        age=32,
        biological_sex=BiologicalSex.FEMALE,
        lactating=True,
    )

    assert (pregnant.pregnant, pregnant.lactating) == (True, False)
    assert (lactating.pregnant, lactating.lactating) == (False, True)


def test_pregnancy_and_lactation_apply_distinct_rules() -> None:
    pregnancy = _assess(pregnant=True)
    lactation = _assess(lactating=True)

    assert _rule_ids(pregnancy) == ["SAFETY-PREG-001"]
    assert _rule_ids(lactation) == ["SAFETY-LACT-001"]
    assert pregnancy.status == RecommendationStatus.NEEDS_REVIEW
    assert lactation.status == RecommendationStatus.NEEDS_REVIEW
    assert "ashwagandha" in pregnancy.excluded_ingredients
    assert "ashwagandha" in lactation.excluded_ingredients


def test_combined_pregnancy_and_lactation_applies_each_rule_once() -> None:
    summary = _assess(pregnant=True, lactating=True)

    assert _rule_ids(summary) == ["SAFETY-PREG-001", "SAFETY-LACT-001"]
    assert summary.status == RecommendationStatus.NEEDS_REVIEW


def test_condition_rules_distinguish_contraindication_from_review() -> None:
    renal_review = _assess(conditions=["kidney disease"])
    severe_renal = _assess(conditions=["kidney failure"])
    hepatic_review = _assess(conditions=["cirrhosis"])
    hemochromatosis = _assess(conditions=["hemochromatosis"])

    assert _rule_ids(renal_review) == ["SAFETY-RENAL-001"]
    assert renal_review.status == RecommendationStatus.NEEDS_REVIEW
    assert "magnesium_glycinate" in renal_review.excluded_ingredients

    assert _rule_ids(severe_renal) == ["SAFETY-RENAL-SEVERE-001"]
    assert severe_renal.status == RecommendationStatus.BLOCKED
    assert "magnesium_glycinate" in severe_renal.excluded_ingredients

    assert _rule_ids(hepatic_review) == ["SAFETY-HEPATIC-001"]
    assert hepatic_review.status == RecommendationStatus.BLOCKED

    assert _rule_ids(hemochromatosis) == ["SAFETY-HEMO-001"]
    assert hemochromatosis.status == RecommendationStatus.NEEDS_REVIEW
    assert {"iron", "vitamin_c"}.issubset(hemochromatosis.excluded_ingredients)


def test_unmatched_condition_does_not_trigger_expanded_rules() -> None:
    summary = _assess(conditions=["seasonal allergies"])

    assert summary.status == RecommendationStatus.OK
    assert summary.rule_refs == []


def test_contraindication_rule_requires_at_least_one_excluded_ingredient() -> None:
    with pytest.raises(ValidationError, match="require excluded_ingredients"):
        ConditionSafetyRule(
            conditions=["example condition"],
            effect="contraindication",
            excluded_ingredients=[],
            metadata=SafetyRuleMetadata(
                rule_id="TEST-CONTRAINDICATION-001",
                message="Test rule.",
                severity=Severity.BLOCKER,
                warning_text="Test warning.",
            ),
        )


def test_runtime_knowledge_keeps_special_population_and_condition_effects() -> None:
    runtime_db = build_runtime_knowledge_db()
    records = {record.rule_id: record for record in runtime_db.contraindication_rules}
    condition_keys = {record.condition_key for record in runtime_db.conditions}

    assert {"pregnancy", "lactation"}.issubset(condition_keys)
    assert "pregnant" not in condition_keys
    assert "lactating" not in condition_keys
    assert records["SAFETY-PREG-001"].condition_keys == ["pregnancy"]
    assert records["SAFETY-LACT-001"].condition_keys == ["lactation"]
    assert records["SAFETY-PREG-001"].applies_when_pregnant is True
    assert records["SAFETY-PREG-001"].applies_when_lactating is False
    assert records["SAFETY-LACT-001"].applies_when_pregnant is False
    assert records["SAFETY-LACT-001"].applies_when_lactating is True
    assert records["SAFETY-RENAL-001"].effect == "review_required"
    assert records["SAFETY-RENAL-SEVERE-001"].effect == "contraindication"
    assert records["SAFETY-HEPATIC-001"].effect == "review_required"
    assert records["SAFETY-HEMO-001"].effect == "contraindication"
