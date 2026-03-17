from pathlib import Path

from wellnessbox_rnd.evals.cgm_candidate_failure_family_diagnostic import (
    build_cgm_candidate_failure_family_diagnostic,
    load_json_artifact,
    render_cgm_candidate_failure_family_diagnostic_markdown,
    write_cgm_candidate_failure_family_diagnostic_files,
)


def test_build_cgm_candidate_failure_family_diagnostic_rejects_cgm_only_hypothesis() -> None:
    diagnostic = build_cgm_candidate_failure_family_diagnostic(
        compare_report=load_json_artifact(
            "artifacts/reports/effect_model_v3_training_view_enforced_candidate_replay_compare_v1.json"
        ),
        compare_report_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_candidate_replay_compare_v1.json"
        ),
        attribution_report=load_json_artifact(
            "artifacts/reports/effect_model_v3_training_view_enforced_candidate_replay_attribution_v1.json"
        ),
        attribution_report_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_candidate_replay_attribution_v1.json"
        ),
        cgm_feature_audit_report=load_json_artifact(
            "artifacts/reports/cgm_combined_replay_feature_audit_v1.json"
        ),
        cgm_feature_audit_report_path="artifacts/reports/cgm_combined_replay_feature_audit_v1.json",
        cgm_slice_bridge_report=load_json_artifact(
            "artifacts/reports/cgm_slice_bridge_summary_v1.json"
        ),
        cgm_slice_bridge_report_path="artifacts/reports/cgm_slice_bridge_summary_v1.json",
        cgm_event_report=load_json_artifact(
            "artifacts/reports/cgm_normalized_event_bridge_v1.json"
        ),
        cgm_event_report_path="artifacts/reports/cgm_normalized_event_bridge_v1.json",
    )

    assert diagnostic["audit_name"] == "cgm_candidate_failure_family_diagnostic_v1"
    assert diagnostic["hypothesis_gate"]["cgm_only_failure_hypothesis_supported"] is False
    assert diagnostic["hypothesis_gate"]["evidence"] == {
        "effect_only_low_risk_final_delta_abs": 52,
        "effect_only_cgm_final_delta_abs": 0,
        "combined_low_risk_final_delta_abs": 6,
        "combined_cgm_final_delta_abs": 4,
        "effect_only_low_risk_disagreement_delta": 132,
        "effect_only_cgm_disagreement_delta": 20,
        "combined_low_risk_disagreement_delta": 68,
        "combined_cgm_disagreement_delta": 11,
        "compare_summary_finding": (
            "Overall final-action delta is entirely low-risk: effect-only final changes are "
            "{'continue_plan->monitor_only': 26}, and none of them are high-risk or "
            "safety-guard families."
        ),
    }
    assert diagnostic["dominant_non_cgm_family"]["decision_family_counts"] == {
        "non_cgm_continue_to_monitor_threshold_cross": 26
    }
    assert diagnostic["residual_cgm_failure_families"]["effect_only_workflow_family"][
        "trajectory_mode_counts"
    ] == {
        "threshold_cgm_balance": 7,
        "threshold_monitor_secondary": 3,
        "threshold_reopt_edge": 3,
    }
    assert diagnostic["residual_cgm_failure_families"]["combined_final_decision_family"][
        "decision_family_counts"
    ] == {"cgm_same_band_policy_score_flip": 2}
    assert diagnostic["bridge_family_assessment"]["bridge_is_primary_delta_driver"] is False
    assert diagnostic["bridge_family_assessment"]["cgm_available_constant_within_slice"] == (
        "expected"
    )
    assert diagnostic["validation_issues"] == []


def test_write_cgm_candidate_failure_family_diagnostic_files_creates_outputs(
    tmp_path: Path,
) -> None:
    diagnostic = build_cgm_candidate_failure_family_diagnostic(
        compare_report=load_json_artifact(
            "artifacts/reports/effect_model_v3_training_view_enforced_candidate_replay_compare_v1.json"
        ),
        compare_report_path="compare.json",
        attribution_report=load_json_artifact(
            "artifacts/reports/effect_model_v3_training_view_enforced_candidate_replay_attribution_v1.json"
        ),
        attribution_report_path="attribution.json",
        cgm_feature_audit_report=load_json_artifact(
            "artifacts/reports/cgm_combined_replay_feature_audit_v1.json"
        ),
        cgm_feature_audit_report_path="feature_audit.json",
        cgm_slice_bridge_report=load_json_artifact(
            "artifacts/reports/cgm_slice_bridge_summary_v1.json"
        ),
        cgm_slice_bridge_report_path="cgm_slice.json",
        cgm_event_report=load_json_artifact(
            "artifacts/reports/cgm_normalized_event_bridge_v1.json"
        ),
        cgm_event_report_path="cgm_event.json",
    )

    json_path = tmp_path / "cgm_candidate_failure_family_diagnostic_v1.json"
    md_path = tmp_path / "cgm_candidate_failure_family_diagnostic_v1.md"
    write_cgm_candidate_failure_family_diagnostic_files(
        diagnostic=diagnostic,
        json_path=json_path,
        md_path=md_path,
    )
    markdown = render_cgm_candidate_failure_family_diagnostic_markdown(diagnostic)

    assert json_path.exists()
    assert md_path.exists()
    assert "cgm_only_failure_hypothesis_supported: `False`" in markdown
    assert "non_cgm_continue_to_monitor_threshold_cross" in markdown
    assert "cgm_same_band_policy_score_flip" in markdown
