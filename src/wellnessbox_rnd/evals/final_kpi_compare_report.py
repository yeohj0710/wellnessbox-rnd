from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_final_kpi_compare_report(
    *,
    baseline_candidate_summary: dict[str, object],
    baseline_candidate_summary_path: str | Path,
    weakest_slice_summary: dict[str, object],
    weakest_slice_summary_path: str | Path,
    core_kpi_path_summary: dict[str, object],
    core_kpi_path_summary_path: str | Path,
) -> dict[str, object]:
    baseline_reference = _as_dict(baseline_candidate_summary.get("baseline_reference"))
    candidate_comparison = _as_dict(
        baseline_candidate_summary.get("candidate_comparison")
    )
    weakest_slice_delta = _as_dict(baseline_candidate_summary.get("weakest_slice_delta"))
    adoption_summary = _as_dict(baseline_candidate_summary.get("adoption_summary"))
    weakest_anchor = _as_dict(weakest_slice_summary.get("frozen_eval_anchor"))
    weakest_overall = _as_dict(weakest_anchor.get("weakest_category_overall"))
    weakest_by_metric = _as_dict(weakest_anchor.get("weakest_category_by_metric"))
    sensor_genetic_anchor = _as_dict(
        weakest_by_metric.get("sensor_genetic_integration_rate_pct")
    )
    core_replay = _as_dict(core_kpi_path_summary.get("replay_compare_status"))
    core_cgm = _as_dict(core_kpi_path_summary.get("cgm_final_step_geometry_status"))
    core_boundary = _as_dict(
        core_kpi_path_summary.get("learned_artifact_replay_only_boundary_status")
    )
    overall_delta = {
        "test_aggregate_mae_delta": _as_dict(candidate_comparison.get("delta_summary")).get(
            "test_aggregate_mae_delta"
        ),
        "test_aggregate_r2_delta": _as_dict(candidate_comparison.get("delta_summary")).get(
            "test_aggregate_r2_delta"
        ),
        "test_policy_proxy_mae_delta": _as_dict(
            candidate_comparison.get("delta_summary")
        ).get("test_policy_proxy_mae_delta"),
    }
    candidate_slice_delta = _as_dict(weakest_slice_delta.get("candidate_slice_delta"))
    effect_only = _as_dict(candidate_slice_delta.get("learned_effect_guarded"))
    combined = _as_dict(candidate_slice_delta.get("learned_effect_and_policy_guarded"))
    regression_balance = _as_dict(
        weakest_slice_delta.get("candidate_regression_balance")
    )
    required_evidence = _as_list(core_replay.get("required_evidence_before_revisit"))

    report = {
        "summary_name": "final_kpi_compare_report_v1",
        "source_artifacts": {
            "baseline_candidate_summary_path": str(baseline_candidate_summary_path),
            "weakest_slice_summary_path": str(weakest_slice_summary_path),
            "core_kpi_path_summary_path": str(core_kpi_path_summary_path),
        },
        "readable_summary": {
            "decision_readout": {
                "decision_class": adoption_summary.get("decision"),
                "candidate_label": candidate_comparison.get("candidate_label"),
                "one_line_judgement": adoption_summary.get("one_line_conclusion"),
                "dominant_candidate_regression_slice": weakest_slice_delta.get(
                    "dominant_candidate_regression_slice"
                ),
                "principal_blocker": _as_dict(
                    core_kpi_path_summary.get("deterministic_baseline_vs_candidate_judgement")
                ).get("principal_blocker"),
            },
            "baseline_reference_digest": {
                "dataset_path": baseline_reference.get("dataset_path"),
                "case_count": baseline_reference.get("case_count"),
                "headline_metrics": _select_headline_metrics(
                    _as_dict(baseline_reference.get("metrics"))
                ),
            },
            "candidate_delta_digest": {
                "candidate_label": candidate_comparison.get("candidate_label"),
                "fit_gate_status": candidate_comparison.get("fit_gate_status"),
                "replay_compare_status": core_replay.get("status"),
                "overall_delta": overall_delta,
            },
            "slice_compare_digest": {
                "overall": {
                    "dominant_candidate_regression_slice": weakest_slice_delta.get(
                        "dominant_candidate_regression_slice"
                    ),
                    "low_risk_regression_score": regression_balance.get(
                        "low_risk_regression_score"
                    ),
                    "cgm_regression_score": regression_balance.get(
                        "cgm_regression_score"
                    ),
                },
                "low_risk": {
                    "combined_disagreement_delta": combined.get(
                        "low_risk_disagreement_delta"
                    ),
                    "combined_final_action_delta": combined.get(
                        "low_risk_final_action_delta"
                    ),
                },
                "cgm": {
                    "combined_disagreement_delta": combined.get(
                        "cgm_disagreement_delta"
                    ),
                    "combined_final_action_delta": combined.get("cgm_final_action_delta"),
                    "geometry_status": core_cgm.get("status"),
                },
            },
            "weakest_slice_delta_digest": {
                "dominant_candidate_regression_slice": weakest_slice_delta.get(
                    "dominant_candidate_regression_slice"
                ),
                "overall_weakest_category": weakest_overall.get("category"),
                "sensor_genetic_weakest_category": sensor_genetic_anchor.get("category"),
                "sensor_genetic_score": sensor_genetic_anchor.get("score"),
                "low_risk_combined_disagreement_delta": combined.get(
                    "low_risk_disagreement_delta"
                ),
                "cgm_combined_disagreement_delta": combined.get(
                    "cgm_disagreement_delta"
                ),
                "still_empty_weakest_families": weakest_slice_summary.get(
                    "still_empty_weakest_families"
                ),
            },
            "audit_path_digest": {
                "weakest_slice_wiring_status": _as_dict(
                    core_kpi_path_summary.get("weakest_slice_frozen_eval_wiring_status")
                ).get("status"),
                "cgm_geometry_status": core_cgm.get("status"),
                "learned_boundary_status": core_boundary.get("status"),
            },
            "next_evidence_digest": (required_evidence[:1] + required_evidence[2:3]),
            "one_line_decision": adoption_summary.get("one_line_conclusion"),
        },
        "baseline_reference": {
            "dataset_path": baseline_reference.get("dataset_path"),
            "case_count": baseline_reference.get("case_count"),
            "metrics": baseline_reference.get("metrics"),
        },
        "latest_candidate": {
            "candidate_label": candidate_comparison.get("candidate_label"),
            "fit_metrics": candidate_comparison.get("candidate_fit_metrics"),
            "reference_fit_metrics": candidate_comparison.get("reference_fit_metrics"),
            "fit_gate_status": candidate_comparison.get("fit_gate_status"),
            "overall_delta": overall_delta,
            "replay_compare_status": core_replay.get("status"),
        },
        "slice_compare": {
            "overall": {
                "dominant_candidate_regression_slice": weakest_slice_delta.get(
                    "dominant_candidate_regression_slice"
                ),
                "low_risk_regression_score": regression_balance.get(
                    "low_risk_regression_score"
                ),
                "cgm_regression_score": regression_balance.get("cgm_regression_score"),
                "overall_fit_delta": overall_delta,
            },
            "low_risk": {
                "effect_only_disagreement_delta": effect_only.get(
                    "low_risk_disagreement_delta"
                ),
                "combined_disagreement_delta": combined.get(
                    "low_risk_disagreement_delta"
                ),
                "effect_only_final_action_delta": effect_only.get(
                    "low_risk_final_action_delta"
                ),
                "combined_final_action_delta": combined.get(
                    "low_risk_final_action_delta"
                ),
            },
            "cgm": {
                "effect_only_disagreement_delta": effect_only.get(
                    "cgm_disagreement_delta"
                ),
                "combined_disagreement_delta": combined.get("cgm_disagreement_delta"),
                "effect_only_final_action_delta": effect_only.get(
                    "cgm_final_action_delta"
                ),
                "combined_final_action_delta": combined.get("cgm_final_action_delta"),
                "geometry_status": core_cgm.get("status"),
                "geometry_blocker_family_summary": core_cgm.get(
                    "blocker_family_summary"
                ),
            },
        },
        "weakest_slice_anchor": {
            "overall_weakest_category": weakest_overall.get("category"),
            "overall_weakest_case_count": weakest_overall.get("case_count"),
            "overall_weakest_metrics": weakest_overall.get("metrics"),
            "sensor_genetic_weakest_category": sensor_genetic_anchor.get("category"),
            "sensor_genetic_score": sensor_genetic_anchor.get("score"),
            "sensor_genetic_target": sensor_genetic_anchor.get("target"),
            "sensor_genetic_passed": sensor_genetic_anchor.get("passed"),
            "still_empty_weakest_families": weakest_slice_summary.get(
                "still_empty_weakest_families"
            ),
            "audit_layer_gap_count": weakest_slice_summary.get("audit_layer_gap_count"),
        },
        "decision_summary": {
            "decision_class": adoption_summary.get("decision"),
            "one_line_judgement": adoption_summary.get("one_line_conclusion"),
            "decision_reason_codes": adoption_summary.get("reason_codes"),
            "latest_hold_context": {
                "fit_gate_status": candidate_comparison.get("fit_gate_status"),
                "dominant_candidate_regression_slice": weakest_slice_delta.get(
                    "dominant_candidate_regression_slice"
                ),
                "learned_boundary_status": core_boundary.get("status"),
            },
        },
        "next_evidence_needed": required_evidence[:1] + required_evidence[2:3],
    }
    report["validation_issues"] = validate_final_kpi_compare_report(report)
    return report


