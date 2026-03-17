from importlib import import_module

diagnostic_module = import_module(
    "wellnessbox_rnd.evals."
    "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_diagnostic"
)


def test_build_regimen_count_diagnostic_matches_current_feature_target() -> None:
    diagnostic = diagnostic_module.build_regimen_count_diagnostic(
        slice_diagnostic=diagnostic_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        slice_diagnostic_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic_v1.json"
        ),
        feature_decision=diagnostic_module.load_json_artifact(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_narrowing_decision_v1.json"
        ),
        feature_decision_path=(
            "artifacts/reports/"
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_narrowing_decision_v1.json"
        ),
    )

    assert (
        diagnostic["audit_name"]
        == "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "regimen_count_diagnostic_v1"
    )
    assert diagnostic["feature_target"]["chosen_feature"] == "regimen_count"
    assert diagnostic["feature_target"]["observed_case_count"] == 5
    assert diagnostic["feature_summary"]["value_summary"]["sum"] == 0.12365
    assert diagnostic["validation_issues"] == []


def test_render_regimen_count_diagnostic_markdown_contains_sections() -> None:
    markdown = diagnostic_module.render_regimen_count_diagnostic_markdown(
        {
            "readable_summary": {"feature_digest": {"chosen_feature": "regimen_count"}},
            "feature_target": {"chosen_feature": "regimen_count"},
            "feature_summary": {"value_summary": {"sum": 0.12365}},
            "summary_findings": ["Focus on regimen_count first."],
            "validation_issues": [],
        }
    )

    assert (
        "# non-cgm threshold-duration-sensitive mid-margin small-drop "
        "regimen-count diagnostic v1" in markdown
    )
    assert "## readable summary" in markdown
    assert "## feature target" in markdown
    assert "## feature summary" in markdown
    assert "## validation" in markdown
