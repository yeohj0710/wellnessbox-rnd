from importlib import import_module

counterfactual_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_counterfactual"
)


def test_build_regimen_count_counterfactual_matches_current_slice_signal() -> None:
    counterfactual = counterfactual_module.build_regimen_count_counterfactual(
        slice_diagnostic=counterfactual_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        slice_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        regimen_count_diagnostic=counterfactual_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_diagnostic_v1.json"
        ),
        regimen_count_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_diagnostic_v1.json"
        ),
    )

    assert (
        counterfactual["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "regimen_count_counterfactual_v1"
    )
    assert counterfactual["target"]["chosen_feature"] == "regimen_count"
    assert counterfactual["target"]["observed_case_count"] == 5
    assert counterfactual["counterfactual_summary"]["add_again_clears_shortfall_case_count"] == 5
    assert counterfactual["counterfactual_summary"]["removal_worsens_case_count"] == 5
    assert counterfactual["validation_issues"] == []


def test_render_regimen_count_counterfactual_markdown_contains_sections() -> None:
    markdown = counterfactual_module.render_regimen_count_counterfactual_markdown(
        {
            "readable_summary": {"counterfactual_digest": {"current_shortfall_mean": 0.01}},
            "target": {"chosen_feature": "regimen_count"},
            "counterfactual_summary": {"add_again_clears_shortfall_case_count": 5},
            "summary_findings": ["regimen_count add-again clears all cases."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "regimen-count counterfactual v1" in markdown
    )
    assert "## readable summary" in markdown
    assert "## target" in markdown
    assert "## counterfactual summary" in markdown
    assert "## validation" in markdown
