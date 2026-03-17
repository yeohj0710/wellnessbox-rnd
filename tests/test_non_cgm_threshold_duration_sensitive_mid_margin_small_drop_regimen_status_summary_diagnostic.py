from importlib import import_module

diagnostic_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_status_summary_diagnostic"
)


def test_build_regimen_status_summary_diagnostic_matches_current_family_target() -> None:
    diagnostic = diagnostic_module.build_regimen_status_summary_diagnostic(
        slice_diagnostic=diagnostic_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        slice_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        family_decision=diagnostic_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_v1.json"
        ),
        family_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_v1.json"
        ),
    )

    assert (
        diagnostic["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "regimen_status_summary_diagnostic_v1"
    )
    assert diagnostic["family_target"]["chosen_feature_family"] == "regimen_status_summary"
    assert diagnostic["family_target"]["observed_matching_case_count"] == 5
    assert diagnostic["family_target"]["family_absolute_value"] == 0.281435
    assert (
        diagnostic["family_feature_summary"]["top_absolute_feature"]["feature"]
        == "regimen_count"
    )
    assert diagnostic["validation_issues"] == []


def test_render_regimen_status_summary_diagnostic_markdown_contains_sections() -> None:
    markdown = diagnostic_module.render_regimen_status_summary_diagnostic_markdown(
        {
            "readable_summary": {"case_digest": {"observed_matching_case_count": 5}},
            "family_target": {"chosen_feature_family": "regimen_status_summary"},
            "family_feature_summary": {
                "top_absolute_feature": {"feature": "regimen_count"}
            },
            "summary_findings": ["Focus on regimen_count first."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "regimen-status-summary diagnostic v1" in markdown
    )
    assert "## readable summary" in markdown
    assert "## family target" in markdown
    assert "## family feature summary" in markdown
    assert "## validation" in markdown
