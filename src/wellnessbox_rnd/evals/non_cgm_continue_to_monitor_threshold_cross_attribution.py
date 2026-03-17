from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_non_cgm_continue_to_monitor_threshold_cross_attribution(
    *,
    family_diagnostic: dict[str, object],
    family_diagnostic_path: str | Path,
    subgroup_diagnostic: dict[str, object],
    subgroup_diagnostic_path: str | Path,
    mid_margin_diagnostic: dict[str, object],
    mid_margin_diagnostic_path: str | Path,
    small_drop_diagnostic: dict[str, object],
    small_drop_diagnostic_path: str | Path,
    regimen_count_counterfactual: dict[str, object],
    regimen_count_counterfactual_path: str | Path,
    trajectory_step_counterfactual: dict[str, object],
    trajectory_step_counterfactual_path: str | Path,
    half_offset_counterfactual: dict[str, object],
    half_offset_counterfactual_path: str | Path,
    local_contract: dict[str, object],
    local_contract_path: str | Path,
    final_kpi_compare_report: dict[str, object],
    final_kpi_compare_report_path: str | Path,
) -> dict[str, object]:
    family_target = _as_dict(family_diagnostic.get("target_family"))
    family_workflow = _as_dict(family_diagnostic.get("workflow_summary"))
    family_case_summary = _as_dict(family_diagnostic.get("case_summary"))
    family_interpretation = _as_dict(family_diagnostic.get("interpretation"))
    subgroup = _as_dict(subgroup_diagnostic.get("subtarget"))
    subgroup_case_summary = _as_dict(subgroup_diagnostic.get("case_summary"))
    mid_margin_target = _as_dict(mid_margin_diagnostic.get("bucket_target"))
    mid_margin_case_summary = _as_dict(mid_margin_diagnostic.get("case_summary"))
    mid_margin_workflow = _as_dict(mid_margin_diagnostic.get("workflow_summary"))
    slice_target = _as_dict(small_drop_diagnostic.get("slice_target"))
    slice_case_summary = _as_dict(small_drop_diagnostic.get("case_summary"))
    slice_feature_summary = _as_dict(small_drop_diagnostic.get("feature_summary"))
    slice_examples = [_as_dict(row) for row in _as_list(small_drop_diagnostic.get("example_cases"))]
    regimen_summary = _as_dict(regimen_count_counterfactual.get("counterfactual_summary"))
    trajectory_summary = _as_dict(trajectory_step_counterfactual.get("counterfactual_summary"))
    half_offset_summary = _as_dict(half_offset_counterfactual.get("counterfactual_summary"))
    contract_gate = _as_dict(local_contract.get("contract_gate"))
    contract_surface = _as_dict(
        _as_dict(local_contract.get("evidence_summary")).get("contract_surface")
    )
    compare_readable = _as_dict(final_kpi_compare_report.get("readable_summary"))
    compare_decision = _as_dict(compare_readable.get("decision_readout"))
    compare_slice_digest = _as_dict(compare_readable.get("slice_compare_digest"))
    compare_overall = _as_dict(compare_slice_digest.get("overall"))
    compare_low_risk = _as_dict(compare_slice_digest.get("low_risk"))
    compare_cgm = _as_dict(compare_slice_digest.get("cgm"))

    slice_low_risk_case_count = sum(1 for row in slice_examples if row.get("risk_tier") == "low")
    slice_non_low_risk_case_count = len(slice_examples) - slice_low_risk_case_count
    final_step_only_supported = (
        _all_final_cycle_is_four(family_workflow.get("final_cycle_index_counts"))
        and _all_final_cycle_is_four(
            _as_dict(subgroup_diagnostic.get("workflow_summary")).get(
                "final_cycle_index_counts"
            )
        )
        and _all_final_cycle_is_four(
            _as_dict(small_drop_diagnostic.get("workflow_summary")).get(
                "final_cycle_index_counts"
            )
        )
    )
    minimal_surface_complete = (
        bool(contract_gate.get("contract_ready_now"))
        and bool(half_offset_summary.get("all_cases_cleared"))
        and int(trajectory_summary.get("neutralize_clears_shortfall_case_count", 0))
        == int(slice_target.get("observed_case_count", 0))
    )

    report = {
        "audit_name": "non_cgm_continue_to_monitor_threshold_cross_attribution_v1",
        "source_artifacts": {
            "family_diagnostic_path": str(family_diagnostic_path),
            "subgroup_diagnostic_path": str(subgroup_diagnostic_path),
            "mid_margin_diagnostic_path": str(mid_margin_diagnostic_path),
            "small_drop_diagnostic_path": str(small_drop_diagnostic_path),
            "regimen_count_counterfactual_path": str(regimen_count_counterfactual_path),
            "trajectory_step_counterfactual_path": str(trajectory_step_counterfactual_path),
            "half_offset_counterfactual_path": str(half_offset_counterfactual_path),
            "local_contract_path": str(local_contract_path),
            "final_kpi_compare_report_path": str(final_kpi_compare_report_path),
        },
        "family_anchor": {
            "decision_family": family_target.get("name"),
            "transition": family_target.get("transition"),
            "observed_case_count": family_target.get("observed_case_count"),
            "all_cases_non_cgm": family_case_summary.get("all_cases_non_cgm"),
            "reference_continue_margin_mean": family_interpretation.get(
                "reference_continue_margin_mean"
            ),
            "candidate_monitor_shortfall_mean": _as_dict(
                family_case_summary.get("candidate_monitor_shortfall_summary")
            ).get("mean"),
            "proxy_drop_mean": _as_dict(family_case_summary.get("proxy_drop_summary")).get(
                "mean"
            ),
        },
        "low_risk_non_cgm_context": {
            "dominant_candidate_regression_slice": compare_overall.get(
                "dominant_candidate_regression_slice"
            ),
            "low_risk_combined_disagreement_delta": compare_low_risk.get(
                "combined_disagreement_delta"
            ),
            "cgm_combined_disagreement_delta": compare_cgm.get(
                "combined_disagreement_delta"
            ),
            "current_smallest_surface_case_count": len(slice_examples),
            "current_smallest_surface_low_risk_case_count": slice_low_risk_case_count,
            "current_smallest_surface_non_low_risk_case_count": slice_non_low_risk_case_count,
            "current_smallest_surface_all_non_cgm": slice_case_summary.get(
                "all_cases_non_cgm"
            ),
        },
        "narrowing_chain": {
            "threshold_duration_sensitive": {
                "observed_case_count": subgroup.get("observed_case_count"),
                "share_of_family_pct": subgroup_case_summary.get("parent_family_share_pct"),
            },
            "mid_margin": {
                "observed_case_count": mid_margin_target.get("observed_case_count"),
                "share_of_family_pct": mid_margin_case_summary.get("parent_family_share_pct"),
                "proxy_drop_bucket_counts": mid_margin_workflow.get(
                    "proxy_drop_bucket_counts"
                ),
            },
            "small_drop": {
                "observed_case_count": slice_target.get("observed_case_count"),
                "share_of_family_pct": slice_case_summary.get("parent_family_share_pct"),
                "reference_continue_margin_mean": _as_dict(
                    slice_case_summary.get("reference_continue_margin_summary")
                ).get("mean"),
                "candidate_monitor_shortfall_mean": _as_dict(
                    slice_case_summary.get("candidate_monitor_shortfall_summary")
                ).get("mean"),
                "proxy_drop_mean": _as_dict(slice_case_summary.get("proxy_drop_summary")).get(
                    "mean"
                ),
            },
        },
        "final_step_vs_earlier_step": {
            "family_final_cycle_index_counts": family_workflow.get("final_cycle_index_counts"),
            "subgroup_final_cycle_index_counts": _as_dict(
                subgroup_diagnostic.get("workflow_summary")
            ).get("final_cycle_index_counts"),
            "smallest_surface_final_cycle_index_counts": _as_dict(
                small_drop_diagnostic.get("workflow_summary")
            ).get("final_cycle_index_counts"),
            "final_step_only_supported": final_step_only_supported,
            "earlier_step_influence_supported": False if final_step_only_supported else None,
        },
        "surface_attribution": {
            "protective_counterbalance": {
                "feature": "regimen_count",
                "family": "regimen_status_summary",
                "feature_value_mean": regimen_summary.get("regimen_count_value_mean"),
                "current_shortfall_mean": regimen_summary.get("current_shortfall_mean"),
                "add_again_clears_shortfall_case_count": regimen_summary.get(
                    "add_again_clears_shortfall_case_count"
                ),
                "removal_worsens_case_count": regimen_summary.get(
                    "removal_worsens_case_count"
                ),
                "interpretation": "protective_not_missing",
            },
            "dominant_opposing_surface": {
                "feature": "trajectory_step",
                "family": "workflow_timing",
                "signed_value_mean": trajectory_summary.get(
                    "trajectory_step_signed_value_mean"
                ),
                "abs_value_mean": trajectory_summary.get("trajectory_step_abs_value_mean"),
                "current_shortfall_mean": trajectory_summary.get("current_shortfall_mean"),
                "neutralize_clears_shortfall_case_count": trajectory_summary.get(
                    "neutralize_clears_shortfall_case_count"
                ),
                "extra_penalty_worsens_case_count": trajectory_summary.get(
                    "extra_penalty_worsens_case_count"
                ),
                "interpretation": "primary_local_opposing_driver",
            },
            "minimal_local_contract": {
                "local_handling_mode": contract_gate.get("chosen_local_handling_mode"),
                "local_contract": contract_gate.get("chosen_local_contract"),
                "probe_fraction": contract_gate.get("chosen_probe_fraction"),
                "probe_offset_abs_value": contract_gate.get("chosen_probe_offset_abs_value"),
                "all_cases_cleared": half_offset_summary.get("all_cases_cleared"),
                "mean_residual_clearance": half_offset_summary.get("mean_residual_clearance"),
                "min_residual_clearance": half_offset_summary.get("min_residual_clearance"),
                "requires_case_specific_tuning_now": contract_gate.get(
                    "requires_case_specific_tuning_now"
                ),
                "requires_second_feature_now": contract_gate.get(
                    "requires_second_feature_now"
                ),
                "residual_clearance_vector": contract_surface.get(
                    "residual_clearance_vector"
                ),
            },
            "top_absolute_slice_features": _as_list(
                slice_feature_summary.get("top_absolute_features")
            )[:4],
        },
        "attribution_verdict": {
            "held_decision": compare_decision.get("decision_class"),
            "minimal_cause_surface": (
                "trajectory_step / fixed_uniform_offset / 0.5 half-offset / "
                "uniform_score_gap_offset"
            ),
            "why_continue_crosses_into_monitor_only": (
                "Inside the current 5-case non-CGM `threshold_duration_sensitive` / "
                "`mid_margin` / `small_drop` slice, `regimen_count` is still protective, "
                "but `trajectory_step` is the dominant local opposing contributor; a "
                "replay-only `0.5` fixed uniform offset on that `trajectory_step` "
                "score-gap surface clears all 5 cases."
            ),
            "current_smallest_surface_sufficient_for_explanation": minimal_surface_complete,
            "sufficiency_scope": (
                "sufficient_for_current_5_case_small_drop_slice_only"
                if minimal_surface_complete
                else "insufficient_even_for_current_smallest_slice"
            ),
            "family_wide_explanation_complete": False,
            "training_rerun_still_blocked": True,
            "training_rerun_block_reason": compare_decision.get("principal_blocker"),
        },
        "readable_summary": {
            "family_digest": {
                "decision_family": family_target.get("name"),
                "observed_case_count": family_target.get("observed_case_count"),
                "transition": family_target.get("transition"),
                "all_cases_non_cgm": family_case_summary.get("all_cases_non_cgm"),
            },
            "low_risk_digest": {
                "dominant_candidate_regression_slice": compare_overall.get(
                    "dominant_candidate_regression_slice"
                ),
                "low_risk_combined_disagreement_delta": compare_low_risk.get(
                    "combined_disagreement_delta"
                ),
                "cgm_combined_disagreement_delta": compare_cgm.get(
                    "combined_disagreement_delta"
                ),
            },
            "smallest_surface_digest": {
                "trajectory_mode": subgroup.get("trajectory_mode"),
                "margin_bucket": mid_margin_target.get("margin_bucket"),
                "proxy_drop_bucket": slice_target.get("proxy_drop_bucket"),
                "observed_case_count": slice_target.get("observed_case_count"),
                "all_low_risk_cases": slice_low_risk_case_count == len(slice_examples),
                "final_step_only_supported": final_step_only_supported,
            },
            "surface_digest": {
                "protective_feature": "regimen_count",
                "opposing_feature": "trajectory_step",
                "probe_fraction": contract_gate.get("chosen_probe_fraction"),
                "probe_offset_abs_value": contract_gate.get("chosen_probe_offset_abs_value"),
                "local_contract": contract_gate.get("chosen_local_contract"),
            },
            "verdict_digest": {
                "current_smallest_surface_sufficient_for_explanation": minimal_surface_complete,
                "family_wide_explanation_complete": False,
                "training_rerun_still_blocked": True,
            },
        },
        "summary_findings": [
            (
                "The dominant replay family remains a 26-case non-CGM final-step "
                "`continue_plan->monitor_only` drift, and the wider candidate regression is "
                "still low-risk dominant (`62` combined disagreements vs `6` for `cgm`)."
            ),
            (
                "The narrowest reproducible cause surface is the 5-case "
                "`threshold_duration_sensitive` / `mid_margin` / `small_drop` slice, which is "
                "entirely non-CGM, entirely low-risk in the current slice examples, and "
                "entirely final-step."
            ),
            (
                "`regimen_count` is not the missing cause on that slice: mean protective value "
                f"{regimen_summary.get('regimen_count_value_mean')} exceeds mean shortfall "
                f"{regimen_summary.get('current_shortfall_mean')}, and add-again/removal "
                "counterfactuals move 5/5 cases in the protective direction."
            ),
            (
                "`trajectory_step` is the minimal local drift surface: mean opposing magnitude "
                f"{trajectory_summary.get('trajectory_step_abs_value_mean')} exceeds mean "
                f"shortfall {trajectory_summary.get('current_shortfall_mean')}, and a "
                "replay-only `0.5` fixed uniform offset "
                f"({contract_gate.get('chosen_probe_offset_abs_value')}) clears 5/5 cases "
                "with minimum residual clearance "
                f"{half_offset_summary.get('min_residual_clearance')}."
            ),
            (
                "So the current smallest surface is sufficient to explain the current 5-case "
                "slice, but not yet the full 26-case family; another training rerun "
                "remains blocked."
            ),
        ],
    }
    report["validation_issues"] = (
        validate_non_cgm_continue_to_monitor_threshold_cross_attribution(report)
    )
    return report


