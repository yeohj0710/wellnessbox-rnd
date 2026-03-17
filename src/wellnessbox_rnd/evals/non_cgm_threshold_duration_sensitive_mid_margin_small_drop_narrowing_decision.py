from __future__ import annotations

import json
from pathlib import Path

TARGET_NON_INTERCEPT_FAMILY = "regimen_status_summary"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision(
    *,
    slice_diagnostic: dict[str, object],
    slice_diagnostic_path: str | Path,
) -> dict[str, object]:
    slice_target = _as_dict(slice_diagnostic.get("slice_target"))
    case_summary = _as_dict(slice_diagnostic.get("case_summary"))
    feature_summary = _as_dict(slice_diagnostic.get("feature_summary"))
    readable_summary = _as_dict(slice_diagnostic.get("readable_summary"))
    top_absolute_families = _as_list(feature_summary.get("top_absolute_families"))
    non_intercept_families = [
        item for item in top_absolute_families if _as_dict(item).get("family") != "intercept"
    ]
    first_family = _as_dict(non_intercept_families[0]) if non_intercept_families else {}
    second_family = _as_dict(non_intercept_families[1]) if len(non_intercept_families) > 1 else {}
    case_count = int(slice_target.get("observed_case_count", 0))

    decision = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_v1"
        ),
        "source_artifacts": {
            "slice_diagnostic_path": str(slice_diagnostic_path),
        },
        "decision_gate": {
            "parent_family": slice_target.get("parent_family"),
            "trajectory_mode": slice_target.get("trajectory_mode"),
            "margin_bucket": slice_target.get("margin_bucket"),
            "proxy_drop_bucket": slice_target.get("proxy_drop_bucket"),
            "decision": "focus_largest_non_intercept_feature_family_first",
            "next_loop_type": "replay_only_narrowing",
            "chosen_first_feature_family": first_family.get("family"),
            "chosen_first_feature_family_value": first_family.get("value"),
            "slice_case_count": case_count,
        },
        "evidence_summary": {
            "slice_target": {
                "observed_case_count": case_count,
                "parent_family_case_count": slice_target.get("parent_family_case_count"),
                "parent_family_share_pct": case_summary.get("parent_family_share_pct"),
            },
            "non_intercept_family_ranking": non_intercept_families,
            "current_geometry": _as_dict(readable_summary.get("margin_digest")),
            "current_feature_anchor": _as_dict(readable_summary.get("feature_digest")),
        },
        "decision_rationale": [
            (
                "Keep the next pass replay-only and bounded by choosing the largest "
                "non-intercept feature family inside the current 5-case slice."
            ),
            (
                f"`{first_family.get('family')}` is currently the largest non-intercept "
                f"family with absolute value {first_family.get('value')}."
            ),
            (
                "This is a smaller next step than reopening the full feature list, wider "
                "bucket, subgroup, or training loop."
            ),
            (
                "Do not target `__intercept__` directly while one non-intercept family "
                "still dominates the residual slice."
            ),
        ],
        "deferred_subtargets": [
            {
                "feature_family": second_family.get("family"),
                "value": second_family.get("value"),
                "reason": (
                    "second non-intercept family; use only if the first family does not "
                    "move enough"
                ),
            },
            {
                "mode": "single_feature_target",
                "feature": _as_dict(
                    _as_dict(readable_summary.get("feature_digest")).get("top_absolute_feature")
                ).get("feature"),
                "reason": (
                    "do not reopen single-feature tuning while the family-level evidence "
                    "is still denser"
                ),
            },
        ],
        "required_success_evidence": [
            (
                f"A replay artifact or validator showing the `{first_family.get('family')}` "
                "family no longer dominates the same 5-case `small_drop` slice."
            ),
            (
                "A replay artifact showing the slice stays non-CGM and does not widen back "
                "to the broader 9-case `mid_margin` bucket."
            ),
        ],
        "summary_findings": [
            (
                "The next bounded replay-only pass should focus on the "
                f"`{first_family.get('family')}` family inside the current `small_drop` slice."
            ),
            (
                f"`{second_family.get('family')}` stays as the deferred second family if "
                "the first pass does not move enough."
            ),
            "Do not reopen training or single-feature tuning for this pass.",
        ],
    }
    decision["validation_issues"] = (
        validate_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision(
            decision
        )
    )
    return decision


def validate_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    current_feature_anchor = _as_dict(evidence.get("current_feature_anchor"))

    if gate.get("decision") != "focus_largest_non_intercept_feature_family_first":
        issues.append("unexpected_narrowing_decision")
    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_first_feature_family") != TARGET_NON_INTERCEPT_FAMILY:
        issues.append("unexpected_first_feature_family")
    if current_feature_anchor.get("dominant_family") != "intercept":
        issues.append("dominant_feature_anchor_drifted")
    if len(_as_list(decision.get("required_success_evidence"))) < 2:
        issues.append("required_success_evidence_missing")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        "# non-cgm threshold-duration-sensitive mid-margin small-drop narrowing decision v1",
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


def write_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_files(
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
        render_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_markdown(
            decision
        ),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision",
    "load_json_artifact",
    "render_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_markdown",
    "validate_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision",
    "write_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision_files",
]
