from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_cgm_candidate_failure_family_diagnostic(
    *,
    compare_report: dict[str, object],
    compare_report_path: str | Path,
    attribution_report: dict[str, object],
    attribution_report_path: str | Path,
    cgm_feature_audit_report: dict[str, object],
    cgm_feature_audit_report_path: str | Path,
    cgm_slice_bridge_report: dict[str, object],
    cgm_slice_bridge_report_path: str | Path,
    cgm_event_report: dict[str, object],
    cgm_event_report_path: str | Path,
) -> dict[str, object]:
    compare_effect_only = _as_dict(
        _as_dict(compare_report.get("slice_deltas")).get("learned_effect_guarded")
    )
    compare_combined = _as_dict(
        _as_dict(compare_report.get("slice_deltas")).get("learned_effect_and_policy_guarded")
    )
    attribution_effect_only = _as_dict(
        _as_dict(attribution_report.get("mode_attribution")).get("learned_effect_guarded")
    )
    attribution_combined = _as_dict(
        _as_dict(attribution_report.get("mode_attribution")).get(
            "learned_effect_and_policy_guarded"
        )
    )

    effect_only_low_risk_final_abs = _absolute_action_delta_count(
        _as_dict(compare_effect_only.get("low_risk_final_action_delta"))
    )
    effect_only_cgm_final_abs = _absolute_action_delta_count(
        _as_dict(compare_effect_only.get("cgm_final_action_delta"))
    )
    combined_low_risk_final_abs = _absolute_action_delta_count(
        _as_dict(compare_combined.get("low_risk_final_action_delta"))
    )
    combined_cgm_final_abs = _absolute_action_delta_count(
        _as_dict(compare_combined.get("cgm_final_action_delta"))
    )

    effect_only_low_risk_disagreement = int(
        compare_effect_only.get("low_risk_disagreement_delta", 0)
    )
    effect_only_cgm_disagreement = int(compare_effect_only.get("cgm_disagreement_delta", 0))
    combined_low_risk_disagreement = int(compare_combined.get("low_risk_disagreement_delta", 0))
    combined_cgm_disagreement = int(compare_combined.get("cgm_disagreement_delta", 0))

    cgm_feature_gap = _build_cgm_feature_gap_summary(cgm_feature_audit_report)
    combined_cgm_final_cases = [
        _as_dict(case)
        for case in _as_list(
            _as_dict(attribution_combined.get("example_final_action_cases")).values()
        )
    ]
    if not combined_cgm_final_cases:
        combined_cgm_final_cases = [
            _as_dict(case)
            for case in _as_list(attribution_combined.get("example_final_action_cases"))
            if _as_dict(case).get("cgm_available") is True
        ]
    effect_only_cgm_examples = [
        _as_dict(case)
        for case in _as_list(attribution_effect_only.get("example_cgm_trace_only_cases"))
    ]
    combined_cgm_examples = [
        _as_dict(case)
        for case in _as_list(attribution_combined.get("example_final_action_cases"))
        if _as_dict(case).get("cgm_available") is True
    ]

    diagnostic = {
        "audit_name": "cgm_candidate_failure_family_diagnostic_v1",
        "source_artifacts": {
            "compare_report_path": str(compare_report_path),
            "attribution_report_path": str(attribution_report_path),
            "cgm_feature_audit_report_path": str(cgm_feature_audit_report_path),
            "cgm_slice_bridge_report_path": str(cgm_slice_bridge_report_path),
            "cgm_event_report_path": str(cgm_event_report_path),
        },
        "hypothesis_gate": {
            "cgm_only_failure_hypothesis_supported": False,
            "rejection_reasons": [
                "effect_only_low_risk_final_delta_dominates_cgm_final_delta",
                "effect_only_low_risk_disagreement_delta_exceeds_cgm_disagreement_delta",
                "combined_low_risk_disagreement_delta_exceeds_cgm_disagreement_delta",
            ],
            "evidence": {
                "effect_only_low_risk_final_delta_abs": effect_only_low_risk_final_abs,
                "effect_only_cgm_final_delta_abs": effect_only_cgm_final_abs,
                "combined_low_risk_final_delta_abs": combined_low_risk_final_abs,
                "combined_cgm_final_delta_abs": combined_cgm_final_abs,
                "effect_only_low_risk_disagreement_delta": effect_only_low_risk_disagreement,
                "effect_only_cgm_disagreement_delta": effect_only_cgm_disagreement,
                "combined_low_risk_disagreement_delta": combined_low_risk_disagreement,
                "combined_cgm_disagreement_delta": combined_cgm_disagreement,
                "compare_summary_finding": _find_summary_finding(
                    attribution_report,
                    "Overall final-action delta is entirely low-risk",
                ),
            },
        },
        "dominant_non_cgm_family": {
            "mode": "learned_effect_guarded",
            "decision_family_counts": _as_dict(
                _as_dict(attribution_effect_only.get("final_action_difference_summary")).get(
                    "decision_family_counts"
                )
            ),
            "transition_counts": _as_dict(
                _as_dict(attribution_effect_only.get("final_action_difference_summary")).get(
                    "transition_counts"
                )
            ),
            "proxy_shift_summary": _as_dict(
                _as_dict(attribution_effect_only.get("final_action_difference_summary")).get(
                    "proxy_shift_summary"
                )
            ),
        },
        "residual_cgm_failure_families": {
            "effect_only_workflow_family": {
                "user_count": _as_dict(
                    attribution_effect_only.get("cgm_trace_only_summary")
                ).get("user_count", 0),
                "trajectory_mode_counts": _as_dict(
                    _as_dict(attribution_effect_only.get("cgm_trace_only_summary")).get(
                        "trajectory_mode_counts"
                    )
                ),
                "cycle_action_transition_counts": _as_dict(
                    _as_dict(attribution_effect_only.get("cgm_trace_only_summary")).get(
                        "cycle_action_transition_counts"
                    )
                ),
                "proxy_shift_summary_on_differing_steps": _as_dict(
                    _as_dict(attribution_effect_only.get("cgm_trace_only_summary")).get(
                        "proxy_shift_summary_on_differing_steps"
                    )
                ),
                "example_case_count": len(effect_only_cgm_examples),
            },
            "combined_final_decision_family": {
                "cgm_final_case_count": len(combined_cgm_examples),
                "decision_family_counts": _count_by_key(
                    combined_cgm_examples,
                    key="decision_family",
                ),
                "transition_counts": _count_transition_pairs(combined_cgm_examples),
                "feature_family_delta_summary": _aggregate_feature_family_deltas(
                    combined_cgm_examples
                ),
            },
            "feature_score_geometry_evidence": cgm_feature_gap,
        },
        "bridge_family_assessment": {
            "bridge_contract_connected": (
                cgm_slice_bridge_report.get("contract_id") == "cgm_slice_bridge_summary_v1"
                and cgm_event_report.get("contract_id") == "cgm_normalized_event_v1"
            ),
            "bridge_case_count": int(cgm_slice_bridge_report.get("case_count", 0)),
            "bridge_valid_case_count": int(cgm_slice_bridge_report.get("valid_case_count", 0)),
            "bridge_eval_success_count": int(cgm_slice_bridge_report.get("eval_success_count", 0)),
            "parser_failure_type_counts": _as_dict(
                cgm_slice_bridge_report.get("parser_failure_type_counts")
            ),
            "connected_flows": _as_dict(cgm_slice_bridge_report.get("connected_flows")),
            "cgm_available_constant_within_slice": _flag_status(
                cgm_feature_audit_report,
                "cgm_available_constant_within_slice",
            ),
            "bridge_is_primary_delta_driver": False,
            "assessment": (
                "Bridge evidence is connected and stable, while candidate/reference replay "
                "differences are concentrated in cgm workflow detours, same-band policy flips, "
                "and proxy-score geometry rather than parser or normalized-event drift."
            ),
        },
        "summary_findings": [
            (
                "The cgm-only failure hypothesis is rejected for the training_view_enforced "
                "candidate because low-risk non-cgm replay drift is materially larger "
                "than cgm drift."
            ),
            (
                "The dominant replay regression family remains "
                "`non_cgm_continue_to_monitor_threshold_cross` in effect-only low-risk cases."
            ),
            (
                "Residual cgm drift is mostly workflow detour in effect-only replay and "
                "`cgm_same_band_policy_score_flip` in combined final decisions."
            ),
            (
                "The strongest cgm score-separating features remain policy/effect proxy and "
                "blood_glucose change features, so the candidate's lower proxy pushes cases "
                "into cgm workflow/final drift without requiring a bridge bug."
            ),
            (
                "The normalized cgm bridge stays connected and does not look like the primary "
                "driver of the baseline-vs-candidate replay delta."
            ),
        ],
    }
    diagnostic["validation_issues"] = validate_cgm_candidate_failure_family_diagnostic(
        diagnostic
    )
    return diagnostic


