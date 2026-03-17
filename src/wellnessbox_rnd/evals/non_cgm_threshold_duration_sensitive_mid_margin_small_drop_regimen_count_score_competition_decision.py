from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "regimen_count"
EXPECTED_FIRST_OPPOSING_FEATURE = "trajectory_step"
EXPECTED_SECOND_OPPOSING_FEATURE = "dose::l_theanine"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_regimen_count_score_competition_decision(
    *,
    slice_diagnostic: dict[str, object],
    slice_diagnostic_path: str | Path,
    fix_scope_decision: dict[str, object],
    fix_scope_decision_path: str | Path,
) -> dict[str, object]:
    slice_target = _as_dict(slice_diagnostic.get("slice_target"))
    feature_summary = _as_dict(slice_diagnostic.get("feature_summary"))
    interpretation = _as_dict(slice_diagnostic.get("interpretation"))
    decision_gate = _as_dict(fix_scope_decision.get("decision_gate"))

    top_negative_features = _as_list(feature_summary.get("top_negative_features"))
    non_intercept_negative_features = [
        feature
        for feature in top_negative_features
        if _as_dict(feature).get("feature") != "__intercept__"
    ]
    first_feature = (
        _as_dict(non_intercept_negative_features[0])
        if non_intercept_negative_features
        else {}
    )
    second_feature = (
        _as_dict(non_intercept_negative_features[1])
        if len(non_intercept_negative_features) > 1
        else {}
    )
    shortfall_mean = float(
        _as_dict(_as_dict(slice_diagnostic.get("case_summary")).get("candidate_monitor_shortfall_summary")).get(
            "mean",
            0.0,
        )
    )
    first_feature_abs_value = abs(float(first_feature.get("value", 0.0)))

    decision = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_count_score_competition_decision_v1"
        ),
        "source_artifacts": {
            "slice_diagnostic_path": str(slice_diagnostic_path),
            "fix_scope_decision_path": str(fix_scope_decision_path),
        },
        "decision_gate": {
            "trajectory_mode": slice_target.get("trajectory_mode"),
            "margin_bucket": slice_target.get("margin_bucket"),
            "proxy_drop_bucket": slice_target.get("proxy_drop_bucket"),
            "chosen_feature_family": decision_gate.get("chosen_feature_family"),
            "chosen_feature": decision_gate.get("chosen_feature"),
            "fix_scope": decision_gate.get("chosen_fix_scope"),
            "decision": "focus_largest_non_intercept_opposing_feature_first",
            "chosen_first_opposing_feature": first_feature.get("feature"),
            "chosen_first_opposing_feature_family": first_feature.get("family"),
            "chosen_first_opposing_feature_value": first_feature.get("value"),
            "observed_case_count": slice_target.get("observed_case_count"),
            "intercept_left_deferred": True,
        },
        "evidence_summary": {
            "current_anchor": {
                "dominant_feature": interpretation.get("dominant_feature"),
                "dominant_feature_family": interpretation.get("dominant_feature_family"),
                "reference_continue_margin_mean": interpretation.get(
                    "reference_continue_margin_mean"
                ),
                "candidate_monitor_shortfall_mean": shortfall_mean,
            },
            "opposing_feature_ranking": non_intercept_negative_features[:5],
            "chosen_feature_vs_shortfall": {
                "chosen_feature": TARGET_FEATURE,
                "chosen_feature_fix_scope": decision_gate.get("chosen_fix_scope"),
                "chosen_first_opposing_feature": first_feature.get("feature"),
                "first_opposing_feature_abs_value": round(first_feature_abs_value, 6),
                "shortfall_mean": round(shortfall_mean, 6),
                "first_opposing_feature_exceeds_shortfall_mean": (
                    first_feature_abs_value > shortfall_mean
                ),
            },
        },
        "decision_rationale": [
            (
                "Keep the next pass replay-only and bounded by choosing the largest "
                "non-intercept opposing feature inside the same 5-case slice."
            ),
            (
                "The fix-scope decision already closed the `feature_absence` story for "
                "`regimen_count`, so the next smallest scope is score competition."
            ),
            (
                f"`{first_feature.get('feature')}` is the largest opposing non-intercept "
                f"feature with aggregate value {first_feature.get('value')}."
            ),
            (
                "Leave `__intercept__` deferred because it is broader and less bounded than "
                "a slice-local opposing feature."
            ),
        ],
        "deferred_subtargets": [
            {
                "feature": second_feature.get("feature"),
                "family": second_feature.get("family"),
                "value": second_feature.get("value"),
                "reason": (
                    "second opposing non-intercept feature; use only if the first target "
                    "does not move enough"
                ),
            },
            {
                "feature": "__intercept__",
                "family": "intercept",
                "reason": (
                    "global opposing anchor; keep deferred until the bounded non-intercept "
                    "path is checked first"
                ),
            },
        ],
        "required_success_evidence": [
            (
                f"A replay artifact, validator, or smallest bounded fix showing "
                f"`{first_feature.get('feature')}` no longer dominates the score-side "
                "competition within the same 5-case slice."
            ),
            (
                "Evidence that the same 5-case slice moves without reopening wider family, "
                "bucket, subgroup, or training scope."
            ),
        ],
        "summary_findings": [
            (
                "The next bounded replay-only pass should focus on "
                f"`{first_feature.get('feature')}` "
                "as the first non-intercept opposing score contributor."
            ),
            (
                f"`{second_feature.get('feature')}` remains the deferred second opposing feature "
                "if the first pass does not move enough."
            ),
            "Do not reopen training or global intercept tuning for this pass.",
        ],
    }
    decision["validation_issues"] = validate_regimen_count_score_competition_decision(decision)
    return decision


def validate_regimen_count_score_competition_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    chosen_feature_vs_shortfall = _as_dict(evidence.get("chosen_feature_vs_shortfall"))

    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_feature_family") != "regimen_status_summary":
        issues.append("unexpected_feature_family")
    if gate.get("chosen_feature") != TARGET_FEATURE:
        issues.append("unexpected_chosen_feature")
    if gate.get("fix_scope") != "score_aggregation_or_competition":
        issues.append("unexpected_fix_scope")
    if gate.get("decision") != "focus_largest_non_intercept_opposing_feature_first":
        issues.append("unexpected_competition_decision")
    if gate.get("chosen_first_opposing_feature") != EXPECTED_FIRST_OPPOSING_FEATURE:
        issues.append("unexpected_first_opposing_feature")
    if not bool(gate.get("intercept_left_deferred")):
        issues.append("intercept_should_stay_deferred")
    if not _as_list(evidence.get("opposing_feature_ranking")):
        issues.append("missing_opposing_feature_ranking")
    if (
        chosen_feature_vs_shortfall.get("chosen_first_opposing_feature")
        != EXPECTED_FIRST_OPPOSING_FEATURE
    ):
        issues.append("shortfall_comparison_feature_mismatch")
    if not bool(chosen_feature_vs_shortfall.get("first_opposing_feature_exceeds_shortfall_mean")):
        issues.append("first_opposing_feature_not_large_enough")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_regimen_count_score_competition_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "regimen-count score-competition decision v1"
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


def write_regimen_count_score_competition_decision_files(
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
        render_regimen_count_score_competition_decision_markdown(decision),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_regimen_count_score_competition_decision",
    "load_json_artifact",
    "render_regimen_count_score_competition_decision_markdown",
    "validate_regimen_count_score_competition_decision",
    "write_regimen_count_score_competition_decision_files",
]
