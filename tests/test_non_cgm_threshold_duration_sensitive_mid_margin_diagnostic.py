from wellnessbox_rnd.evals.non_cgm_threshold_duration_sensitive_mid_margin_diagnostic import (
    build_non_cgm_threshold_duration_sensitive_mid_margin_diagnostic,
    load_json_artifact,
    render_non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_markdown,
)


def test_build_mid_margin_diagnostic_matches_current_bucket_target() -> None:
    diagnostic = build_non_cgm_threshold_duration_sensitive_mid_margin_diagnostic(
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
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_narrowing_decision_v1.json"
        ),
        narrowing_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_narrowing_decision_v1.json"
        ),
    )

    assert (
        diagnostic["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1"
    )
    assert diagnostic["bucket_target"]["trajectory_mode"] == "threshold_duration_sensitive"
    assert diagnostic["bucket_target"]["margin_bucket"] == "mid_margin"
    assert diagnostic["bucket_target"]["expected_case_count_from_narrowing_decision"] == 9
    assert diagnostic["bucket_target"]["observed_case_count"] == 9
    assert diagnostic["readable_summary"]["feature_digest"]["dominant_family"] == "intercept"
    assert diagnostic["validation_issues"] == []


def test_render_mid_margin_diagnostic_markdown_contains_sections() -> None:
    markdown = render_non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_markdown(
        {
            "readable_summary": {"case_digest": {"observed_case_count": 9}},
            "bucket_target": {"margin_bucket": "mid_margin"},
            "workflow_summary": {"proxy_drop_bucket_counts": {"small_drop": 4}},
            "case_summary": {"all_cases_match_target_bucket": True},
            "feature_summary": {"top_absolute_features": [{"feature": "__intercept__"}]},
            "interpretation": {
                "dominant_feature_family": "intercept",
                "summary": "Mid-margin bucket remains intercept-led.",
            },
            "summary_findings": ["Focus on the mid_margin bucket."],
            "validation_issues": [],
        }
    )

    assert "# non-cgm threshold-duration-sensitive mid-margin diagnostic v1" in markdown
    assert "## readable summary" in markdown
    assert "## bucket target" in markdown
    assert "## workflow summary" in markdown
    assert "## feature summary" in markdown
    assert "Mid-margin bucket remains intercept-led." in markdown
