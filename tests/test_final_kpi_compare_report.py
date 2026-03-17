from wellnessbox_rnd.evals.final_kpi_compare_report import (
    build_final_kpi_compare_report,
    load_json,
    render_final_kpi_compare_report_markdown,
)


def test_build_final_kpi_compare_report_surfaces_decision_useful_compare_state() -> None:
    report = build_final_kpi_compare_report(
        baseline_candidate_summary=load_json(
            "artifacts/reports/baseline_candidate_kpi_summary_v1.json"
        ),
        baseline_candidate_summary_path="artifacts/reports/baseline_candidate_kpi_summary_v1.json",
        weakest_slice_summary=load_json(
            "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
        ),
        weakest_slice_summary_path="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
        core_kpi_path_summary=load_json(
            "artifacts/reports/core_kpi_path_summary_v1.json"
        ),
        core_kpi_path_summary_path="artifacts/reports/core_kpi_path_summary_v1.json",
    )

    assert report["baseline_reference"]["case_count"] == 256
    assert (
        report["latest_candidate"]["candidate_label"]
        == "effect_model_v3_training_view_enforced_slice_balanced_candidate"
    )
    assert report["latest_candidate"]["fit_gate_status"] == "worse_on_all_fit_gates"
    assert report["slice_compare"]["overall"]["dominant_candidate_regression_slice"] == (
        "low_risk"
    )
    assert report["slice_compare"]["cgm"]["geometry_status"] == (
        "structural_continue_plan_overlap_persists"
    )
    assert report["weakest_slice_anchor"]["overall_weakest_category"] == "safety_blocked"
    assert report["decision_summary"]["decision_class"] == (
        "hold_baseline_candidate_not_ready"
    )
    assert report["readable_summary"]["decision_readout"]["principal_blocker"] == (
        "synthetic_data_circularity_and_generator_contamination"
    )
    assert report["readable_summary"]["baseline_reference_digest"]["case_count"] == 256
    assert (
        report["readable_summary"]["candidate_delta_digest"]["fit_gate_status"]
        == "worse_on_all_fit_gates"
    )
    assert (
        report["readable_summary"]["slice_compare_digest"]["overall"][
            "dominant_candidate_regression_slice"
        ]
        == "low_risk"
    )
    assert (
        report["readable_summary"]["weakest_slice_delta_digest"][
            "low_risk_combined_disagreement_delta"
        ]
        == 62
    )
    assert (
        report["readable_summary"]["audit_path_digest"]["weakest_slice_wiring_status"]
        == "connected_with_remaining_gaps"
    )
    assert len(report["readable_summary"]["next_evidence_digest"]) == 2
    assert len(report["next_evidence_needed"]) == 2


def test_render_final_kpi_compare_report_markdown_contains_required_sections() -> None:
    markdown = render_final_kpi_compare_report_markdown(
        {
            "readable_summary": {
                "decision_readout": {
                    "decision_class": "hold_baseline_candidate_not_ready",
                    "candidate_label": "candidate_a",
                    "one_line_judgement": "Hold baseline.",
                    "dominant_candidate_regression_slice": "low_risk",
                    "principal_blocker": "synthetic_data_circularity_and_generator_contamination",
                },
                "baseline_reference_digest": {"case_count": 256},
                "candidate_delta_digest": {"fit_gate_status": "worse_on_all_fit_gates"},
                "slice_compare_digest": {
                    "overall": {"dominant_candidate_regression_slice": "low_risk"}
                },
                "weakest_slice_delta_digest": {"low_risk_combined_disagreement_delta": 62},
                "audit_path_digest": {"weakest_slice_wiring_status": "connected"},
                "next_evidence_digest": [
                    "Need one replay-only improvement proof.",
                    "Need one bounded family explanation.",
                ],
                "one_line_decision": "Hold baseline.",
            },
            "baseline_reference": {
                "dataset_path": "data/frozen_eval/frozen_eval_v1.jsonl",
                "case_count": 256,
                "metrics": {
                    "recommendation_coverage_pct": {"score": 100.0},
                    "efficacy_improvement_pp": {"score": 9.9},
                    "next_action_accuracy_pct": {"score": 99.2},
                    "safety_reference_accuracy_pct": {"score": 99.8},
                    "sensor_genetic_integration_rate_pct": {"score": 90.4},
                },
            },
            "latest_candidate": {
                "candidate_label": "candidate_a",
                "fit_metrics": {"aggregate_mae": 0.01},
                "reference_fit_metrics": {"aggregate_mae": 0.003},
                "fit_gate_status": "worse_on_all_fit_gates",
                "overall_delta": {"test_aggregate_mae_delta": 0.007},
            },
            "slice_compare": {
                "overall": {"dominant_candidate_regression_slice": "low_risk"},
                "low_risk": {"combined_disagreement_delta": 62},
                "cgm": {"combined_disagreement_delta": 6},
            },
            "weakest_slice_anchor": {
                "overall_weakest_category": "safety_blocked",
                "overall_weakest_metrics": ["next_action_accuracy_pct"],
                "sensor_genetic_weakest_category": "free_text_alias",
                "sensor_genetic_score": 66.67,
                "still_empty_weakest_families": ["bone_joint"],
            },
            "decision_summary": {
                "decision_class": "hold_baseline_candidate_not_ready",
                "one_line_judgement": "Hold baseline.",
            },
            "next_evidence_needed": [
                "Need one replay-only improvement proof.",
                "Need one bounded family explanation.",
            ],
        }
    )

    assert "# final kpi compare report v1" in markdown
    assert "## Decision Readout" in markdown
    assert "## Readable Summary" in markdown
    assert "## Baseline Reference" in markdown
    assert "## Latest Candidate" in markdown
    assert "## Slice Compare" in markdown
    assert "## Weakest-Slice Anchor" in markdown
    assert "## Next Evidence" in markdown
    assert "Hold baseline." in markdown
    assert "aggregate_mae_delta" in markdown
    assert "low_risk_combined_disagreement_delta" in markdown
