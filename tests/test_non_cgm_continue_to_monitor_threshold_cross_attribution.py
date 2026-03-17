from importlib import import_module

attribution_module = import_module(
    "wellnessbox_rnd.evals.non_cgm_continue_to_monitor_threshold_cross_attribution"
)


def test_build_non_cgm_continue_to_monitor_threshold_cross_attribution_locks_current_surface(
) -> None:
    report = attribution_module.build_non_cgm_continue_to_monitor_threshold_cross_attribution(
        family_diagnostic=attribution_module.load_json_artifact(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        family_diagnostic_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        subgroup_diagnostic=attribution_module.load_json_artifact(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json"
        ),
        subgroup_diagnostic_path=(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_diagnostic_v1.json"
        ),
        mid_margin_diagnostic=attribution_module.load_json_artifact(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json"
        ),
        mid_margin_diagnostic_path=(
            "artifacts/reports/non_cgm_threshold_duration_sensitive_mid_margin_diagnostic_v1.json"
        ),
        small_drop_diagnostic=attribution_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        small_drop_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        regimen_count_counterfactual=attribution_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_counterfactual_v1.json"
        ),
        regimen_count_counterfactual_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_counterfactual_v1.json"
        ),
        trajectory_step_counterfactual=attribution_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
        trajectory_step_counterfactual_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_counterfactual_v1.json"
        ),
        half_offset_counterfactual=attribution_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1.json"
        ),
        half_offset_counterfactual_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1.json"
        ),
        local_contract=attribution_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_local_contract_v1.json"
        ),
        local_contract_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_local_contract_v1.json"
        ),
        final_kpi_compare_report=attribution_module.load_json_artifact(
            "artifacts/reports/final_kpi_compare_report_v1.json"
        ),
        final_kpi_compare_report_path="artifacts/reports/final_kpi_compare_report_v1.json",
    )

    assert report["audit_name"] == "non_cgm_continue_to_monitor_threshold_cross_attribution_v1"
    assert (
        report["family_anchor"]["decision_family"]
        == "non_cgm_continue_to_monitor_threshold_cross"
    )
    assert report["family_anchor"]["observed_case_count"] == 26
    assert report["narrowing_chain"]["threshold_duration_sensitive"]["observed_case_count"] == 10
    assert report["narrowing_chain"]["mid_margin"]["observed_case_count"] == 9
    assert report["narrowing_chain"]["small_drop"]["observed_case_count"] == 5
    assert report["low_risk_non_cgm_context"]["dominant_candidate_regression_slice"] == "low_risk"
    assert report["low_risk_non_cgm_context"]["current_smallest_surface_low_risk_case_count"] == 5
    assert report["final_step_vs_earlier_step"]["final_step_only_supported"] is True
    assert report["surface_attribution"]["protective_counterbalance"]["feature"] == "regimen_count"
    assert (
        report["surface_attribution"]["dominant_opposing_surface"]["feature"]
        == "trajectory_step"
    )
    assert report["surface_attribution"]["minimal_local_contract"]["probe_fraction"] == 0.5
    assert (
        report["attribution_verdict"]["current_smallest_surface_sufficient_for_explanation"]
        is True
    )
    assert (
        report["attribution_verdict"]["sufficiency_scope"]
        == "sufficient_for_current_5_case_small_drop_slice_only"
    )
    assert report["attribution_verdict"]["training_rerun_still_blocked"] is True
    assert report["validation_issues"] == []


def test_render_non_cgm_continue_to_monitor_threshold_cross_attribution_markdown_contains_sections(
) -> None:
    markdown = (
        attribution_module.render_non_cgm_continue_to_monitor_threshold_cross_attribution_markdown(
            {
                "readable_summary": {
                    "verdict_digest": {"training_rerun_still_blocked": True}
                },
                "family_anchor": {
                    "decision_family": "non_cgm_continue_to_monitor_threshold_cross"
                },
                "surface_attribution": {
                    "dominant_opposing_surface": {"feature": "trajectory_step"}
                },
                "attribution_verdict": {
                    "current_smallest_surface_sufficient_for_explanation": True
                },
                "summary_findings": [
                    "Current smallest surface is sufficient for the 5-case slice."
                ],
                "validation_issues": [],
            }
        )
    )

    assert "# non-cgm continue-to-monitor threshold-cross attribution v1" in markdown
    assert "## readable summary" in markdown
    assert "## family anchor" in markdown
    assert "## surface attribution" in markdown
    assert "## attribution verdict" in markdown
    assert "## validation" in markdown
