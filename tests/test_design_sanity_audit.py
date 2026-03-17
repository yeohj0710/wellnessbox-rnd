from wellnessbox_rnd.evals.design_sanity_audit import (
    build_design_sanity_audit,
    load_json,
    render_design_sanity_audit_markdown,
)


def test_build_design_sanity_audit_reports_directionally_sound_but_data_risky() -> None:
    audit = build_design_sanity_audit(
        learned_boundary_audit=load_json("artifacts/reports/learned_runtime_boundary_audit_v1.json"),
        learned_boundary_audit_path="artifacts/reports/learned_runtime_boundary_audit_v1.json",
        next_action_audit=load_json("artifacts/reports/next_action_state_machine_audit_v1.json"),
        next_action_audit_path="artifacts/reports/next_action_state_machine_audit_v1.json",
        pro_contract=load_json("artifacts/reports/pro_scoring_contract_v1.json"),
        pro_contract_path="artifacts/reports/pro_scoring_contract_v1.json",
        baseline_identical_signal_audit=load_json(
            "artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json"
        ),
        baseline_identical_signal_audit_path="artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json",
        partition_validity_audit=load_json(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        partition_validity_audit_path="artifacts/reports/dataset_f_partition_validity_audit_v1.json",
        calibration_dependence_audit=load_json(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        calibration_dependence_audit_path="artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json",
        weakest_slice_summary=load_json(
            "artifacts/reports/weakest_slice_frozen_eval_summary_v1.json"
        ),
        weakest_slice_summary_path="artifacts/reports/weakest_slice_frozen_eval_summary_v1.json",
        core_kpi_path_summary=load_json("artifacts/reports/core_kpi_path_summary_v1.json"),
        core_kpi_path_summary_path="artifacts/reports/core_kpi_path_summary_v1.json",
        latest_effect_candidate_reject_decision=load_json(
            "artifacts/reports/latest_effect_candidate_reject_decision_v1.json"
        ),
        latest_effect_candidate_reject_decision_path=(
            "artifacts/reports/latest_effect_candidate_reject_decision_v1.json"
        ),
        latest_training_compare_vs_baseline=load_json(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_"
            "replay_compare_vs_baseline_v1.json"
        ),
        latest_training_compare_vs_baseline_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_"
            "replay_compare_vs_baseline_v1.json"
        ),
        latest_training_compare_vs_prior_candidate=load_json(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_"
            "replay_compare_vs_prior_candidate_v1.json"
        ),
        latest_training_compare_vs_prior_candidate_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_"
            "replay_compare_vs_prior_candidate_v1.json"
        ),
        recommendation_service_path="src/wellnessbox_rnd/orchestration/recommendation_service.py",
        optimizer_service_path="src/wellnessbox_rnd/optimizer/service.py",
    )

    overall = audit["overall_verdict"]
    assert overall["fundamentally_wrong_research_direction"] is False
    assert overall["direction_status"] == "directionally_sound_but_data_validity_risky"
    assert overall["current_phase"] == "contract_data_eval_hardening"
    assert overall["principal_blocker"] == "synthetic_data_circularity_and_generator_contamination"
    assert (
        overall["current_candidate_assessment"]["adoption_status"]
        == "reject_candidate_keep_baseline"
    )
    assert (
        overall["current_candidate_assessment"]["latest_training_loop_result"]
        == "null_result_same_as_current_held_candidate"
    )
    assert (
        overall["current_candidate_assessment"]["evidence"][
            "prior_candidate_test_aggregate_mae_delta"
        ]
        == 0.0
    )
    readable = audit["readable_summary"]
    assert readable["design_verdict"]["fundamentally_wrong_research_direction"] is False
    assert (
        readable["deterministic_runtime_digest"]["deterministic_safety_separation"]
        == "sound_with_gaps"
    )
    assert readable["kpi_path_digest"]["pro_baseline_followup_kpi_path"] == "sound"
    assert readable["synthetic_risk_digest"]["status"] == "material_risk"
    assert len(readable["evidence_needed_digest"]) == 2

    dimensions = audit["dimensions"]
    assert dimensions["deterministic_safety_separation"]["status"] == "sound_with_gaps"
    assert dimensions["lightweight_recommendation_optimization_separation"]["status"] == "sound"
    assert dimensions["pro_baseline_followup_kpi_path"]["status"] == "sound"
    assert dimensions["explicit_next_action_state_machine"]["status"] == "sound"
    assert dimensions["replay_only_learned_boundary"]["status"] == "sound"
    assert (
        dimensions["synthetic_data_leakage_circularity_baseline_identical_risk"]["status"]
        == "material_risk"
    )
    assert overall["strong_dimension_count"] == 5


def test_render_design_sanity_audit_markdown_surfaces_required_sections() -> None:
    audit = {
        "readable_summary": {
            "design_verdict": {
                "fundamentally_wrong_research_direction": False,
                "direction_status": "directionally_sound_but_data_validity_risky",
                "current_phase": "contract_data_eval_hardening",
                "principal_blocker": "synthetic_data_circularity_and_generator_contamination",
                "short_conclusion": "Current direction is not fundamentally wrong.",
            },
            "deterministic_runtime_digest": {
                "deterministic_safety_separation": "sound_with_gaps",
                "recommendation_optimization_separation": "sound",
                "explicit_next_action_state_machine": "sound",
                "replay_only_learned_boundary": "sound",
            },
            "kpi_path_digest": {
                "pro_baseline_followup_kpi_path": "sound",
                "latest_candidate_adoption_status": "reject_candidate_keep_baseline",
                "latest_candidate_fit_gate_status": "worse_on_all_fit_gates",
            },
            "synthetic_risk_digest": {"status": "material_risk"},
            "evidence_needed_digest": ["c"],
        },
        "overall_verdict": {
            "direction_status": "directionally_sound_but_data_validity_risky",
            "fundamentally_wrong_research_direction": False,
            "current_phase": "contract_data_eval_hardening",
            "principal_blocker": "synthetic_data_circularity_and_generator_contamination",
            "summary": "summary",
            "rationale": ["a", "b"],
            "evidence_needed_before_claiming_directional_success": ["c"],
        },
        "dimensions": {
            "deterministic_safety_separation": {
                "status": "sound_with_gaps",
                "judgement": "deterministic_safety_is_separate_and_precedent_preserving",
                "summary": "ok",
            }
        },
    }

    markdown = render_design_sanity_audit_markdown(audit)

    assert "# design sanity audit v1" in markdown
    assert "## Verdict" in markdown
    assert "## Current Read" in markdown
    assert "direction_status" in markdown
    assert "deterministic_safety_separation" in markdown
    assert "evidence needed" in markdown
    assert "fundamentally_wrong_research_direction" in markdown
    assert "current candidate" in markdown