def validate_final_kpi_compare_report(report: dict[str, object]) -> list[str]:
    issues: list[str] = []
    readable_summary = _as_dict(report.get("readable_summary"))
    baseline_reference = _as_dict(report.get("baseline_reference"))
    latest_candidate = _as_dict(report.get("latest_candidate"))
    slice_compare = _as_dict(report.get("slice_compare"))
    weakest_slice_anchor = _as_dict(report.get("weakest_slice_anchor"))
    decision_summary = _as_dict(report.get("decision_summary"))

    if baseline_reference.get("case_count") is None:
        issues.append("missing_baseline_case_count")
    if latest_candidate.get("candidate_label") is None:
        issues.append("missing_candidate_label")
    if _as_dict(slice_compare.get("low_risk")).get("combined_disagreement_delta") is None:
        issues.append("missing_low_risk_slice_delta")
    if _as_dict(slice_compare.get("cgm")).get("combined_disagreement_delta") is None:
        issues.append("missing_cgm_slice_delta")
    if weakest_slice_anchor.get("overall_weakest_category") is None:
        issues.append("missing_weakest_slice_anchor")
    if decision_summary.get("decision_class") is None:
        issues.append("missing_decision_class")
    if _as_dict(readable_summary.get("decision_readout")).get("one_line_judgement") is None:
        issues.append("missing_decision_readout")
    if _as_dict(readable_summary.get("slice_compare_digest")).get("overall") == {}:
        issues.append("missing_slice_compare_digest")
    if len(_as_list(readable_summary.get("next_evidence_digest"))) == 0:
        issues.append("missing_next_evidence_digest")
    return issues


