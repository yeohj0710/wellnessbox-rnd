from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "regimen_count"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_regimen_status_summary_narrowing_decision(
    *,
    family_diagnostic: dict[str, object],
    family_diagnostic_path: str | Path,
) -> dict[str, object]:
    family_target = _as_dict(family_diagnostic.get("family_target"))
    family_feature_summary = _as_dict(family_diagnostic.get("family_feature_summary"))
    readable_summary = _as_dict(family_diagnostic.get("readable_summary"))
    ordered_features = _as_list(family_feature_summary.get("ordered_features"))
    first_feature = _as_dict(ordered_features[0]) if ordered_features else {}
    second_feature = _as_dict(ordered_features[1]) if len(ordered_features) > 1 else {}

    decision = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "regimen_status_summary_narrowing_decision_v1"
        ),
        "source_artifacts": {
            "family_diagnostic_path": str(family_diagnostic_path),
        },
        "decision_gate": {
            "parent_family": family_target.get("parent_family"),
            "trajectory_mode": family_target.get("trajectory_mode"),
            "margin_bucket": family_target.get("margin_bucket"),
            "proxy_drop_bucket": family_target.get("proxy_drop_bucket"),
            "chosen_feature_family": family_target.get("chosen_feature_family"),
            "decision": "focus_largest_family_internal_feature_first",
            "next_loop_type": "replay_only_narrowing",
            "chosen_first_feature": first_feature.get("feature"),
            "chosen_first_feature_value": first_feature.get("value"),
            "observed_matching_case_count": family_target.get("observed_matching_case_count"),
        },
        "evidence_summary": {
            "family_target": {
                "observed_matching_case_count": family_target.get(
                    "observed_matching_case_count"
                ),
                "family_absolute_value": family_target.get("family_absolute_value"),
            },
            "family_internal_feature_ranking": ordered_features[:5],
            "current_family_feature_anchor": _as_dict(readable_summary.get("feature_digest")),
        },
        "decision_rationale": [
            (
                "Keep the next pass replay-only and bounded by choosing the largest "
                "feature inside the already-selected family."
            ),
            (
                f"`{first_feature.get('feature')}` is currently the largest internal "
                f"feature with value {first_feature.get('value')}."
            ),
            (
                "This is smaller than reopening the whole family, the wider slice, or training."
            ),
            (
                "Do not reopen cross-family comparisons while one family-internal feature "
                "still dominates."
            ),
        ],
        "deferred_subtargets": [
            {
                "feature": second_feature.get("feature"),
                "value": second_feature.get("value"),
                "reason": (
                    "second family-internal feature; use only if the first feature does not "
                    "move enough"
                ),
            }
        ],
        "required_success_evidence": [
            (
                f"A replay artifact or validator showing `{first_feature.get('feature')}` "
                "no longer dominates the same `regimen_status_summary` family inside the "
                "`small_drop` slice."
            ),
            (
                "A replay artifact showing the same 5-case slice stays stable without widening "
                "back to the broader bucket or family."
            ),
        ],
        "summary_findings": [
            (
                "The next bounded replay-only pass should focus on "
                f"`{first_feature.get('feature')}` inside `regimen_status_summary`."
            ),
            (
                f"`{second_feature.get('feature')}` stays as the deferred second feature if "
                "the first pass does not move enough."
            ),
            "Do not reopen training or wider feature-family tuning for this pass.",
        ],
    }
    decision["validation_issues"] = validate_regimen_status_summary_narrowing_decision(
        decision
    )
    return decision


def validate_regimen_status_summary_narrowing_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))

    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_feature_family") != "regimen_status_summary":
        issues.append("unexpected_feature_family")
    if gate.get("decision") != "focus_largest_family_internal_feature_first":
        issues.append("unexpected_narrowing_decision")
    if gate.get("chosen_first_feature") != TARGET_FEATURE:
        issues.append("unexpected_first_feature")
    if not _as_list(_as_dict(evidence).get("family_internal_feature_ranking")):
        issues.append("missing_internal_feature_ranking")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_regimen_status_summary_narrowing_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "regimen-status-summary narrowing decision v1"
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


def write_regimen_status_summary_narrowing_decision_files(
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
        render_regimen_status_summary_narrowing_decision_markdown(decision),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_regimen_status_summary_narrowing_decision",
    "load_json_artifact",
    "render_regimen_status_summary_narrowing_decision_markdown",
    "validate_regimen_status_summary_narrowing_decision",
    "write_regimen_status_summary_narrowing_decision_files",
]
