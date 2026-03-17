from pathlib import Path

from wellnessbox_rnd.training.dataset_f_data_quality import (
    build_dataset_f_data_quality_report,
    render_dataset_f_data_quality_markdown,
    write_dataset_f_data_quality_files,
)


def test_build_dataset_f_data_quality_report_pins_current_distribution() -> None:
    report = build_dataset_f_data_quality_report(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        manifest_path="artifacts/reports/dataset_f_effect_prepost_manifest_v1.json",
        pair_summary_path="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
    )

    dataset_summary = report["dataset_summary"]
    heterogeneity = report["response_profile_heterogeneity"]
    slice_balance = report["slice_balance"]
    low_risk_distribution = report["low_risk_vs_cgm_distribution"]
    follow_up_diversity = report["follow_up_change_diversity"]
    readable_summary = report["readable_summary"]

    assert report["report_name"] == "dataset_f_data_quality_v1"
    assert dataset_summary["case_count"] == 480
    assert dataset_summary["user_count"] == 96
    assert heterogeneity["response_family_normalized_entropy"] == 0.9655
    assert heterogeneity["trajectory_mode_normalized_entropy"] == 0.9655
    assert heterogeneity["smallest_response_family"] == {
        "name": "adherence_limited_recovery",
        "count": 20,
    }
    assert round(heterogeneity["smallest_to_largest_family_ratio"], 4) == 0.25
    assert slice_balance["risk_cgm_counts"] == {
        "high__cgm_false": 55,
        "high__cgm_true": 100,
        "low__cgm_false": 260,
        "low__cgm_true": 65,
    }
    assert slice_balance["smallest_nonzero_risk_cgm_family_slice"] == {
        "risk_tier": "low",
        "cgm": True,
        "response_family": "low_response_edge",
        "case_count": 15,
    }
    assert low_risk_distribution["low_risk_cgm_case_count"] == 65
    assert low_risk_distribution["low_risk_cgm_share_of_low_risk_pct"] == 20.0
    assert low_risk_distribution["low_risk_cgm_goal_counts"] == {"blood_glucose": 65}
    assert low_risk_distribution["low_risk_cgm_response_family_counts"] == {
        "cgm_threshold_sensitive": 35,
        "low_response_edge": 15,
        "monitor_plateau": 15,
    }
    assert low_risk_distribution["low_risk_cgm_next_action_counts"] == {
        "continue_plan": 39,
        "monitor_only": 12,
        "re_optimize": 14,
    }
    assert readable_summary["response_profile_digest"] == {
        "response_family_normalized_entropy": 0.9655,
        "trajectory_mode_normalized_entropy": 0.9655,
        "smallest_response_family": {
            "name": "adherence_limited_recovery",
            "count": 20,
        },
        "largest_response_family": {
            "name": "tolerability_limited",
            "count": 80,
        },
        "smallest_to_largest_family_ratio": 0.25,
    }
    assert readable_summary["slice_balance_digest"] == {
        "low_risk_case_count": 325,
        "high_risk_case_count": 155,
        "low_risk_cgm_case_count": 65,
        "low_risk_cgm_share_of_low_risk_pct": 20.0,
        "low_risk_cgm_single_goal_pct": 100.0,
        "smallest_nonzero_risk_cgm_family_slice": {
            "risk_tier": "low",
            "cgm": True,
            "response_family": "low_response_edge",
            "case_count": 15,
        },
        "largest_risk_cgm_family_slice": {
            "risk_tier": "low",
            "cgm": False,
            "response_family": "monitor_plateau",
            "case_count": 65,
        },
    }
    assert readable_summary["low_risk_vs_cgm_digest"] == {
        "low_risk_cgm_response_family_count": 3,
        "low_risk_cgm_response_family_counts": {
            "cgm_threshold_sensitive": 35,
            "low_response_edge": 15,
            "monitor_plateau": 15,
        },
        "low_risk_cgm_next_action_counts": {
            "continue_plan": 39,
            "monitor_only": 12,
            "re_optimize": 14,
        },
        "low_risk_non_cgm_next_action_counts": {
            "ask_targeted_followup": 8,
            "continue_plan": 183,
            "monitor_only": 65,
            "re_optimize": 4,
        },
        "low_risk_cgm_next_action_entropy": 0.8639,
        "low_risk_non_cgm_next_action_entropy": 0.5519,
    }
    assert follow_up_diversity["unique_aggregate_delta_count"] == 82
    assert follow_up_diversity["unique_delta_signature_count"] == 152
    assert follow_up_diversity["zero_delta_signature_case_count"] == 31
    assert follow_up_diversity["uniform_non_goal_delta_case_count"] == 394
    assert follow_up_diversity["uniform_non_goal_delta_case_pct"] == 82.08
    assert follow_up_diversity["lowest_signature_diversity_families"][0] == {
        "response_family": "cgm_threshold_sensitive",
        "case_count": 35,
        "unique_signature_count": 5,
        "signature_diversity_pct": 14.29,
    }
    assert readable_summary["follow_up_diversity_digest"] == {
        "unique_aggregate_delta_count": 82,
        "unique_delta_signature_count": 152,
        "uniform_non_goal_delta_case_pct": 82.08,
        "weakest_signature_diversity_family": {
            "response_family": "cgm_threshold_sensitive",
            "case_count": 35,
            "unique_signature_count": 5,
            "signature_diversity_pct": 14.29,
        },
        "top_repeated_delta_signature_case_count": 31,
    }
    assert readable_summary["signal_simplicity_verdict"] == {
        "weakest_slice": "low_risk_cgm",
        "weakest_diversity_family": "cgm_threshold_sensitive",
        "signal_homogeneity_risk": "material_but_not_single_mode",
        "why": (
            "low_risk_cgm stays narrow and single-goal, while "
            "cgm_threshold_sensitive has only 5 unique signatures across 35 rows "
            "and 82.08% of all cases keep uniform non-goal spillover."
        ),
    }
    assert readable_summary["weakest_slice_surface"] == {
        "slice_name": "low_risk_cgm",
        "slice_case_count": 65,
        "slice_goal_counts": {"blood_glucose": 65},
        "slice_response_family_counts": {
            "cgm_threshold_sensitive": 35,
            "low_response_edge": 15,
            "monitor_plateau": 15,
        },
        "slice_next_action_counts": {
            "continue_plan": 39,
            "monitor_only": 12,
            "re_optimize": 14,
        },
        "weakest_diversity_family": {
            "response_family": "cgm_threshold_sensitive",
            "case_count": 35,
            "unique_signature_count": 5,
            "signature_diversity_pct": 14.29,
        },
    }
    assert readable_summary["sample_example_digest"] == {
        "low_risk_cgm_record_ids": [
            "syn-v4-004-step-0",
            "syn-v4-004-step-1",
            "syn-v4-009-step-0",
        ],
        "repeated_zero_delta_record_ids": [
            "syn-v4-005-step-0",
            "syn-v4-006-step-0",
            "syn-v4-008-step-0",
        ],
        "weakest_diversity_family_record_ids": [
            "syn-v4-009-step-0",
            "syn-v4-009-step-1",
            "syn-v4-009-step-2",
        ],
    }
    assert (
        report["sample_examples"]["low_risk_cgm_examples"][0]["record_id"]
        == "syn-v4-004-step-0"
    )
    assert (
        report["sample_examples"]["repeated_zero_delta_examples"][0]["record_id"]
        == "syn-v4-005-step-0"
    )


def test_write_dataset_f_data_quality_files_creates_outputs(tmp_path: Path) -> None:
    report = build_dataset_f_data_quality_report(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        manifest_path="artifacts/reports/dataset_f_effect_prepost_manifest_v1.json",
        pair_summary_path="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
    )

    json_path = tmp_path / "dataset_f_data_quality_v1.json"
    md_path = tmp_path / "dataset_f_data_quality_v1.md"
    write_dataset_f_data_quality_files(
        report=report,
        json_path=json_path,
        md_path=md_path,
    )
    markdown = render_dataset_f_data_quality_markdown(report)

    assert json_path.exists()
    assert md_path.exists()
    assert "## Readable Summary" in markdown
    assert "## Response-Profile Heterogeneity" in markdown
    assert "## Follow-Up Change Diversity" in markdown
    assert "low_risk_cgm_share_of_low_risk_pct: `20.0`" in markdown
