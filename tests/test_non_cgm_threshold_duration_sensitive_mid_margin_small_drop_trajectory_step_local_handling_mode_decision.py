from importlib import import_module

decision_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_local_handling_mode_decision"
)


def test_build_trajectory_step_local_handling_mode_decision_stays_fixed_and_uniform() -> None:
    decision = decision_module.build_trajectory_step_local_handling_mode_decision(
        readiness=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_readiness_v1.json"
        ),
        readiness_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_readiness_v1.json"
        ),
        fix_scope_decision=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fix_scope_decision_v1.json"
        ),
        fix_scope_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fix_scope_decision_v1.json"
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
        slice_diagnostic=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "diagnostic_v1.json"
        ),
        slice_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "diagnostic_v1.json"
        ),
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_local_handling_mode_decision_v1"
    )
    assert decision["decision_gate"]["chosen_first_opposing_feature"] == "trajectory_step"
    assert (
        decision["decision_gate"]["chosen_local_handling_mode"]
        == "fixed_uniform_offset"
    )
    assert decision["decision_gate"]["trajectory_step_value_uniform"] is True
    assert decision["decision_gate"]["final_cycle_index_uniform"] is True
    assert decision["decision_gate"]["cycle_conditioned_mode_needed_now"] is False
    assert decision["decision_gate"]["second_feature_widening_needed_now"] is False
    assert decision["validation_issues"] == []


def test_render_trajectory_step_local_handling_mode_decision_markdown_contains_sections(
) -> None:
    markdown = (
        decision_module.render_trajectory_step_local_handling_mode_decision_markdown(
            {
                "decision_gate": {
                    "chosen_local_handling_mode": "fixed_uniform_offset"
                },
                "evidence_summary": {
                    "uniformity_digest": {"trajectory_step_value_uniform": True}
                },
                "decision_rationale": ["Stay fixed and uniform first."],
                "deferred_modes": [{"mode": "cycle_conditioned_offset"}],
                "summary_findings": ["Do not widen yet."],
                "validation_issues": [],
            }
        )
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "trajectory-step local-handling mode decision v1" in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## decision rationale" in markdown
    assert "## deferred modes" in markdown
    assert "## summary findings" in markdown
    assert "## validation" in markdown
