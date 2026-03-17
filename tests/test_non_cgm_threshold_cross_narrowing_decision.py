from pathlib import Path

from wellnessbox_rnd.evals.non_cgm_threshold_cross_narrowing_decision import (
    build_non_cgm_threshold_cross_narrowing_decision,
    load_json_artifact,
    render_non_cgm_threshold_cross_narrowing_decision_markdown,
    validate_non_cgm_threshold_cross_narrowing_decision,
    write_non_cgm_threshold_cross_narrowing_decision_files,
)


def test_build_non_cgm_threshold_cross_narrowing_decision_selects_largest_mode() -> None:
    decision = build_non_cgm_threshold_cross_narrowing_decision(
        non_cgm_diagnostic=load_json_artifact(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        non_cgm_diagnostic_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
            "non_cgm_threshold_cross_diagnostic_v1.json"
        ),
        reject_decision=load_json_artifact(
            "artifacts/reports/latest_effect_candidate_reject_decision_v1.json"
        ),
        reject_decision_path="artifacts/reports/latest_effect_candidate_reject_decision_v1.json",
    )

    assert decision["decision_gate"]["decision_family"] == (
        "non_cgm_continue_to_monitor_threshold_cross"
    )
    assert decision["decision_gate"]["decision"] == "focus_largest_single_workflow_mode_first"
    assert decision["decision_gate"]["chosen_first_target_mode"] == (
        "threshold_duration_sensitive"
    )
    assert decision["decision_gate"]["chosen_first_target_case_count"] == 10
    assert decision["decision_gate"]["chosen_first_target_share_pct"] == 38.46
    assert (
        decision["evidence_summary"]["feature_anchor"]["dominant_feature_family"]
        == "intercept"
    )
    assert validate_non_cgm_threshold_cross_narrowing_decision(decision) == []


def test_write_non_cgm_threshold_cross_narrowing_decision_files_creates_outputs(
    tmp_path: Path,
) -> None:
    decision = {
        "audit_name": "non_cgm_threshold_cross_narrowing_decision_v1",
        "decision_gate": {
            "decision": "focus_largest_single_workflow_mode_first",
            "chosen_first_target_mode": "threshold_duration_sensitive",
        },
        "evidence_summary": {
            "workflow_mode_ranking": [{"mode": "threshold_duration_sensitive", "count": 10}]
        },
        "decision_rationale": ["Focus the next loop on the largest single subgroup."],
        "deferred_subtargets": [{"mode": "threshold_monitor_secondary", "count": 7}],
        "required_success_evidence": ["Reduce the chosen subgroup count."],
        "summary_findings": ["Focus first on threshold_duration_sensitive."],
        "validation_issues": [],
    }

    json_path = tmp_path / "non_cgm_threshold_cross_narrowing_decision_v1.json"
    md_path = tmp_path / "non_cgm_threshold_cross_narrowing_decision_v1.md"
    write_non_cgm_threshold_cross_narrowing_decision_files(
        decision=decision,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_non_cgm_threshold_cross_narrowing_decision_markdown(decision)
    assert "## decision gate" in markdown
    assert "## deferred subtargets" in markdown
    assert "threshold_duration_sensitive" in markdown
