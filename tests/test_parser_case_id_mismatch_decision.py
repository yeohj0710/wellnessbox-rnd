from pathlib import Path

from wellnessbox_rnd.evals.parser_case_id_mismatch_decision import (
    build_parser_case_id_mismatch_decision,
    render_parser_case_id_mismatch_decision_markdown,
    validate_parser_case_id_mismatch_decision,
    write_parser_case_id_mismatch_decision_files,
)


def test_build_parser_case_id_mismatch_decision_marks_current_gap_non_blocking() -> None:
    decision = build_parser_case_id_mismatch_decision(
        parser_report={
            "cases_json_path": "data/samples/sensor_genetic_parser_cases_v1.json",
            "case_count": 4,
            "supported_failure_types": [
                "cgm_mean_glucose_invalid_numeric_ignored",
                "cgm_time_in_range_invalid_numeric_ignored",
            ],
            "normalized_cases": [
                {"case_id": "cgm_mmol_conversion"},
                {"case_id": "malformed_numeric_fallback"},
            ],
        },
        parser_report_path="parser.json",
        normalization_audit={
            "normalization_drift_detected": False,
            "validation_issues": [],
            "consistency_checks": {"integration_path_connected": True},
            "integration_metric_path": {
                "weakest_metric_score": 66.66666666666667,
                "required_component_statuses": {
                    "parser_outputs": "connected",
                    "file_schema_validation": "connected",
                },
            },
            "frozen_eval_category_join": {
                "weakest_category": "free_text_alias",
                "case_ids": ["eval-019", "eval-030", "eval-034"],
                "pooled_score_matches_weakest_metric": True,
                "modality_attempted_success": {"pooled": {"score": 66.666667}},
            },
            "direct_cgm_case_family_join": {
                "selected_family": "normal_recommendation",
                "case_ids": ["eval-001"],
                "join_status": "connected",
                "selection_rule": "lowest_cgm_score_with_attempted_gt_zero",
                "modality_attempted_success": {"cgm": {"attempted": 1, "score": 0.0}},
            },
        },
        normalization_audit_path="normalization.json",
        weakest_slice_summary={
            "case_family_summaries": [
                {
                    "family": "free_text_alias",
                    "case_count": 3,
                    "coverage_status": "connected",
                    "weakest_metrics": ["sensor_genetic_integration_rate_pct"],
                }
            ]
        },
        weakest_slice_summary_path="summary.json",
    )

    assert decision["decision_gate"]["blocks_kpi_interpretation"] is False
    assert (
        decision["decision_gate"]["decision"]
        == "mismatch_not_blocking_current_kpi_interpretation"
    )
    assert "weakest_metric_score_reproduced" in decision["decision_gate"]["reason_codes"]
    assert (
        "fixture_case_ids_do_not_match_eval_case_ids"
        in decision["decision_gate"]["reason_codes"]
    )
    assert validate_parser_case_id_mismatch_decision(decision) == []


def test_write_parser_case_id_mismatch_decision_files_creates_outputs(
    tmp_path: Path,
) -> None:
    decision = {
        "audit_name": "parser_case_id_mismatch_decision_v1",
        "decision_gate": {"decision": "mismatch_not_blocking_current_kpi_interpretation"},
        "evidence_summary": {"parser_fixture_scope": {"parser_case_count": 4}},
        "decision_rationale": ["Category-level KPI anchor is still readable."],
        "summary_findings": ["The mismatch is not blocking right now."],
        "validation_issues": [],
    }

    json_path = tmp_path / "parser_case_id_mismatch_decision_v1.json"
    md_path = tmp_path / "parser_case_id_mismatch_decision_v1.md"
    write_parser_case_id_mismatch_decision_files(
        decision=decision,
        json_path=json_path,
        md_path=md_path,
    )

    assert json_path.exists()
    assert md_path.exists()
    markdown = render_parser_case_id_mismatch_decision_markdown(decision)
    assert "## decision gate" in markdown
    assert "## summary findings" in markdown
