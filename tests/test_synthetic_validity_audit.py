from pathlib import Path

from wellnessbox_rnd.training.synthetic_validity_audit import (
    build_synthetic_validity_audit,
    load_json,
    render_synthetic_validity_audit_markdown,
    write_synthetic_validity_audit_files,
)


def test_build_synthetic_validity_audit_pins_current_repo_validity_verdict() -> None:
    audit = build_synthetic_validity_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        path_safety_audit=load_json("artifacts/reports/dataset_f_path_safety_audit_v2.json"),
        path_safety_audit_path="artifacts/reports/dataset_f_path_safety_audit_v2.json",
        baseline_identical_audit=load_json(
            "artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json"
        ),
        baseline_identical_audit_path=(
            "artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json"
        ),
        partition_validity_audit=load_json(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        partition_validity_audit_path=(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        calibration_dependence_audit=load_json(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        calibration_dependence_audit_path=(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        synthetic_prepost_audit=load_json(
            "artifacts/reports/synthetic_prepost_path_audit_v1.json"
        ),
        synthetic_prepost_audit_path="artifacts/reports/synthetic_prepost_path_audit_v1.json",
        feature_schema=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json"
        ),
        feature_schema_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json"
        ),
        split_manifest=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        split_manifest_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
    )

    path_map = audit["path_map"]
    status_answers = audit["status_answers"]
    memo = audit["go_no_go_memo"]
    readable_summary = audit["readable_summary"]
    upstream = audit["upstream_consistency"]

    assert path_map["training_inputs"] == {
        "allowed_fields": [
            "goal",
            "baseline",
            "input_flags",
            "recommended_set",
            "period",
        ],
        "forbidden_outcome_side_fields": [
            "follow_up",
            "adverse_event",
            "expected_effect_proxy",
            "adherence_proxy",
            "side_effect_proxy",
            "next_action",
            "risk_tier",
            "response_profile",
        ],
        "forbidden_feature_count": 0,
        "contract_version": "dataset_f_effect_training_view_v1",
    }
    assert path_map["calibration_targets"] == {
        "primary_target": "expected_effect_proxy",
        "fit_stage": "policy_proxy_calibration",
        "selection_stage": "pre_policy_proxy_calibration",
        "selection_pre_policy_proxy_mae": 0.200593,
    }
    assert path_map["split_independence"]["split_record_counts"] == {
        "train_record_count": 275,
        "val_record_count": 125,
        "test_record_count": 80,
    }

    assert status_answers["circularity"]["status"] == "present"
    assert status_answers["circularity"]["key_metrics"] == {
        "supported_exact_reconstruction_rate_pct": 100.0,
        "supported_case_count": 325,
    }
    assert status_answers["generator_contamination"]["status"] == "present"
    assert status_answers["generator_contamination"]["key_metrics"] == {
        "supported_assignment_top2_match_rate_pct": 100.0,
        "unsupported_assignment_top2_match_rate_pct": 30.32,
    }
    assert status_answers["calibration_target_coupling"]["status"] == "present"
    assert status_answers["calibration_target_coupling"]["key_metrics"] == {
        "dependence_status": "material",
        "concentration_status": "supported_effect_enriched_slice",
        "candidate_test_supported_gain": 0.182137,
        "candidate_test_unsupported_gain": -0.019194,
    }
    assert status_answers["direct_training_input_leakage"]["status"] == (
        "absent_on_current_training_view"
    )
    assert status_answers["frozen_eval_contamination"]["status"] == (
        "absent_on_current_checks"
    )
    assert status_answers["split_independence"]["status"] == "adequate_but_not_sufficient"

    assert memo["verdict"] == "no_go_for_training_rerun_justification"
    assert memo["circularity_answer"] == "present"
    assert memo["generator_contamination_answer"] == "present"
    assert memo["calibration_target_coupling_answer"] == "present"
    assert memo["training_rerun_justified_now"] is False
    assert memo["minimum_changes_before_future_training_rerun"] == [
        (
            "stop using supported effect-enriched exact-fit evidence as independent "
            "efficacy proof"
        ),
        (
            "separate pre-calibration fit from calibration-on-expected_effect_proxy "
            "gains in rerun gating"
        ),
        (
            "earn at least one new replay/data proof on a less circular surface "
            "before revisiting training"
        ),
    ]

    assert readable_summary["supported_slice_digest"] == {
        "supported_case_count": 325,
        "supported_exact_reconstruction_rate_pct": 100.0,
        "supported_assignment_top2_match_rate_pct": 100.0,
        "candidate_test_supported_calibration_gain": 0.182137,
    }
    assert readable_summary["unsupported_slice_digest"] == {
        "unsupported_case_count": 155,
        "unsupported_assignment_top2_match_rate_pct": 30.32,
        "candidate_test_unsupported_calibration_gain": -0.019194,
    }
    assert readable_summary["rerun_gate_digest"] == {
        "go_no_go": "no_go_for_training_rerun_justification",
        "training_rerun_justified_now": False,
        "principal_blocker": "synthetic_data_circularity_and_generator_contamination",
    }

    assert upstream == {
        "synthetic_prepost_verdict": "guarded_but_not_safe_for_strong_independent_efficacy_claim",
        "partition_verdict": "do_not_pool_supported_and_base_clone_validity",
        "baseline_identical_verdict": (
            "baseline_identical_label_copy_risk_reduced_but_generator_simple_signal_remains"
        ),
        "calibration_dependence_verdict": "material_supported_slice_calibration_dependence",
    }
    assert len(audit["contamination_paths"]) == 5
    assert audit["validation_issues"] == []


def test_write_synthetic_validity_audit_files_creates_outputs(tmp_path: Path) -> None:
    audit = build_synthetic_validity_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        path_safety_audit=load_json("artifacts/reports/dataset_f_path_safety_audit_v2.json"),
        path_safety_audit_path="artifacts/reports/dataset_f_path_safety_audit_v2.json",
        baseline_identical_audit=load_json(
            "artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json"
        ),
        baseline_identical_audit_path=(
            "artifacts/reports/dataset_f_baseline_identical_signal_audit_v1.json"
        ),
        partition_validity_audit=load_json(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        partition_validity_audit_path=(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        calibration_dependence_audit=load_json(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        calibration_dependence_audit_path=(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        synthetic_prepost_audit=load_json(
            "artifacts/reports/synthetic_prepost_path_audit_v1.json"
        ),
        synthetic_prepost_audit_path="artifacts/reports/synthetic_prepost_path_audit_v1.json",
        feature_schema=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json"
        ),
        feature_schema_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json"
        ),
        split_manifest=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        split_manifest_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
    )

    json_path = tmp_path / "synthetic_validity_audit_v1.json"
    md_path = tmp_path / "synthetic_validity_audit_v1.md"
    write_synthetic_validity_audit_files(
        audit=audit,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_synthetic_validity_audit_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "# synthetic validity audit v1" in markdown
    assert "Status Answers" in markdown
    assert "Contamination Paths" in markdown
    assert "Ranked Remediation" in markdown
    assert "Minimum Changes Before Future Training Rerun" in markdown
