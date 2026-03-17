from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "trajectory_step"
TARGET_MODE = "fixed_uniform_offset"
TARGET_PROBE_FRACTION = 0.5


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_half_offset_fix_scope_decision(
    *,
    mode_decision: dict[str, object],
    mode_decision_path: str | Path,
    probe_decision: dict[str, object],
    probe_decision_path: str | Path,
    half_offset_counterfactual: dict[str, object],
    half_offset_counterfactual_path: str | Path,
) -> dict[str, object]:
    mode_gate = _as_dict(mode_decision.get("decision_gate"))
    probe_gate = _as_dict(probe_decision.get("decision_gate"))
    summary = _as_dict(half_offset_counterfactual.get("counterfactual_summary"))
    case_rows = [_as_dict(row) for row in _as_list(half_offset_counterfactual.get("case_rows"))]
    residuals = [
        round(float(row.get("residual_clearance", 0.0)), 6)
        for row in case_rows
    ]

    decision = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_fix_scope_decision_v1"
        ),
        "source_artifacts": {
            "mode_decision_path": str(mode_decision_path),
            "probe_decision_path": str(probe_decision_path),
            "half_offset_counterfactual_path": str(half_offset_counterfactual_path),
        },
        "decision_gate": {
            "trajectory_mode": probe_gate.get("trajectory_mode"),
            "margin_bucket": probe_gate.get("margin_bucket"),
            "proxy_drop_bucket": probe_gate.get("proxy_drop_bucket"),
            "chosen_first_opposing_feature": probe_gate.get(
                "chosen_first_opposing_feature"
            ),
            "decision": "treat_as_direct_half_offset_local_handling_ready",
            "next_loop_type": "replay_only_smallest_bounded_fix",
            "chosen_fix_scope": "trajectory_step_half_offset_local_score_handling",
            "chosen_local_handling_mode": probe_gate.get("chosen_local_handling_mode"),
            "chosen_probe_fraction": probe_gate.get("chosen_probe_fraction"),
            "chosen_probe_offset_abs_value": probe_gate.get(
                "chosen_probe_offset_abs_value"
            ),
            "observed_case_count": len(case_rows),
            "all_cases_cleared": summary.get("all_cases_cleared"),
            "min_residual_clearance_positive": (
                float(summary.get("min_residual_clearance", 0.0)) > 0.0
            ),
            "cycle_conditioned_mode_needed_now": mode_gate.get(
                "cycle_conditioned_mode_needed_now"
            ),
            "second_feature_widening_needed_now": mode_gate.get(
                "second_feature_widening_needed_now"
            ),
        },
        "evidence_summary": {
            "mode_anchor": {
                "chosen_fix_scope": mode_gate.get("chosen_fix_scope"),
                "chosen_local_handling_mode": mode_gate.get(
                    "chosen_local_handling_mode"
                ),
                "trajectory_step_value_uniform": mode_gate.get(
                    "trajectory_step_value_uniform"
                ),
                "final_cycle_index_uniform": mode_gate.get("final_cycle_index_uniform"),
            },
            "probe_anchor": {
                "chosen_probe_fraction": probe_gate.get("chosen_probe_fraction"),
                "chosen_probe_offset_abs_value": probe_gate.get(
                    "chosen_probe_offset_abs_value"
                ),
                "chosen_probe_clears_all_cases": probe_gate.get(
                    "chosen_probe_clears_all_cases"
                ),
            },
            "counterfactual_read": {
                "cleared_case_count": summary.get("cleared_case_count"),
                "all_cases_cleared": summary.get("all_cases_cleared"),
                "mean_residual_clearance": summary.get("mean_residual_clearance"),
                "min_residual_clearance": summary.get("min_residual_clearance"),
                "max_residual_clearance": summary.get("max_residual_clearance"),
                "residual_clearance_vector": residuals,
            },
        },
        "decision_rationale": [
            (
                "The bounded half-offset path already clears all 5 cases, so the next pass "
                "can stay on direct half-offset local handling instead of widening scope."
            ),
            (
                "The current fixed-uniform mode remains sufficient because cycle-conditioned "
                "handling is still unnecessary on the present slice."
            ),
            (
                "This keeps the next replay-only loop on one smallest fix scope: "
                "`trajectory_step` half-offset local score handling."
            ),
        ],
        "deferred_paths": [
            {
                "path": "cycle_conditioned_offset",
                "reason": (
                    "defer until the current half-offset local path stops being sufficient"
                ),
            },
            {
                "path": "dose::l_theanine",
                "reason": (
                    "defer second-feature widening until the bounded trajectory_step "
                    "half-offset path no longer clears the same 5-case slice"
                ),
            },
        ],
        "summary_findings": [
            (
                "Current artifacts support treating the `0.5` trajectory-step offset as the "
                "direct next local-handling scope, not just a feasibility hint."
            ),
            (
                "All 5 target cases still clear with positive residual room under the chosen "
                "half-offset probe."
            ),
            "Do not widen to cycle-conditioned handling or a second feature yet.",
        ],
    }
    decision["validation_issues"] = validate_trajectory_step_half_offset_fix_scope_decision(
        decision
    )
    return decision


