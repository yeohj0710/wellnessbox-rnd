from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "trajectory_step"
DEFERRED_SECOND_FEATURE = "dose::l_theanine"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_fix_scope_decision(
    *,
    competition_decision: dict[str, object],
    competition_decision_path: str | Path,
    trajectory_step_counterfactual: dict[str, object],
    trajectory_step_counterfactual_path: str | Path,
) -> dict[str, object]:
    competition_gate = _as_dict(competition_decision.get("decision_gate"))
    counterfactual_target = _as_dict(trajectory_step_counterfactual.get("target"))
    counterfactual_summary = _as_dict(
        trajectory_step_counterfactual.get("counterfactual_summary")
    )
    case_rows = _as_list(trajectory_step_counterfactual.get("case_rows"))
    per_case_values = [
        round(float(_as_dict(row).get("trajectory_step_value", 0.0)), 6)
        for row in case_rows
    ]
    abs_values = [
        round(float(_as_dict(row).get("trajectory_step_abs_value", 0.0)), 6)
        for row in case_rows
    ]
    per_case_value_uniform = len(set(per_case_values)) == 1 if per_case_values else False
    abs_value_uniform = len(set(abs_values)) == 1 if abs_values else False

    decision = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fix_scope_decision_v1"
        ),
        "source_artifacts": {
            "competition_decision_path": str(competition_decision_path),
            "trajectory_step_counterfactual_path": str(trajectory_step_counterfactual_path),
        },
        "decision_gate": {
            "trajectory_mode": competition_gate.get("trajectory_mode"),
            "margin_bucket": competition_gate.get("margin_bucket"),
            "proxy_drop_bucket": competition_gate.get("proxy_drop_bucket"),
            "chosen_feature_family": competition_gate.get("chosen_feature_family"),
            "chosen_feature": competition_gate.get("chosen_feature"),
            "chosen_first_opposing_feature": competition_gate.get(
                "chosen_first_opposing_feature"
            ),
            "decision": "treat_as_direct_opposing_lever_not_multifeature_mix",
            "next_loop_type": "replay_only_smallest_bounded_fix",
            "chosen_fix_scope": "trajectory_step_local_score_handling",
            "observed_case_count": counterfactual_target.get("observed_case_count"),
            "neutralize_clears_all_cases": (
                int(
                    counterfactual_summary.get(
                        "neutralize_clears_shortfall_case_count", 0
                    )
                )
                == int(counterfactual_target.get("observed_case_count", 0))
            ),
            "extra_penalty_worsens_all_cases": (
                int(counterfactual_summary.get("extra_penalty_worsens_case_count", 0))
                == int(counterfactual_target.get("observed_case_count", 0))
            ),
            "per_case_value_uniform": per_case_value_uniform,
            "per_case_abs_value_uniform": abs_value_uniform,
            "widen_to_multifeature_mix_supported": False,
        },
        "evidence_summary": {
            "competition_anchor": {
                "chosen_first_opposing_feature": competition_gate.get(
                    "chosen_first_opposing_feature"
                ),
                "chosen_first_opposing_feature_family": competition_gate.get(
                    "chosen_first_opposing_feature_family"
                ),
                "chosen_first_opposing_feature_value": competition_gate.get(
                    "chosen_first_opposing_feature_value"
                ),
            },
            "counterfactual_read": {
                "current_shortfall_mean": counterfactual_summary.get(
                    "current_shortfall_mean"
                ),
                "trajectory_step_abs_value_mean": counterfactual_summary.get(
                    "trajectory_step_abs_value_mean"
                ),
                "neutralize_clears_shortfall_case_count": counterfactual_summary.get(
                    "neutralize_clears_shortfall_case_count"
                ),
                "extra_penalty_worsens_case_count": counterfactual_summary.get(
                    "extra_penalty_worsens_case_count"
                ),
            },
            "per_case_surface": {
                "trajectory_step_values": per_case_values,
                "trajectory_step_abs_values": abs_values,
                "case_row_count": len(case_rows),
            },
        },
        "decision_rationale": [
            (
                "Keep the next pass replay-only and bounded by closing the "
                "`multifeature_mix` story before widening beyond `trajectory_step`."
            ),
            (
                "`trajectory_step` already clears the shortfall in all 5 cases under a "
                "neutralize counterfactual and worsens all 5 under extra penalty."
            ),
            (
                "This makes direct trajectory-step-local score handling the smallest next "
                "fix scope worth testing."
            ),
            (
                "Do not reopen `dose::l_theanine`, wider multifeature competition, or "
                "training until the bounded trajectory-step path is checked first."
            ),
        ],
        "deferred_subtargets": [
            {
                "target": DEFERRED_SECOND_FEATURE,
                "reason": (
                    "second opposing non-intercept feature; use only if the bounded "
                    "`trajectory_step` path does not move enough"
                ),
            },
            {
                "target": "__intercept__",
                "reason": (
                    "global opposing anchor; keep deferred until the bounded local feature "
                    "path is checked first"
                ),
            },
        ],
        "required_success_evidence": [
            (
                "A replay artifact, validator, or smallest bounded fix showing the same "
                "5-case slice no longer fails while `trajectory_step` handling changes."
            ),
            (
                "Evidence that any movement came from trajectory-step-local score handling, "
                "not widening to multifeature compensation or retraining."
            ),
        ],
        "summary_findings": [
            (
                "Inference from current artifacts: `trajectory_step` now looks like a direct "
                "opposing lever, not just one member of a wider multifeature mix."
            ),
            (
                "The next bounded replay-only pass should test trajectory-step-local score "
                "handling on the same 5-case slice."
            ),
            "Do not reopen training or wider multifeature tuning for this pass.",
        ],
    }
    decision["validation_issues"] = validate_trajectory_step_fix_scope_decision(decision)
    return decision