def render_final_kpi_compare_report_markdown(report: dict[str, object]) -> str:
    readable_summary = _as_dict(report.get("readable_summary"))
    decision_readout = _as_dict(readable_summary.get("decision_readout"))
    baseline_reference = _as_dict(report.get("baseline_reference"))
    baseline_metrics = _as_dict(baseline_reference.get("metrics"))
    latest_candidate = _as_dict(report.get("latest_candidate"))
    slice_compare = _as_dict(report.get("slice_compare"))
    overall = _as_dict(slice_compare.get("overall"))
    low_risk = _as_dict(slice_compare.get("low_risk"))
    cgm = _as_dict(slice_compare.get("cgm"))
    weakest = _as_dict(report.get("weakest_slice_anchor"))
    decision_summary = _as_dict(report.get("decision_summary"))
    next_evidence = _as_list(report.get("next_evidence_needed"))
    readable_next_evidence = _as_list(readable_summary.get("next_evidence_digest"))

    lines = [
        "# final kpi compare report v1",
        "",
        f"- decision: `{decision_summary.get('decision_class')}`",
        f"- judgement: `{decision_summary.get('one_line_judgement')}`",
        "",
        "## Decision Readout",
        "",
        f"- candidate_label: `{decision_readout.get('candidate_label')}`",
        f"- decision_class: `{decision_readout.get('decision_class')}`",
        (
            "- dominant_candidate_regression_slice: "
            f"`{decision_readout.get('dominant_candidate_regression_slice')}`"
        ),
        f"- principal_blocker: `{decision_readout.get('principal_blocker')}`",
        f"- one_line_judgement: `{decision_readout.get('one_line_judgement')}`",
        "",
        "## Readable Summary",
        "",
        (
            "- baseline_reference_digest_case_count: "
            f"`{_as_dict(readable_summary.get('baseline_reference_digest')).get('case_count')}`"
        ),
        (
            "- candidate_delta_digest_fit_gate_status: "
            f"`{_as_dict(readable_summary.get('candidate_delta_digest')).get('fit_gate_status')}`"
        ),
        (
            "- slice_compare_digest_dominant_slice: "
            f"`{_as_dict(_as_dict(readable_summary.get('slice_compare_digest')).get('overall')).get('dominant_candidate_regression_slice')}`"
        ),
        (
            "- weakest_slice_overall_category: "
            f"`{_as_dict(readable_summary.get('weakest_slice_delta_digest')).get('overall_weakest_category')}`"
        ),
        (
            "- audit_path_digest: "
            f"`{readable_summary.get('audit_path_digest')}`"
        ),
        f"- one_line_decision: `{readable_summary.get('one_line_decision')}`",
        "",
        "## Baseline Reference",
        "",
        f"- dataset_path: `{baseline_reference.get('dataset_path')}`",
        f"- case_count: `{baseline_reference.get('case_count')}`",
        (
            "- recommendation_coverage_pct: "
            f"`{_metric_score(baseline_metrics, 'recommendation_coverage_pct')}`"
        ),
        (
            "- efficacy_improvement_pp: "
            f"`{_metric_score(baseline_metrics, 'efficacy_improvement_pp')}`"
        ),
        (
            "- next_action_accuracy_pct: "
            f"`{_metric_score(baseline_metrics, 'next_action_accuracy_pct')}`"
        ),
        (
            "- safety_reference_accuracy_pct: "
            f"`{_metric_score(baseline_metrics, 'safety_reference_accuracy_pct')}`"
        ),
        (
            "- sensor_genetic_integration_rate_pct: "
            f"`{_metric_score(baseline_metrics, 'sensor_genetic_integration_rate_pct')}`"
        ),
        "",
        "## Latest Candidate",
        "",
        f"- candidate_label: `{latest_candidate.get('candidate_label')}`",
        f"- fit_gate_status: `{latest_candidate.get('fit_gate_status')}`",
        f"- replay_compare_status: `{latest_candidate.get('replay_compare_status')}`",
        (
            "- aggregate_mae_delta: "
            f"`{_as_dict(latest_candidate.get('overall_delta')).get('test_aggregate_mae_delta')}`"
        ),
        (
            "- aggregate_r2_delta: "
            f"`{_as_dict(latest_candidate.get('overall_delta')).get('test_aggregate_r2_delta')}`"
        ),
        (
            "- policy_proxy_mae_delta: "
            f"`{_as_dict(latest_candidate.get('overall_delta')).get('test_policy_proxy_mae_delta')}`"
        ),
        "",
        "## Slice Compare",
        "",
        (
            "- overall_dominant_candidate_regression_slice: "
            f"`{overall.get('dominant_candidate_regression_slice')}`"
        ),
        f"- overall_low_risk_regression_score: `{overall.get('low_risk_regression_score')}`",
        f"- overall_cgm_regression_score: `{overall.get('cgm_regression_score')}`",
        f"- low_risk_combined_disagreement_delta: `{low_risk.get('combined_disagreement_delta')}`",
        f"- low_risk_combined_final_action_delta: `{low_risk.get('combined_final_action_delta')}`",
        f"- cgm_combined_disagreement_delta: `{cgm.get('combined_disagreement_delta')}`",
        f"- cgm_combined_final_action_delta: `{cgm.get('combined_final_action_delta')}`",
        f"- cgm_geometry_status: `{cgm.get('geometry_status')}`",
        "",
        "## Weakest-Slice Anchor",
        "",
        f"- overall_weakest_category: `{weakest.get('overall_weakest_category')}`",
        f"- overall_weakest_case_count: `{weakest.get('overall_weakest_case_count')}`",
        f"- overall_weakest_metrics: `{weakest.get('overall_weakest_metrics')}`",
        f"- sensor_genetic_weakest_category: `{weakest.get('sensor_genetic_weakest_category')}`",
        f"- sensor_genetic_score: `{weakest.get('sensor_genetic_score')}`",
        (
            "- still_empty_weakest_families: "
            f"`{weakest.get('still_empty_weakest_families')}`"
        ),
        "",
        "## Next Evidence",
        "",
    ]
    for item in readable_next_evidence or next_evidence:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def write_final_kpi_compare_report_files(
    report: dict[str, object],
    *,
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        render_final_kpi_compare_report_markdown(report),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _select_headline_metrics(metrics: dict[str, object]) -> dict[str, object]:
    headline_keys = [
        "recommendation_coverage_pct",
        "efficacy_improvement_pp",
        "next_action_accuracy_pct",
        "safety_reference_accuracy_pct",
        "sensor_genetic_integration_rate_pct",
    ]
    return {key: metrics.get(key) for key in headline_keys if key in metrics}


def _metric_score(metrics: dict[str, object], key: str) -> object:
    return _as_dict(metrics.get(key)).get("score")


__all__ = [
    "build_final_kpi_compare_report",
    "load_json",
    "render_final_kpi_compare_report_markdown",
    "validate_final_kpi_compare_report",
    "write_final_kpi_compare_report_files",
]
