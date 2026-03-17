from pathlib import Path

from wellnessbox_rnd.evals.training_readiness_gate import (
    build_training_readiness_gate,
    load_json,
    render_training_readiness_gate_markdown,
    write_training_readiness_gate_files,
)


def test_build_training_readiness_gate_returns_strict_no_go_v2() -> None:
    report = build_training_readiness_gate(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        case_count=480,
        replay_attribution=load_json(
            "artifacts/reports/non_cgm_residual_threshold_cross_attribution_v2.json"
        ),
        replay_attribution_path=(
            "artifacts/reports/non_cgm_residual_threshold_cross_attribution_v2.json"
        ),
        synthetic_validity_followup=load_json(
            "artifacts/reports/synthetic_validity_followup_single_item_v1.json"
        ),
        synthetic_validity_followup_path=(
            "artifacts/reports/synthetic_validity_followup_single_item_v1.json"
        ),
        cgm_core_summary=load_json("artifacts/reports/core_kpi_path_summary_v1.json"),
        cgm_core_summary_path="artifacts/reports/core_kpi_path_summary_v1.json",
        cgm_geometry_audit=None,
        cgm_geometry_audit_path="artifacts/reports/cgm_outside_band_final_step_geometry_v2.json",
    )

    gate = report["gate_decision"]
    criteria = report["criteria_assessment"]
    next_loop = report["next_non_training_loop"]
    readable = report["readable_summary"]

    assert gate == {
        "authorized_now": False,
        "decision": "no_go_keep_training_blocked",
        "decision_standard": "strict_all_criteria_required_default_no_go",
        "failed_criteria": [
            "dominant_replay_residual_explained_tightly_enough",
            "chosen_synthetic_validity_item_resolved_or_bounded_tightly_enough",
            "reopened_cgm_blocker_closed_or_proven_non_blocking",
            "next_rerun_target_can_be_stated_narrowly",
        ],
        "first_blocking_criterion": "dominant_replay_residual_explained_tightly_enough",
    }
    assert len(criteria) == 5
    assert criteria[0]["passed"] is False
    assert criteria[0]["evidence"]["current_residual_case_count"] == 4
    assert criteria[1]["passed"] is False
    assert criteria[1]["evidence"]["chosen_item"] == "calibration_target_coupling"
    assert criteria[1]["evidence"]["resolution_state"] == "still_risky"
    assert criteria[2]["passed"] is False
    assert criteria[2]["evidence"]["cgm_geometry_artifact_present"] is False
    assert criteria[2]["evidence"]["outside_monitor_band_count"] == 8
    assert criteria[3]["passed"] is False
    assert criteria[3]["evidence"]["blocking_pre_rerun_loop"] == {
        "task": (
            "replay_only_attribution_for_threshold_duration_sensitive_mid_margin_"
            "large_drop"
        ),
        "decision_family": "non_cgm_continue_to_monitor_threshold_cross",
        "trajectory_mode": "threshold_duration_sensitive",
        "margin_bucket": "mid_margin",
        "proxy_drop_bucket": "large_drop",
        "observed_case_count": 3,
    }
    assert criteria[4]["passed"] is True

    assert next_loop == {
        "required_before_any_future_rerun": (
            "replay_only_attribution_for_threshold_duration_sensitive_mid_margin_large_drop"
        ),
        "why": (
            "Criterion 1 fails first: the dominant replay residual is still not explained "
            "tightly enough, and the `large_drop` bucket is the densest remaining slice."
        ),
        "bounded_target": {
            "decision_family": "non_cgm_continue_to_monitor_threshold_cross",
            "trajectory_mode": "threshold_duration_sensitive",
            "margin_bucket": "mid_margin",
            "proxy_drop_bucket": "large_drop",
            "observed_case_count": 3,
        },
    }
    assert readable["gate_digest"]["decision"] == "no_go_keep_training_blocked"
    assert readable["replay_digest"] == {
        "decision_family": "non_cgm_continue_to_monitor_threshold_cross",
        "current_residual_case_count": 4,
        "primary_residual_family": "mixed_residual_overlap",
        "explained_well_enough_for_future_gate_work": False,
    }
    assert readable["synthetic_digest"] == {
        "chosen_item": "calibration_target_coupling",
        "resolution_state": "still_risky",
        "actionable_for_future_gate_work": True,
    }
    assert readable["cgm_digest"] == {
        "artifact_present": False,
        "status": "structural_continue_plan_overlap_persists",
        "outside_monitor_band_count": 8,
        "threshold_edge_case_count": 1,
    }
    assert report["validation_issues"] == []


def test_write_training_readiness_gate_files_creates_outputs(tmp_path: Path) -> None:
    report = build_training_readiness_gate(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        case_count=480,
        replay_attribution=load_json(
            "artifacts/reports/non_cgm_residual_threshold_cross_attribution_v2.json"
        ),
        replay_attribution_path=(
            "artifacts/reports/non_cgm_residual_threshold_cross_attribution_v2.json"
        ),
        synthetic_validity_followup=load_json(
            "artifacts/reports/synthetic_validity_followup_single_item_v1.json"
        ),
        synthetic_validity_followup_path=(
            "artifacts/reports/synthetic_validity_followup_single_item_v1.json"
        ),
        cgm_core_summary=load_json("artifacts/reports/core_kpi_path_summary_v1.json"),
        cgm_core_summary_path="artifacts/reports/core_kpi_path_summary_v1.json",
        cgm_geometry_audit=None,
        cgm_geometry_audit_path="artifacts/reports/cgm_outside_band_final_step_geometry_v2.json",
    )

    json_path = tmp_path / "training_readiness_gate_v2.json"
    md_path = tmp_path / "training_readiness_gate_v2.md"
    write_training_readiness_gate_files(
        report=report,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_training_readiness_gate_markdown(report)

    assert json_path.exists()
    assert md_path.exists()
    assert "# training readiness gate v2" in markdown
    assert "Criteria Assessment" in markdown
    assert "Next Non-Training Loop" in markdown
    assert "Summary Findings" in markdown
