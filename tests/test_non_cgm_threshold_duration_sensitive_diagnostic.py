from wellnessbox_rnd.evals.non_cgm_threshold_duration_sensitive_diagnostic import (
    build_non_cgm_threshold_duration_sensitive_diagnostic,
    load_json_artifact,
    render_non_cgm_threshold_duration_sensitive_diagnostic_markdown,
)


def test_build_non_cgm_threshold_duration_sensitive_diagnostic_matches_narrowing_target() -> None:
    diagnostic = build_non_cgm_threshold_duration_sensitive_diagnostic(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        max_cycles=5,
        max_users=96,
        policy_artifact_path="artifacts/models/policy_model_v1.json",
        reference_effect_artifact_path="artifacts/models/effect_model_v3.json",
        candidate_effect_artifact_path=(
            "artifacts/models/effect_model_v3_training_view_enforced_"
            "slice_balanced_candidate.json"
        ),
        narrowing_decision=load_json_artifact(
            "artifacts/reports/non_cgm_threshold_cross_narrowing_decision_v1.json"
        ),
        narrowing_decision_path=(
            "artifacts/reports/non_cgm_threshold_cross_narrowing_decision_v1.json"
        ),
    )

    assert diagnostic["audit_name"] == "non_cgm_threshold_duration_sensitive_diagnostic_v1"
    assert diagnostic["subtarget"]["trajectory_mode"] == "threshold_duration_sensitive"
    assert diagnostic["subtarget"]["expected_case_count_from_narrowing_decision"] == 10
    assert diagnostic["subtarget"]["observed_case_count"] == 10
    assert diagnostic["case_summary"]["parent_family_share_pct"] == 38.46
    assert diagnostic["workflow_summary"]["reference_continue_margin_bucket_counts"] == {
        "comfortable_margin": 1,
        "mid_margin": 9,
    }
    assert diagnostic["readable_summary"]["feature_digest"]["dominant_family"] == "intercept"
    assert diagnostic["validation_issues"] == []


def test_render_non_cgm_threshold_duration_sensitive_markdown_contains_sections() -> None:
    markdown = render_non_cgm_threshold_duration_sensitive_diagnostic_markdown(
        {
            "readable_summary": {"case_digest": {"observed_case_count": 10}},
            "subtarget": {"trajectory_mode": "threshold_duration_sensitive"},
            "workflow_summary": {"reference_continue_margin_bucket_counts": {"mid_margin": 9}},
            "case_summary": {"all_cases_match_target_mode": True},
            "feature_summary": {"top_absolute_features": [{"feature": "__intercept__"}]},
            "interpretation": {
                "dominant_feature_family": "intercept",
                "summary": "Current subgroup remains intercept-led.",
            },
            "summary_findings": ["Threshold duration sensitive remains the first subtarget."],
            "validation_issues": [],
        }
    )

    assert "# non-cgm threshold-duration-sensitive diagnostic v1" in markdown
    assert "## readable summary" in markdown
    assert "## subtarget" in markdown
    assert "## workflow summary" in markdown
    assert "## feature summary" in markdown
    assert "Current subgroup remains intercept-led." in markdown
