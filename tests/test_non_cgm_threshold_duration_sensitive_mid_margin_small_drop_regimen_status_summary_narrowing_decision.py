from importlib import import_module

narrowing_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "regimen_status_summary_narrowing_decision"
)


def test_build_regimen_status_summary_narrowing_decision_matches_current_feature_target() -> None:
    decision = narrowing_module.build_regimen_status_summary_narrowing_decision(
        family_diagnostic=narrowing_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_diagnostic_v1.json"
        ),
        family_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_diagnostic_v1.json"
        ),
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "regimen_status_summary_narrowing_decision_v1"
    )
    assert decision["decision_gate"]["chosen_feature_family"] == "regimen_status_summary"
    assert decision["decision_gate"]["chosen_first_feature"] == "regimen_count"
    assert decision["decision_gate"]["chosen_first_feature_value"] == 0.12365
    assert decision["validation_issues"] == []


def test_render_regimen_status_summary_narrowing_decision_markdown_contains_sections() -> None:
    markdown = narrowing_module.render_regimen_status_summary_narrowing_decision_markdown(
        {
            "decision_gate": {"chosen_first_feature": "regimen_count"},
            "evidence_summary": {"family_target": {"observed_matching_case_count": 5}},
            "decision_rationale": ["Choose the largest family-internal feature first."],
            "deferred_subtargets": [{"feature": "planned_regimen_count"}],
            "required_success_evidence": ["regimen_count no longer dominates."],
            "summary_findings": ["Focus on regimen_count first."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "regimen-status-summary narrowing decision v1" in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## decision rationale" in markdown
    assert "## validation" in markdown
