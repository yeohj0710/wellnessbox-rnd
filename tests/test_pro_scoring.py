from wellnessbox_rnd.metrics.pro_scoring import (
    build_default_pro_form_schema_v1,
    summarize_pro_form_contract_v1,
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
