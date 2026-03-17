from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_effect_candidate_reject_decision(
    *,
    compare_report: dict[str, object],
    compare_report_path: str | Path,
    final_compare_report: dict[str, object],
    final_compare_report_path: str | Path,
    non_cgm_diagnostic_report: dict[str, object],
    non_cgm_diagnostic_report_path: str | Path,
    cgm_diagnostic_report: dict[str, object],
    cgm_diagnostic_report_path: str | Path,
    core_kpi_path_summary: dict[str, object],
    core_kpi_path_summary_path: str | Path,
) -> dict[str, object]:
    latest_candidate = _as_dict(final_compare_report.get("latest_candidate"))
    overall_delta = _as_dict(latest_candidate.get("overall_delta"))
    overall_slice = _as_dict(_as_dict(final_compare_report.get("slice_compare")).get("overall"))
    low_risk_slice = _as_dict(_as_dict(final_compare_report.get("slice_compare")).get("low_risk"))
    cgm_slice = _as_dict(_as_dict(final_compare_report.get("slice_compare")).get("cgm"))
    target_family = _as_dict(non_cgm_diagnostic_report.get("target_family"))
    interpretation = _as_dict(non_cgm_diagnostic_report.get("interpretation"))
    workflow_summary = _as_dict(non_cgm_diagnostic_report.get("workflow_summary"))
    cgm_gate = _as_dict(cgm_diagnostic_report.get("hypothesis_gate"))
    residual_cgm = _as_dict(cgm_diagnostic_report.get("residual_cgm_failure_families"))
    bridge_assessment = _as_dict(cgm_diagnostic_report.get("bridge_and_workflow_assessment"))
    baseline_judgement = _as_dict(
        core_kpi_path_summary.get("deterministic_baseline_vs_candidate_judgement")
    )
    replay_compare_status = _as_dict(core_kpi_path_summary.get("replay_compare_status"))

    decision = {
        "audit_name": "latest_effect_candidate_reject_decision_v1",
        "source_artifacts": {
            "compare_report_path": str(compare_report_path),
            "final_compare_report_path": str(final_compare_report_path),
            "non_cgm_diagnostic_report_path": str(non_cgm_diagnostic_report_path),
            "cgm_diagnostic_report_path": str(cgm_diagnostic_report_path),
            "core_kpi_path_summary_path": str(core_kpi_path_summary_path),
        },
        "decision_gate": {
            "candidate_label": latest_candidate.get("candidate_label"),
            "overall_clearly_worse_than_baseline": (
                latest_candidate.get("fit_gate_status") == "worse_on_all_fit_gates"
            ),
            "fit_gate_status": latest_candidate.get("fit_gate_status"),
            "gate_evidence": {
                "test_aggregate_mae_delta": _to_float(
                    overall_delta.get("test_aggregate_mae_delta")
                ),
                "test_aggregate_r2_delta": _to_float(
                    overall_delta.get("test_aggregate_r2_delta")
                ),
                "test_policy_proxy_mae_delta": _to_float(
                    overall_delta.get("test_policy_proxy_mae_delta")
                ),
            },
            "decision": "reject_candidate_keep_baseline",
            "fork_recommendation": "analysis_only_fork",
        },
        "regression_slices": {
            "overall_fit": {
                "aggregate_mae_delta": _to_float(
                    overall_delta.get("test_aggregate_mae_delta")
                ),
                "aggregate_r2_delta": _to_float(
                    overall_delta.get("test_aggregate_r2_delta")
                ),
                "policy_proxy_mae_delta": _to_float(
                    overall_delta.get("test_policy_proxy_mae_delta")
                ),
                "dominant_candidate_regression_slice": overall_slice.get(
                    "dominant_candidate_regression_slice"
                ),
                "low_risk_regression_score": _to_int(
                    overall_slice.get("low_risk_regression_score")
                ),
                "cgm_regression_score": _to_int(overall_slice.get("cgm_regression_score")),
            },
            "dominant_low_risk_slice": {
                "decision_family": target_family.get("name"),
                "observed_case_count": _to_int(target_family.get("observed_case_count")),
                "transition": target_family.get("transition"),
                "effect_only_disagreement_delta": _to_int(
                    low_risk_slice.get("effect_only_disagreement_delta")
                ),
                "combined_disagreement_delta": _to_int(
                    low_risk_slice.get("combined_disagreement_delta")
                ),
                "effect_only_final_action_delta": _as_dict(
                    low_risk_slice.get("effect_only_final_action_delta")
                ),
                "combined_final_action_delta": _as_dict(
                    low_risk_slice.get("combined_final_action_delta")
                ),
                "dominant_workflow_modes": _as_list(
                    interpretation.get("dominant_workflow_modes")
                ),
                "dominant_feature_family": interpretation.get("dominant_feature_family"),
                "why_regression": interpretation.get("summary"),
                "reference_continue_margin_mean": interpretation.get(
                    "reference_continue_margin_mean"
                ),
                "proxy_drop_bucket_counts": _as_dict(
                    workflow_summary.get("proxy_drop_bucket_counts")
                ),
            },
            "residual_cgm_slice": {
                "cgm_only_failure_hypothesis_supported": cgm_gate.get(
                    "overall_ok_but_cgm_only_worse_supported"
                ),
                "rejection_reasons": _as_list(cgm_gate.get("rejection_reasons")),
                "effect_only_disagreement_delta": _to_int(
                    cgm_slice.get("effect_only_disagreement_delta")
                ),
                "combined_disagreement_delta": _to_int(
                    cgm_slice.get("combined_disagreement_delta")
                ),
                "geometry_status": cgm_slice.get("geometry_status"),
                "geometry_blocker_family_summary": _as_dict(
                    residual_cgm.get("geometry_blocker_family_summary")
                ),
                "combined_final_action_delta": _as_dict(
                    residual_cgm.get("combined_final_action_delta")
                ),
                "feature_families": _extract_cgm_feature_names(residual_cgm),
                "bridge_is_primary_driver": bridge_assessment.get(
                    "bridge_is_primary_driver"
                ),
            },
        },
        "baseline_hold_rationale": [
            str(_as_dict(final_compare_report.get("decision_summary")).get("one_line_judgement")),
            (
                "Baseline retention is rational because the candidate loses on aggregate MAE, "
                "aggregate R2, and policy-proxy MAE with no compensating overall slice gain."
            ),
            (
                "The dominant replay regression sits in low-risk non-cgm "
                f"`{target_family.get('name')}`, not in a cgm-only slice that could justify "
                "promotion."
            ),
            (
                "Any further work should stay in an analysis or fork lane because the current "
                f"principal blocker remains `{baseline_judgement.get('principal_blocker')}`."
            ),
        ],
        "required_evidence_before_next_training_loop": [
            (
                "A replay-only candidate result showing aggregate_mae_delta <= 0, "
                "aggregate_r2_delta >= 0, and policy_proxy_mae_delta <= 0 versus baseline."
            ),
            (
                "A bounded replay-side explanation or fix for "
                f"`{target_family.get('name')}` that materially reduces low-risk disagreement "
                "without shifting the problem into cgm."
            ),
            (
                "A narrow validity proof that any candidate gain survives outside the "
                "supported effect-enriched circular slice instead of depending on synthetic "
                "generator or calibration coupling."
            ),
        ],
        "summary_findings": [
            (
                f"{latest_candidate.get('candidate_label')} should not be adopted because it is "
                "clearly worse overall than the deterministic baseline."
            ),
            (
                "The main regression is low-risk non-cgm threshold-cross drift, anchored by "
                f"`{target_family.get('name')}` with "
                f"{_to_int(target_family.get('observed_case_count'))} observed cases."
            ),
            (
                "Baseline hold is rational because cgm remains a smaller residual problem and "
                "the current cgm gate explicitly rejects the 'overall okay but only cgm worse' "
                "story."
            ),
            (
                "Any fork should remain analysis-only until replay fit gates improve and the "
                "dominant low-risk family is narrowed with non-training evidence."
            ),
        ],
        "hold_context": {
            "adoption_decision": replay_compare_status.get("adoption_decision"),
            "dominant_candidate_regression_slice": replay_compare_status.get(
                "dominant_candidate_regression_slice"
            ),
            "principal_blocker": baseline_judgement.get("principal_blocker"),
            "dominant_replay_regression_family": baseline_judgement.get(
                "dominant_replay_regression_family"
            ),
        },
    }
    decision["validation_issues"] = validate_effect_candidate_reject_decision(decision)
    return decision


