from pathlib import Path

from wellnessbox_rnd.evals.structured_safety_rule_overlap_decision import (
    build_structured_safety_rule_overlap_decision,
    render_structured_safety_rule_overlap_decision_markdown,
    validate_structured_safety_rule_overlap_decision,
    write_structured_safety_rule_overlap_decision_files,
)


def test_build_structured_safety_rule_overlap_decision_marks_current_gap_non_blocking() -> None:
    decision = build_structured_safety_rule_overlap_decision(
        weakest_slice_audit={
            "structured_safety_evidence_linkage_audit": {
                "reference_linkage_status": "deterministic_only",
                "reference_linkage_completeness": {
                    "rule_count": 2,
                    "reference_backed_rule_count": 0,
                    "reference_coverage_pct": 0.0,
                },
                "next_action_workflow_category_join": {
                    "join_status": "connected",
                    "coverage_pct": 100.0,
                    "category_case_count": 17,
                    "actual_status_counts": {"blocked": 4, "ok": 13},
                    "actual_next_action_counts": {
                        "collect_more_input": 4,
                        "start_plan": 13,
                    },
                    "unmatched_next_action_counts": {},
                },
                "frozen_eval_category_join": {
                    "join_status": "connected",
                    "fixture_rule_ids": [
                        "SAFETY-DOSE-VITD3-001",
                        "SAFETY-DUP-001",
                    ],
                    "fixture_rule_overlap_ids": ["SAFETY-DUP-001"],
                    "observed_rule_id_counts": {
                        "INTAKE-SURVEY-001": 17,
                        "SAFETY-ANTICOAG-001": 7,
                        "SAFETY-DUP-001": 3,
                    },
                    "fixture_next_action": "trigger_safety_recheck",
                    "workflow_contract_next_action": "start_plan",
                    "fixture_next_action_seen_in_family": False,
                    "workflow_contract_next_action_seen_in_family": True,
                },
            }
        },
        weakest_slice_audit_path="audit.json",
        weakest_slice_summary={
            "frozen_eval_anchor": {
                "weakest_category_by_metric": {
                    "safety_reference_accuracy_pct": {
                        "category": "safety_blocked",
                        "score": 98.03921568627452,
                        "target": 95.0,
                        "passed": True,
                    }
                }
            },
            "case_family_summaries": [
                {
                    "family": "safety_blocked",
                    "coverage_status": "connected",
                    "case_count": 17,
                    "weakest_metrics": [
                        "explanation_quality_accuracy_pct",
                        "next_action_accuracy_pct",
                        "safety_reference_accuracy_pct",
                    ],
                    "remaining_gaps": [
                        "Structured safety evidence linkage now joins weakest safety_blocked "
                        "cases at the category level, but the current request-fixture rule "
                        "bundle still only partially overlaps the observed weakest-slice "
                        "rule families."
                    ],
                }
            ],
        },
        weakest_slice_summary_path="summary.json",
        eval_report={
            "summary": {
                "safety_reference_accuracy_pct": {
                    "score": 99.86979166666667,
                    "target": 95.0,
                    "passed": True,
                }
            }
        },
        eval_report_path="eval.json",
    )

    assert decision["decision_gate"]["blocks_kpi_interpretation"] is False
    assert (
        decision["decision_gate"]["decision"]
        == "partial_rule_overlap_not_blocking_current_kpi_interpretation"
    )
    assert "workflow_branch_coverage_complete" in decision["decision_gate"]["reason_codes"]
    assert "structured_safety_rule_overlap_partial" in decision["decision_gate"]["reason_codes"]
    assert validate_structured_safety_rule_overlap_decision(decision) == []


def test_write_structured_safety_rule_overlap_decision_files_creates_outputs(
    tmp_path: Path,
) -> None:
    decision = {
        "audit_name": "structured_safety_rule_overlap_decision_v1",
        "decision_gate": {
            "decision": "partial_rule_overlap_not_blocking_current_kpi_interpretation"
        },
        "evidence_summary": {"structured_safety_rule_overlap": {"fixture_rule_overlap_count": 1}},
        "decision_rationale": ["Workflow coverage is complete."],
        "summary_findings": ["The overlap is partial but non-blocking."],
        "validation_issues": [],
    }

    json_path = tmp_path / "structured_safety_rule_overlap_decision_v1.json"
    md_path = tmp_path / "structured_safety_rule_overlap_decision_v1.md"
    write_structured_safety_rule_overlap_decision_files(
        decision=decision,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_structured_safety_rule_overlap_decision_markdown(decision)
    assert "## decision gate" in markdown
    assert "## summary findings" in markdown