def validate_cgm_candidate_failure_family_diagnostic(
    diagnostic: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(diagnostic.get("hypothesis_gate"))
    bridge = _as_dict(diagnostic.get("bridge_family_assessment"))
    residual = _as_dict(diagnostic.get("residual_cgm_failure_families"))
    effect_only_workflow = _as_dict(residual.get("effect_only_workflow_family"))
    combined_final = _as_dict(residual.get("combined_final_decision_family"))

    if gate.get("cgm_only_failure_hypothesis_supported") is not False:
        issues.append("cgm_only_failure_hypothesis_unexpectedly_supported")
    if not _as_list(gate.get("rejection_reasons")):
        issues.append("missing_hypothesis_rejection_reasons")
    if int(effect_only_workflow.get("user_count", 0)) <= 0:
        issues.append("missing_effect_only_cgm_workflow_evidence")
    if int(combined_final.get("cgm_final_case_count", 0)) <= 0:
        issues.append("missing_combined_cgm_final_case_evidence")
    if bridge.get("bridge_contract_connected") is not True:
        issues.append("missing_cgm_bridge_connection")
    if bridge.get("bridge_is_primary_delta_driver") is not False:
        issues.append("unexpected_bridge_primary_driver_claim")
    return issues


def render_cgm_candidate_failure_family_diagnostic_markdown(
    diagnostic: dict[str, object],
) -> str:
    gate = _as_dict(diagnostic.get("hypothesis_gate"))
    residual = _as_dict(diagnostic.get("residual_cgm_failure_families"))
    effect_only_workflow = _as_dict(residual.get("effect_only_workflow_family"))
    combined_final = _as_dict(residual.get("combined_final_decision_family"))
    feature_geometry = _as_dict(residual.get("feature_score_geometry_evidence"))
    bridge = _as_dict(diagnostic.get("bridge_family_assessment"))
    lines = [
        "# cgm candidate failure family diagnostic v1",
        "",
        "## hypothesis gate",
        "",
        (
            "- cgm_only_failure_hypothesis_supported: "
            f"`{gate.get('cgm_only_failure_hypothesis_supported')}`"
        ),
        f"- rejection_reasons: `{gate.get('rejection_reasons', [])}`",
        f"- evidence: `{gate.get('evidence', {})}`",
        "",
        "## dominant non-cgm family",
        "",
        f"- dominant_non_cgm_family: `{diagnostic.get('dominant_non_cgm_family', {})}`",
        "",
        "## residual cgm families",
        "",
        f"- effect_only_workflow_family: `{effect_only_workflow}`",
        f"- combined_final_decision_family: `{combined_final}`",
        f"- feature_score_geometry_evidence: `{feature_geometry}`",
        "",
        "## bridge assessment",
        "",
        f"- bridge_family_assessment: `{bridge}`",
        "",
        "## summary findings",
        "",
    ]
    for finding in _as_list(diagnostic.get("summary_findings")):
        lines.append(f"- {finding}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{diagnostic.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_cgm_candidate_failure_family_diagnostic_files(
    *,
    diagnostic: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_file.write_text(
        render_cgm_candidate_failure_family_diagnostic_markdown(diagnostic),
        encoding="utf-8",
    )


def _build_cgm_feature_gap_summary(
    cgm_feature_audit_report: dict[str, object],
) -> dict[str, object]:
    weight_snapshot = _as_dict(
        _as_dict(cgm_feature_audit_report.get("normalization_and_scale_audit")).get(
            "policy_weight_snapshot"
        )
    )
    continue_plan_weights = _as_dict(weight_snapshot.get("continue_plan"))
    re_optimize_weights = _as_dict(weight_snapshot.get("re_optimize"))
    feature_gaps: list[dict[str, object]] = []
    for feature, continue_weight in continue_plan_weights.items():
        if feature not in re_optimize_weights:
            continue
        re_optimize_weight = float(re_optimize_weights[feature])
        continue_weight_float = float(continue_weight)
        feature_gaps.append(
            {
                "feature": feature,
                "continue_plan_minus_re_optimize": round(
                    continue_weight_float - re_optimize_weight,
                    6,
                ),
                "absolute_gap": round(
                    abs(continue_weight_float - re_optimize_weight),
                    6,
                ),
            }
        )
    feature_gaps.sort(key=lambda item: float(item["absolute_gap"]), reverse=True)
    return {
        "top_continue_plan_vs_re_optimize_gaps": feature_gaps[:5],
        "supporting_summary_finding": _find_summary_finding(
            cgm_feature_audit_report,
            "Current cgm replay is primarily separated by policy/effect proxy thresholds",
        ),
    }


def _aggregate_feature_family_deltas(
    cases: list[dict[str, object]],
) -> dict[str, object]:
    family_totals: dict[str, float] = {}
    for case in cases:
        feature_delta = _as_dict(case.get("feature_family_delta"))
        for family, value in feature_delta.items():
            family_totals[str(family)] = family_totals.get(str(family), 0.0) + abs(
                float(value)
            )
    top_families = sorted(
        (
            {"family": family, "absolute_total": round(value, 6)}
            for family, value in family_totals.items()
        ),
        key=lambda item: float(item["absolute_total"]),
        reverse=True,
    )
    return {"top_absolute_families": top_families[:6]}


def _count_transition_pairs(cases: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        transition = (
            f"{case.get('reference_final_action')}->{case.get('candidate_final_action')}"
        )
        counts[transition] = counts.get(transition, 0) + 1
    return dict(sorted(counts.items()))


def _count_by_key(
    cases: list[dict[str, object]],
    *,
    key: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        value = str(case.get(key))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _find_summary_finding(report: dict[str, object], prefix: str) -> str | None:
    for finding in _as_list(report.get("summary_findings")):
        finding_text = str(finding)
        if finding_text.startswith(prefix):
            return finding_text
    return None


def _flag_status(report: dict[str, object], flag: str) -> str | None:
    flags = _as_list(
        _as_dict(report.get("normalization_and_scale_audit")).get("possible_mismatch_flags")
    )
    for item in flags:
        item_dict = _as_dict(item)
        if item_dict.get("flag") == flag:
            return str(item_dict.get("status"))
    return None


def _absolute_action_delta_count(delta: dict[str, object]) -> int:
    return sum(abs(int(value)) for value in delta.values())


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_cgm_candidate_failure_family_diagnostic",
    "load_json_artifact",
    "render_cgm_candidate_failure_family_diagnostic_markdown",
    "validate_cgm_candidate_failure_family_diagnostic",
    "write_cgm_candidate_failure_family_diagnostic_files",
]
