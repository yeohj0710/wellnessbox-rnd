from pathlib import Path

from wellnessbox_rnd.evals.training_readiness_gate import (
    build_training_readiness_gate,
    load_json,
    render_training_readiness_gate_markdown,
    write_training_readiness_gate_files,
)


def test_build_training_readiness_gate_returns_strict_no_go() -> None:
    report = build_training_readiness_gate(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        case_count=480,
        replay_attribution=load_json(
            "artifacts/reports/non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json"
        ),
        replay_attribution_path=(
            "artifacts/reports/non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json"
        ),
        synthetic_validity_audit=load_json(
            "artifacts/reports/synthetic_validity_audit_v1.json"
        ),
        synthetic_validity_audit_path="artifacts/reports/synthetic_validity_audit_v1.json",
        weakest_slice_summary=load_json(
            "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
        ),
        weakest_slice_summary_path=(
            "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
        ),
        parser_case_id_mismatch_decision=load_json(
            "artifacts/reports/parser_case_id_mismatch_decision_v1.json"
        ),
        parser_case_id_mismatch_decision_path=(
            "artifacts/reports/parser_case_id_mismatch_decision_v1.json"
        ),
        structured_safety_rule_overlap_decision=load_json(
            "artifacts/reports/structured_safety_rule_overlap_decision_v1.json"
        ),
        structured_safety_rule_overlap_decision_path=(
            "artifacts/reports/structured_safety_rule_overlap_decision_v1.json"
        ),
        requested_weakest_slice_lineage_proof_path=(
            "artifacts/reports/weakest_slice_lineage_proof_v1.json"
        ),
    )

    gate = report["gate_decision"]
    criteria = report["criteria_assessment"]
    next_loop = report["next_non_training_loop"]
    readable = report["readable_summary"]

    assert gate == {
        "authorized_now": False,
        "decision": "no_go_keep_training_blocked",
        "decision_standard": "strict_all_criteria_required",
        "failed_criteria": [
            "dominant_replay_family_explained_well_enough",
            "synthetic_validity_bounded_tightly_enough",
            "weakest_slice_lineage_closed_enough_for_relevant_slice",
            "future_rerun_objective_can_be_stated_narrowly",
        ],
    }
    assert len(criteria) == 5
    assert criteria[0]["passed"] is False
    assert criteria[0]["evidence"]["family_wide_explanation_complete"] is False
    assert criteria[1]["passed"] is False
    assert criteria[1]["evidence"]["circularity"] == "present"
    assert criteria[2]["passed"] is False
    assert criteria[2]["evidence"]["requested_lineage_proof_present"] is False
    assert criteria[2]["evidence"]["audit_layer_gap_count"] == 4
    assert criteria[3]["passed"] is False
    assert criteria[4]["passed"] is True

    assert next_loop == {
        "required_before_any_future_rerun": (
            "replay_only_residual_attribution_for_non_cgm_continue_to_monitor_threshold_cross"
        ),
        "why": (
            "The dominant replay family is not yet explained beyond the current 5-case smallest "
            "surface, so replay evidence must tighten before any rerun objective is safe."
        ),
        "bounded_target": {
            "trajectory_mode": "threshold_duration_sensitive",
            "margin_bucket": "mid_margin",
            "residual_proxy_drop_buckets": ["large_drop", "medium_drop"],
        },
    }
    assert readable["gate_digest"]["decision"] == "no_go_keep_training_blocked"
    assert readable["replay_digest"] == {
        "decision_family": "non_cgm_continue_to_monitor_threshold_cross",
        "current_smallest_surface_sufficient_for_explanation": True,
        "family_wide_explanation_complete": False,
    }
    assert readable["synthetic_digest"] == {
        "circularity": "present",
        "generator_contamination": "present",
        "calibration_target_coupling": "present",
        "training_rerun_justified_now": False,
    }
    assert readable["weakest_slice_digest"] == {
        "overall_weakest_category": "safety_blocked",
        "audit_layer_gap_count": 4,
        "parser_case_id_mismatch_non_blocking": True,
        "structured_safety_overlap_non_blocking": True,
    }
    assert report["validation_issues"] == []


def test_write_training_readiness_gate_files_creates_outputs(tmp_path: Path) -> None:
    report = build_training_readiness_gate(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        case_count=480,
        replay_attribution=load_json(
            "artifacts/reports/non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json"
        ),
        replay_attribution_path=(
            "artifacts/reports/non_cgm_continue_to_monitor_threshold_cross_attribution_v1.json"
        ),
        synthetic_validity_audit=load_json(
            "artifacts/reports/synthetic_validity_audit_v1.json"
        ),
        synthetic_validity_audit_path="artifacts/reports/synthetic_validity_audit_v1.json",
        weakest_slice_summary=load_json(
            "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
        ),
        weakest_slice_summary_path=(
            "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
        ),
        parser_case_id_mismatch_decision=load_json(
            "artifacts/reports/parser_case_id_mismatch_decision_v1.json"
        ),
        parser_case_id_mismatch_decision_path=(
            "artifacts/reports/parser_case_id_mismatch_decision_v1.json"
        ),
        structured_safety_rule_overlap_decision=load_json(
            "artifacts/reports/structured_safety_rule_overlap_decision_v1.json"
        ),
        structured_safety_rule_overlap_decision_path=(
            "artifacts/reports/structured_safety_rule_overlap_decision_v1.json"
        ),
        requested_weakest_slice_lineage_proof_path=(
            "artifacts/reports/weakest_slice_lineage_proof_v1.json"
        ),
    )

    json_path = tmp_path / "training_readiness_gate_v1.json"
    md_path = tmp_path / "training_readiness_gate_v1.md"
    write_training_readiness_gate_files(
        report=report,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_training_readiness_gate_markdown(report)

    assert json_path.exists()
    assert md_path.exists()
    assert "# training readiness gate v1" in markdown
    assert "Criteria Assessment" in markdown
    assert "Next Non-Training Loop" in markdown
    assert "Summary Findings" in markdown
