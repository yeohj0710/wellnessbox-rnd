from wellnessbox_rnd.evals.kpi_candidate_summary import (
    build_kpi_candidate_summary,
    load_json,
    render_kpi_candidate_summary_markdown,
)


def test_build_kpi_candidate_summary_surfaces_baseline_candidate_and_weakest_slice() -> None:
    summary = build_kpi_candidate_summary(
        baseline_eval_report=load_json("artifacts/reports/full_eval_harness_with_compare_v1/eval_report.json"),
        baseline_eval_report_path="artifacts/reports/full_eval_harness_with_compare_v1/eval_report.json",
        candidate_compare_report=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_replay_compare_vs_baseline_v1.json"
        ),
        candidate_compare_report_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_replay_compare_vs_baseline_v1.json"
        ),
        weakest_slice_summary=load_json(
            "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
        ),
        weakest_slice_summary_path="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
    )

    assert summary["baseline_reference"]["case_count"] == 256
    assert summary["baseline_reference"]["metrics"]["recommendation_coverage_pct"]["score"] == 100.0
    assert (
        summary["candidate_comparison"]["candidate_label"]
        == "effect_model_v3_training_view_enforced_slice_balanced_candidate"
    )
    assert summary["candidate_comparison"]["fit_gate_status"] == "worse_on_all_fit_gates"
    assert (
        summary["candidate_comparison"]["delta_summary"]["test_aggregate_mae_delta"]
        == 0.005063
    )
    assert (
        summary["weakest_slice_delta"]["frozen_eval_anchor"]["overall_category"]
        == "safety_blocked"
    )
    assert (
        summary["weakest_slice_delta"]["dominant_candidate_regression_slice"] == "low_risk"
    )
    assert summary["adoption_summary"]["decision"] == "hold_baseline_candidate_not_ready"


def test_render_kpi_candidate_summary_markdown_contains_required_sections() -> None:
    summary = {
        "baseline_reference": {
            "case_count": 256,
            "metrics": {
                "recommendation_coverage_pct": {
                    "score": 100.0,
                    "target": 80.0,
                    "passed": True,
                }
            },
        },
        "candidate_comparison": {
            "candidate_label": "candidate_a",
            "fit_gate_status": "worse_on_all_fit_gates",
            "delta_summary": {
                "test_aggregate_mae_delta": 0.1,
                "test_aggregate_r2_delta": -0.2,
                "test_policy_proxy_mae_delta": 0.3,
            },
        },
        "weakest_slice_delta": {
            "frozen_eval_anchor": {
                "overall_category": "safety_blocked",
                "overall_case_count": 17,
                "overall_metric_names": ["next_action_accuracy_pct"],
                "sensor_genetic_category": "free_text_alias",
                "sensor_genetic_score": 66.66666666666667,
                "sensor_genetic_target": 90.0,
            },
            "dominant_candidate_regression_slice": "low_risk",
            "candidate_regression_balance": {
                "low_risk_regression_score": 20,
                "cgm_regression_score": 8,
            },
            "still_empty_weakest_families": ["bone_joint", "safety_warning"],
        },
        "adoption_summary": {
            "decision": "hold_baseline_candidate_not_ready",
            "one_line_conclusion": "Hold baseline.",
        },
    }

    markdown = render_kpi_candidate_summary_markdown(summary)

    assert "# baseline candidate kpi summary v1" in markdown
    assert "## Baseline Reference" in markdown
    assert "## Candidate Delta" in markdown
    assert "## Weakest Slice Delta" in markdown
    assert "Hold baseline." in markdown
