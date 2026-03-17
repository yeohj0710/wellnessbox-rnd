from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_effect_training_revisit_decision(
    *,
    baseline_candidate_summary: dict[str, object],
    baseline_candidate_summary_path: str | Path,
    replay_split_audit: dict[str, object],
    replay_split_audit_path: str | Path,
    partition_validity_audit: dict[str, object],
    partition_validity_audit_path: str | Path,
    design_sanity_audit: dict[str, object],
    design_sanity_audit_path: str | Path,
    non_cgm_diagnostic: dict[str, object],
    non_cgm_diagnostic_path: str | Path,
) -> dict[str, object]:
    adoption_summary = _as_dict(baseline_candidate_summary.get("adoption_summary"))
    candidate_comparison = _as_dict(baseline_candidate_summary.get("candidate_comparison"))
    weakest_slice_delta = _as_dict(baseline_candidate_summary.get("weakest_slice_delta"))
    replay_assessment = _as_dict(replay_split_audit.get("assessment"))
    partition_assessment = _as_dict(partition_validity_audit.get("assessment"))
    overall_verdict = _as_dict(design_sanity_audit.get("overall_verdict"))
    target_family = _as_dict(non_cgm_diagnostic.get("target_family"))
    workflow_summary = _as_dict(non_cgm_diagnostic.get("workflow_summary"))
    feature_summary = _as_dict(non_cgm_diagnostic.get("feature_summary"))

    hold_baseline = (
        adoption_summary.get("decision") == "hold_baseline_candidate_not_ready"
    )
    fit_gate_status = str(candidate_comparison.get("fit_gate_status") or "")
    replay_shift_concentrated = (
        replay_assessment.get("verdict") == "supported_slice_replay_shift_concentrated"
    )
    partition_invalid_for_pooled_claim = (
        partition_assessment.get("verdict") == "do_not_pool_supported_and_base_clone_validity"
    )
    data_validity_risky = (
        overall_verdict.get("direction_status") == "directionally_sound_but_data_validity_risky"
        and overall_verdict.get("principal_blocker")
        == "synthetic_data_circularity_and_generator_contamination"
    )
    unresolved_non_cgm_family = (
        str(target_family.get("name") or "") == "non_cgm_continue_to_monitor_threshold_cross"
        and _to_int(target_family.get("observed_case_count")) > 0
    )

    revisit_justified_now = not any(
        (
            hold_baseline,
            fit_gate_status == "worse_on_all_fit_gates",
            replay_shift_concentrated,
            partition_invalid_for_pooled_claim,
            data_validity_risky,
            unresolved_non_cgm_family,
        )
    )

    decision = {
        "audit_name": "effect_training_revisit_decision_v1",
        "source_artifacts": {
            "baseline_candidate_summary_path": str(baseline_candidate_summary_path),
            "replay_split_audit_path": str(replay_split_audit_path),
            "partition_validity_audit_path": str(partition_validity_audit_path),
            "design_sanity_audit_path": str(design_sanity_audit_path),
            "non_cgm_diagnostic_path": str(non_cgm_diagnostic_path),
        },
        "decision_gate": {
            "revisit_justified_now": revisit_justified_now,
            "decision": (
                "defer_new_effect_training_loop"
                if not revisit_justified_now
                else "training_revisit_can_be_considered"
            ),
            "reason_codes": _reason_codes(
                hold_baseline=hold_baseline,
                fit_gate_status=fit_gate_status,
                replay_shift_concentrated=replay_shift_concentrated,
                partition_invalid_for_pooled_claim=partition_invalid_for_pooled_claim,
                data_validity_risky=data_validity_risky,
                unresolved_non_cgm_family=unresolved_non_cgm_family,
            ),
        },
        "evidence_summary": {
            "baseline_vs_candidate": {
                "adoption_decision": adoption_summary.get("decision"),
                "fit_gate_status": fit_gate_status,
                "one_line_conclusion": adoption_summary.get("one_line_conclusion"),
                "delta_summary": _as_dict(candidate_comparison.get("delta_summary")),
                "dominant_candidate_regression_slice": weakest_slice_delta.get(
                    "dominant_candidate_regression_slice"
                ),
            },
            "replay_split_boundary": {
                "verdict": replay_assessment.get("verdict"),
                "effect_only_shift_concentration": replay_assessment.get(
                    "effect_only_shift_concentration"
                ),
                "combined_shift_concentration": replay_assessment.get(
                    "combined_shift_concentration"
                ),
                "supported_effect_only_changed_trace_user_count": replay_assessment.get(
                    "supported_effect_only_changed_trace_user_count"
                ),
                "unsupported_effect_only_changed_trace_user_count": replay_assessment.get(
                    "unsupported_effect_only_changed_trace_user_count"
                ),
                "supported_combined_changed_trace_user_count": replay_assessment.get(
                    "supported_combined_changed_trace_user_count"
                ),
                "unsupported_combined_changed_trace_user_count": replay_assessment.get(
                    "unsupported_combined_changed_trace_user_count"
                ),
            },
            "synthetic_validity": {
                "partition_verdict": partition_assessment.get("verdict"),
                "supported_partition_role": partition_assessment.get(
                    "supported_partition_role"
                ),
                "unsupported_partition_role": partition_assessment.get(
                    "unsupported_partition_role"
                ),
                "leakage_status": partition_assessment.get("leakage_status"),
                "baseline_identical_label_status": partition_assessment.get(
                    "baseline_identical_label_status"
                ),
                "calibration_dependence_status": partition_assessment.get(
                    "calibration_dependence_status"
                ),
                "calibration_dependence_concentration": partition_assessment.get(
                    "calibration_dependence_concentration"
                ),
            },
            "design_sanity": {
                "direction_status": overall_verdict.get("direction_status"),
                "current_phase": overall_verdict.get("current_phase"),
                "principal_blocker": overall_verdict.get("principal_blocker"),
            },
            "unresolved_regression_family": {
                "target_family": target_family.get("name"),
                "observed_case_count": target_family.get("observed_case_count"),
                "transition": target_family.get("transition"),
                "trajectory_mode_counts": workflow_summary.get("trajectory_mode_counts"),
                "top_feature_families": _as_dict(
                    feature_summary.get("feature_family_delta_summary")
                ).get("top_absolute_families"),
            },
        },
        "decision_rationale": [
            (
                "Do not start another effect-training loop yet because the current candidate "
                "still loses to baseline on all overall fit gates."
            ),
            (
                "Replay-only neutralization evidence shows supported effect-enriched users are "
                "where calibration dependence changes behavior, so the remaining uncertainty is "
                "still inside the most circular synthetic slice."
            ),
            (
                "Dataset F validity is still split: supported rows are generator-circular and "
                "unsupported rows are control-like, so pooled improvement claims remain unsafe."
            ),
            (
                "The dominant unresolved regression family is still "
                "`non_cgm_continue_to_monitor_threshold_cross`, not a resolved cgm bottleneck."
            ),
        ],
        "required_evidence_before_revisit": [
            (
                "A replay-only result showing a new candidate no longer loses on aggregate_mae, "
                "aggregate_r2, and policy_proxy_mae versus baseline."
            ),
            (
                "Replay evidence that supported effect-enriched shift concentration is reduced "
                "rather than amplified under calibration-sensitive comparisons."
            ),
            (
                "A bounded explanation or fix for non_cgm_continue_to_monitor_threshold_cross "
                "that does not rely on broader synthetic validity assumptions."
            ),
        ],
        "summary_findings": [
            (
                "Current evidence does not justify another effect-training loop yet; keep work "
                "in replay-only / audit mode."
            ),
            (
                "The blocker is not missing architecture wiring but unresolved synthetic-data "
                "validity risk concentrated in supported effect-enriched rows."
            ),
            (
                "The remaining regression pressure is low-risk non-cgm threshold-cross drift, "
                "so more training churn would be premature."
            ),
        ],
    }
    decision["validation_issues"] = validate_effect_training_revisit_decision(decision)
    return decision


