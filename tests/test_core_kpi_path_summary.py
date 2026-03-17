from wellnessbox_rnd.evals.core_kpi_path_summary import (
    build_core_kpi_path_summary,
    load_json,
    render_core_kpi_path_summary_markdown,
)


def test_build_core_kpi_path_summary_surfaces_current_kpi_path_state() -> None:
    summary = build_core_kpi_path_summary(
        final_kpi_compare_report=load_json(
            "artifacts/reports/final_kpi_compare_report_v1.json"
        ),
        final_kpi_compare_report_path="artifacts/reports/final_kpi_compare_report_v1.json",
        baseline_followup_pro_event_contract=load_json(
            "artifacts/reports/baseline_followup_pro_event_contract_v1.json"
        ),
        baseline_followup_pro_event_contract_path="artifacts/reports/baseline_followup_pro_event_contract_v1.json",
        pro_scoring_contract=load_json("artifacts/reports/pro_scoring_contract_v1.json"),
        pro_scoring_contract_path="artifacts/reports/pro_scoring_contract_v1.json",
        weakest_slice_frozen_eval_audit=load_json(
            "artifacts/reports/weakest_slice_frozen_eval_audit_v1.json"
        ),
        weakest_slice_frozen_eval_audit_path="artifacts/reports/weakest_slice_frozen_eval_audit_v1.json",
        cgm_geometry_summary=load_json(
            "artifacts/reports/cgm_final_step_reoptimize_geometry_calibration_v1.json"
        ),
        cgm_geometry_summary_path="artifacts/reports/cgm_final_step_reoptimize_geometry_calibration_v1.json",
        learned_runtime_boundary_audit=load_json(
            "artifacts/reports/learned_runtime_boundary_audit_v1.json"
        ),
        learned_runtime_boundary_audit_path="artifacts/reports/learned_runtime_boundary_audit_v1.json",
        latest_effect_candidate_reject_decision=load_json(
            "artifacts/reports/latest_effect_candidate_reject_decision_v1.json"
        ),
        latest_effect_candidate_reject_decision_path="artifacts/reports/latest_effect_candidate_reject_decision_v1.json",
    )

    assert summary["baseline_reference"]["case_count"] == 256
    assert summary["replay_compare_status"]["status"] == "complete_candidate_held"
    assert (
        summary["replay_compare_status"]["adoption_decision"]
        == "hold_baseline_candidate_not_ready"
    )
    assert (
        summary["pro_baseline_followup_contract_status"]["shared_event_adapter"]
        == "summarize_pro_improvement_from_event_v1"
    )
    assert (
        summary["weakest_slice_frozen_eval_wiring_status"]["path_status"]
        == "bridge_connected_with_direct_gap"
    )
    assert (
        summary["cgm_final_step_geometry_status"][
            "continue_to_reoptimize_top_action_flip_count"
        ]
        == 1
    )
    assert (
        summary["learned_artifact_replay_only_boundary_status"][
            "chat_optional_only"
        ]
        is True
    )
    assert (
        summary["deterministic_baseline_vs_candidate_judgement"]["decision"]
        == "hold_baseline_candidate_not_ready"
    )
    assert (
        summary["current_path_readable_summary"]["replay_compare_digest"][
            "dominant_replay_regression_family"
        ]
        == "non_cgm_continue_to_monitor_threshold_cross"
    )


def test_render_core_kpi_path_summary_markdown_contains_required_sections() -> None:
    markdown = render_core_kpi_path_summary_markdown(
        {
            "current_path_readable_summary": {
                "replay_compare_digest": {"status": "complete_candidate_held"},
                "pro_contract_digest": {"status": "shared_event_path_connected"},
                "weakest_slice_digest": {"status": "connected_with_remaining_gaps"},
                "cgm_final_step_geometry_digest": {
                    "status": "structural_continue_plan_overlap_persists"
                },
                "learned_boundary_digest": {"status": "replay_only_boundary_preserved"},
                "baseline_vs_candidate_digest": {
                    "decision": "hold_baseline_candidate_not_ready"
                },
            },
            "replay_compare_status": {
                "status": "complete_candidate_held",
                "candidate_label": "candidate_a",
                "adoption_decision": "hold_baseline_candidate_not_ready",
                "fit_gate_status": "worse_on_all_fit_gates",
                "dominant_replay_regression_family": "non_cgm_continue_to_monitor_threshold_cross",
            },
            "pro_baseline_followup_contract_status": {
                "status": "shared_event_path_connected",
                "contract_id": "baseline_followup_pro_event_v1",
                "package_public_summary_entrypoint": "summarize_pro_improvement_from_event_v1",
                "valid_case_count": 480,
                "invalid_case_count": 0,
            },
            "weakest_slice_frozen_eval_wiring_status": {
                "status": "connected_with_remaining_gaps",
                "path_status": "bridge_connected_with_direct_gap",
                "overall_weakest_category": "safety_blocked",
                "sensor_genetic_weakest_category": "free_text_alias",
                "audit_layer_gap_count": 4,
            },
            "cgm_final_step_geometry_status": {
                "status": "structural_continue_plan_overlap_persists",
                "selected_continue_case_count": 9,
                "continue_to_reoptimize_top_action_flip_count": 1,
                "outside_monitor_band_count": 8,
                "blocker_family_summary": {"outside_monitor_band_large_monitor_gap": 8},
            },
            "learned_artifact_replay_only_boundary_status": {
                "status": "replay_only_boundary_preserved",
                "core_path_count": 4,
                "promoted_core_path_count": 0,
                "chat_optional_only": True,
            },
            "deterministic_baseline_vs_candidate_judgement": {
                "dataset_path": "data/frozen_eval/frozen_eval_v1.jsonl",
                "case_count": 256,
                "decision": "hold_baseline_candidate_not_ready",
                "one_line_conclusion": "Hold baseline.",
                "principal_blocker": "synthetic_data_circularity_and_generator_contamination",
                "dominant_replay_regression_family": "non_cgm_continue_to_monitor_threshold_cross",
            },
        }
    )

    assert "# core kpi path summary v1" in markdown
    assert "## Current Path" in markdown
    assert "## Replay Compare" in markdown
    assert "## PRO Contract" in markdown
    assert "## Weakest-Slice Wiring" in markdown
    assert "## CGM Final-Step Geometry" in markdown
    assert "## Learned Boundary" in markdown
    assert "## Baseline vs Candidate" in markdown
    assert "Hold baseline." in markdown
