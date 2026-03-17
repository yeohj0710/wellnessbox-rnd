from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "regimen_count"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_regimen_count_fix_scope_decision(
    *,
    regimen_count_diagnostic: dict[str, object],
    regimen_count_diagnostic_path: str | Path,
    regimen_count_counterfactual: dict[str, object],
    regimen_count_counterfactual_path: str | Path,
) -> dict[str, object]:
    feature_target = _as_dict(regimen_count_diagnostic.get("feature_target"))
    feature_summary = _as_dict(regimen_count_diagnostic.get("feature_summary"))
    value_summary = _as_dict(feature_summary.get("value_summary"))
    counterfactual_summary = _as_dict(
        regimen_count_counterfactual.get("counterfactual_summary")
    )
    case_rows = _as_list(regimen_count_counterfactual.get("case_rows"))
    per_case_values = [
        round(float(value), 6)
        for value in _as_list(feature_summary.get("per_case_values"))
    ]

    per_case_value_uniform = len(set(per_case_values)) == 1 if per_case_values else False
    all_cases_cleared = (
        int(counterfactual_summary.get("add_again_clears_shortfall_case_count", 0))
        == int(feature_target.get("observed_case_count", 0))
    )
    all_cases_worsened = (
        int(counterfactual_summary.get("removal_worsens_case_count", 0))
        == int(feature_target.get("observed_case_count", 0))
    )

    decision = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_fix_scope_decision_v1"
        ),
        "source_artifacts": {
            "regimen_count_diagnostic_path": str(regimen_count_diagnostic_path),
            "regimen_count_counterfactual_path": str(regimen_count_counterfactual_path),
        },
        "decision_gate": {
            "trajectory_mode": feature_target.get("trajectory_mode"),
            "margin_bucket": feature_target.get("margin_bucket"),
            "proxy_drop_bucket": feature_target.get("proxy_drop_bucket"),
            "chosen_feature_family": feature_target.get("chosen_feature_family"),
            "chosen_feature": feature_target.get("chosen_feature"),
            "decision": "treat_as_score_side_lever_not_feature_absence",
            "next_loop_type": "replay_only_smallest_bounded_fix",
            "chosen_fix_scope": "score_aggregation_or_competition",
            "observed_case_count": feature_target.get("observed_case_count"),
            "raw_feature_absence_story_supported": False,
            "same_size_counterfactual_clears_shortfall": all_cases_cleared,
            "removal_worsens_all_cases": all_cases_worsened,
            "feature_present_in_all_cases": (
                int(feature_summary.get("feature_present_case_count", 0))
                == int(feature_target.get("observed_case_count", 0))
            ),
            "per_case_value_uniform": per_case_value_uniform,
        },
        "evidence_summary": {
            "feature_before_state": {
                "expected_feature_value": feature_target.get("expected_feature_value"),
                "per_case_values": per_case_values,
                "feature_present_case_count": feature_summary.get(
                    "feature_present_case_count"
                ),
                "sum_case_value": value_summary.get("sum"),
            },
            "counterfactual_read": {
                "current_shortfall_mean": counterfactual_summary.get(
                    "current_shortfall_mean"
                ),
                "regimen_count_value_mean": counterfactual_summary.get(
                    "regimen_count_value_mean"
                ),
                "add_again_clears_shortfall_case_count": counterfactual_summary.get(
                    "add_again_clears_shortfall_case_count"
                ),
                "removal_worsens_case_count": counterfactual_summary.get(
                    "removal_worsens_case_count"
                ),
            },
            "case_row_count": len(case_rows),
        },
        "decision_rationale": [
            (
                "Keep the next pass replay-only and bounded by closing the "
                "`feature_absence` story before reopening wider feature families or training."
            ),
            (
                "Current evidence shows `regimen_count` is already present in all 5 cases "
                "and its same-size counterfactual clears all current shortfalls."
            ),
            (
                "This makes score aggregation or competition the smallest next fix scope "
                "worth testing on the same 5-case slice."
            ),
            (
                "Do not reopen `planned_regimen_count`, the wider family, or training until "
                "the score-side story is checked first."
            ),
        ],
        "deferred_subtargets": [
            {
                "target": "planned_regimen_count",
                "reason": (
                    "second feature inside the same family; use only if score-side leverage "
                    "around `regimen_count` does not move enough"
                ),
            },
            {
                "target": "regimen_status_summary",
                "reason": (
                    "reopen the wider family only if `regimen_count` stops being the most "
                    "useful bounded target"
                ),
            },
        ],
        "required_success_evidence": [
            (
                "A replay artifact, validator, or smallest bounded fix showing the same "
                "5-case slice no longer fails despite `regimen_count` staying present."
            ),
            (
                "Evidence that any improvement came from score aggregation or competition "
                "behavior, not from widening back to a larger slice or retraining."
            ),
        ],
        "summary_findings": [
            (
                "Inference from current artifacts: `regimen_count` looks like a real "
                "protective lever, not a missing feature."
            ),
            (
                "The next bounded replay-only pass should test score-side aggregation or "
                "competition around `regimen_count` on the same 5-case slice."
            ),
            "Do not reopen training or wider family tuning for this pass.",
        ],
    }
    decision["validation_issues"] = validate_regimen_count_fix_scope_decision(decision)
    return decision


def validate_regimen_count_fix_scope_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    feature_before_state = _as_dict(evidence.get("feature_before_state"))
    counterfactual_read = _as_dict(evidence.get("counterfactual_read"))

    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_feature_family") != "regimen_status_summary":
        issues.append("unexpected_feature_family")
    if gate.get("chosen_feature") != TARGET_FEATURE:
        issues.append("unexpected_feature_target")
    if gate.get("decision") != "treat_as_score_side_lever_not_feature_absence":
        issues.append("unexpected_fix_scope_decision")
    if gate.get("chosen_fix_scope") != "score_aggregation_or_competition":
        issues.append("unexpected_fix_scope")
    if bool(gate.get("raw_feature_absence_story_supported")):
        issues.append("feature_absence_story_should_be_closed")
    if not bool(gate.get("feature_present_in_all_cases")):
        issues.append("feature_not_present_in_all_cases")
    if not bool(gate.get("same_size_counterfactual_clears_shortfall")):
        issues.append("counterfactual_does_not_clear_all_cases")
    if not bool(gate.get("removal_worsens_all_cases")):
        issues.append("removal_does_not_worsen_all_cases")
    if not bool(gate.get("per_case_value_uniform")):
        issues.append("feature_values_not_uniform")
    if int(evidence.get("case_row_count", 0)) != int(gate.get("observed_case_count", 0)):
        issues.append("case_row_count_mismatch")
    if round(float(feature_before_state.get("sum_case_value", 0.0)), 6) != 0.12365:
        issues.append("unexpected_sum_case_value")
    if int(counterfactual_read.get("removal_worsens_case_count", 0)) != int(
        gate.get("observed_case_count", 0)
    ):
        issues.append("counterfactual_read_removal_mismatch")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_regimen_count_fix_scope_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "regimen-count fix-scope decision v1"
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


def write_regimen_count_fix_scope_decision_files(
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
        render_regimen_count_fix_scope_decision_markdown(decision),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_regimen_count_fix_scope_decision",
    "load_json_artifact",
    "render_regimen_count_fix_scope_decision_markdown",
    "validate_regimen_count_fix_scope_decision",
    "write_regimen_count_fix_scope_decision_files",
]
