from pathlib import Path

from wellnessbox_rnd.evals.effect_candidate_reject_decision import (
    build_effect_candidate_reject_decision,
    load_json_artifact,
    render_effect_candidate_reject_decision_markdown,
    write_effect_candidate_reject_decision_files,
)


def test_build_effect_candidate_reject_decision_supports_baseline_hold() -> None:
    decision = build_effect_candidate_reject_decision(
        compare_report=load_json_artifact(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_replay_compare_vs_baseline_v1.json"
        ),
        compare_report_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_replay_compare_vs_baseline_v1.json"
        ),
        final_compare_report=load_json_artifact(
            "artifacts/reports/final_kpi_compare_report_v1.json"
        ),
        final_compare_report_path=(
            "artifacts/reports/final_kpi_compare_report_v1.json"
        ),
        non_cgm_diagnostic_report=load_json_artifact(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        non_cgm_diagnostic_report_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        cgm_diagnostic_report=load_json_artifact(
            "artifacts/reports/latest_candidate_cgm_slice_diagnostic_v1.json"
        ),
        cgm_diagnostic_report_path=(
            "artifacts/reports/latest_candidate_cgm_slice_diagnostic_v1.json"
        ),
        core_kpi_path_summary=load_json_artifact(
            "artifacts/reports/core_kpi_path_summary_v1.json"
        ),
        core_kpi_path_summary_path=(
            "artifacts/reports/core_kpi_path_summary_v1.json"
        ),
    )

    assert decision["audit_name"] == "latest_effect_candidate_reject_decision_v1"
    assert decision["decision_gate"] == {
        "candidate_label": "effect_model_v3_training_view_enforced_slice_balanced_candidate",
        "overall_clearly_worse_than_baseline": True,
        "fit_gate_status": "worse_on_all_fit_gates",
        "gate_evidence": {
            "test_aggregate_mae_delta": 0.005063,
            "test_aggregate_r2_delta": -0.059257,
            "test_policy_proxy_mae_delta": 0.002425,
        },
        "decision": "reject_candidate_keep_baseline",
        "fork_recommendation": "analysis_only_fork",
    }
    assert decision["regression_slices"]["dominant_low_risk_slice"] == {
        "decision_family": "non_cgm_continue_to_monitor_threshold_cross",
        "observed_case_count": 26,
        "transition": "continue_plan->monitor_only",
        "effect_only_disagreement_delta": 132,
        "combined_disagreement_delta": 62,
        "effect_only_final_action_delta": {
            "continue_plan": -26,
            "monitor_only": 26,
        },
        "combined_final_action_delta": {
            "continue_plan": -3,
            "monitor_only": 0,
            "re_optimize": 3,
        },
        "dominant_workflow_modes": [
            {"name": "threshold_duration_sensitive", "count": 10},
            {"name": "threshold_monitor_secondary", "count": 7},
            {"name": "threshold_reopt_edge", "count": 4},
        ],
        "dominant_feature_family": "intercept",
        "why_regression": (
            "This regression is not explained as pure threshold-edge widening alone: "
            "26/26 cases start with more than a near-edge continue margin, and the dominant "
            "contribution pattern is intercept led by __intercept__."
        ),
        "reference_continue_margin_mean": 0.053676,
        "proxy_drop_bucket_counts": {
            "large_drop": 9,
            "medium_drop": 9,
            "small_drop": 8,
        },
    }
    assert decision["regression_slices"]["residual_cgm_slice"][
        "cgm_only_failure_hypothesis_supported"
    ] is False
    assert decision["regression_slices"]["residual_cgm_slice"][
        "feature_families"
    ] == [
        "policy_effect_proxy_used",
        "predicted_effect_proxy",
        "expected_effect_proxy",
        "adherence_proxy",
        "side_effect_proxy",
    ]
    assert len(decision["required_evidence_before_next_training_loop"]) == 3
    assert decision["validation_issues"] == []


def test_write_effect_candidate_reject_decision_files_creates_outputs(
    tmp_path: Path,
) -> None:
    decision = build_effect_candidate_reject_decision(
        compare_report=load_json_artifact(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_replay_compare_vs_baseline_v1.json"
        ),
        compare_report_path="compare.json",
        final_compare_report=load_json_artifact(
            "artifacts/reports/final_kpi_compare_report_v1.json"
        ),
        final_compare_report_path="final_compare.json",
        non_cgm_diagnostic_report=load_json_artifact(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        non_cgm_diagnostic_report_path="non_cgm.json",
        cgm_diagnostic_report=load_json_artifact(
            "artifacts/reports/latest_candidate_cgm_slice_diagnostic_v1.json"
        ),
        cgm_diagnostic_report_path="cgm_diagnostic.json",
        core_kpi_path_summary=load_json_artifact(
            "artifacts/reports/core_kpi_path_summary_v1.json"
        ),
        core_kpi_path_summary_path="core_kpi.json",
    )

    json_path = tmp_path / "latest_effect_candidate_reject_decision_v1.json"
    md_path = tmp_path / "latest_effect_candidate_reject_decision_v1.md"
    write_effect_candidate_reject_decision_files(
        decision=decision,
        json_path=json_path,
        md_path=md_path,
    )
    markdown = render_effect_candidate_reject_decision_markdown(decision)

    assert json_path.exists()
    assert md_path.exists()
    assert "reject_candidate_keep_baseline" in markdown
    assert "non_cgm_continue_to_monitor_threshold_cross" in markdown
