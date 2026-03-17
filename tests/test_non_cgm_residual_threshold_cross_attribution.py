from wellnessbox_rnd.evals.non_cgm_residual_threshold_cross_attribution import (
    build_non_cgm_residual_threshold_cross_attribution,
    load_json_artifact,
    render_non_cgm_residual_threshold_cross_attribution_markdown,
)


def test_build_non_cgm_residual_threshold_cross_attribution_locks_residual_surface() -> None:
    report = build_non_cgm_residual_threshold_cross_attribution(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        max_cycles=5,
        max_users=96,
        policy_artifact_path="artifacts/models/policy_model_v1.json",
        reference_effect_artifact_path="artifacts/models/effect_model_v3.json",
        candidate_effect_artifact_path=(
            "artifacts/models/effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        family_diagnostic=load_json_artifact(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        family_diagnostic_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        subgroup_diagnostic=load_json_artifact(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json"
        ),
        subgroup_diagnostic_path=(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json"
        ),
        mid_margin_diagnostic=load_json_artifact(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json"
        ),
        mid_margin_diagnostic_path=(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json"
        ),
        prior_small_drop_attribution=load_json_artifact(
            "artifacts/reports/non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json"
        ),
        prior_small_drop_attribution_path=(
            "artifacts/reports/non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json"
        ),
    )

    assert report["audit_name"] == "non_cgm_residual_threshold_cross_attribution_v2"
    assert (
        report["target_residual_slice"]["decision_family"]
        == "non_cgm_continue_to_monitor_threshold_cross"
    )
    assert report["reproduction_chain"]["family_case_count"] == 26
    assert report["reproduction_chain"]["threshold_duration_sensitive_case_count"] == 10
    assert report["reproduction_chain"]["mid_margin_case_count"] == 9
    assert report["reproduction_chain"]["prior_small_drop_case_count"] == 5
    assert report["reproduction_chain"]["current_residual_case_count"] == 4
    assert report["target_residual_slice"]["bucket_case_counts"] == {
        "large_drop": 3,
        "medium_drop": 1,
    }
    assert report["target_residual_slice"]["trajectory_step_values"] == [-0.063114]
    assert report["target_residual_slice"]["day_index_values"] == [0.071532]
    assert report["bucket_summaries"]["large_drop"]["second_opposing_feature_counts"] == {
        "schedule::before_dinner": 3
    }
    assert report["bucket_summaries"]["medium_drop"]["second_opposing_feature_counts"] == {
        "dose::l_theanine": 1
    }
    assert (
        report["residual_contribution_summary"]["negative_abs_share_pct"]["score_geometry"]
        > report["residual_contribution_summary"]["negative_abs_share_pct"][
            "trajectory_step_behavior"
        ]
    )
    assert report["residual_contribution_summary"]["mixed_overlap_case_count"] == 4
    assert report["verdict"]["primary_residual_family"] == "mixed_residual_overlap"
    assert report["verdict"]["explained_well_enough_for_future_gate_work"] is False
    assert report["validation_issues"] == []


def test_render_non_cgm_residual_threshold_cross_attribution_markdown_contains_sections() -> None:
    markdown = render_non_cgm_residual_threshold_cross_attribution_markdown(
        {
            "target_residual_slice": {"observed_case_count": 4},
            "reproduction_chain": {"family_case_count": 26},
            "residual_contribution_summary": {
                "negative_abs_share_pct": {"score_geometry": 74.52}
            },
            "verdict": {"primary_residual_family": "mixed_residual_overlap"},
            "summary_findings": ["Residual surface remains mixed."],
            "validation_issues": [],
        }
    )

    assert "# non-cgm residual threshold-cross attribution v2" in markdown
    assert "## target residual slice" in markdown
    assert "## reproduction chain" in markdown
    assert "## residual contribution summary" in markdown
    assert "## verdict" in markdown
    assert "## validation" in markdown
