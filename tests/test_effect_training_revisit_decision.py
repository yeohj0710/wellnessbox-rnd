from pathlib import Path

from wellnessbox_rnd.evals.effect_training_revisit_decision import (
    build_effect_training_revisit_decision,
    render_effect_training_revisit_decision_markdown,
    validate_effect_training_revisit_decision,
    write_effect_training_revisit_decision_files,
)


def test_build_effect_training_revisit_decision_defers_training() -> None:
    decision = build_effect_training_revisit_decision(
        baseline_candidate_summary={
            "candidate_comparison": {
                "fit_gate_status": "worse_on_all_fit_gates",
                "delta_summary": {"test_aggregate_mae_delta": 0.005},
            },
            "weakest_slice_delta": {
                "dominant_candidate_regression_slice": "low_risk",
            },
            "adoption_summary": {
                "decision": "hold_baseline_candidate_not_ready",
                "one_line_conclusion": "Hold baseline.",
            },
        },
        baseline_candidate_summary_path="baseline.json",
        replay_split_audit={
            "assessment": {
                "verdict": "supported_slice_replay_shift_concentrated",
                "effect_only_shift_concentration": "supported_effect_enriched",
                "combined_shift_concentration": "supported_effect_enriched",
                "supported_effect_only_changed_trace_user_count": 10,
                "unsupported_effect_only_changed_trace_user_count": 0,
                "supported_combined_changed_trace_user_count": 9,
                "unsupported_combined_changed_trace_user_count": 0,
            }
        },
        replay_split_audit_path="replay.json",
        partition_validity_audit={
            "assessment": {
                "verdict": "do_not_pool_supported_and_base_clone_validity",
                "supported_partition_role": "generator_circular_effect_fit_surface",
                "unsupported_partition_role": "high_risk_base_clone_control_surface",
                "leakage_status": "guarded_but_not_zero",
                "baseline_identical_label_status": "low_risk",
                "calibration_dependence_status": "material",
                "calibration_dependence_concentration": "supported_effect_enriched_slice",
            }
        },
        partition_validity_audit_path="partition.json",
        design_sanity_audit={
            "overall_verdict": {
                "direction_status": "directionally_sound_but_data_validity_risky",
                "current_phase": "contract_data_eval_hardening",
                "principal_blocker": "synthetic_data_circularity_and_generator_contamination",
            }
        },
        design_sanity_audit_path="design.json",
        non_cgm_diagnostic={
            "target_family": {
                "name": "non_cgm_continue_to_monitor_threshold_cross",
                "observed_case_count": 26,
                "transition": "continue_plan->monitor_only",
            },
            "workflow_summary": {
                "trajectory_mode_counts": {"threshold_duration_sensitive": 10}
            },
            "feature_summary": {
                "feature_family_delta_summary": {
                    "top_absolute_families": [{"family": "intercept", "value": 3.37}]
                }
            },
        },
        non_cgm_diagnostic_path="non_cgm.json",
    )

    assert decision["decision_gate"]["revisit_justified_now"] is False
    assert decision["decision_gate"]["decision"] == "defer_new_effect_training_loop"
    assert "overall_fit_gates_still_worse" in decision["decision_gate"]["reason_codes"]
    assert decision["evidence_summary"]["synthetic_validity"]["partition_verdict"] == (
        "do_not_pool_supported_and_base_clone_validity"
    )
    assert validate_effect_training_revisit_decision(decision) == []


def test_write_effect_training_revisit_decision_files_creates_outputs(
    tmp_path: Path,
) -> None:
    decision = {
        "audit_name": "effect_training_revisit_decision_v1",
        "decision_gate": {"decision": "defer_new_effect_training_loop"},
        "evidence_summary": {"baseline_vs_candidate": {"fit_gate_status": "worse"}},
        "decision_rationale": ["Hold off."],
        "required_evidence_before_revisit": ["Need better replay evidence."],
        "summary_findings": ["Training revisit not justified."],
        "validation_issues": [],
    }

    json_path = tmp_path / "effect_training_revisit_decision_v1.json"
    md_path = tmp_path / "effect_training_revisit_decision_v1.md"
    write_effect_training_revisit_decision_files(
        decision=decision,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_effect_training_revisit_decision_markdown(decision)
    assert "## decision gate" in markdown
    assert "## required evidence before revisit" in markdown
