from pathlib import Path

from wellnessbox_rnd.evals.latest_candidate_cgm_slice_diagnostic import (
    build_latest_candidate_cgm_slice_diagnostic,
    load_json_artifact,
    render_latest_candidate_cgm_slice_diagnostic_markdown,
    validate_latest_candidate_cgm_slice_diagnostic,
    write_latest_candidate_cgm_slice_diagnostic_files,
)


def test_build_latest_candidate_cgm_slice_diagnostic_rejects_cgm_only_gate() -> None:
    diagnostic = build_latest_candidate_cgm_slice_diagnostic(
        compare_report=load_json_artifact(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "replay_compare_vs_baseline_v1.json"
        ),
        compare_report_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "replay_compare_vs_baseline_v1.json"
        ),
        final_compare_report=load_json_artifact(
            "artifacts/reports/final_kpi_compare_report_v1.json"
        ),
        final_compare_report_path="artifacts/reports/final_kpi_compare_report_v1.json",
        cgm_feature_audit_report=load_json_artifact(
            "artifacts/reports/cgm_combined_replay_feature_audit_v1.json"
        ),
        cgm_feature_audit_report_path="artifacts/reports/cgm_combined_replay_feature_audit_v1.json",
        cgm_geometry_report=load_json_artifact(
            "artifacts/reports/cgm_final_step_reoptimize_geometry_calibration_v1.json"
        ),
        cgm_geometry_report_path=(
            "artifacts/reports/cgm_final_step_reoptimize_geometry_calibration_v1.json"
        ),
        cgm_slice_bridge_report=load_json_artifact(
            "artifacts/reports/cgm_slice_bridge_summary_v1.json"
        ),
        cgm_slice_bridge_report_path="artifacts/reports/cgm_slice_bridge_summary_v1.json",
    )

    assert diagnostic["audit_name"] == "latest_candidate_cgm_slice_diagnostic_v1"
    assert diagnostic["hypothesis_gate"] == {
        "overall_ok_but_cgm_only_worse_supported": False,
        "rejection_reasons": [
            "overall_fit_gate_already_failed",
            "dominant_regression_slice_is_low_risk_not_cgm",
        ],
        "evidence": {
            "fit_gate_status": "worse_on_all_fit_gates",
            "dominant_candidate_regression_slice": "low_risk",
            "low_risk_regression_score": 252,
            "cgm_regression_score": 30,
            "effect_only_low_risk_disagreement_delta": 132,
            "effect_only_cgm_disagreement_delta": 20,
            "combined_low_risk_disagreement_delta": 62,
            "combined_cgm_disagreement_delta": 6,
            "effect_only_low_risk_final_delta_abs": 52,
            "effect_only_cgm_final_delta_abs": 0,
            "combined_low_risk_final_delta_abs": 6,
            "combined_cgm_final_delta_abs": 4,
        },
    }
    assert diagnostic["residual_cgm_failure_families"][
        "geometry_blocker_family_summary"
    ] == {
        "outside_monitor_band_large_monitor_gap": 8,
        "threshold_edge_monitor_band_continue": 1,
    }
    assert diagnostic["bridge_and_workflow_assessment"][
        "continue_to_reoptimize_top_action_flip_count"
    ] == 1
    assert diagnostic["bridge_and_workflow_assessment"]["bridge_is_primary_driver"] is False
    assert validate_latest_candidate_cgm_slice_diagnostic(diagnostic) == []


def test_write_latest_candidate_cgm_slice_diagnostic_files_creates_outputs(
    tmp_path: Path,
) -> None:
    diagnostic = {
        "hypothesis_gate": {
            "overall_ok_but_cgm_only_worse_supported": False,
            "rejection_reasons": ["overall_fit_gate_already_failed"],
        },
        "residual_cgm_failure_families": {
            "geometry_blocker_family_summary": {
                "outside_monitor_band_large_monitor_gap": 8
            },
            "feature_family_summary": {"top_feature_gaps": [{"feature": "expected_effect_proxy"}]},
        },
        "bridge_and_workflow_assessment": {
            "bridge_contract_connected": True,
            "bridge_is_primary_driver": False,
        },
        "summary_findings": ["test finding"],
        "validation_issues": [],
    }

    json_path = tmp_path / "latest_candidate_cgm_slice_diagnostic_v1.json"
    md_path = tmp_path / "latest_candidate_cgm_slice_diagnostic_v1.md"
    write_latest_candidate_cgm_slice_diagnostic_files(
        diagnostic=diagnostic,
        json_path=json_path,
        md_path=md_path,
    )

    markdown = render_latest_candidate_cgm_slice_diagnostic_markdown(diagnostic)
    assert json_path.exists()
    assert md_path.exists()
    assert "# latest candidate cgm slice diagnostic v1" in markdown
    assert "overall_ok_but_cgm_only_worse_supported" in markdown
    assert "## bridge and workflow assessment" in markdown
