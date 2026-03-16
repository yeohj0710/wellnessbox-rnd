from wellnessbox_rnd.metrics.pro_scoring import (
    build_default_pro_domain_norms_v1,
    build_default_pro_form_schema_v1,
    summarize_pro_form_contract_v1,
    summarize_pro_improvement_v1,
    transform_pro_response_to_zscores_v1,
    validate_pro_domain_norms_v1,
    validate_pro_form_response_v1,
)
from wellnessbox_rnd.synthetic.rich_longitudinal_v4 import generate_rich_synthetic_cohort_v4


def test_build_default_pro_form_schema_v1_covers_expected_domains() -> None:
    schema = build_default_pro_form_schema_v1()

    assert schema.schema_version == "pro_form_schema_v1"
    assert schema.timepoints == ("baseline", "follow_up")
    assert [domain.domain_key.value for domain in schema.domains] == [
        "stress_support",
        "sleep_support",
        "immunity_support",
        "energy_support",
        "gut_health",
        "bone_joint",
        "heart_health",
        "blood_glucose",
        "general_wellness",
    ]
    assert all(len(domain.items) == 4 for domain in schema.domains)


def test_validate_pro_form_response_v1_flags_missing_and_unknown_keys() -> None:
    schema = build_default_pro_form_schema_v1()
    response = {
        "timepoint": "baseline",
        "domain_item_scores": {
            "stress_support": {
                "perceived_stress_load": 2,
                "tension_burden": 3,
                "calm_recovery_delay": 1,
                "stress_resilience_drop": 2,
                "unexpected_item": 4,
            },
            "unknown_domain": {"noise": 1},
        },
    }

    issues = validate_pro_form_response_v1(schema=schema, response=response)

    assert "unknown_domain::unknown_domain" in issues
    assert "unknown_item::stress_support::unexpected_item" in issues
    assert "missing_domain::sleep_support" in issues


def test_summarize_pro_form_contract_v1_matches_rich_synthetic_domain_coverage() -> None:
    records = generate_rich_synthetic_cohort_v4(seed=602, user_count=24)

    summary = summarize_pro_form_contract_v1(
        records,
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
    )

    assert summary["case_count"] == len(records)
    assert summary["domain_count"] == 9
    assert (
        summary["synthetic_alignment"]["all_schema_domains_present_baseline_case_count"]
        == len(records)
    )
    assert (
        summary["synthetic_alignment"]["all_schema_domains_present_follow_up_case_count"]
        == len(records)
    )
    assert summary["synthetic_alignment"]["baseline_domain_coverage_pct"]["blood_glucose"] == 100.0
    assert summary["zscore_transform"]["transform_version"] == "pro_zscore_transform_v1"
    assert (
        summary["zscore_transform"]["sample_transforms"]["mid_problem_score_zero_z"][
            "aggregate_z"
        ]
        == 0.0
    )


def test_transform_pro_response_to_zscores_v1_uses_default_problem_norms() -> None:
    schema = build_default_pro_form_schema_v1()
    response = {
        "timepoint": "follow_up",
        "domain_item_scores": {
            domain.domain_key.value: {
                item.item_key: (1 if domain.domain_key.value == "sleep_support" else 2)
                for item in domain.items
            }
            for domain in schema.domains
        },
    }

    transformed = transform_pro_response_to_zscores_v1(response, schema=schema)

    assert transformed.transform_version == "pro_zscore_transform_v1"
    assert transformed.norm_version == "pro_zscore_norm_v1"
    assert transformed.domain_problem_scores["sleep_support"] == 1.0
    assert transformed.domain_z["sleep_support"] == 1.0
    assert transformed.domain_z["stress_support"] == 0.0
    assert transformed.aggregate_z == round(1.0 / 9.0, 6)


def test_validate_pro_domain_norms_v1_flags_missing_unknown_and_bad_std() -> None:
    schema = build_default_pro_form_schema_v1()
    norms = build_default_pro_domain_norms_v1(schema)
    norms.pop("general_wellness")
    norms["unexpected_domain"] = {
        "domain_key": "stress_support",
        "problem_score_mean": 2.0,
        "problem_score_std": 1.0,
        "score_orientation": "lower_is_better_for_problem_score",
    }
    norms["sleep_support"] = {
        "domain_key": "sleep_support",
        "problem_score_mean": 2.0,
        "problem_score_std": 0.0,
        "score_orientation": "lower_is_better_for_problem_score",
    }

    issues = validate_pro_domain_norms_v1(norms=norms, schema=schema)

    assert "missing_norm::general_wellness" in issues
    assert "unknown_norm::unexpected_domain" in issues
    assert any(issue.startswith("invalid_norm_std::sleep_support::") for issue in issues)


def test_summarize_pro_improvement_v1_computes_deltas_and_status() -> None:
    schema = build_default_pro_form_schema_v1()
    baseline = transform_pro_response_to_zscores_v1(
        {
            "timepoint": "baseline",
            "domain_item_scores": {
                domain.domain_key.value: {item.item_key: 2 for item in domain.items}
                for domain in schema.domains
            },
        },
        schema=schema,
    )
    follow_up = transform_pro_response_to_zscores_v1(
        {
            "timepoint": "follow_up",
            "domain_item_scores": {
                domain.domain_key.value: {
                    item.item_key: (1 if domain.domain_key.value == "sleep_support" else 2)
                    for item in domain.items
                }
                for domain in schema.domains
            },
        },
        schema=schema,
    )

    summary = summarize_pro_improvement_v1(
        baseline_snapshot=baseline,
        follow_up_snapshot=follow_up,
    )

    assert summary.summary_version == "pro_improvement_summary_v1"
    assert summary.aggregate_delta_z == round(1.0 / 9.0, 6)
    assert summary.domain_delta_z["sleep_support"] == 1.0
    assert summary.improved_domain_count == 1
    assert summary.worsened_domain_count == 0
    assert summary.unchanged_domain_count == 8
    assert summary.net_status == "net_improvement"
