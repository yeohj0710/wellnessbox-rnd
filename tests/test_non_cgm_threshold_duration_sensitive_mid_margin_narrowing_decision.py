from wellnessbox_rnd.evals import (
    non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision as narrowing_decision,
)


def test_build_mid_margin_narrowing_decision_matches_current_proxy_drop_target() -> None:
    build_decision = (
        narrowing_decision.build_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision
    )
    decision = build_decision(
        bucket_diagnostic=narrowing_decision.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json"
        ),
        bucket_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json"
        ),
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_v1"
    )
    assert decision["decision_gate"]["subtarget_mode"] == "threshold_duration_sensitive"
    assert decision["decision_gate"]["margin_bucket"] == "mid_margin"
    assert decision["decision_gate"]["chosen_first_proxy_drop_bucket"] == "small_drop"
    assert decision["decision_gate"]["chosen_first_proxy_drop_bucket_case_count"] == 5
    assert decision["decision_gate"]["chosen_first_proxy_drop_bucket_share_pct"] == 55.56
    assert decision["evidence_summary"]["feature_anchor"]["dominant_feature_family"] == "intercept"
    assert decision["validation_issues"] == []


def test_render_mid_margin_narrowing_markdown_contains_sections() -> None:
    markdown = (
        narrowing_decision.render_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_markdown(
            {
                "decision_gate": {"chosen_first_proxy_drop_bucket": "small_drop"},
                "evidence_summary": {"bucket_target": {"observed_case_count": 9}},
                "decision_rationale": ["Choose the largest proxy-drop bucket first."],
                "deferred_subtargets": [{"proxy_drop_bucket": "large_drop"}],
                "required_success_evidence": ["small_drop count decreases."],
                "summary_findings": ["Focus on small_drop first."],
                "validation_issues": [],
            }
        )
    )

    assert "# non-cgm threshold-duration-sensitive mid-margin narrowing decision v1" in markdown
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## decision rationale" in markdown
    assert "## deferred subtargets" in markdown
    assert "## validation" in markdown
