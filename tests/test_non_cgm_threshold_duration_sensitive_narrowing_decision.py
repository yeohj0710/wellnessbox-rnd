from wellnessbox_rnd.evals.non_cgm_threshold_duration_sensitive_narrowing_decision import (
    build_non_cgm_threshold_duration_sensitive_narrowing_decision,
    load_json_artifact,
    render_non_cgm_threshold_duration_sensitive_narrowing_decision_markdown,
)


def test_build_threshold_duration_sensitive_narrowing_decision_matches_current_bucket() -> None:
    decision = build_non_cgm_threshold_duration_sensitive_narrowing_decision(
        subgroup_diagnostic=load_json_artifact(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json"
        ),
        subgroup_diagnostic_path=(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json"
        ),
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_narrowing_decision_v1"
    )
    assert decision["decision_gate"]["subtarget_mode"] == "threshold_duration_sensitive"
    assert decision["decision_gate"]["chosen_first_margin_bucket"] == "mid_margin"
    assert decision["decision_gate"]["chosen_first_margin_bucket_case_count"] == 9
    assert decision["decision_gate"]["chosen_first_margin_bucket_share_pct"] == 90.0
    assert decision["evidence_summary"]["feature_anchor"]["dominant_feature_family"] == "intercept"
    assert decision["validation_issues"] == []


def test_render_threshold_duration_sensitive_narrowing_markdown_contains_sections() -> None:
    markdown = render_non_cgm_threshold_duration_sensitive_narrowing_decision_markdown(
        {
            "decision_gate": {"chosen_first_margin_bucket": "mid_margin"},
            "evidence_summary": {"subtarget": {"observed_case_count": 10}},
            "decision_rationale": ["Choose the largest margin bucket first."],
            "deferred_subtargets": [{"margin_bucket": "comfortable_margin"}],
            "required_success_evidence": ["Subgroup count decreases."],
            "summary_findings": ["Focus on mid_margin first."],
            "validation_issues": [],
        }
    )

    assert "# non-cgm threshold-duration-sensitive narrowing decision v1" in markdown
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## decision rationale" in markdown
    assert "## deferred subtargets" in markdown
    assert "## validation" in markdown