def validate_effect_candidate_reject_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    decision_gate = _as_dict(decision.get("decision_gate"))
    regression_slices = _as_dict(decision.get("regression_slices"))
    overall_fit = _as_dict(regression_slices.get("overall_fit"))
    low_risk_slice = _as_dict(regression_slices.get("dominant_low_risk_slice"))
    residual_cgm_slice = _as_dict(regression_slices.get("residual_cgm_slice"))

    if decision_gate.get("overall_clearly_worse_than_baseline") is not True:
        issues.append("reject_gate_not_closed")
    if decision_gate.get("decision") != "reject_candidate_keep_baseline":
        issues.append("unexpected_adoption_decision")
    if decision_gate.get("fork_recommendation") != "analysis_only_fork":
        issues.append("unexpected_fork_recommendation")
    if (
        _to_int(overall_fit.get("low_risk_regression_score"))
        <= _to_int(overall_fit.get("cgm_regression_score"))
    ):
        issues.append("low_risk_not_dominant")
    if _to_int(low_risk_slice.get("observed_case_count")) <= 0:
        issues.append("missing_low_risk_family_evidence")
    if residual_cgm_slice.get("cgm_only_failure_hypothesis_supported") is not False:
        issues.append("unexpected_cgm_only_gate")
    if len(_as_list(decision.get("required_evidence_before_next_training_loop"))) < 2:
        issues.append("insufficient_next_evidence_requirements")
    return issues


def render_effect_candidate_reject_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        "# latest effect candidate reject decision v1",
        "",
        "## decision gate",
        "",
        f"- decision_gate: `{decision.get('decision_gate', {})}`",
        "",
        "## regression slices",
        "",
        f"- regression_slices: `{decision.get('regression_slices', {})}`",
        "",
        "## baseline hold rationale",
        "",
    ]
    for item in _as_list(decision.get("baseline_hold_rationale")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## required evidence before next training loop",
            "",
        ]
    )
    for item in _as_list(decision.get("required_evidence_before_next_training_loop")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## summary findings",
            "",
        ]
    )
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


def write_effect_candidate_reject_decision_files(
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
        render_effect_candidate_reject_decision_markdown(decision),
        encoding="utf-8",
    )


def _extract_cgm_feature_names(residual_cgm: dict[str, object]) -> list[str]:
    feature_family_summary = _as_dict(residual_cgm.get("feature_family_summary"))
    feature_names: list[str] = []
    for item in _as_list(feature_family_summary.get("top_feature_gaps")):
        payload = _as_dict(item)
        feature = payload.get("feature")
        if isinstance(feature, str):
            feature_names.append(feature)
    return feature_names


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _to_float(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_effect_candidate_reject_decision",
    "load_json_artifact",
    "render_effect_candidate_reject_decision_markdown",
    "validate_effect_candidate_reject_decision",
    "write_effect_candidate_reject_decision_files",
]
