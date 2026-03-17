from importlib import import_module

feasibility_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_fixed_uniform_offset_feasibility"
)


def test_build_trajectory_step_fixed_uniform_offset_feasibility_has_half_offset_probe() -> None:
    feasibility = feasibility_module.build_trajectory_step_fixed_uniform_offset_feasibility(
        mode_decision=feasibility_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_mode_decision_v1.json"
        ),
        mode_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_mode_decision_v1.json"
        ),
        trajectory_step_counterfactual=feasibility_module.load_json_artifact(
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
        feasibility["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_fixed_uniform_offset_feasibility_v1"
    )
    assert feasibility["decision_gate"]["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert feasibility["decision_gate"]["full_offset_clears_all_cases"] is True
    assert feasibility["decision_gate"]["first_grid_fraction_clearing_all"] == 0.5
    assert feasibility["decision_gate"]["second_feature_widening_needed_now"] is False
    assert feasibility["validation_issues"] == []


def test_render_trajectory_step_fixed_uniform_offset_feasibility_markdown_contains_sections(
) -> None:
    markdown = (
        feasibility_module.render_trajectory_step_fixed_uniform_offset_feasibility_markdown(
            {
                "decision_gate": {"first_grid_fraction_clearing_all": 0.5},
                "evidence_summary": {
                    "offset_digest": {
                        "minimum_clearing_fraction_of_full_offset": 0.27
                    }
                },
                "summary_findings": ["Half offset clears all cases."],
                "validation_issues": [],
            }
        )
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "trajectory-step fixed-uniform-offset feasibility v1" in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## summary findings" in markdown
    assert "## validation" in markdown
