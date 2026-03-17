from pathlib import Path

from wellnessbox_rnd.training.synthetic_prepost_path_audit import (
    build_synthetic_prepost_path_audit,
    load_json,
    render_synthetic_prepost_path_audit_markdown,
    write_synthetic_prepost_path_audit_files,
)


def test_build_synthetic_prepost_path_audit_pins_current_repo_risk_posture() -> None:
    audit = build_synthetic_prepost_path_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        pair_dataset_path="artifacts/datasets/dataset_f_effect_prepost_pairs_v1.jsonl",
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
        design_sanity_audit=load_json("artifacts/reports/design_sanity_audit_v1.json"),
        design_sanity_audit_path="artifacts/reports/design_sanity_audit_v1.json",
    )

    risk_posture = audit["risk_posture"]
    evidence = audit["evidence_snapshot"]
    readable_summary = audit["readable_summary"]
    overall = audit["overall_assessment"]

    assert risk_posture["leakage_status"] == "guarded_but_not_zero"
    assert risk_posture["circularity_status"] == "high_risk"
    assert risk_posture["baseline_identical_label_status"] == "low_risk"
    assert risk_posture["generator_contamination_status"] == "high_risk"
    assert risk_posture["frozen_eval_contamination_status"] == "low_risk"
    assert risk_posture["calibration_dependence_status"] == "material"
    assert risk_posture["partition_verdict"] == "do_not_pool_supported_and_base_clone_validity"

    assert evidence["case_count"] == 480
    assert evidence["pair_row_count"] == 480
    assert evidence["supported_effect_enriched_record_count"] == 325
    assert evidence["unsupported_or_base_clone_record_count"] == 155
    assert evidence["forbidden_training_feature_count"] == 0
    assert evidence["exact_reconstruction_rate_pct"] == 100.0
    assert evidence["supported_mode_top2_match_rate_pct"] == 100.0
    assert evidence["constant_baseline_user_count"] == 96
    assert evidence["constant_baseline_with_label_variation_user_count"] == 70
    assert evidence["shares_path_with_frozen_eval"] is False
    assert evidence["exact_line_overlap_count"] == 0
    assert (
        evidence["principal_blocker"]
        == "synthetic_data_circularity_and_generator_contamination"
    )
    assert readable_summary["risk_matrix"] == {
        "leakage": {
            "status": "guarded_but_not_zero",
            "headline": (
                "training-view enforcement blocks direct follow_up and other "
                "outcome-side fields from learned inputs."
            ),
        },
        "circularity": {
            "status": "high_risk",
            "headline": (
                "supported rows still reconstruct exactly from generator-produced "
                "follow_up formulas."
            ),
        },
        "baseline_identical_label": {
            "status": "low_risk",
            "headline": (
                "baseline-identical label-copy risk is reduced because many "
                "constant-baseline users still vary labels."
            ),
        },
        "generator_contamination": {
            "status": "high_risk",
            "headline": (
                "generator recommendation and label formulas still shape supported "
                "training targets directly."
            ),
        },
        "frozen_eval_contamination": {
            "status": "low_risk",
            "headline": (
                "path-level and exact-line checks still show no frozen-eval overlap."
            ),
        },
    }
    assert readable_summary["safe_now_digest"] == {
        "forbidden_training_feature_count": 0,
        "training_input_allowed_fields": [
            "goal",
            "baseline",
            "input_flags",
            "recommended_set",
            "period",
        ],
        "training_input_forbidden_fields": [
            "follow_up",
            "adverse_event",
            "expected_effect_proxy",
            "adherence_proxy",
            "side_effect_proxy",
            "next_action",
            "risk_tier",
            "response_profile",
        ],
        "constant_baseline_with_label_variation_rate_pct": 72.92,
        "shares_path_with_frozen_eval": False,
        "exact_line_overlap_count": 0,
    }
    assert readable_summary["risky_now_digest"] == {
        "exact_reconstruction_rate_pct": 100.0,
        "supported_mode_top2_match_rate_pct": 100.0,
        "calibration_dependence_status": "material",
        "calibration_dependence_concentration": "supported_effect_enriched_slice",
        "partition_verdict": "do_not_pool_supported_and_base_clone_validity",
    }
    assert readable_summary["pinpointed_path_digest"] == {
        "calibration_target_coupling": [
            "src/wellnessbox_rnd/training/effect_model_v1.py:1862"
        ],
        "circularity": [
            "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:625"
        ],
        "frozen_eval_guard": [
            "src/wellnessbox_rnd/training/effect_model_v1.py:1044"
        ],
        "generator_contamination": [
            "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:207",
            "src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py:765",
        ],
        "leakage_guard": [
            "src/wellnessbox_rnd/training/effect_model_v1.py:169",
            "src/wellnessbox_rnd/training/effect_model_v1.py:1939",
        ],
        "pair_contract_mixing": [
            "src/wellnessbox_rnd/training/effect_model_v1.py:90"
        ],
    }
    assert readable_summary["one_line_read"] == (
        "Direct feature leakage and frozen-eval contamination are guarded, "
        "but supported-slice circularity, generator contamination, and "
        "calibration-target coupling still make this path unsafe for a strong "
        "independent efficacy claim."
    )

    assert overall["verdict"] == "guarded_but_not_safe_for_strong_independent_efficacy_claim"
    assert "circularity" in overall["principal_risky_families"]
    assert "frozen_eval_contamination" in overall["principal_safe_families"]
    assert len(audit["pinpointed_risk_paths"]) == 8
    assert audit["validation_issues"] == []


def test_write_synthetic_prepost_path_audit_files_creates_outputs(tmp_path: Path) -> None:
    audit = build_synthetic_prepost_path_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        pair_dataset_path="artifacts/datasets/dataset_f_effect_prepost_pairs_v1.jsonl",
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
        design_sanity_audit=load_json("artifacts/reports/design_sanity_audit_v1.json"),
        design_sanity_audit_path="artifacts/reports/design_sanity_audit_v1.json",
    )

    json_path = tmp_path / "synthetic_prepost_path_audit_v1.json"
    md_path = tmp_path / "synthetic_prepost_path_audit_v1.md"
    write_synthetic_prepost_path_audit_files(
        audit=audit,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_synthetic_prepost_path_audit_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "# synthetic prepost path audit v1" in markdown
    assert "Readable Summary" in markdown
    assert "Pinpointed Risk Paths" in markdown
    assert "Safe Now" in markdown
    assert "Risky Now" in markdown
