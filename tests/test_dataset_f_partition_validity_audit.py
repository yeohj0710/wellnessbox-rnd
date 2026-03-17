from pathlib import Path

from wellnessbox_rnd.training.dataset_f_partition_validity_audit import (
    build_dataset_f_partition_validity_audit,
    load_json,
    render_dataset_f_partition_validity_audit_markdown,
    write_dataset_f_partition_validity_audit_files,
)


def test_build_dataset_f_partition_validity_audit_splits_supported_and_base_clone() -> None:
    audit = build_dataset_f_partition_validity_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        path_safety_audit=load_json("artifacts/reports/dataset_f_path_safety_audit_v2.json"),
        path_safety_audit_path="artifacts/reports/dataset_f_path_safety_audit_v2.json",
        calibration_dependence_audit=load_json(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        calibration_dependence_audit_path=(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        pair_summary=load_json("artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json"),
        pair_summary_path="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
    )

    assessment = audit["assessment"]
    supported = audit["partitions"]["supported_effect_enriched"]
    unsupported = audit["partitions"]["unsupported_base_clone"]

    assert assessment["verdict"] == "do_not_pool_supported_and_base_clone_validity"
    assert supported["case_count"] == 325
    assert unsupported["case_count"] == 155
    assert supported["risk_tier_counts"] == {"low": 325}
    assert unsupported["risk_tier_counts"] == {"high": 155}
    assert supported["adverse_event_count"] == 0
    assert unsupported["adverse_event_count"] == 31
    assert supported["path_evidence"]["exact_reconstruction_rate_pct"] == 100.0
    assert supported["path_evidence"]["assignment_top2_match_rate_pct"] == 100.0
    assert supported["path_evidence"]["candidate_test_calibration_gain"] == 0.182137
    assert unsupported["path_evidence"]["candidate_test_calibration_gain"] == -0.019194
    assert audit["validation_issues"] == []


def test_write_dataset_f_partition_validity_audit_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = build_dataset_f_partition_validity_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        path_safety_audit=load_json("artifacts/reports/dataset_f_path_safety_audit_v2.json"),
        path_safety_audit_path="artifacts/reports/dataset_f_path_safety_audit_v2.json",
        calibration_dependence_audit=load_json(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        calibration_dependence_audit_path=(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        pair_summary=load_json("artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json"),
        pair_summary_path="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
    )

    json_path = tmp_path / "dataset_f_partition_validity_audit_v1.json"
    md_path = tmp_path / "dataset_f_partition_validity_audit_v1.md"
    write_dataset_f_partition_validity_audit_files(
        audit=audit,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_dataset_f_partition_validity_audit_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "# dataset f partition validity audit v1" in markdown
    assert "Supported Effect-Enriched" in markdown
    assert "Unsupported Base-Clone" in markdown
