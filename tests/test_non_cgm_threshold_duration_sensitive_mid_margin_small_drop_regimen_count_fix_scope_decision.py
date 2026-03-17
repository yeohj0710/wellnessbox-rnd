from importlib import import_module

decision_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_fix_scope_decision"
)


def test_build_regimen_count_fix_scope_decision_closes_feature_absence_story() -> None:
    decision = decision_module.build_regimen_count_fix_scope_decision(
        regimen_count_diagnostic=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_diagnostic_v1.json"
        ),
        regimen_count_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_diagnostic_v1.json"
        ),
        regimen_count_counterfactual=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_counterfactual_v1.json"
        ),
        regimen_count_counterfactual_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_counterfactual_v1.json"
        ),
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "regimen_count_fix_scope_decision_v1"
    )
    assert decision["decision_gate"]["chosen_feature"] == "regimen_count"
    assert decision["decision_gate"]["chosen_fix_scope"] == "score_aggregation_or_competition"
    assert decision["decision_gate"]["raw_feature_absence_story_supported"] is False
    assert decision["decision_gate"]["same_size_counterfactual_clears_shortfall"] is True
    assert decision["validation_issues"] == []


def test_render_regimen_count_fix_scope_decision_markdown_contains_sections() -> None:
    markdown = decision_module.render_regimen_count_fix_scope_decision_markdown(
        {
            "decision_gate": {"chosen_feature": "regimen_count"},
            "evidence_summary": {"case_row_count": 5},
            "decision_rationale": ["Close feature absence first."],
            "deferred_subtargets": [{"target": "planned_regimen_count"}],
            "required_success_evidence": ["Stay on the same 5-case slice."],
            "summary_findings": ["Use a score-side bounded fix next."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "regimen-count fix-scope decision v1" in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## deferred subtargets" in markdown
    assert "## validation" in markdown
