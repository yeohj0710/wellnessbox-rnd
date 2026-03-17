from importlib import import_module

contract_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
    "trajectory_step_half_offset_local_contract"
)


def test_build_trajectory_step_half_offset_local_contract_stays_uniform_and_ready() -> None:
    contract = contract_module.build_trajectory_step_half_offset_local_contract(
        fix_scope_decision=contract_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_fix_scope_decision_v1.json"
        ),
        fix_scope_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_fix_scope_decision_v1.json"
        ),
        half_offset_counterfactual=contract_module.load_json_artifact(
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
        contract["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_half_offset_local_contract_v1"
    )
    assert contract["contract_gate"]["chosen_local_contract"] == "uniform_score_gap_offset"
    assert contract["contract_gate"]["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert contract["contract_gate"]["chosen_probe_fraction"] == 0.5
    assert contract["contract_gate"]["chosen_probe_offset_abs_value"] == 0.031557
    assert contract["contract_gate"]["contract_ready_now"] is True
    assert contract["contract_gate"]["requires_case_specific_tuning_now"] is False
    assert contract["contract_gate"]["requires_second_feature_now"] is False
    assert contract["validation_issues"] == []


def test_render_trajectory_step_half_offset_local_contract_markdown_contains_sections() -> None:
    markdown = contract_module.render_trajectory_step_half_offset_local_contract_markdown(
        {
            "contract_gate": {"chosen_local_contract": "uniform_score_gap_offset"},
            "evidence_summary": {
                "contract_surface": {"all_cases_cleared": True}
            },
            "summary_findings": ["Uniform half-offset contract is ready."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "trajectory-step half-offset local contract v1" in markdown
    )
    assert "## contract gate" in markdown
    assert "## evidence summary" in markdown
    assert "## summary findings" in markdown
    assert "## validation" in markdown
