from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "trajectory_step"
DEFERRED_SECOND_FEATURE = "dose::l_theanine"
TARGET_CYCLE_INDEX = "4"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_local_handling_mode_decision(
    *,
    readiness: dict[str, object],
    readiness_path: str | Path,
    fix_scope_decision: dict[str, object],
    fix_scope_decision_path: str | Path,
    trajectory_step_counterfactual: dict[str, object],
    trajectory_step_counterfactual_path: str | Path,
    slice_diagnostic: dict[str, object],
    slice_diagnostic_path: str | Path,
) -> dict[str, object]:
    readiness_gate = _as_dict(readiness.get("readiness_gate"))
    readiness_evidence = _as_dict(readiness.get("evidence_summary"))
    fix_scope_gate = _as_dict(fix_scope_decision.get("decision_gate"))
    counterfactual_summary = _as_dict(
        trajectory_step_counterfactual.get("counterfactual_summary")
    )
    case_rows = _as_list(trajectory_step_counterfactual.get("case_rows"))
    workflow_summary = _as_dict(slice_diagnostic.get("workflow_summary"))
    final_cycle_index_counts = _as_dict(workflow_summary.get("final_cycle_index_counts"))

    per_case_values = [
        round(float(_as_dict(row).get("trajectory_step_value", 0.0)), 6)
        for row in case_rows
    ]
    unique_values = sorted(set(per_case_values))
    value_uniform = len(unique_values) == 1 if per_case_values else False
    observed_case_count = int(readiness_gate.get("observed_case_count", 0))
    final_cycle_uniform = final_cycle_index_counts == {TARGET_CYCLE_INDEX: observed_case_count}
    shortfall_mean = round(
        float(counterfactual_summary.get("current_shortfall_mean", 0.0)), 6
    )
    feature_abs_mean = round(
        float(counterfactual_summary.get("trajectory_step_abs_value_mean", 0.0)), 6
    )
    chosen_mode = "fixed_uniform_offset"

    decision = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_mode_decision_v1"
        ),
        "source_artifacts": {
            "readiness_path": str(readiness_path),
            "fix_scope_decision_path": str(fix_scope_decision_path),
            "trajectory_step_counterfactual_path": str(
                trajectory_step_counterfactual_path
            ),
            "slice_diagnostic_path": str(slice_diagnostic_path),
        },
        "decision_gate": {
            "trajectory_mode": readiness_gate.get("trajectory_mode"),
            "margin_bucket": readiness_gate.get("margin_bucket"),
            "proxy_drop_bucket": readiness_gate.get("proxy_drop_bucket"),
            "chosen_first_opposing_feature": readiness_gate.get(
                "chosen_first_opposing_feature"
            ),
            "decision": "fixed_uniform_offset_local_handling_first",
            "chosen_fix_scope": readiness_gate.get("chosen_fix_scope"),
            "chosen_local_handling_mode": chosen_mode,
            "observed_case_count": observed_case_count,
            "single_feature_path_supported": readiness_gate.get(
                "single_feature_path_supported"
            ),
            "trajectory_step_value_uniform": value_uniform,
            "final_cycle_index_uniform": final_cycle_uniform,
            "cycle_conditioned_mode_needed_now": False,
            "second_feature_widening_needed_now": False,
        },
        "evidence_summary": {
            "uniformity_digest": {
                "trajectory_step_values": per_case_values,
                "unique_trajectory_step_values": unique_values,
                "trajectory_step_value_uniform": value_uniform,
                "final_cycle_index_counts": final_cycle_index_counts,
                "final_cycle_index_uniform": final_cycle_uniform,
            },
            "coverage_digest": {
                "current_shortfall_mean": shortfall_mean,
                "trajectory_step_abs_value_mean": feature_abs_mean,
                "trajectory_step_covers_shortfall_mean": _as_dict(
                    readiness_evidence.get("shortfall_digest")
                ).get("trajectory_step_covers_shortfall_mean"),
                "neutralize_clears_all_cases": fix_scope_gate.get(
                    "neutralize_clears_all_cases"
                ),
            },
            "defer_digest": {
                "deferred_second_opposing_feature": readiness_gate.get(
                    "deferred_second_opposing_feature"
                ),
                "widen_to_second_feature_needed_now": readiness_gate.get(
                    "widen_to_second_feature_needed_now"
                ),
                "cycle_conditioned_mode_needed_now": False,
            },
        },
        "decision_rationale": [
            (
                "All 5 target cases share the same `trajectory_step` value and the same "
                "final cycle index, so the first bounded local-handling mode can stay fixed."
            ),
            (
                "The current trajectory-step counterfactual already clears the mean shortfall "
                "without widening to the deferred second opposing feature."
            ),
            (
                "This keeps the next replay-only pass on one smallest mode: fixed uniform "
                "offset handling for `trajectory_step`."
            ),
        ],
        "deferred_modes": [
            {
                "mode": "cycle_conditioned_offset",
                "reason": (
                    "defer until the fixed uniform mode fails or cycle heterogeneity appears"
                ),
            },
            {
                "mode": "second_feature_widening",
                "target": DEFERRED_SECOND_FEATURE,
                "reason": (
                    "defer until the direct trajectory_step local mode is no longer sufficient"
                ),
            },
        ],
        "summary_findings": [
            (
                "`trajectory_step` local handling should stay on a fixed uniform offset first "
                "because all 5 cases share the same feature value `-0.063114`."
            ),
            (
                "All 5 cases also sit at final cycle index `4`, so cycle-conditioned local "
                "handling is not yet justified."
            ),
            (
                "Do not widen to `dose::l_theanine` or a more adaptive mode unless the fixed "
                "uniform path fails to move the same slice."
            ),
        ],
    }
    decision["validation_issues"] = validate_trajectory_step_local_handling_mode_decision(
        decision
    )
    return decision


