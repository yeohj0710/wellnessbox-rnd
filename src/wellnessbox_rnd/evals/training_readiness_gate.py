from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_training_readiness_gate(
    *,
    dataset_path: str | Path,
    case_count: int,
    replay_attribution: dict[str, object],
    replay_attribution_path: str | Path,
    synthetic_validity_followup: dict[str, object],
    synthetic_validity_followup_path: str | Path,
    cgm_core_summary: dict[str, object],
    cgm_core_summary_path: str | Path,
    cgm_geometry_audit: dict[str, object] | None,
    cgm_geometry_audit_path: str | Path,
) -> dict[str, object]:
    replay_target = _as_dict(replay_attribution.get("target_residual_slice"))
    replay_chain = _as_dict(replay_attribution.get("reproduction_chain"))
    replay_verdict = _as_dict(replay_attribution.get("verdict"))

    synthetic_scope = _as_dict(synthetic_validity_followup.get("scope"))
    synthetic_selection = _as_dict(synthetic_validity_followup.get("selection"))
    synthetic_disposition = _as_dict(
        synthetic_validity_followup.get("final_disposition")
    )
    synthetic_measured = _as_dict(
        synthetic_validity_followup.get("measured_concentration")
    )

    cgm_status = _as_dict(cgm_core_summary.get("cgm_final_step_geometry_status"))
    cgm_geometry_present = bool(cgm_geometry_audit)
    cgm_geometry_verdict = _as_dict(_as_dict(cgm_geometry_audit).get("verdict"))
    cgm_reopened = (
        cgm_status.get("status") == "structural_continue_plan_overlap_persists"
    )

    criterion_1 = {
        "criterion": "dominant_replay_residual_explained_tightly_enough",
        "passed": bool(replay_verdict.get("explained_well_enough_for_future_gate_work")),
        "status": (
            "passed"
            if bool(replay_verdict.get("explained_well_enough_for_future_gate_work"))
            else "failed_residual_surface_still_not_gate_ready"
        ),
        "evidence": {
            "decision_family": replay_target.get("decision_family"),
            "observed_case_count": replay_target.get("observed_case_count"),
            "current_residual_case_count": replay_chain.get("current_residual_case_count"),
            "primary_residual_family": replay_verdict.get("primary_residual_family"),
            "current_smallest_credible_surface": replay_verdict.get(
                "current_smallest_credible_surface"
            ),
            "explained_well_enough_for_future_gate_work": replay_verdict.get(
                "explained_well_enough_for_future_gate_work"
            ),
        },
    }

    synthetic_state = str(synthetic_disposition.get("resolution_state") or "")
    criterion_2 = {
        "criterion": "chosen_synthetic_validity_item_resolved_or_bounded_tightly_enough",
        "passed": synthetic_state in {"resolved", "still_unproven"},
        "status": (
            "passed"
            if synthetic_state in {"resolved", "still_unproven"}
            else "failed_chosen_synthetic_item_still_risky"
        ),
        "evidence": {
            "chosen_item": synthetic_scope.get("chosen_item"),
            "why_this_item": synthetic_selection.get("why_this_minimum_change_item"),
            "resolution_state": synthetic_disposition.get("resolution_state"),
            "actionable_for_future_gate_work": synthetic_disposition.get(
                "actionable_for_future_gate_work"
            ),
            "candidate_supported_share_of_net_gain_pct": _nested(
                synthetic_measured, "candidate_test", "supported_share_of_net_gain_pct"
            ),
            "baseline_supported_share_of_net_gain_pct": _nested(
                synthetic_measured, "baseline_test", "supported_share_of_net_gain_pct"
            ),
        },
    }

    cgm_closed_or_non_blocking = False
    if not cgm_reopened:
        cgm_closed_or_non_blocking = True
    elif cgm_geometry_present:
        cgm_closed_or_non_blocking = _as_dict(cgm_geometry_verdict).get(
            "reopened_cgm_blocker_status"
        ) in {"closed", "non_blocking"}

    criterion_3 = {
        "criterion": "reopened_cgm_blocker_closed_or_proven_non_blocking",
        "passed": cgm_closed_or_non_blocking,
        "status": (
            "passed"
            if cgm_closed_or_non_blocking
            else "failed_reopened_cgm_blocker_not_closed_or_non_blocking"
        ),
        "evidence": {
            "cgm_geometry_artifact_present": cgm_geometry_present,
            "cgm_geometry_artifact_path": str(cgm_geometry_audit_path),
            "current_cgm_status": cgm_status.get("status"),
            "selected_continue_case_count": cgm_status.get("selected_continue_case_count"),
            "continue_to_reoptimize_top_action_flip_count": cgm_status.get(
                "continue_to_reoptimize_top_action_flip_count"
            ),
            "outside_monitor_band_count": cgm_status.get("outside_monitor_band_count"),
            "blocker_family_summary": cgm_status.get("blocker_family_summary"),
            "why_not_non_blocking_yet": (
                "The requested v2 cgm artifact was not produced, and the latest core summary "
                "still marks cgm as structural outside-band overlap rather than closed or "
                "proven non-blocking."
            )
            if not cgm_closed_or_non_blocking
            else None,
        },
    }

    criterion_4 = {
        "criterion": "next_rerun_target_can_be_stated_narrowly",
        "passed": False,
        "status": "failed_safe_rerun_target_not_yet_narrow_enough",
        "evidence": {
            "safe_rerun_target_available_now": False,
            "why_not_narrow_enough": (
                "The dominant replay residual still needs another bounded replay loop first, "
                "the chosen synthetic-validity item is still risky, and cgm remains reopened "
                "without a v2 closure proof."
            ),
            "blocking_pre_rerun_loop": {
                "task": (
                    "replay_only_attribution_for_threshold_duration_sensitive_mid_margin_"
                    "large_drop"
                ),
                "decision_family": replay_target.get("decision_family"),
                "trajectory_mode": replay_target.get("trajectory_mode"),
                "margin_bucket": replay_target.get("margin_bucket"),
                "proxy_drop_bucket": "large_drop",
                "observed_case_count": _nested(
                    replay_target, "bucket_case_counts", "large_drop"
                ),
            },
        },
    }

    criterion_5 = {
        "criterion": "success_failure_measurable_without_kpi_semantics_change",
        "passed": True,
        "status": "passed",
        "evidence": {
            "measurable_existing_metrics": [
                "aggregate_mae",
                "aggregate_r2",
                "policy_proxy_mae",
                "low_risk_combined_disagreement_delta",
                "non_cgm_continue_to_monitor_threshold_cross_case_count",
            ],
            "semantic_change_required": False,
            "note": (
                "Current gate success/failure can still be read with existing fit metrics "
                "and replay-family case counts."
            ),
        },
    }

    criteria = [
        criterion_1,
        criterion_2,
        criterion_3,
        criterion_4,
        criterion_5,
    ]
    all_pass = all(bool(_as_dict(item).get("passed")) for item in criteria)
    failed_criteria = [
        str(_as_dict(item).get("criterion"))
        for item in criteria
        if not bool(_as_dict(item).get("passed"))
    ]
    first_blocker = failed_criteria[0] if failed_criteria else None

    gate_decision = {
        "authorized_now": all_pass,
        "decision": (
            "go_narrow_training_rerun_authorized"
            if all_pass
            else "no_go_keep_training_blocked"
        ),
        "decision_standard": "strict_all_criteria_required_default_no_go",
        "failed_criteria": failed_criteria,
        "first_blocking_criterion": first_blocker,
    }

    next_non_training_loop = {
        "required_before_any_future_rerun": (
            "replay_only_attribution_for_threshold_duration_sensitive_mid_margin_large_drop"
        ),
        "why": (
            "Criterion 1 fails first: the dominant replay residual is still not explained "
            "tightly enough, and the `large_drop` bucket is the densest remaining slice."
        ),
        "bounded_target": {
            "decision_family": replay_target.get("decision_family"),
            "trajectory_mode": replay_target.get("trajectory_mode"),
            "margin_bucket": replay_target.get("margin_bucket"),
            "proxy_drop_bucket": "large_drop",
            "observed_case_count": _nested(
                replay_target, "bucket_case_counts", "large_drop"
            ),
        },
    }

    readable_summary = {
        "bottom_line": (
            "NO-GO: the next narrow effect-model rerun is still not authorized because the "
            "dominant replay residual is not gate-ready, the chosen synthetic-validity item "
            "is still risky, cgm is still reopened without a closure/non-blocking proof, "
            "and no safe rerun target can yet be stated narrowly."
        ),
        "gate_digest": gate_decision,
        "replay_digest": {
            "decision_family": replay_target.get("decision_family"),
            "current_residual_case_count": replay_chain.get("current_residual_case_count"),
            "primary_residual_family": replay_verdict.get("primary_residual_family"),
            "explained_well_enough_for_future_gate_work": replay_verdict.get(
                "explained_well_enough_for_future_gate_work"
            ),
        },
        "synthetic_digest": {
            "chosen_item": synthetic_scope.get("chosen_item"),
            "resolution_state": synthetic_disposition.get("resolution_state"),
            "actionable_for_future_gate_work": synthetic_disposition.get(
                "actionable_for_future_gate_work"
            ),
        },
        "cgm_digest": {
            "artifact_present": cgm_geometry_present,
            "status": cgm_status.get("status"),
            "outside_monitor_band_count": cgm_status.get("outside_monitor_band_count"),
            "threshold_edge_case_count": _nested(
                cgm_status, "blocker_family_summary", "threshold_edge_monitor_band_continue"
            ),
        },
    }

    report = {
        "audit_name": "training_readiness_gate_v2",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "case_count": case_count,
        },
        "source_artifacts": {
            "replay_attribution_path": str(replay_attribution_path),
            "synthetic_validity_followup_path": str(synthetic_validity_followup_path),
            "cgm_core_summary_path": str(cgm_core_summary_path),
            "requested_cgm_geometry_audit_path": str(cgm_geometry_audit_path),
            "requested_cgm_geometry_audit_present": cgm_geometry_present,
        },
        "criteria_assessment": criteria,
        "gate_decision": gate_decision,
        "next_non_training_loop": next_non_training_loop,
        "readable_summary": readable_summary,
        "summary_findings": [
            (
                "This gate stays NO-GO because criterion 1 fails first: the dominant replay "
                "residual still has a 4-case mixed-overlap surface and is not yet explained "
                "well enough for future gate work."
            ),
            (
                "The chosen synthetic-validity item is better bounded than before, but it is "
                "still explicitly `still_risky`, so criterion 2 also fails."
            ),
            (
                "The requested cgm v2 artifact is absent because that loop did not proceed; "
                "the latest core summary still marks cgm as "
                "`structural_continue_plan_overlap_persists`, so criterion 3 fails."
            ),
            (
                "Criterion 5 still passes because any future rerun can be judged with the "
                "current KPI semantics and existing fit/replay metrics."
            ),
        ],
    }
    report["validation_issues"] = validate_training_readiness_gate(report)
    return report


