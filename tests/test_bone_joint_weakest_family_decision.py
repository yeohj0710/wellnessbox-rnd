from pathlib import Path

from wellnessbox_rnd.evals.bone_joint_weakest_family_decision import (
    build_bone_joint_weakest_family_decision,
    render_bone_joint_weakest_family_decision_markdown,
    validate_bone_joint_weakest_family_decision,
    write_bone_joint_weakest_family_decision_files,
)


def test_build_bone_joint_weakest_family_decision_keeps_empty_anchor() -> None:
    decision = build_bone_joint_weakest_family_decision(
        weakest_slice_summary={
            "frozen_eval_anchor": {
                "weakest_category_by_metric": {
                    "recommendation_coverage_pct": {
                        "category": "bone_joint",
                        "score": 100.0,
                        "passed": True,
                    },
                    "adverse_event_count_yearly": {
                        "category": "bone_joint",
                        "score": 0.0,
                        "passed": True,
                    },
                }
            },
            "case_family_summaries": [
                {
                    "family": "bone_joint",
                    "case_count": 1,
                    "coverage_status": "empty",
                    "weakest_metrics": [
                        "adverse_event_count_yearly",
                        "recommendation_coverage_pct",
                    ],
                    "remaining_gaps": [
                        (
                            "No dedicated contract bundle is mapped to this weakest "
                            "family in the current audit layer."
                        )
                    ],
                }
            ],
        },
        weakest_slice_summary_path="summary.json",
        eval_report={
            "case_results": [
                {
                    "case_id": "eval-017",
                    "category": "bone_joint",
                    "description": (
                        "bone and joint baseline should recommend vitamin D3 "
                        "and calcium citrate"
                    ),
                    "case_metrics": {
                        "recommendation_coverage_pct": 100.0,
                        "next_action_accuracy_pct": 100.0,
                        "explanation_quality_accuracy_pct": 100.0,
                        "safety_reference_accuracy_pct": 100.0,
                    },
                    "actual": {
                        "status": "ok",
                        "next_action": "start_plan",
                        "recommendation_keys": ["vitamin_d3", "calcium_citrate"],
                    },
                }
            ]
        },
        eval_report_path="eval.json",
        training_revisit_decision={
            "decision_gate": {
                "decision": "defer_new_effect_training_loop",
                "reason_codes": ["overall_fit_gates_still_worse"],
            }
        },
        training_revisit_decision_path="training.json",
    )

    assert decision["decision_gate"]["keep_explicit_empty_anchor"] is True
    assert decision["decision_gate"]["decision"] == "keep_explicit_empty_anchor"
    assert "single_case_anchor" in decision["decision_gate"]["reason_codes"]
    assert validate_bone_joint_weakest_family_decision(decision) == []


def test_write_bone_joint_weakest_family_decision_files_creates_outputs(
    tmp_path: Path,
) -> None:
    decision = {
        "audit_name": "bone_joint_weakest_family_decision_v1",
        "decision_gate": {"decision": "keep_explicit_empty_anchor"},
        "evidence_summary": {"family_summary": {"case_count": 1}},
        "decision_rationale": ["Keep it empty."],
        "revisit_triggers": ["Trigger later if it fails KPI."],
        "summary_findings": ["bone_joint stays empty."],
        "validation_issues": [],
    }

    json_path = tmp_path / "bone_joint_weakest_family_decision_v1.json"
    md_path = tmp_path / "bone_joint_weakest_family_decision_v1.md"
    write_bone_joint_weakest_family_decision_files(
        decision=decision,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_bone_joint_weakest_family_decision_markdown(decision)
    assert "## decision gate" in markdown
    assert "## revisit triggers" in markdown
