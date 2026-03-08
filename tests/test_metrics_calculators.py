from wellnessbox_rnd.metrics.calculators import (
    explanation_term_coverage_pct,
    percentile_improvement_pp,
    recommendation_coverage_pct,
    safety_reference_accuracy_pct,
)


def test_recommendation_coverage_pct_returns_expected_percentage() -> None:
    score = recommendation_coverage_pct(
        required_ingredients=["magnesium_glycinate", "l_theanine"],
        actual_ingredients=["magnesium_glycinate", "vitamin_d3"],
    )

    assert score == 50.0


def test_percentile_improvement_pp_is_positive_when_post_is_higher() -> None:
    score = percentile_improvement_pp(z_pre=-0.2, z_post=0.4)

    assert score > 0


def test_safety_reference_accuracy_pct_requires_status_rule_and_exclusion_match() -> None:
    score = safety_reference_accuracy_pct(
        expected_status="needs_review",
        actual_status="needs_review",
        required_rule_ids=["RULE-1"],
        actual_rule_ids=["RULE-1", "RULE-2"],
        required_excluded_ingredients=["omega3"],
        actual_excluded_ingredients=["omega3", "berberine"],
    )

    assert score == 100.0


def test_explanation_term_coverage_pct_counts_required_terms() -> None:
    score = explanation_term_coverage_pct(
        required_terms=["mock deterministic", "선택"],
        actual_text="입력 목표와 현재 mock deterministic 규칙 점수에 따라 선택되었습니다.",
    )

    assert score == 100.0

