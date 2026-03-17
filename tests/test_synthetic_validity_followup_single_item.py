from pathlib import Path

from wellnessbox_rnd.training.synthetic_validity_followup_single_item import (
    build_synthetic_validity_followup_single_item,
    load_json,
    render_synthetic_validity_followup_single_item_markdown,
    write_synthetic_validity_followup_single_item_files,
)


def test_build_synthetic_validity_followup_single_item_marks_calibration_target_as_still_risky(
) -> None:
    audit = build_synthetic_validity_followup_single_item(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        synthetic_validity_audit=load_json(
            "artifacts/reports/synthetic_validity_audit_v1.json"
        ),
        synthetic_validity_audit_path="artifacts/reports/synthetic_validity_audit_v1.json",
        calibration_dependence_audit=load_json(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        calibration_dependence_audit_path=(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        partition_validity_audit=load_json(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        partition_validity_audit_path=(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        policy_proxy_replay_split_audit=load_json(
            "artifacts/reports/policy_proxy_replay_split_audit_v1.json"
        ),
        policy_proxy_replay_split_audit_path=(
            "artifacts/reports/policy_proxy_replay_split_audit_v1.json"
        ),
    )

    assert audit["scope"]["chosen_item"] == "calibration_target_coupling"
    assert audit["scope"]["case_count"] == 480
    assert audit["selection"]["chosen_item"] == "calibration_target_coupling"

    candidate = audit["measured_concentration"]["candidate_test"]
    baseline = audit["measured_concentration"]["baseline_test"]
    replay = audit["measured_concentration"]["replay_shift_assessment"]
    disposition = audit["final_disposition"]
    evidence_path = audit["evidence_path"]

    assert candidate == {
        "overall_record_count": 80,
        "supported_record_count": 50,
        "unsupported_record_count": 30,
        "overall_gain": 0.106638,
        "supported_gain": 0.182137,
        "unsupported_gain": -0.019194,
        "supported_weighted_contribution": 0.113836,
        "unsupported_weighted_contribution": -0.007198,
        "supported_share_of_net_gain_pct": 106.75,
        "unsupported_share_of_net_gain_pct": -6.75,
        "supported_minus_unsupported_gain": 0.201331,
    }
    assert baseline == {
        "overall_record_count": 80,
        "supported_record_count": 50,
        "unsupported_record_count": 30,
        "overall_gain": 0.110188,
        "supported_gain": 0.19599,
        "unsupported_gain": -0.032817,
        "supported_weighted_contribution": 0.122494,
        "unsupported_weighted_contribution": -0.012306,
        "supported_share_of_net_gain_pct": 111.17,
        "unsupported_share_of_net_gain_pct": -11.17,
        "supported_minus_unsupported_gain": 0.228807,
    }
    assert len(evidence_path["acceptable_shared_assumptions"]) == 3
    assert len(evidence_path["unacceptable_leakage_or_contamination"]) == 3
    assert len(evidence_path["ambiguous_remaining_risk"]) == 2
    assert replay == {
        "verdict": "supported_slice_replay_shift_concentrated",
        "effect_only_shift_concentration": "supported_effect_enriched",
        "combined_shift_concentration": "supported_effect_enriched",
        "summary": (
            "Calibration-neutralization replay shifts are concentrated in supported "
            "effect-enriched users for both effect-only and combined modes, while the "
            "unsupported base-clone split stays behaviorally unchanged."
        ),
        "overall_effect_only_changed_trace_user_count": 10,
        "supported_effect_only_changed_trace_user_count": 10,
        "unsupported_effect_only_changed_trace_user_count": 0,
        "overall_combined_changed_trace_user_count": 9,
        "supported_combined_changed_trace_user_count": 9,
        "unsupported_combined_changed_trace_user_count": 0,
    }
    assert disposition["resolution_state"] == "still_risky"
    assert disposition["actionable_for_future_gate_work"] is True
    assert "pre-policy-proxy or neutralized proxy metrics" in disposition[
        "narrow_remediation_recommendation"
    ]
    assert audit["validation_issues"] == []


def test_write_synthetic_validity_followup_single_item_files_creates_outputs(
    tmp_path: Path,
) -> None:
    audit = build_synthetic_validity_followup_single_item(
        dataset_path="data/synthetic/synthetic_longitudinal_v4.jsonl",
        synthetic_validity_audit=load_json(
            "artifacts/reports/synthetic_validity_audit_v1.json"
        ),
        synthetic_validity_audit_path="artifacts/reports/synthetic_validity_audit_v1.json",
        calibration_dependence_audit=load_json(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        calibration_dependence_audit_path=(
            "artifacts/reports/policy_proxy_calibration_dependence_audit_v1.json"
        ),
        partition_validity_audit=load_json(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        partition_validity_audit_path=(
            "artifacts/reports/dataset_f_partition_validity_audit_v1.json"
        ),
        policy_proxy_replay_split_audit=load_json(
            "artifacts/reports/policy_proxy_replay_split_audit_v1.json"
        ),
        policy_proxy_replay_split_audit_path=(
            "artifacts/reports/policy_proxy_replay_split_audit_v1.json"
        ),
    )

    json_path = tmp_path / "synthetic_validity_followup_single_item_v1.json"
    md_path = tmp_path / "synthetic_validity_followup_single_item_v1.md"
    write_synthetic_validity_followup_single_item_files(
        audit=audit,
        report_json_path=json_path,
        report_md_path=md_path,
    )
    markdown = render_synthetic_validity_followup_single_item_markdown(audit)

    assert json_path.exists()
    assert md_path.exists()
    assert "# synthetic validity followup single item v1" in markdown
    assert "Acceptable Shared Assumptions" in markdown
    assert "Unacceptable Leakage Or Contamination" in markdown
    assert "Final Disposition" in markdown
    assert "resolution_state: `still_risky`" in markdown