def validate_trajectory_step_half_offset_fix_scope_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    mode_anchor = _as_dict(evidence.get("mode_anchor"))
    probe_anchor = _as_dict(evidence.get("probe_anchor"))
    counterfactual_read = _as_dict(evidence.get("counterfactual_read"))

    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_first_opposing_feature") != TARGET_FEATURE:
        issues.append("unexpected_first_opposing_feature")
    if gate.get("decision") != "treat_as_direct_half_offset_local_handling_ready":
        issues.append("unexpected_fix_scope_decision")
    if gate.get("chosen_fix_scope") != "trajectory_step_half_offset_local_score_handling":
        issues.append("unexpected_fix_scope")
    if gate.get("chosen_local_handling_mode") != TARGET_MODE:
        issues.append("unexpected_local_handling_mode")
    if gate.get("chosen_probe_fraction") != TARGET_PROBE_FRACTION:
        issues.append("unexpected_probe_fraction")
    if not bool(gate.get("all_cases_cleared")):
        issues.append("not_all_cases_cleared")
    if not bool(gate.get("min_residual_clearance_positive")):
        issues.append("min_residual_not_positive")
    if bool(gate.get("cycle_conditioned_mode_needed_now")):
        issues.append("unexpected_cycle_conditioning")
    if bool(gate.get("second_feature_widening_needed_now")):
        issues.append("unexpected_second_feature_widening")
    if mode_anchor.get("chosen_fix_scope") != "trajectory_step_local_score_handling":
        issues.append("unexpected_mode_anchor_fix_scope")
    if not bool(mode_anchor.get("trajectory_step_value_uniform")):
        issues.append("trajectory_step_value_not_uniform")
    if not bool(mode_anchor.get("final_cycle_index_uniform")):
        issues.append("final_cycle_index_not_uniform")
    if probe_anchor.get("chosen_probe_fraction") != TARGET_PROBE_FRACTION:
        issues.append("probe_anchor_fraction_mismatch")
    if not bool(probe_anchor.get("chosen_probe_clears_all_cases")):
        issues.append("probe_anchor_not_clearing")
    if int(counterfactual_read.get("cleared_case_count", 0)) != int(
        gate.get("observed_case_count", 0)
    ):
        issues.append("cleared_case_count_mismatch")
    if float(counterfactual_read.get("min_residual_clearance", 0.0)) <= 0.0:
        issues.append("counterfactual_min_residual_not_positive")
    if len(_as_list(counterfactual_read.get("residual_clearance_vector"))) != int(
        gate.get("observed_case_count", 0)
    ):
        issues.append("residual_vector_size_mismatch")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_half_offset_fix_scope_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step half-offset fix-scope decision v1"
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
    lines.extend(["", "## deferred paths", ""])
    for item in _as_list(decision.get("deferred_paths")):
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


def write_trajectory_step_half_offset_fix_scope_decision_files(
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
        render_trajectory_step_half_offset_fix_scope_decision_markdown(decision),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_half_offset_fix_scope_decision",
    "load_json_artifact",
    "render_trajectory_step_half_offset_fix_scope_decision_markdown",
    "validate_trajectory_step_half_offset_fix_scope_decision",
    "write_trajectory_step_half_offset_fix_scope_decision_files",
]
