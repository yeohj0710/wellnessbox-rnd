from importlib import import_module

counterfactual_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_half_offset_counterfactual"
)


def test_build_trajectory_step_half_offset_counterfactual_clears_all_cases() -> None:
    counterfactual = counterfactual_module.build_trajectory_step_half_offset_counterfactual(
        probe_decision=counterfactual_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_probe_decision_v1.json"
        ),
        probe_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_probe_decision_v1.json"
        ),
        trajectory_step_counterfactual=counterfactual_module.load_json_artifact(
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
        counterfactual["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_half_offset_counterfactual_v1"
    )
    assert counterfactual["target"]["chosen_probe_fraction"] == 0.5
    assert counterfactual["target"]["chosen_probe_offset_abs_value"] == 0.031557
    assert counterfactual["counterfactual_summary"]["cleared_case_count"] == 5
    assert counterfactual["counterfactual_summary"]["all_cases_cleared"] is True
    assert counterfactual["counterfactual_summary"]["min_residual_clearance"] == 0.0145
    assert counterfactual["validation_issues"] == []


def test_render_trajectory_step_half_offset_counterfactual_markdown_contains_sections(
) -> None:
    markdown = counterfactual_module.render_trajectory_step_half_offset_counterfactual_markdown(
        {
            "target": {"chosen_probe_fraction": 0.5},
            "counterfactual_summary": {"all_cases_cleared": True},
            "summary_findings": ["Half offset clears all cases."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "trajectory-step half-offset counterfactual v1" in markdown
    )
    assert "## target" in markdown
    assert "## counterfactual summary" in markdown
    assert "## summary findings" in markdown
    assert "## validation" in markdown