def validate_effect_training_revisit_decision(
    decision: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    baseline = _as_dict(evidence.get("baseline_vs_candidate"))
    replay = _as_dict(evidence.get("replay_split_boundary"))
    synthetic = _as_dict(evidence.get("synthetic_validity"))
    design = _as_dict(evidence.get("design_sanity"))
    unresolved = _as_dict(evidence.get("unresolved_regression_family"))

    if gate.get("revisit_justified_now") is not False:
        issues.append("revisit_gate_should_be_deferred")
    if gate.get("decision") != "defer_new_effect_training_loop":
        issues.append("missing_defer_training_decision")
    if baseline.get("fit_gate_status") != "worse_on_all_fit_gates":
        issues.append("baseline_candidate_fit_gate_not_worse")
    if replay.get("effect_only_shift_concentration") != "supported_effect_enriched":
        issues.append("effect_only_shift_not_supported_concentrated")
    if replay.get("combined_shift_concentration") != "supported_effect_enriched":
        issues.append("combined_shift_not_supported_concentrated")
    if synthetic.get("partition_verdict") != "do_not_pool_supported_and_base_clone_validity":
        issues.append("partition_validity_gate_missing")
    if design.get("principal_blocker") != "synthetic_data_circularity_and_generator_contamination":
        issues.append("principal_blocker_not_data_validity")
    if unresolved.get("target_family") != "non_cgm_continue_to_monitor_threshold_cross":
        issues.append("unexpected_unresolved_regression_family")
    if len(_as_list(decision.get("required_evidence_before_revisit"))) < 3:
        issues.append("missing_revisit_requirements")
    return issues


def render_effect_training_revisit_decision_markdown(
    decision: dict[str, object],
) -> str:
    lines = [
        "# effect training revisit decision v1",
        "",
        "## decision gate",
        "",
        f"- decision_gate: `{decision.get('decision_gate', {})}`",
        "",
        "## evidence summary",
        "",
    ]
    for key, value in _as_dict(decision.get("evidence_summary")).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## decision rationale", ""])
    for finding in _as_list(decision.get("decision_rationale")):
        lines.append(f"- {finding}")
    lines.extend(["", "## required evidence before revisit", ""])
    for finding in _as_list(decision.get("required_evidence_before_revisit")):
        lines.append(f"- {finding}")
    lines.extend(["", "## summary findings", ""])
    for finding in _as_list(decision.get("summary_findings")):
        lines.append(f"- {finding}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{decision.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_effect_training_revisit_decision_files(
    *,
    decision: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_effect_training_revisit_decision_markdown(decision),
        encoding="utf-8",
    )


def _reason_codes(
    *,
    hold_baseline: bool,
    fit_gate_status: str,
    replay_shift_concentrated: bool,
    partition_invalid_for_pooled_claim: bool,
    data_validity_risky: bool,
    unresolved_non_cgm_family: bool,
) -> list[str]:
    reasons: list[str] = []
    if hold_baseline:
        reasons.append("baseline_hold_candidate_not_ready")
    if fit_gate_status == "worse_on_all_fit_gates":
        reasons.append("overall_fit_gates_still_worse")
    if replay_shift_concentrated:
        reasons.append("supported_effect_enriched_replay_shift_concentrated")
    if partition_invalid_for_pooled_claim:
        reasons.append("dataset_f_partition_validity_not_poolable")
    if data_validity_risky:
        reasons.append("synthetic_data_circularity_and_generator_contamination")
    if unresolved_non_cgm_family:
        reasons.append("non_cgm_threshold_cross_unresolved")
    return reasons


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


__all__ = [
    "build_effect_training_revisit_decision",
    "load_json_artifact",
    "render_effect_training_revisit_decision_markdown",
    "validate_effect_training_revisit_decision",
    "write_effect_training_revisit_decision_files",
]
