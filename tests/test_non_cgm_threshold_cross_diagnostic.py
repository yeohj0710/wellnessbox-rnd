from wellnessbox_rnd.evals.non_cgm_threshold_cross_diagnostic import (
    build_non_cgm_threshold_cross_diagnostic,
    load_json_artifact,
    render_non_cgm_threshold_cross_diagnostic_markdown,
)


def test_build_non_cgm_threshold_cross_diagnostic_matches_latest_replay_family() -> None:
    diagnostic = build_non_cgm_threshold_cross_diagnostic(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        max_cycles=5,
        max_users=96,
        policy_artifact_path="artifacts/models/policy_model_v1.json",
        reference_effect_artifact_path="artifacts/models/effect_model_v3.json",
        candidate_effect_artifact_path=(
            "artifacts/models/effect_model_v3_training_view_enforced_"
            "slice_balanced_candidate.json"
        ),
        compare_report=load_json_artifact(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "replay_compare_vs_baseline_v1.json"
        ),
        compare_report_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "replay_compare_vs_baseline_v1.json"
        ),
    )

    assert diagnostic["audit_name"] == "non_cgm_threshold_cross_diagnostic_v1"
    assert diagnostic["target_family"]["expected_case_count_from_compare"] == 26
    assert diagnostic["target_family"]["observed_case_count"] == 26
    assert diagnostic["case_summary"]["all_cases_non_cgm"] is True
    assert diagnostic["case_summary"]["all_transitions_match_target"] is True
    assert diagnostic["interpretation"]["threshold_edge_only_story_supported"] is False
    assert diagnostic["readable_summary"]["case_digest"]["observed_case_count"] == 26
    assert (
        diagnostic["readable_summary"]["dominant_feature_digest"]["family"]
        == "intercept"
    )
    assert diagnostic["summary_findings"]
    assert diagnostic["validation_issues"] == []


def test_render_non_cgm_threshold_cross_diagnostic_markdown_contains_sections() -> None:
    markdown = render_non_cgm_threshold_cross_diagnostic_markdown(
        {
            "target_family": {"name": "non_cgm_continue_to_monitor_threshold_cross"},
            "workflow_summary": {"trajectory_mode_counts": {"threshold_duration_sensitive": 10}},
            "case_summary": {"all_cases_non_cgm": True},
            "feature_summary": {"top_absolute_features": [{"feature": "__intercept__"}]},
            "readable_summary": {"case_digest": {"observed_case_count": 26}},
            "interpretation": {
                "threshold_edge_only_story_supported": False,
                "summary": "Not a pure threshold-edge story.",
            },
            "summary_findings": ["Current blocker remains non-cgm threshold cross."],
            "validation_issues": [],
        }
    )

    assert "# non-cgm threshold-cross diagnostic v1" in markdown
    assert "## readable summary" in markdown
    assert "## workflow summary" in markdown
    assert "## case summary" in markdown
    assert "## feature summary" in markdown
    assert "## summary findings" in markdown
    assert "Not a pure threshold-edge story." in markdown
