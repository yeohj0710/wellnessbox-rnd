from wellnessbox_rnd.evals import (
    non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic as small_drop_diagnostic,
)


def test_build_small_drop_diagnostic_matches_current_slice_target() -> None:
    diagnostic = (
        small_drop_diagnostic.build_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic(
            dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
            max_cycles=5,
            max_users=96,
            policy_artifact_path="artifacts/models/policy_model_v1.json",
            reference_effect_artifact_path="artifacts/models/effect_model_v3.json",
            candidate_effect_artifact_path=(
                "artifacts/models/effect_model_v3_training_view_enforced_"
                "slice_balanced_candidate.json"
            ),
            narrowing_decision=small_drop_diagnostic.load_json_artifact(
                "artifacts/reports/"
                "non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_v1.json"
            ),
            narrowing_decision_path=(
                "artifacts/reports/"
                "non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_v1.json"
            ),
        )
    )

    assert (
        diagnostic["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1"
    )
    assert diagnostic["slice_target"]["trajectory_mode"] == "threshold_duration_sensitive"
    assert diagnostic["slice_target"]["margin_bucket"] == "mid_margin"
    assert diagnostic["slice_target"]["proxy_drop_bucket"] == "small_drop"
    assert diagnostic["slice_target"]["expected_case_count_from_narrowing_decision"] == 5
    assert diagnostic["slice_target"]["observed_case_count"] == 5
    assert diagnostic["readable_summary"]["feature_digest"]["dominant_family"] == "intercept"
    assert diagnostic["validation_issues"] == []


def test_render_small_drop_diagnostic_markdown_contains_sections() -> None:
    markdown = (
        small_drop_diagnostic.render_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_markdown(
            {
                "readable_summary": {"case_digest": {"observed_case_count": 5}},
                "slice_target": {"proxy_drop_bucket": "small_drop"},
                "workflow_summary": {"final_cycle_index_counts": {"4": 5}},
                "case_summary": {"all_cases_match_target_proxy_drop_bucket": True},
                "feature_summary": {"top_absolute_features": [{"feature": "__intercept__"}]},
                "interpretation": {
                    "dominant_feature_family": "intercept",
                    "summary": "Small-drop slice remains intercept-led.",
                },
                "summary_findings": ["Focus on the small_drop slice."],
                "validation_issues": [],
            }
        )
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop diagnostic v1"
        in markdown
    )
    assert "## readable summary" in markdown
    assert "## slice target" in markdown
    assert "## workflow summary" in markdown
    assert "## feature summary" in markdown
    assert "Small-drop slice remains intercept-led." in markdown
