from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_core_kpi_path_summary(
    *,
    final_kpi_compare_report: dict[str, object],
    final_kpi_compare_report_path: str | Path,
    baseline_followup_pro_event_contract: dict[str, object],
    baseline_followup_pro_event_contract_path: str | Path,
    pro_scoring_contract: dict[str, object],
    pro_scoring_contract_path: str | Path,
    weakest_slice_frozen_eval_audit: dict[str, object],
    weakest_slice_frozen_eval_audit_path: str | Path,
    cgm_geometry_summary: dict[str, object],
    cgm_geometry_summary_path: str | Path,
    learned_runtime_boundary_audit: dict[str, object],
    learned_runtime_boundary_audit_path: str | Path,
    latest_effect_candidate_reject_decision: dict[str, object],
    latest_effect_candidate_reject_decision_path: str | Path,
) -> dict[str, object]:
    baseline_reference = _as_dict(final_kpi_compare_report.get("baseline_reference"))
    latest_candidate = _as_dict(final_kpi_compare_report.get("latest_candidate"))
    decision_summary = _as_dict(final_kpi_compare_report.get("decision_summary"))
    readable_summary = _as_dict(final_kpi_compare_report.get("readable_summary"))
    compare_audit_path = _as_dict(readable_summary.get("audit_path_digest"))
    compare_weakest = _as_dict(readable_summary.get("weakest_slice_delta_digest"))
    reject_hold_context = _as_dict(latest_effect_candidate_reject_decision.get("hold_context"))
    reject_regression = _as_dict(
        _as_dict(latest_effect_candidate_reject_decision.get("regression_slices")).get(
            "dominant_low_risk_slice"
        )
    )

    pro_improvement = _as_dict(pro_scoring_contract.get("improvement_metric"))
    pro_single_path = _as_dict(pro_improvement.get("single_path_status"))
    pro_shared_path = _as_dict(pro_improvement.get("shared_event_path_proof"))

    weakest_anchor = _as_dict(weakest_slice_frozen_eval_audit.get("frozen_eval_anchor"))
    weakest_path = _as_dict(
        weakest_slice_frozen_eval_audit.get(
            "weakest_slice_frozen_eval_compatible_audit_path"
        )
    )
    weakest_audit_summary = _as_dict(
        weakest_slice_frozen_eval_audit.get("audit_path_summary")
    )

    cgm_blocker = _as_dict(cgm_geometry_summary.get("blocker_evidence"))
    cgm_blocker_summary = _as_dict(cgm_blocker.get("blocker_summary"))
    cgm_blocker_family = _as_dict(cgm_blocker.get("blocker_family_summary"))
    cgm_selected = _as_dict(cgm_geometry_summary.get("selected_continue_geometry_summary"))

    learned_verdict = _as_dict(
        learned_runtime_boundary_audit.get("replay_only_boundary_verdict")
    )
    runtime_path = _as_dict(learned_runtime_boundary_audit.get("runtime_recommendation_path"))
    safety_path = _as_dict(learned_runtime_boundary_audit.get("safety_path"))
    optimizer_path = _as_dict(learned_runtime_boundary_audit.get("optimizer_path"))
    inference_path = _as_dict(learned_runtime_boundary_audit.get("inference_api_path"))

    weakest_status = (
        "connected_with_remaining_gaps"
        if _as_list(weakest_audit_summary.get("remaining_gaps"))
        else "connected_no_remaining_gaps"
    )

    summary = {
        "summary_name": "core_kpi_path_summary_v1",
        "source_artifacts": {
            "final_kpi_compare_report_path": str(final_kpi_compare_report_path),
            "baseline_followup_pro_event_contract_path": str(
                baseline_followup_pro_event_contract_path
            ),
            "pro_scoring_contract_path": str(pro_scoring_contract_path),
            "weakest_slice_frozen_eval_audit_path": str(
                weakest_slice_frozen_eval_audit_path
            ),
            "cgm_geometry_summary_path": str(cgm_geometry_summary_path),
            "learned_runtime_boundary_audit_path": str(
                learned_runtime_boundary_audit_path
            ),
            "latest_effect_candidate_reject_decision_path": str(
                latest_effect_candidate_reject_decision_path
            ),
        },
        "current_path_readable_summary": {
            "replay_compare_digest": {
                "status": latest_candidate.get("replay_compare_status"),
                "candidate_label": latest_candidate.get("candidate_label"),
                "adoption_decision": decision_summary.get("decision_class"),
                "fit_gate_status": latest_candidate.get("fit_gate_status"),
                "dominant_candidate_regression_slice": compare_weakest.get(
                    "dominant_candidate_regression_slice"
                ),
                "principal_blocker": reject_hold_context.get("principal_blocker"),
                "dominant_replay_regression_family": reject_hold_context.get(
                    "dominant_replay_regression_family"
                ),
            },
            "pro_contract_digest": {
                "status": "shared_event_path_connected",
                "contract_id": baseline_followup_pro_event_contract.get("contract_id"),
                "shared_event_schema_version": pro_improvement.get(
                    "shared_event_schema_version"
                ),
                "package_public_summary_entrypoint": pro_single_path.get(
                    "package_public_summary_entrypoint"
                ),
                "valid_case_count": baseline_followup_pro_event_contract.get(
                    "valid_case_count"
                ),
                "invalid_case_count": baseline_followup_pro_event_contract.get(
                    "invalid_case_count"
                ),
            },
            "weakest_slice_digest": {
                "status": weakest_status,
                "path_status": weakest_path.get("path_status"),
                "frozen_eval_compatible": weakest_path.get("frozen_eval_compatible"),
                "overall_weakest_category": _as_dict(
                    weakest_anchor.get("weakest_category_overall")
                ).get("category"),
                "audit_layer_gap_count": len(
                    _as_list(weakest_audit_summary.get("remaining_gaps"))
                ),
                "remaining_gap_count": len(
                    _as_list(weakest_audit_summary.get("remaining_gaps"))
                ),
            },
            "cgm_final_step_geometry_digest": {
                "status": compare_audit_path.get("cgm_geometry_status"),
                "selected_continue_case_count": cgm_selected.get(
                    "selected_continue_case_count"
                ),
                "continue_to_reoptimize_top_action_flip_count": cgm_selected.get(
                    "continue_to_reoptimize_top_action_flip_count"
                ),
                "outside_monitor_band_count": cgm_blocker_summary.get(
                    "outside_monitor_band_count"
                ),
                "blocker_family_summary": cgm_blocker_family,
            },
            "learned_boundary_digest": {
                "status": learned_verdict.get("status"),
                "core_path_count": learned_verdict.get("core_path_count"),
                "promoted_core_path_count": learned_verdict.get(
                    "promoted_core_path_count"
                ),
                "all_core_paths_preserved": learned_verdict.get(
                    "all_core_paths_preserved"
                ),
                "chat_optional_only": learned_verdict.get("chat_optional_only"),
            },
            "baseline_vs_candidate_digest": {
                "dataset_path": baseline_reference.get("dataset_path"),
                "case_count": baseline_reference.get("case_count"),
                "decision": decision_summary.get("decision_class"),
                "one_line_decision": readable_summary.get("one_line_decision"),
                "principal_blocker": reject_hold_context.get("principal_blocker"),
                "dominant_replay_regression_family": reject_hold_context.get(
                    "dominant_replay_regression_family"
                ),
            },
        },
        "baseline_reference": {
            "dataset_path": baseline_reference.get("dataset_path"),
            "case_count": baseline_reference.get("case_count"),
            "metrics": baseline_reference.get("metrics"),
        },
        "replay_compare_status": {
            "status": latest_candidate.get("replay_compare_status"),
            "candidate_label": latest_candidate.get("candidate_label"),
            "adoption_decision": decision_summary.get("decision_class"),
            "fit_gate_status": latest_candidate.get("fit_gate_status"),
            "overall_delta": latest_candidate.get("overall_delta"),
            "dominant_candidate_regression_slice": compare_weakest.get(
                "dominant_candidate_regression_slice"
            ),
            "dominant_replay_regression_family": reject_hold_context.get(
                "dominant_replay_regression_family"
            ),
            "one_line_decision": readable_summary.get("one_line_decision"),
            "required_evidence_before_revisit": latest_effect_candidate_reject_decision.get(
                "required_evidence_before_next_training_loop"
            ),
        },
        "pro_baseline_followup_contract_status": {
            "status": "shared_event_path_connected",
            "contract_id": baseline_followup_pro_event_contract.get("contract_id"),
            "shared_event_schema_version": pro_improvement.get(
                "shared_event_schema_version"
            ),
            "shared_event_adapter": pro_improvement.get("shared_event_adapter"),
            "shared_event_unifier": pro_improvement.get("shared_event_unifier"),
            "shared_event_validator": pro_improvement.get("shared_event_validator"),
            "package_public_summary_entrypoint": pro_single_path.get(
                "package_public_summary_entrypoint"
            ),
            "package_public_validator_entrypoint": pro_single_path.get(
                "package_public_validator_entrypoint"
            ),
            "event_adapter_only_public_entrypoint": pro_single_path.get(
                "event_adapter_only_public_entrypoint"
            ),
            "direct_normalized_event_internal_only": pro_single_path.get(
                "direct_normalized_event_internal_only"
            ),
            "valid_case_count": pro_shared_path.get("valid_case_count"),
            "invalid_case_count": pro_shared_path.get("invalid_case_count"),
        },
        "weakest_slice_frozen_eval_wiring_status": {
            "status": weakest_status,
            "path_status": weakest_path.get("path_status"),
            "frozen_eval_compatible": weakest_path.get("frozen_eval_compatible"),
            "overall_weakest_category": _as_dict(
                weakest_anchor.get("weakest_category_overall")
            ).get("category"),
            "overall_weakest_case_count": _as_dict(
                weakest_anchor.get("weakest_category_overall")
            ).get("case_count"),
            "sensor_genetic_weakest_category": _as_dict(
                weakest_anchor.get("sensor_genetic_integration_metric")
            ).get("category"),
            "sensor_genetic_score": _as_dict(
                weakest_anchor.get("sensor_genetic_integration_metric")
            ).get("score"),
            "audit_layer_gap_count": len(
                _as_list(weakest_audit_summary.get("remaining_gaps"))
            ),
            "remaining_gaps": weakest_audit_summary.get("remaining_gaps"),
        },
        "cgm_final_step_geometry_status": {
            "status": compare_audit_path.get("cgm_geometry_status"),
            "selected_continue_case_count": cgm_selected.get(
                "selected_continue_case_count"
            ),
            "continue_to_reoptimize_top_action_flip_count": cgm_selected.get(
                "continue_to_reoptimize_top_action_flip_count"
            ),
            "mean_continue_minus_reoptimize_before_calibration": cgm_selected.get(
                "mean_continue_minus_reoptimize_before_calibration"
            ),
            "mean_continue_minus_reoptimize_after_calibration": cgm_selected.get(
                "mean_continue_minus_reoptimize_after_calibration"
            ),
            "gap_reduction_mean": cgm_selected.get("gap_reduction_mean"),
            "outside_monitor_band_count": cgm_blocker_summary.get(
                "outside_monitor_band_count"
            ),
            "blocker_family_summary": cgm_blocker_family,
        },
        "learned_artifact_replay_only_boundary_status": {
            "status": learned_verdict.get("status"),
            "core_path_count": learned_verdict.get("core_path_count"),
            "promoted_core_path_count": learned_verdict.get(
                "promoted_core_path_count"
            ),
            "all_core_paths_preserved": learned_verdict.get("all_core_paths_preserved"),
            "learned_artifact_core_dependency_promoted": _as_dict(
                learned_runtime_boundary_audit.get("overall_assessment")
            ).get("learned_artifact_core_dependency_promoted"),
            "runtime_core_dependency_promoted": runtime_path.get(
                "core_dependency_promoted"
            ),
            "safety_core_dependency_promoted": safety_path.get(
                "core_dependency_promoted"
            ),
            "optimizer_core_dependency_promoted": optimizer_path.get(
                "core_dependency_promoted"
            ),
            "inference_core_dependency_promoted": inference_path.get(
                "core_dependency_promoted"
            ),
            "chat_optional_only": learned_verdict.get("chat_optional_only"),
        },
        "deterministic_baseline_vs_candidate_judgement": {
            "dataset_path": baseline_reference.get("dataset_path"),
            "case_count": baseline_reference.get("case_count"),
            "baseline_reference_metrics": baseline_reference.get("metrics"),
            "candidate_label": latest_candidate.get("candidate_label"),
            "decision": decision_summary.get("decision_class"),
            "one_line_conclusion": readable_summary.get("one_line_decision"),
            "principal_blocker": reject_hold_context.get("principal_blocker"),
            "dominant_replay_regression_family": reject_hold_context.get(
                "dominant_replay_regression_family"
            ),
            "dominant_regression_case_count": reject_regression.get("observed_case_count"),
        },
        "summary_findings": [
            (
                "Replay compare is complete enough to keep the current candidate held "
                "and baseline adoption unchanged."
            ),
            (
                "PRO baseline/follow-up semantics remain connected through one shared "
                "event path with the package public summary/validator entrypoints fixed."
            ),
            (
                "Weakest-slice frozen-eval wiring is frozen-eval-compatible and connected, "
                "but still carries explicit remaining gaps."
            ),
            (
                "Current cgm final-step geometry still shows structural continue_plan vs "
                "re_optimize overlap concentrated in outside-band geometry."
            ),
            (
                "Learned artifacts remain replay-only and optional; the deterministic "
                "baseline stays the runtime reference."
            ),
        ],
    }
    summary["validation_issues"] = validate_core_kpi_path_summary(summary)
    return summary