def validate_trajectory_step_fix_scope_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    per_case_surface = _as_dict(evidence.get("per_case_surface"))
    counterfactual_read = _as_dict(evidence.get("counterfactual_read"))

    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_feature_family") != "regimen_status_summary":
        issues.append("unexpected_feature_family")
    if gate.get("chosen_feature") != "regimen_count":
        issues.append("unexpected_chosen_feature")
    if gate.get("chosen_first_opposing_feature") != TARGET_FEATURE:
        issues.append("unexpected_first_opposing_feature")
    if gate.get("decision") != "treat_as_direct_opposing_lever_not_multifeature_mix":
        issues.append("unexpected_fix_scope_decision")
    if gate.get("chosen_fix_scope") != "trajectory_step_local_score_handling":
        issues.append("unexpected_fix_scope")
    if bool(gate.get("widen_to_multifeature_mix_supported")):
        issues.append("multifeature_mix_story_should_be_closed")
    if not bool(gate.get("neutralize_clears_all_cases")):
        issues.append("neutralize_does_not_clear_all_cases")
    if not bool(gate.get("extra_penalty_worsens_all_cases")):
        issues.append("extra_penalty_does_not_worsen_all_cases")
    if not bool(gate.get("per_case_value_uniform")):
        issues.append("trajectory_step_values_not_uniform")
    if not bool(gate.get("per_case_abs_value_uniform")):
        issues.append("trajectory_step_abs_values_not_uniform")
    if int(per_case_surface.get("case_row_count", 0)) != int(gate.get("observed_case_count", 0)):
        issues.append("case_row_count_mismatch")
    if int(counterfactual_read.get("neutralize_clears_shortfall_case_count", 0)) != int(
        gate.get("observed_case_count", 0)
    ):
        issues.append("counterfactual_neutralize_mismatch")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_fix_scope_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step fix-scope decision v1"
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
    lines.extend(["", "## deferred subtargets", ""])
    for item in _as_list(decision.get("deferred_subtargets")):
        lines.append(f"- {item}")
    lines.extend(["", "## required success evidence", ""])
    for item in _as_list(decision.get("required_success_evidence")):
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


def write_trajectory_step_fix_scope_decision_files(
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
        render_trajectory_step_fix_scope_decision_markdown(decision),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_fix_scope_decision",
    "load_json_artifact",
    "render_trajectory_step_fix_scope_decision_markdown",
    "validate_trajectory_step_fix_scope_decision",
    "write_trajectory_step_fix_scope_decision_files",
]