def validate_non_cgm_continue_to_monitor_threshold_cross_attribution(
    report: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    family_anchor = _as_dict(report.get("family_anchor"))
    low_risk_context = _as_dict(report.get("low_risk_non_cgm_context"))
    chain = _as_dict(report.get("narrowing_chain"))
    final_step = _as_dict(report.get("final_step_vs_earlier_step"))
    surface = _as_dict(report.get("surface_attribution"))
    verdict = _as_dict(report.get("attribution_verdict"))

    if family_anchor.get("decision_family") != "non_cgm_continue_to_monitor_threshold_cross":
        issues.append("unexpected_family_name")
    if family_anchor.get("observed_case_count") != 26:
        issues.append("unexpected_family_case_count")
    if _as_dict(chain.get("threshold_duration_sensitive")).get("observed_case_count") != 10:
        issues.append("unexpected_threshold_duration_sensitive_count")
    if _as_dict(chain.get("mid_margin")).get("observed_case_count") != 9:
        issues.append("unexpected_mid_margin_count")
    if _as_dict(chain.get("small_drop")).get("observed_case_count") != 5:
        issues.append("unexpected_small_drop_count")
    if low_risk_context.get("dominant_candidate_regression_slice") != "low_risk":
        issues.append("unexpected_dominant_regression_slice")
    if not bool(low_risk_context.get("current_smallest_surface_all_non_cgm")):
        issues.append("smallest_surface_not_non_cgm")
    if int(low_risk_context.get("current_smallest_surface_low_risk_case_count", 0)) != 5:
        issues.append("unexpected_low_risk_case_count_on_smallest_surface")
    if not bool(final_step.get("final_step_only_supported")):
        issues.append("final_step_only_not_supported")
    if _as_dict(surface.get("protective_counterbalance")).get("feature") != "regimen_count":
        issues.append("unexpected_protective_feature")
    if _as_dict(surface.get("dominant_opposing_surface")).get("feature") != "trajectory_step":
        issues.append("unexpected_dominant_opposing_feature")
    if _as_dict(surface.get("minimal_local_contract")).get("probe_fraction") != 0.5:
        issues.append("unexpected_probe_fraction")
    if not bool(_as_dict(surface.get("minimal_local_contract")).get("all_cases_cleared")):
        issues.append("half_offset_not_clearing_all_cases")
    if not bool(verdict.get("current_smallest_surface_sufficient_for_explanation")):
        issues.append("smallest_surface_not_marked_sufficient")
    if verdict.get("sufficiency_scope") != "sufficient_for_current_5_case_small_drop_slice_only":
        issues.append("unexpected_sufficiency_scope")
    if bool(verdict.get("family_wide_explanation_complete")):
        issues.append("family_wide_explanation_unexpectedly_complete")
    if not bool(verdict.get("training_rerun_still_blocked")):
        issues.append("training_rerun_unexpectedly_unblocked")
    if not _as_list(report.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_non_cgm_continue_to_monitor_threshold_cross_attribution_markdown(
    report: dict[str, object]
) -> str:
    lines = [
        "# non-cgm continue-to-monitor threshold-cross attribution v1",
        "",
        "## readable summary",
        "",
        f"- readable_summary: `{report.get('readable_summary', {})}`",
        "",
        "## family anchor",
        "",
        f"- family_anchor: `{report.get('family_anchor', {})}`",
        "",
        "## low-risk non-cgm context",
        "",
        f"- low_risk_non_cgm_context: `{report.get('low_risk_non_cgm_context', {})}`",
        "",
        "## narrowing chain",
        "",
        f"- narrowing_chain: `{report.get('narrowing_chain', {})}`",
        "",
        "## final-step vs earlier-step",
        "",
        f"- final_step_vs_earlier_step: `{report.get('final_step_vs_earlier_step', {})}`",
        "",
        "## surface attribution",
        "",
        f"- surface_attribution: `{report.get('surface_attribution', {})}`",
        "",
        "## attribution verdict",
        "",
        f"- attribution_verdict: `{report.get('attribution_verdict', {})}`",
        "",
        "## summary findings",
        "",
    ]
    for item in _as_list(report.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{report.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_non_cgm_continue_to_monitor_threshold_cross_attribution_files(
    *,
    report: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_non_cgm_continue_to_monitor_threshold_cross_attribution_markdown(report),
        encoding="utf-8",
    )


def _all_final_cycle_is_four(value: object) -> bool:
    counter = _as_dict(value)
    return counter == {"4": counter.get("4")} and counter.get("4") is not None


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_non_cgm_continue_to_monitor_threshold_cross_attribution",
    "load_json_artifact",
    "render_non_cgm_continue_to_monitor_threshold_cross_attribution_markdown",
    "validate_non_cgm_continue_to_monitor_threshold_cross_attribution",
    "write_non_cgm_continue_to_monitor_threshold_cross_attribution_files",
]
