from importlib import import_module

decision_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_fixed_uniform_offset_probe_decision"
)


def test_build_trajectory_step_fixed_uniform_offset_probe_decision_chooses_half_first() -> None:
    decision = decision_module.build_trajectory_step_fixed_uniform_offset_probe_decision(
        feasibility=decision_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_feasibility_v1.json"
        ),
        feasibility_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_feasibility_v1.json"
        ),
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
    )

    assert (
        decision["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_fixed_uniform_offset_probe_decision_v1"
    )
    assert decision["decision_gate"]["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert decision["decision_gate"]["chosen_probe_fraction"] == 0.5
    assert decision["decision_gate"]["chosen_probe_offset_abs_value"] == 0.031557
    assert decision["decision_gate"]["chosen_probe_clears_all_cases"] is True
    assert decision["validation_issues"] == []


def test_render_trajectory_step_fixed_uniform_offset_probe_decision_markdown_contains_sections(
) -> None:
    markdown = (
        decision_module.render_trajectory_step_fixed_uniform_offset_probe_decision_markdown(
            {
                "decision_gate": {"chosen_probe_fraction": 0.5},
                "evidence_summary": {
                    "probe_comparison_digest": {
                        "half_probe": {"clears_all_cases": True}
                    }
                },
                "summary_findings": ["Half probe is the first bounded clearing probe."],
                "validation_issues": [],
            }
        )
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "trajectory-step fixed-uniform-offset probe decision v1" in markdown
    )
    assert "## decision gate" in markdown
    assert "## evidence summary" in markdown
    assert "## summary findings" in markdown
    assert "## validation" in markdown