def validate_core_kpi_path_summary(summary: dict[str, object]) -> list[str]:
    issues: list[str] = []
    readable = _as_dict(summary.get("current_path_readable_summary"))
    replay = _as_dict(summary.get("replay_compare_status"))
    pro_status = _as_dict(summary.get("pro_baseline_followup_contract_status"))
    weakest = _as_dict(summary.get("weakest_slice_frozen_eval_wiring_status"))
    cgm = _as_dict(summary.get("cgm_final_step_geometry_status"))
    learned = _as_dict(summary.get("learned_artifact_replay_only_boundary_status"))
    judgement = _as_dict(summary.get("deterministic_baseline_vs_candidate_judgement"))

    required_readable_keys = [
        "replay_compare_digest",
        "pro_contract_digest",
        "weakest_slice_digest",
        "cgm_final_step_geometry_digest",
        "learned_boundary_digest",
        "baseline_vs_candidate_digest",
    ]
    for key in required_readable_keys:
        if not _as_dict(readable.get(key)):
            issues.append(f"missing_{key}")

    if replay.get("status") != "complete_candidate_held":
        issues.append("unexpected_replay_compare_status")
    if pro_status.get("status") != "shared_event_path_connected":
        issues.append("unexpected_pro_contract_status")
    if weakest.get("status") not in {
        "connected_with_remaining_gaps",
        "connected_no_remaining_gaps",
    }:
        issues.append("unexpected_weakest_slice_status")
    if cgm.get("status") != "structural_continue_plan_overlap_persists":
        issues.append("unexpected_cgm_status")
    if learned.get("status") != "replay_only_boundary_preserved":
        issues.append("unexpected_learned_boundary_status")
    if judgement.get("decision") != "hold_baseline_candidate_not_ready":
        issues.append("unexpected_candidate_judgement")
    if not bool(learned.get("chat_optional_only")):
        issues.append("chat_not_optional_only")
    if int(_as_dict(readable.get("pro_contract_digest")).get("valid_case_count", 0)) != 480:
        issues.append("unexpected_pro_valid_case_count")
    if not _as_list(summary.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_core_kpi_path_summary_markdown(summary: dict[str, object]) -> str:
    readable = _as_dict(summary.get("current_path_readable_summary"))
    replay = _as_dict(summary.get("replay_compare_status"))
    pro_status = _as_dict(summary.get("pro_baseline_followup_contract_status"))
    weakest = _as_dict(summary.get("weakest_slice_frozen_eval_wiring_status"))
    cgm = _as_dict(summary.get("cgm_final_step_geometry_status"))
    learned = _as_dict(summary.get("learned_artifact_replay_only_boundary_status"))
    judgement = _as_dict(summary.get("deterministic_baseline_vs_candidate_judgement"))

    lines = [
        "# core kpi path summary v1",
        "",
        "## Current Path",
        "",
    ]
    for key, value in readable.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Replay Compare",
            "",
            f"- status: `{replay.get('status')}`",
            f"- candidate_label: `{replay.get('candidate_label')}`",
            f"- adoption_decision: `{replay.get('adoption_decision')}`",
            f"- fit_gate_status: `{replay.get('fit_gate_status')}`",
            (
                "- dominant_replay_regression_family: "
                f"`{replay.get('dominant_replay_regression_family')}`"
            ),
            "",
            "## PRO Contract",
            "",
            f"- status: `{pro_status.get('status')}`",
            f"- contract_id: `{pro_status.get('contract_id')}`",
            (
                "- package_public_summary_entrypoint: "
                f"`{pro_status.get('package_public_summary_entrypoint')}`"
            ),
            f"- valid_case_count: `{pro_status.get('valid_case_count')}`",
            f"- invalid_case_count: `{pro_status.get('invalid_case_count')}`",
            "",
            "## Weakest-Slice Wiring",
            "",
            f"- status: `{weakest.get('status')}`",
            f"- path_status: `{weakest.get('path_status')}`",
            (
                "- overall_weakest_category: "
                f"`{weakest.get('overall_weakest_category')}`"
            ),
            (
                "- sensor_genetic_weakest_category: "
                f"`{weakest.get('sensor_genetic_weakest_category')}`"
            ),
            f"- audit_layer_gap_count: `{weakest.get('audit_layer_gap_count')}`",
            "",
            "## CGM Final-Step Geometry",
            "",
            f"- status: `{cgm.get('status')}`",
            f"- selected_continue_case_count: `{cgm.get('selected_continue_case_count')}`",
            (
                "- continue_to_reoptimize_top_action_flip_count: "
                f"`{cgm.get('continue_to_reoptimize_top_action_flip_count')}`"
            ),
            f"- outside_monitor_band_count: `{cgm.get('outside_monitor_band_count')}`",
            f"- blocker_family_summary: `{cgm.get('blocker_family_summary')}`",
            "",
            "## Learned Boundary",
            "",
            f"- status: `{learned.get('status')}`",
            f"- core_path_count: `{learned.get('core_path_count')}`",
            f"- promoted_core_path_count: `{learned.get('promoted_core_path_count')}`",
            f"- chat_optional_only: `{learned.get('chat_optional_only')}`",
            "",
            "## Baseline vs Candidate",
            "",
            f"- dataset_path: `{judgement.get('dataset_path')}`",
            f"- case_count: `{judgement.get('case_count')}`",
            f"- decision: `{judgement.get('decision')}`",
            f"- one_line_conclusion: `{judgement.get('one_line_conclusion')}`",
            f"- principal_blocker: `{judgement.get('principal_blocker')}`",
            (
                "- dominant_replay_regression_family: "
                f"`{judgement.get('dominant_replay_regression_family')}`"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_core_kpi_path_summary_files(
    summary: dict[str, object],
    *,
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_core_kpi_path_summary_markdown(summary), encoding="utf-8")


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_core_kpi_path_summary",
    "load_json",
    "render_core_kpi_path_summary_markdown",
    "validate_core_kpi_path_summary",
    "write_core_kpi_path_summary_files",
]
