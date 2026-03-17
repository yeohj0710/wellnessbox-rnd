from pathlib import Path

from wellnessbox_rnd.training.dataset_f_path_safety_audit import (
    build_dataset_f_path_safety_audit,
    render_dataset_f_path_safety_audit_markdown,
    write_dataset_f_path_safety_audit_files,
)


def test_build_dataset_f_path_safety_audit_reports_current_repo_evidence() -> None:
    audit = build_dataset_f_path_safety_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        pair_summary_path="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
        feature_schema_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_candidate_feature_schema.json"
        ),
        eval_report_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_candidate_eval.json"
        ),
    )

    dataset_summary = audit["dataset_summary"]
    risk_assessment = audit["risk_assessment"]
    current_training_path = audit["current_training_path_evidence"]

    assert audit["audit_name"] == "dataset_f_path_safety_audit_v2"
    assert dataset_summary["case_count"] == 480
    assert dataset_summary["user_count"] == 96
    assert dataset_summary["supported_effect_enriched_record_count"] == 325
    assert dataset_summary["unsupported_or_base_clone_record_count"] == 155
    assert risk_assessment["leakage"]["status"] == "guarded_but_not_zero"
    assert risk_assessment["leakage"]["evidence"]["forbidden_training_feature_count"] == 0
    assert risk_assessment["circularity"]["status"] == "high_risk"
    assert risk_assessment["circularity"]["evidence"]["exact_full_reconstruction_count"] == 325
    assert risk_assessment["circularity"]["evidence"]["exact_reconstruction_rate_pct"] == 100.0
    assert risk_assessment["baseline_identical_label"]["status"] == "low_risk"
    assert (
        risk_assessment["baseline_identical_label"]["evidence"][
            "constant_baseline_user_count"
        ]
        == 96
    )
    assert (
        risk_assessment["baseline_identical_label"]["evidence"][
            "constant_baseline_with_label_variation_user_count"
        ]
        == 70
    )
    assert risk_assessment["generator_contamination"]["status"] == "high_risk"
    assert (
        risk_assessment["generator_contamination"]["evidence"][
            "supported_mode_top2_match_count"
        ]
        == 325
    )
    assert (
        risk_assessment["generator_contamination"]["evidence"][
            "supported_mode_top2_match_rate_pct"
        ]
        == 100.0
    )
    assert risk_assessment["frozen_eval_contamination"]["status"] == "low_risk"
    assert (
        risk_assessment["frozen_eval_contamination"]["evidence"][
            "exact_line_overlap_count"
        ]
        == 0
    )
    assert current_training_path["feature_count"] == 66
    assert current_training_path["test_metrics"]["aggregate_r2"] == 0.926918
    assert audit["overall_assessment"]["highest_risk_family"] == "circularity"


def test_write_dataset_f_path_safety_audit_files_creates_json_and_markdown(
    tmp_path: Path,
) -> None:
    audit = build_dataset_f_path_safety_audit(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        pair_summary_path="artifacts/reports/dataset_f_effect_prepost_pairs_summary_v1.json",
        feature_schema_path=(
            "artifacts/reports/"
            "effect_model_v3_training_view_enforced_candidate_feature_schema.json"
        ),
        eval_report_path=(
            "artifacts/reports/effect_model_v3_training_view_enforced_candidate_eval.json"
        ),
    )

    json_path = tmp_path / "dataset_f_path_safety_audit_v2.json"
    md_path = tmp_path / "dataset_f_path_safety_audit_v2.md"
    write_dataset_f_path_safety_audit_files(
        audit=audit,
        json_path=json_path,
        md_path=md_path,
    )
    markdown = render_dataset_f_path_safety_audit_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "## Risk Assessment" in markdown
    assert "### circularity" in markdown
    assert "highest_risk_family: `circularity`" in markdown
