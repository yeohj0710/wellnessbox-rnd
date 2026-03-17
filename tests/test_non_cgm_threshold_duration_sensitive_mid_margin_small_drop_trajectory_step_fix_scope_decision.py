from importlib import import_module

decision_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_fix_scope_decision"
)


def test_build_trajectory_step_fix_scope_decision_closes_multifeature_mix_story() -> None:
    decision = decision_module.build_trajectory_step_fix_scope_decision(
        competition_decision=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_score_competition_decision_v1.json"
        ),
        competition_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_score_competition_decision_v1.json"
        ),
        trajectory_step_counterfactual=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
        trajectory_step_counterfactual_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_fix_scope_decision_v1"
    )
    assert decision["decision_gate"]["chosen_first_opposing_feature"] == "trajectory_step"
    assert (
        decision["decision_gate"]["chosen_fix_scope"]
        == "trajectory_step_local_score_handling"
    )
    assert decision["decision_gate"]["widen_to_multifeature_mix_supported"] is False
    assert decision["validation_issues"] == []


def test_render_trajectory_step_fix_scope_decision_markdown_contains_sections() -> None:
    markdown = decision_module.render_trajectory_step_fix_scope_decision_markdown(
        {
            "decision_gate": {"chosen_first_opposing_feature": "trajectory_step"},
            "evidence_summary": {"per_case_surface": {"case_row_count": 5}},
            "decision_rationale": ["Close multifeature mix first."],
            "deferred_subtargets": [{"target": "dose::l_theanine"}],
            "required_success_evidence": ["Stay on the same 5-case slice."],
            "summary_findings": ["Test trajectory-step-local handling first."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "trajectory-step fix-scope decision v1" in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## deferred subtargets" in markdown
    assert "## validation" in markdown
