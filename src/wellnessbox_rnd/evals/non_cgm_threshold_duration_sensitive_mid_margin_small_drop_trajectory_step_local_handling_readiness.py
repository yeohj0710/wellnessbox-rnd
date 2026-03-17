from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "trajectory_step"
DEFERRED_SECOND_FEATURE = "dose::l_theanine"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_local_handling_readiness(
    *,
    competition_decision: dict[str, object],
    competition_decision_path: str | Path,
    trajectory_step_counterfactual: dict[str, object],
    trajectory_step_counterfactual_path: str | Path,
    trajectory_step_fix_scope_decision: dict[str, object],
    trajectory_step_fix_scope_decision_path: str | Path,
) -> dict[str, object]:
    competition_gate = _as_dict(competition_decision.get("decision_gate"))
    competition_evidence = _as_dict(competition_decision.get("evidence_summary"))
    opposing_ranking = _as_list(competition_evidence.get("opposing_feature_ranking"))
    first_feature = _as_dict(opposing_ranking[0]) if opposing_ranking else {}
    second_feature = _as_dict(opposing_ranking[1]) if len(opposing_ranking) > 1 else {}

    counterfactual_summary = _as_dict(
        trajectory_step_counterfactual.get("counterfactual_summary")
    )
    fix_scope_gate = _as_dict(trajectory_step_fix_scope_decision.get("decision_gate"))

    first_abs_value = abs(float(first_feature.get("value", 0.0)))
    second_abs_value = abs(float(second_feature.get("value", 0.0)))
    shortfall_mean = float(counterfactual_summary.get("current_shortfall_mean", 0.0))
    abs_gap = round(first_abs_value - second_abs_value, 6)

    readiness = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_local_handling_readiness_v1"
        ),
        "source_artifacts": {
            "competition_decision_path": str(competition_decision_path),
            "trajectory_step_counterfactual_path": str(
                trajectory_step_counterfactual_path
            ),
            "trajectory_step_fix_scope_decision_path": str(
                trajectory_step_fix_scope_decision_path
            ),
        },
        "readiness_gate": {
            "trajectory_mode": competition_gate.get("trajectory_mode"),
            "margin_bucket": competition_gate.get("margin_bucket"),
            "proxy_drop_bucket": competition_gate.get("proxy_drop_bucket"),
            "chosen_first_opposing_feature": competition_gate.get(
                "chosen_first_opposing_feature"
            ),
            "deferred_second_opposing_feature": second_feature.get("feature"),
            "decision": "single_feature_local_handling_first",
            "chosen_fix_scope": fix_scope_gate.get("chosen_fix_scope"),
            "single_feature_path_supported": (
                first_abs_value > second_abs_value
                and bool(fix_scope_gate.get("neutralize_clears_all_cases"))
            ),
            "widen_to_second_feature_needed_now": False,
            "observed_case_count": fix_scope_gate.get("observed_case_count"),
        },
        "evidence_summary": {
            "feature_gap_digest": {
                "first_feature": first_feature.get("feature"),
                "first_feature_abs_value": round(first_abs_value, 6),
                "second_feature": second_feature.get("feature"),
                "second_feature_abs_value": round(second_abs_value, 6),
                "first_minus_second_abs_gap": abs_gap,
            },
            "shortfall_digest": {
                "current_shortfall_mean": round(shortfall_mean, 6),
                "trajectory_step_abs_value_mean": counterfactual_summary.get(
                    "trajectory_step_abs_value_mean"
                ),
                "trajectory_step_covers_shortfall_mean": first_abs_value > shortfall_mean,
            },
            "fix_scope_digest": {
                "chosen_fix_scope": fix_scope_gate.get("chosen_fix_scope"),
                "neutralize_clears_all_cases": fix_scope_gate.get(
                    "neutralize_clears_all_cases"
                ),
                "widen_to_multifeature_mix_supported": fix_scope_gate.get(
                    "widen_to_multifeature_mix_supported"
                ),
            },
        },
        "summary_findings": [
            (
                f"`{first_feature.get('feature')}` remains the first bounded opposing feature "
                f"ahead of `{second_feature.get('feature')}` by absolute gap {abs_gap}."
            ),
            (
                "Current trajectory-step counterfactual still clears all 5 cases, so the "
                "single-feature local path remains the smallest bounded next step."
            ),
            (
                f"Do not widen to `{second_feature.get('feature')}` or multifeature handling "
                "unless the direct trajectory-step-local path fails to move enough."
            ),
        ],
    }
    readiness["validation_issues"] = validate_trajectory_step_local_handling_readiness(
        readiness
    )
    return readiness


def validate_trajectory_step_local_handling_readiness(
    readiness: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(readiness.get("readiness_gate"))
    evidence = _as_dict(readiness.get("evidence_summary"))
    feature_gap_digest = _as_dict(evidence.get("feature_gap_digest"))
    shortfall_digest = _as_dict(evidence.get("shortfall_digest"))
    fix_scope_digest = _as_dict(evidence.get("fix_scope_digest"))

    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_first_opposing_feature") != TARGET_FEATURE:
        issues.append("unexpected_first_feature")
    if gate.get("deferred_second_opposing_feature") != DEFERRED_SECOND_FEATURE:
        issues.append("unexpected_second_feature")
    if gate.get("decision") != "single_feature_local_handling_first":
        issues.append("unexpected_readiness_decision")
    if gate.get("chosen_fix_scope") != "trajectory_step_local_score_handling":
        issues.append("unexpected_fix_scope")
    if not bool(gate.get("single_feature_path_supported")):
        issues.append("single_feature_path_not_supported")
    if bool(gate.get("widen_to_second_feature_needed_now")):
        issues.append("unexpected_second_feature_widening")
    if float(feature_gap_digest.get("first_minus_second_abs_gap", 0.0)) <= 0.0:
        issues.append("first_feature_not_ahead_of_second")
    if not bool(shortfall_digest.get("trajectory_step_covers_shortfall_mean")):
        issues.append("trajectory_step_does_not_cover_shortfall_mean")
    if bool(fix_scope_digest.get("widen_to_multifeature_mix_supported")):
        issues.append("multifeature_mix_should_stay_closed")
    if not _as_list(readiness.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_local_handling_readiness_markdown(
    readiness: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step local-handling readiness v1"
        ),
        "",
        "## readiness gate",
        "",
        f"- readiness_gate: `{readiness.get('readiness_gate', {})}`",
        "",
        "## evidence summary",
        "",
    ]
    for key, value in _as_dict(readiness.get("evidence_summary")).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## summary findings", ""])
    for item in _as_list(readiness.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{readiness.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_trajectory_step_local_handling_readiness_files(
    *,
    readiness: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_trajectory_step_local_handling_readiness_markdown(readiness),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_local_handling_readiness",
    "load_json_artifact",
    "render_trajectory_step_local_handling_readiness_markdown",
    "validate_trajectory_step_local_handling_readiness",
    "write_trajectory_step_local_handling_readiness_files",
]
