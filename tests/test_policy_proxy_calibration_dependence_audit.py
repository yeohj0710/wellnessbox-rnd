from pathlib import Path

from wellnessbox_rnd.training.policy_proxy_calibration_dependence_audit import (
    build_policy_proxy_calibration_dependence_audit,
    load_effect_model_v1_artifact,
    load_json,
    render_policy_proxy_calibration_dependence_audit_markdown,
    write_policy_proxy_calibration_dependence_audit_files,
)


def test_build_policy_proxy_calibration_dependence_audit_reports_supported_slice_concentration(
) -> None:
    audit = build_policy_proxy_calibration_dependence_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        split_manifest=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        split_manifest_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        baseline_artifact=load_effect_model_v1_artifact("artifacts/models/effect_model_v3.json"),
        baseline_artifact_path="artifacts/models/effect_model_v3.json",
        candidate_artifact=load_effect_model_v1_artifact(
            "artifacts/models/effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        candidate_artifact_path=(
            "artifacts/models/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        candidate_eval_report=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_eval.json"
        ),
        candidate_eval_report_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_eval.json"
        ),
        candidate_feature_schema=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json"
        ),
        candidate_feature_schema_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json"
        ),
    )

    assessment = audit["assessment"]
    dataset_support_summary = audit["dataset_support_summary"]
    candidate_test_supported = audit["artifact_summaries"]["candidate"]["splits"]["test"][
        "supported_effect_enriched"
    ]
    candidate_test_unsupported = audit["artifact_summaries"]["candidate"]["splits"]["test"][
        "unsupported_base_clone"
    ]
    consistency_checks = audit["consistency_checks"]

    assert assessment["verdict"] == "material_supported_slice_calibration_dependence"
    assert assessment["dependence_status"] == "material"
    assert assessment["concentration_status"] == "supported_effect_enriched_slice"
    assert dataset_support_summary["supported_effect_enriched_case_count"] == 325
    assert dataset_support_summary["unsupported_base_clone_case_count"] == 155
    assert candidate_test_supported["record_count"] == 50
    assert candidate_test_unsupported["record_count"] == 30
    assert candidate_test_supported["policy_proxy_calibration_gain"] == 0.182137
    assert candidate_test_unsupported["policy_proxy_calibration_gain"] == -0.019194
    assert assessment["baseline_test_supported_gain"] == 0.19599
    assert assessment["baseline_test_unsupported_gain"] == -0.032817
    assert consistency_checks["candidate_val_pre_policy_proxy_mae_matches_feature_schema"] is True
    assert audit["validation_issues"] == []


def test_write_policy_proxy_calibration_dependence_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = build_policy_proxy_calibration_dependence_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        split_manifest=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        split_manifest_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_splits.json"
        ),
        baseline_artifact=load_effect_model_v1_artifact("artifacts/models/effect_model_v3.json"),
        baseline_artifact_path="artifacts/models/effect_model_v3.json",
        candidate_artifact=load_effect_model_v1_artifact(
            "artifacts/models/effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        candidate_artifact_path=(
            "artifacts/models/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate.json"
        ),
        candidate_eval_report=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_eval.json"
        ),
        candidate_eval_report_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_eval.json"
        ),
        candidate_feature_schema=load_json(
            "artifacts/reports/effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json"
        ),
        candidate_feature_schema_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_slice_balanced_candidate_feature_schema.json"
        ),
    )

    json_path = tmp_path / "policy_proxy_calibration_dependence_audit_v1.json"
    md_path = tmp_path / "policy_proxy_calibration_dependence_audit_v1.md"
    write_policy_proxy_calibration_dependence_audit_files(
        audit=audit,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_policy_proxy_calibration_dependence_audit_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "# policy proxy calibration dependence audit v1" in markdown
    assert "Pinpointed Risk Paths" in markdown
    assert "Summary Findings" in markdown
