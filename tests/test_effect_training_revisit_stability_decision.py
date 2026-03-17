from pathlib import Path

from wellnessbox_rnd.evals.effect_training_revisit_stability_decision import (
    build_effect_training_revisit_stability_decision,
    render_effect_training_revisit_stability_decision_markdown,
    validate_effect_training_revisit_stability_decision,
    write_effect_training_revisit_stability_decision_files,
)


def test_build_effect_training_revisit_stability_decision_keeps_defer_gate() -> None:
    decision = build_effect_training_revisit_stability_decision(
        prior_revisit_decision={
            "decision_gate": {
                "revisit_justified_now": False,
                "decision": "defer_new_effect_training_loop",
                "reason_codes": [
                    "overall_fit_gates_still_worse",
                    "supported_effect_enriched_replay_shift_concentrated",
                ],
            }
        },
        prior_revisit_decision_path="prior.json",
        baseline_candidate_summary={
            "candidate_comparison": {
                "fit_gate_status": "worse_on_all_fit_gates",
                "delta_summary": {"test_aggregate_mae_delta": 0.005063},
            },
            "weakest_slice_delta": {
                "dominant_candidate_regression_slice": "low_risk"
            },
            "adoption_summary": {
                "decision": "hold_baseline_candidate_not_ready",
            },
        },
        baseline_candidate_summary_path="summary.json",
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
        replay_split_audit_path="split.json",
        non_cgm_diagnostic={
            "target_family": {
                "name": "non_cgm_continue_to_monitor_threshold_cross",
                "observed_case_count": 26,
                "transition": "continue_plan->monitor_only",
            },
            "workflow_summary": {
                "trajectory_mode_counts": {"threshold_duration_sensitive": 10}
            },
        },
        non_cgm_diagnostic_path="diag.json",
    )

    assert decision["decision_gate"]["material_replay_change_detected"] is False
    assert decision["decision_gate"]["revisit_justified_now"] is False
    assert (
        decision["decision_gate"]["decision"]
        == "current_defer_decision_still_holds"
    )
    assert (
        "dominant_non_cgm_replay_family_still_unresolved"
        in decision["decision_gate"]["reason_codes"]
    )
    assert validate_effect_training_revisit_stability_decision(decision) == []


def test_write_effect_training_revisit_stability_decision_files_creates_outputs(
    tmp_path: Path,
) -> None:
    decision = {
        "audit_name": "effect_training_revisit_stability_decision_v1",
        "decision_gate": {"decision": "current_defer_decision_still_holds"},
        "evidence_summary": {
            "prior_defer_gate": {
                "prior_decision": "defer_new_effect_training_loop"
            }
        },
        "decision_rationale": ["Replay gates are unchanged."],
        "summary_findings": ["The defer decision still holds."],
        "validation_issues": [],
    }

    json_path = tmp_path / "effect_training_revisit_stability_decision_v1.json"
    md_path = tmp_path / "effect_training_revisit_stability_decision_v1.md"
    write_effect_training_revisit_stability_decision_files(
        decision=decision,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_effect_training_revisit_stability_decision_markdown(decision)
    assert "## decision gate" in markdown
    assert "## summary findings" in markdown
