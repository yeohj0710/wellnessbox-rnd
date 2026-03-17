from importlib import import_module

decision_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_score_competition_decision"
)


def test_build_regimen_count_score_competition_decision_picks_first_opposing_feature() -> None:
    decision = decision_module.build_regimen_count_score_competition_decision(
        slice_diagnostic=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        slice_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        fix_scope_decision=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_fix_scope_decision_v1.json"
        ),
        fix_scope_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_fix_scope_decision_v1.json"
        ),
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "regimen_count_score_competition_decision_v1"
    )
    assert decision["decision_gate"]["chosen_feature"] == "regimen_count"
    assert (
        decision["decision_gate"]["chosen_first_opposing_feature"] == "trajectory_step"
    )
    assert decision["decision_gate"]["intercept_left_deferred"] is True
    assert decision["validation_issues"] == []


def test_render_regimen_count_score_competition_decision_markdown_contains_sections() -> None:
    markdown = decision_module.render_regimen_count_score_competition_decision_markdown(
        {
            "decision_gate": {"chosen_first_opposing_feature": "trajectory_step"},
            "evidence_summary": {"opposing_feature_ranking": []},
            "decision_rationale": ["Focus on the largest opposing feature first."],
            "deferred_subtargets": [{"feature": "dose::l_theanine"}],
            "required_success_evidence": ["Keep the same 5-case slice."],
            "summary_findings": ["Do not reopen training."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "regimen-count score-competition decision v1" in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## deferred subtargets" in markdown
    assert "## validation" in markdown
