from wellnessbox_rnd.metrics.calculators import (
    explanation_term_coverage_pct,
    integration_modality_breakdown,
    integration_modality_rate_pct,
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
        required_terms=["mock deterministic", "selected"],
        actual_text=(
            "The baseline selected this mock deterministic candidate after a "
            "rule-and-score comparison."
        ),
    )

    assert score == 100.0


def test_integration_modality_rate_pct_returns_per_modality_score() -> None:
    records = [
        {
            "wearable": {"attempted": 1, "success": 1},
            "cgm": {"attempted": 1, "success": 0},
            "genetic": {"attempted": 0, "success": 0},
        },
        {
            "wearable": {"attempted": 1, "success": 1},
            "cgm": {"attempted": 1, "success": 1},
            "genetic": {"attempted": 1, "success": 0},
        },
    ]

    assert integration_modality_rate_pct(records, "wearable") == 100.0
    assert integration_modality_rate_pct(records, "cgm") == 50.0
    assert integration_modality_rate_pct(records, "genetic") == 0.0


def test_integration_modality_breakdown_returns_attempt_success_and_score() -> None:
    records = [
        {
            "wearable": {"attempted": 2, "success": 2},
            "cgm": {"attempted": 1, "success": 0},
        },
        {
            "wearable": {"attempted": 1, "success": 1},
            "genetic": {"attempted": 2, "success": 1},
        },
    ]

    breakdown = integration_modality_breakdown(records)

    assert breakdown["wearable"] == {"attempted": 3, "success": 3, "score": 100.0}
    assert breakdown["cgm"] == {"attempted": 1, "success": 0, "score": 0.0}
    assert breakdown["genetic"] == {"attempted": 2, "success": 1, "score": 50.0}