def validate_trajectory_step_local_handling_mode_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    uniformity_digest = _as_dict(evidence.get("uniformity_digest"))
    coverage_digest = _as_dict(evidence.get("coverage_digest"))
    defer_digest = _as_dict(evidence.get("defer_digest"))

    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_first_opposing_feature") != TARGET_FEATURE:
        issues.append("unexpected_first_opposing_feature")
    if gate.get("decision") != "fixed_uniform_offset_local_handling_first":
        issues.append("unexpected_local_handling_mode_decision")
    if gate.get("chosen_fix_scope") != "trajectory_step_local_score_handling":
        issues.append("unexpected_fix_scope")
    if gate.get("chosen_local_handling_mode") != "fixed_uniform_offset":
        issues.append("unexpected_local_handling_mode")
    if not bool(gate.get("single_feature_path_supported")):
        issues.append("single_feature_path_not_supported")
    if not bool(gate.get("trajectory_step_value_uniform")):
        issues.append("trajectory_step_value_not_uniform")
    if not bool(gate.get("final_cycle_index_uniform")):
        issues.append("final_cycle_index_not_uniform")
    if bool(gate.get("cycle_conditioned_mode_needed_now")):
        issues.append("unexpected_cycle_conditioning")
    if bool(gate.get("second_feature_widening_needed_now")):
        issues.append("unexpected_second_feature_widening")
    if uniformity_digest.get("final_cycle_index_counts") != {
        TARGET_CYCLE_INDEX: gate.get("observed_case_count")
    }:
        issues.append("final_cycle_count_mismatch")
    if not bool(coverage_digest.get("trajectory_step_covers_shortfall_mean")):
        issues.append("trajectory_step_does_not_cover_shortfall_mean")
    if not bool(coverage_digest.get("neutralize_clears_all_cases")):
        issues.append("neutralize_does_not_clear_all_cases")
    if defer_digest.get("deferred_second_opposing_feature") != DEFERRED_SECOND_FEATURE:
        issues.append("unexpected_deferred_second_feature")
    if bool(defer_digest.get("cycle_conditioned_mode_needed_now")):
        issues.append("defer_digest_unexpected_cycle_conditioning")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_local_handling_mode_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step local-handling mode decision v1"
        ),
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
    for item in _as_list(decision.get("decision_rationale")):
        lines.append(f"- {item}")
    lines.extend(["", "## deferred modes", ""])
    for item in _as_list(decision.get("deferred_modes")):
        lines.append(f"- {item}")
    lines.extend(["", "## summary findings", ""])
    for item in _as_list(decision.get("summary_findings")):
        lines.append(f"- {item}")
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


def write_trajectory_step_local_handling_mode_decision_files(
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
        render_trajectory_step_local_handling_mode_decision_markdown(decision),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_local_handling_mode_decision",
    "load_json_artifact",
    "render_trajectory_step_local_handling_mode_decision_markdown",
    "validate_trajectory_step_local_handling_mode_decision",
    "write_trajectory_step_local_handling_mode_decision_files",
]
