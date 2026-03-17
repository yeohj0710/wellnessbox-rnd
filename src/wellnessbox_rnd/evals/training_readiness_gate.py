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
    synthetic_validity_audit: dict[str, object],
    synthetic_validity_audit_path: str | Path,
    weakest_slice_summary: dict[str, object],
    weakest_slice_summary_path: str | Path,
    parser_case_id_mismatch_decision: dict[str, object],
    parser_case_id_mismatch_decision_path: str | Path,
    structured_safety_rule_overlap_decision: dict[str, object],
    structured_safety_rule_overlap_decision_path: str | Path,
    requested_weakest_slice_lineage_proof_path: str | Path,
) -> dict[str, object]:
    attribution_verdict = _as_dict(replay_attribution.get("attribution_verdict"))
    replay_summary = _as_dict(replay_attribution.get("readable_summary"))
    replay_smallest_surface = _as_dict(replay_summary.get("smallest_surface_digest"))
    replay_surface = _as_dict(replay_summary.get("surface_digest"))

    synthetic_gate = _as_dict(synthetic_validity_audit.get("go_no_go_memo"))
    synthetic_status = _as_dict(synthetic_validity_audit.get("status_answers"))
    synthetic_supported = _as_dict(
        _as_dict(synthetic_validity_audit.get("readable_summary")).get(
            "supported_slice_digest"
        )
    )

    weakest_anchor = _as_dict(weakest_slice_summary.get("frozen_eval_anchor"))
    parser_gate = _as_dict(parser_case_id_mismatch_decision.get("decision_gate"))
    safety_gate = _as_dict(structured_safety_rule_overlap_decision.get("decision_gate"))

    criterion_1 = {
        "criterion": "dominant_replay_family_explained_well_enough",
        "passed": bool(
            attribution_verdict.get("current_smallest_surface_sufficient_for_explanation")
        )
        and bool(attribution_verdict.get("family_wide_explanation_complete")),
        "status": (
            "failed_residual_family_unexplained"
            if not bool(attribution_verdict.get("family_wide_explanation_complete"))
            else "passed"
        ),
        "evidence": {
            "decision_family": _as_dict(replay_summary.get("family_digest")).get(
                "decision_family"
            ),
            "observed_case_count": _as_dict(replay_summary.get("family_digest")).get(
                "observed_case_count"
            ),
            "current_smallest_surface_sufficient_for_explanation": attribution_verdict.get(
                "current_smallest_surface_sufficient_for_explanation"
            ),
            "family_wide_explanation_complete": attribution_verdict.get(
                "family_wide_explanation_complete"
            ),
            "sufficiency_scope": attribution_verdict.get("sufficiency_scope"),
        },
    }

    synthetic_present = any(
        _as_dict(synthetic_status.get(key)).get("status") == "present"
        for key in (
            "circularity",
            "generator_contamination",
            "calibration_target_coupling",
        )
    )
    criterion_2 = {
        "criterion": "synthetic_validity_bounded_tightly_enough",
        "passed": not synthetic_present
        and synthetic_gate.get("training_rerun_justified_now") is True,
        "status": (
            "failed_material_validity_risk_still_present"
            if synthetic_present
            else "passed"
        ),
        "evidence": {
            "circularity": _as_dict(synthetic_status.get("circularity")).get("status"),
            "generator_contamination": _as_dict(
                synthetic_status.get("generator_contamination")
            ).get("status"),
            "calibration_target_coupling": _as_dict(
                synthetic_status.get("calibration_target_coupling")
            ).get("status"),
            "training_rerun_justified_now": synthetic_gate.get(
                "training_rerun_justified_now"
            ),
            "supported_exact_reconstruction_rate_pct": synthetic_supported.get(
                "supported_exact_reconstruction_rate_pct"
            ),
            "supported_assignment_top2_match_rate_pct": synthetic_supported.get(
                "supported_assignment_top2_match_rate_pct"
            ),
        },
    }

    audit_layer_gap_count = _to_int(weakest_slice_summary.get("audit_layer_gap_count"))
    criterion_3 = {
        "criterion": "weakest_slice_lineage_closed_enough_for_relevant_slice",
        "passed": audit_layer_gap_count == 0
        and parser_gate.get("blocks_kpi_interpretation") is False
        and safety_gate.get("blocks_kpi_interpretation") is False,
        "status": (
            "failed_lineage_still_bridge_connected_with_direct_gap"
            if audit_layer_gap_count > 0
            else "passed"
        ),
        "evidence": {
            "requested_lineage_proof_present": False,
            "substitute_lineage_anchor": weakest_slice_summary.get("summary_name"),
            "audit_layer_gap_count": audit_layer_gap_count,
            "still_empty_weakest_families": weakest_slice_summary.get(
                "still_empty_weakest_families"
            ),
            "parser_case_id_mismatch_blocks_kpi_interpretation": parser_gate.get(
                "blocks_kpi_interpretation"
            ),
            "structured_safety_overlap_blocks_kpi_interpretation": safety_gate.get(
                "blocks_kpi_interpretation"
            ),
        },
    }

    criterion_4 = {
        "criterion": "future_rerun_objective_can_be_stated_narrowly",
        "passed": False,
        "status": "failed_current_objective_still_broad_or_risky",
        "evidence": {
            "current_smallest_surface": {
                "trajectory_mode": replay_smallest_surface.get("trajectory_mode"),
                "margin_bucket": replay_smallest_surface.get("margin_bucket"),
                "proxy_drop_bucket": replay_smallest_surface.get("proxy_drop_bucket"),
                "opposing_feature": replay_surface.get("opposing_feature"),
                "local_contract": replay_surface.get("local_contract"),
            },
            "why_not_narrow_enough_yet": (
                "The current replay explanation is slice-local only and the remaining family "
                "plus synthetic-validity blocker would make a rerun objective broader than one "
                "safe local contract."
            ),
        },
    }

    criterion_5 = {
        "criterion": "future_rerun_success_condition_measurable_without_kpi_semantics_change",
        "passed": True,
        "status": "passed_but_gate_still_closed",
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
                "Success could be measured with current metrics, but the earlier criteria are "
                "not met, so measurability alone does not authorize a rerun."
            ),
        },
    }

    criteria = [criterion_1, criterion_2, criterion_3, criterion_4, criterion_5]
    all_pass = all(bool(_as_dict(item).get("passed")) for item in criteria)

    gate_decision = {
        "authorized_now": all_pass,
        "decision": (
            "go_narrow_training_rerun_authorized"
            if all_pass
            else "no_go_keep_training_blocked"
        ),
        "decision_standard": "strict_all_criteria_required",
        "failed_criteria": [
            _as_dict(item).get("criterion")
            for item in criteria
            if not bool(_as_dict(item).get("passed"))
        ],
    }

    next_non_training_loop = {
        "required_before_any_future_rerun": (
            "replay_only_residual_attribution_for_non_cgm_continue_to_monitor_threshold_cross"
        ),
        "why": (
            "The dominant replay family is not yet explained beyond the current 5-case smallest "
            "surface, so replay evidence must tighten before any rerun objective is safe."
        ),
        "bounded_target": {
            "trajectory_mode": "threshold_duration_sensitive",
            "margin_bucket": "mid_margin",
            "residual_proxy_drop_buckets": ["large_drop", "medium_drop"],
        },
    }

    readable_summary = {
        "bottom_line": (
            "NO-GO: a narrow future training rerun is still not authorized because the dominant "
            "replay family is only partially explained, synthetic validity risks remain present, "
            "and weakest-slice lineage is still bridge-connected rather than fully closed."
        ),
        "gate_digest": gate_decision,
        "replay_digest": {
            "decision_family": _as_dict(replay_summary.get("family_digest")).get(
                "decision_family"
            ),
            "current_smallest_surface_sufficient_for_explanation": attribution_verdict.get(
                "current_smallest_surface_sufficient_for_explanation"
            ),
            "family_wide_explanation_complete": attribution_verdict.get(
                "family_wide_explanation_complete"
            ),
        },
        "synthetic_digest": {
            "circularity": _as_dict(synthetic_status.get("circularity")).get("status"),
            "generator_contamination": _as_dict(
                synthetic_status.get("generator_contamination")
            ).get("status"),
            "calibration_target_coupling": _as_dict(
                synthetic_status.get("calibration_target_coupling")
            ).get("status"),
            "training_rerun_justified_now": synthetic_gate.get(
                "training_rerun_justified_now"
            ),
        },
        "weakest_slice_digest": {
            "overall_weakest_category": _as_dict(
                weakest_anchor.get("weakest_category_overall")
            ).get("category"),
            "audit_layer_gap_count": audit_layer_gap_count,
            "parser_case_id_mismatch_non_blocking": parser_gate.get(
                "blocks_kpi_interpretation"
            )
            is False,
            "structured_safety_overlap_non_blocking": safety_gate.get(
                "blocks_kpi_interpretation"
            )
            is False,
        },
    }

    report = {
        "audit_name": "training_readiness_gate_v1",
        "scope": {
            "dataset_path": str(Path(dataset_path)),
            "case_count": case_count,
        },
        "source_artifacts": {
            "replay_attribution_path": str(replay_attribution_path),
            "synthetic_validity_audit_path": str(synthetic_validity_audit_path),
            "requested_weakest_slice_lineage_proof_path": str(
                requested_weakest_slice_lineage_proof_path
            ),
            "resolved_weakest_slice_summary_path": str(weakest_slice_summary_path),
            "parser_case_id_mismatch_decision_path": str(
                parser_case_id_mismatch_decision_path
            ),
            "structured_safety_rule_overlap_decision_path": str(
                structured_safety_rule_overlap_decision_path
            ),
        },
        "criteria_assessment": criteria,
        "gate_decision": gate_decision,
        "next_non_training_loop": next_non_training_loop,
        "readable_summary": readable_summary,
        "summary_findings": [
            (
                "The requested weakest-slice lineage proof artifact path is not present in the "
                "repo, so this gate used the latest weakest-slice frozen-eval summary plus the "
                "current parser/safety residual decisions as the closest lineage evidence."
            ),
            (
                "This still returns NO-GO because the dominant replay family is only explained "
                "for the current 5-case smallest surface, not for the full family."
            ),
            (
                "Synthetic validity also remains explicitly NO-GO: circularity, generator "
                "contamination, and calibration-target coupling are all still present."
            ),
            (
                "Weakest-slice lineage is readable enough for current KPI interpretation, but "
                "not fully closed enough to upgrade the training gate by itself."
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
        issues.append("gate decision drifted")
    if len(criteria) != 5:
        issues.append("gate must assess exactly five criteria")
    failed = gate.get("failed_criteria")
    if not isinstance(failed, list) or len(failed) < 1:
        issues.append("no-go gate must name failed criteria")
    if next_loop.get("required_before_any_future_rerun") != (
        "replay_only_residual_attribution_for_non_cgm_continue_to_monitor_threshold_cross"
    ):
        issues.append("unexpected next non-training loop")
    return issues


def render_training_readiness_gate_markdown(report: dict[str, object]) -> str:
    lines = [
        "# training readiness gate v1",
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
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(render_training_readiness_gate_markdown(report), encoding="utf-8")


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
    "build_training_readiness_gate",
    "load_json",
    "render_training_readiness_gate_markdown",
    "validate_training_readiness_gate",
    "write_training_readiness_gate_files",
]
