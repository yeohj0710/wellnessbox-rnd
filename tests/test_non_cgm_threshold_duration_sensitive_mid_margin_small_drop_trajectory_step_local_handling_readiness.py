from importlib import import_module

readiness_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_local_handling_readiness"
)


def test_build_trajectory_step_local_handling_readiness_stays_single_feature_first() -> None:
    readiness = readiness_module.build_trajectory_step_local_handling_readiness(
        competition_decision=readiness_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_score_competition_decision_v1.json"
        ),
        competition_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_score_competition_decision_v1.json"
        ),
        trajectory_step_counterfactual=readiness_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
        trajectory_step_counterfactual_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
        trajectory_step_fix_scope_decision=readiness_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fix_scope_decision_v1.json"
        ),
        trajectory_step_fix_scope_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fix_scope_decision_v1.json"
        ),
    )

    assert (
        readiness["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_local_handling_readiness_v1"
    )
    assert readiness["readiness_gate"]["chosen_first_opposing_feature"] == "trajectory_step"
    assert (
        readiness["readiness_gate"]["deferred_second_opposing_feature"]
        == "dose::l_theanine"
    )
    assert readiness["readiness_gate"]["single_feature_path_supported"] is True
    assert readiness["readiness_gate"]["widen_to_second_feature_needed_now"] is False
    assert readiness["validation_issues"] == []


def test_render_trajectory_step_local_handling_readiness_markdown_contains_sections() -> None:
    markdown = readiness_module.render_trajectory_step_local_handling_readiness_markdown(
        {
            "readiness_gate": {"chosen_first_opposing_feature": "trajectory_step"},
            "evidence_summary": {"feature_gap_digest": {"first_minus_second_abs_gap": 0.01}},
            "summary_findings": ["Stay on single-feature local handling first."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "trajectory-step local-handling readiness v1" in markdown
    )
    assert "## readiness gate" in markdown
    assert "## evidence summary" in markdown
    assert "## summary findings" in markdown
    assert "## validation" in markdown
