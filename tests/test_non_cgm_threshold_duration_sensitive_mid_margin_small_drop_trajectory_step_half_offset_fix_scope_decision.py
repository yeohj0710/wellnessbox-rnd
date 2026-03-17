from importlib import import_module

decision_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_half_offset_fix_scope_decision"
)


def test_build_trajectory_step_half_offset_fix_scope_decision_stays_bounded() -> None:
    decision = decision_module.build_trajectory_step_half_offset_fix_scope_decision(
        mode_decision=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_mode_decision_v1.json"
        ),
        mode_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_mode_decision_v1.json"
        ),
        probe_decision=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_probe_decision_v1.json"
        ),
        probe_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_probe_decision_v1.json"
        ),
        half_offset_counterfactual=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1.json"
        ),
        half_offset_counterfactual_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1.json"
        ),
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_half_offset_fix_scope_decision_v1"
    )
    assert (
        decision["decision_gate"]["chosen_fix_scope"]
        == "trajectory_step_half_offset_local_score_handling"
    )
    assert decision["decision_gate"]["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert decision["decision_gate"]["chosen_probe_fraction"] == 0.5
    assert decision["decision_gate"]["all_cases_cleared"] is True
    assert decision["decision_gate"]["min_residual_clearance_positive"] is True
    assert decision["decision_gate"]["cycle_conditioned_mode_needed_now"] is False
    assert decision["decision_gate"]["second_feature_widening_needed_now"] is False
    assert decision["validation_issues"] == []


def test_render_trajectory_step_half_offset_fix_scope_decision_markdown_contains_sections(
) -> None:
    markdown = decision_module.render_trajectory_step_half_offset_fix_scope_decision_markdown(
        {
            "decision_gate": {"chosen_probe_fraction": 0.5},
            "evidence_summary": {
                "counterfactual_read": {"all_cases_cleared": True}
            },
            "decision_rationale": ["Stay on the bounded half-offset path first."],
            "deferred_paths": [{"path": "cycle_conditioned_offset"}],
            "summary_findings": ["All 5 cases still clear with positive residual room."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "trajectory-step half-offset fix-scope decision v1" in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## decision rationale" in markdown
    assert "## deferred paths" in markdown
    assert "## summary findings" in markdown
    assert "## validation" in markdown
