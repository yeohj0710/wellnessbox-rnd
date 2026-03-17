from importlib import import_module

narrowing_decision = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision"
)


def test_build_small_drop_narrowing_decision_matches_current_family_target() -> None:
    decision = (
        narrowing_decision.build_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision(
            slice_diagnostic=narrowing_decision.load_json_artifact(
                "artifacts/reports/"
                "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
            ),
            slice_diagnostic_path=(
                "artifacts/reports/"
                "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
            ),
        )
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_v1"
    )
    assert decision["decision_gate"]["trajectory_mode"] == "threshold_duration_sensitive"
    assert decision["decision_gate"]["margin_bucket"] == "mid_margin"
    assert decision["decision_gate"]["proxy_drop_bucket"] == "small_drop"
    assert (
        decision["decision_gate"]["chosen_first_feature_family"]
        == "regimen_status_summary"
    )
    assert (
        decision["evidence_summary"]["current_feature_anchor"]["dominant_family"]
        == "intercept"
    )
    assert decision["validation_issues"] == []


def test_render_small_drop_narrowing_markdown_contains_sections() -> None:
    markdown = (
        narrowing_decision.render_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_markdown(
            {
                "decision_gate": {"chosen_first_feature_family": "regimen_status_summary"},
                "evidence_summary": {"slice_target": {"observed_case_count": 5}},
                "decision_rationale": ["Choose the largest non-intercept family first."],
                "deferred_subtargets": [{"feature_family": "user_context"}],
                "required_success_evidence": ["family dominance decreases."],
                "summary_findings": ["Focus on regimen_status_summary first."],
                "validation_issues": [],
            }
        )
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop narrowing decision v1"
        in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## decision rationale" in markdown
    assert "## deferred subtargets" in markdown
    assert "## validation" in markdown