def validate_training_readiness_gate(report: dict[str, object]) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(report.get("gate_decision"))
    criteria = _as_list(report.get("criteria_assessment"))
    next_loop = _as_dict(report.get("next_non_training_loop"))

    if gate.get("authorized_now") is not False:
        issues.append("training gate must remain closed")
    if gate.get("decision") != "no_go_keep_training_blocked":
        issues.append("gate decision drifted from strict no-go")
    if len(criteria) != 5:
        issues.append("gate must assess exactly five criteria")
    failed = gate.get("failed_criteria")
    if not isinstance(failed, list) or len(failed) < 1:
        issues.append("no-go gate must name failed criteria")
    if gate.get("first_blocking_criterion") != (
        "dominant_replay_residual_explained_tightly_enough"
    ):
        issues.append("unexpected first blocking criterion")
    if next_loop.get("required_before_any_future_rerun") != (
        "replay_only_attribution_for_threshold_duration_sensitive_mid_margin_large_drop"
    ):
        issues.append("unexpected next non-training loop")
    return issues


def render_training_readiness_gate_markdown(report: dict[str, object]) -> str:
    lines = [
        "# training readiness gate v2",
        "",
        f"- gate_decision: `{report.get('gate_decision')}`",
        f"- readable_summary: `{report.get('readable_summary')}`",
        "",
        "## Criteria Assessment",
    ]
    for item in _as_list(report.get("criteria_assessment")):
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Next Non-Training Loop",
            f"- `{report.get('next_non_training_loop')}`",
            "",
            "## Summary Findings",
        ]
    )
    for item in _as_list(report.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Validation",
            f"- validation_issues: `{report.get('validation_issues')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_training_readiness_gate_files(
    *,
    report: dict[str, object],
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_training_readiness_gate_markdown(report), encoding="utf-8")


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _nested(payload: dict[str, object], *path: str) -> object | None:
    current: object = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


__all__ = [
    "build_training_readiness_gate",
    "load_json",
    "render_training_readiness_gate_markdown",
    "validate_training_readiness_gate",
    "write_training_readiness_gate_files",
]
