from pathlib import Path

from wellnessbox_rnd.evals.next_action_state_machine_audit import (
    build_next_action_state_machine_audit,
    render_next_action_state_machine_audit_markdown,
    validate_next_action_state_machine_audit,
    write_next_action_state_machine_audit_files,
)


def test_build_next_action_state_machine_audit_surfaces_phase_sensitive_drift() -> None:
    audit = build_next_action_state_machine_audit(
        followup_report={
            "schema_version": "followup_transition_event_v1",
            "dataset_path": "data/synthetic/synthetic_longitudinal_v4.jsonl",
        },
        followup_report_path="followup.json",
        next_action_report={
            "schema_version": "next_action_workflow_contract_v1",
            "state_machine_scope": "runtime_request_decision",
            "phase_sensitive_followup_actions": [
                "ask_targeted_followup",
                "continue_plan",
                "monitor_only",
                "start_plan",
            ],
        },
        next_action_report_path="next_action.json",
    )

    assert audit["explicit_contract_status"] == {
        "followup_contract_schema_version": "followup_transition_event_v1",
        "next_action_contract_schema_version": "next_action_workflow_contract_v1",
        "next_action_state_machine_scope": "runtime_request_decision",
        "phase_sensitive_followup_actions": [
            "ask_targeted_followup",
            "continue_plan",
            "monitor_only",
            "start_plan",
        ],
        "shared_followup_actions": [
            "ask_targeted_followup",
            "continue_plan",
            "monitor_only",
            "re_optimize",
            "reduce_or_stop",
            "start_plan",
            "trigger_safety_recheck",
        ],
        "runtime_only_actions": ["blocked", "collect_more_input"],
        "next_action_contract_declares_phase_sensitive_actions": True,
    }
    assert audit["dataset_action_distribution"]["step0_action_counts"]["re_optimize"] > 0
    assert audit["dataset_action_distribution"]["step_positive_action_counts"]["continue_plan"] > 0
    assert [item["next_action"] for item in audit["drift_findings"]] == [
        "ask_targeted_followup",
        "start_plan",
        "continue_plan",
        "monitor_only",
    ]
    assert {item["drift_kind"] for item in audit["drift_findings"]} == {
        "expected_phase_sensitive_divergence"
    }
    assert audit["readable_summary"] == {
        "audit_status": "explicit_shared_contract_no_unexpected_drift",
        "shared_followup_action_count": 7,
        "runtime_only_action_count": 2,
        "continue_plan_alignment": {
            "runtime_workflow_state": "followup_due",
            "followup_step0_state": "recommendation_ready",
            "followup_step_positive_state": "followup_due",
            "runtime_matches_followup_step_positive": True,
        },
        "re_optimize_alignment": {
            "runtime_workflow_state": "adjust_plan",
            "followup_step0_state": "adjust_plan",
            "followup_step_positive_state": "adjust_plan",
            "runtime_matches_followup_step0": True,
            "runtime_matches_followup_step_positive": True,
        },
        "unexpected_drift_count": 0,
    }
    assert validate_next_action_state_machine_audit(audit) == []


def test_write_next_action_state_machine_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = {
        "audit_name": "next_action_state_machine_audit_v1",
        "explicit_contract_status": {
            "next_action_state_machine_scope": "runtime_request_decision",
            "phase_sensitive_followup_actions": ["continue_plan"],
            "shared_followup_actions": ["continue_plan", "re_optimize"],
            "runtime_only_actions": ["blocked", "collect_more_input"],
            "next_action_contract_declares_phase_sensitive_actions": True,
        },
        "readable_summary": {
            "audit_status": "explicit_shared_contract_no_unexpected_drift",
            "continue_plan_alignment": {},
            "re_optimize_alignment": {},
            "unexpected_drift_count": 0,
        },
        "dataset_action_distribution": {
            "step0_action_counts": {"re_optimize": 1},
            "step_positive_action_counts": {"continue_plan": 2},
        },
        "transition_matrix": [],
        "shared_action_transition_matrix": [],
        "drift_findings": [],
        "validation_issues": [],
    }

    json_path = tmp_path / "next_action_state_machine_audit_v1.json"
    md_path = tmp_path / "next_action_state_machine_audit_v1.md"
    write_next_action_state_machine_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_next_action_state_machine_audit_markdown(audit)
    assert "## readable summary" in markdown
    assert "## shared action transition matrix" in markdown
    assert "## contract status" in markdown
    assert "## transition matrix" in markdown
