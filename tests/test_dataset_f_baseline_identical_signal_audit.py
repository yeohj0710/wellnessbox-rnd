from pathlib import Path

from wellnessbox_rnd.training.dataset_f_baseline_identical_signal_audit import (
    build_dataset_f_baseline_identical_signal_audit,
    load_json,
    render_dataset_f_baseline_identical_signal_audit_markdown,
    write_dataset_f_baseline_identical_signal_audit_files,
)


def test_build_dataset_f_baseline_identical_signal_audit_reports_reduced_label_copy() -> None:
    audit = build_dataset_f_baseline_identical_signal_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        path_safety_audit=load_json("artifacts/reports/dataset_f_path_safety_audit_v2.json"),
        path_safety_audit_path="artifacts/reports/dataset_f_path_safety_audit_v2.json",
        data_quality_report=load_json("artifacts/reports/dataset_f_data_quality_v1.json"),
        data_quality_report_path="artifacts/reports/dataset_f_data_quality_v1.json",
        feature_schema=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_heterogeneity_candidate_feature_schema.json"
        ),
        feature_schema_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_feature_schema.json"
        ),
        pair_summary=load_json(
            "artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json"
        ),
        pair_summary_path="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
        split_manifest=load_json(
            "artifacts/reports/dataset_f_effect_prepost_pairs_split_manifest_v1.json"
        ),
        split_manifest_path=(
            "artifacts/reports/dataset_f_effect_prepost_pairs_split_manifest_v1.json"
        ),
        replay_compare_report=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_heterogeneity_candidate_replay_compare_vs_baseline_v1.json"
        ),
        replay_compare_report_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_replay_compare_vs_baseline_v1.json"
        ),
    )

    assessment = audit["baseline_identical_signal_assessment"]
    evidence = audit["evidence"]

    assert (
        assessment["verdict"]
        == "baseline_identical_label_copy_risk_reduced_but_generator_simple_signal_remains"
    )
    assert assessment["label_copy_risk_status"] == "low_risk"
    assert (
        assessment["behavioral_replay_identity_status"]
        == "not_identical_to_deterministic_baseline"
    )
    assert assessment["generator_simple_signal_status"] == "still_present"
    assert (
        assessment["current_candidate_label"]
        == "effect_model_v3_training_view_enforced_heterogeneity_candidate"
    )
    assert evidence["label_copy_reduction"]["constant_baseline_user_count"] == 96
    assert (
        evidence["label_copy_reduction"]["constant_baseline_with_label_variation_user_count"]
        == 70
    )
    assert evidence["residual_signal_risk"]["exact_reconstruction_rate_pct"] == 100.0
    assert evidence["residual_signal_risk"]["supported_mode_top2_match_rate_pct"] == 100.0
    assert evidence["feature_schema_guard"]["forbidden_feature_count"] == 0
    assert evidence["feature_schema_guard"]["schema_validator_issue_count"] == 0
    assert evidence["feature_schema_guard"]["schema_validator_issues"] == []
    assert evidence["split_hygiene"]["shares_path_with_frozen_eval"] is False
    assert evidence["replay_evidence"]["effect_only_low_risk_disagreement_delta"] == 132


def test_write_dataset_f_baseline_identical_signal_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = build_dataset_f_baseline_identical_signal_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        path_safety_audit=load_json("artifacts/reports/dataset_f_path_safety_audit_v2.json"),
        path_safety_audit_path="artifacts/reports/dataset_f_path_safety_audit_v2.json",
        data_quality_report=load_json("artifacts/reports/dataset_f_data_quality_v1.json"),
        data_quality_report_path="artifacts/reports/dataset_f_data_quality_v1.json",
        feature_schema=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_heterogeneity_candidate_feature_schema.json"
        ),
        feature_schema_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_feature_schema.json"
        ),
        pair_summary=load_json(
            "artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json"
        ),
        pair_summary_path="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
        split_manifest=load_json(
            "artifacts/reports/dataset_f_effect_prepost_pairs_split_manifest_v1.json"
        ),
        split_manifest_path=(
            "artifacts/reports/dataset_f_effect_prepost_pairs_split_manifest_v1.json"
        ),
        replay_compare_report=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_heterogeneity_candidate_replay_compare_vs_baseline_v1.json"
        ),
        replay_compare_report_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_heterogeneity_candidate_replay_compare_vs_baseline_v1.json"
        ),
    )

    json_path = tmp_path / "dataset_f_baseline_identical_signal_audit_v1.json"
    md_path = tmp_path / "dataset_f_baseline_identical_signal_audit_v1.md"
    write_dataset_f_baseline_identical_signal_audit_files(
        audit=audit,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_dataset_f_baseline_identical_signal_audit_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "# dataset f baseline-identical signal audit v1" in markdown
    assert "Residual Risk Paths" in markdown
    assert "Already Reduced Evidence" in markdown
