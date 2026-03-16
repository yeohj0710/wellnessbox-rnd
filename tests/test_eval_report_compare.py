from pathlib import Path

from wellnessbox_rnd.evals.report_compare import (
    compare_eval_reports,
    render_eval_report_comparison_markdown,
    write_eval_report_comparison_files,
)


def test_compare_eval_reports_returns_metric_deltas_and_weakest_slice_changes() -> None:
    baseline_report = {
        "case_count": 10,
        "summary": {
            "efficacy_improvement_pp": {
                "score": 3.0,
                "passed": True,
                "target": 0.0,
                "comparison": "positive",
                "unit": "percentage_points",
            },
            "next_action_accuracy_pct": {
                "score": 90.0,
                "passed": True,
                "target": 80.0,
                "comparison": "min",
                "unit": "percent",
            },
        },
        "weakest_slice_summary": {
            "weakest_category_overall": {"category": "free_text_alias"},
            "weakest_category_by_metric": {
                "efficacy_improvement_pp": {"category": "safety_warning"},
            },
        },
    }
    candidate_report = {
        "case_count": 12,
        "summary": {
            "efficacy_improvement_pp": {
                "score": 4.5,
                "passed": True,
                "target": 0.0,
                "comparison": "positive",
                "unit": "percentage_points",
            },
            "next_action_accuracy_pct": {
                "score": 88.0,
                "passed": True,
                "target": 80.0,
                "comparison": "min",
                "unit": "percent",
            },
        },
        "weakest_slice_summary": {
            "weakest_category_overall": {"category": "missing_context"},
            "weakest_category_by_metric": {
                "efficacy_improvement_pp": {"category": "edge_case"},
            },
        },
    }

    comparison = compare_eval_reports(
        baseline_report,
        candidate_report,
        baseline_report_path="baseline.json",
        candidate_report_path="candidate.json",
    )

    assert comparison["case_count_delta"] == 2.0
    assert comparison["metric_deltas"]["efficacy_improvement_pp"]["delta"] == 1.5
    assert comparison["metric_deltas"]["next_action_accuracy_pct"]["delta"] == -2.0
    assert comparison["weakest_slice_delta"]["both_available"] is True
    assert comparison["weakest_slice_delta"]["overall_category_changed"] is True
    assert (
        comparison["weakest_slice_delta"]["metric_category_changes"]["efficacy_improvement_pp"][
            "changed"
        ]
        is True
    )


def test_write_eval_report_comparison_files_creates_json_and_markdown(tmp_path: Path) -> None:
    comparison = compare_eval_reports(
        {
            "case_count": 1,
            "summary": {
                "recommendation_coverage_pct": {
                    "score": 100.0,
                    "passed": True,
                    "target": 80.0,
                    "comparison": "min",
                    "unit": "percent",
                }
            },
        },
        {
            "case_count": 1,
            "summary": {
                "recommendation_coverage_pct": {
                    "score": 95.0,
                    "passed": True,
                    "target": 80.0,
                    "comparison": "min",
                    "unit": "percent",
                }
            },
        },
        baseline_report_path="baseline.json",
        candidate_report_path="candidate.json",
    )

    output_json = tmp_path / "eval_compare.json"
    output_md = tmp_path / "eval_compare.md"
    write_eval_report_comparison_files(
        comparison,
        output_json_path=output_json,
        output_md_path=output_md,
    )

    assert output_json.exists()
    assert output_md.exists()
    assert "metric deltas" in render_eval_report_comparison_markdown(comparison)
    assert "weakest slice delta" in render_eval_report_comparison_markdown(comparison)
