from __future__ import annotations

import json
from pathlib import Path

TARGET_BUCKET = "mid_margin"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_non_cgm_threshold_duration_sensitive_narrowing_decision(
    *,
    subgroup_diagnostic: dict[str, object],
    subgroup_diagnostic_path: str | Path,
) -> dict[str, object]:
    subtarget = _as_dict(subgroup_diagnostic.get("subtarget"))
    readable_summary = _as_dict(subgroup_diagnostic.get("readable_summary"))
    margin_digest = _as_dict(readable_summary.get("margin_digest"))
    feature_digest = _as_dict(readable_summary.get("feature_digest"))
    bucket_counts = {
        str(key): int(value)
        for key, value in _as_dict(
            margin_digest.get("reference_continue_margin_bucket_counts")
        ).items()
    }
    ranked_buckets = sorted(
        bucket_counts.items(),
        key=lambda item: int(item[1]),
        reverse=True,
    )
    first_bucket, first_count = ranked_buckets[0]
    second_bucket, second_count = ranked_buckets[1]
    subgroup_case_count = int(subtarget.get("observed_case_count", 0))

    decision = {
        "audit_name": "non_cgm_threshold_duration_sensitive_narrowing_decision_v1",
        "source_artifacts": {
            "subgroup_diagnostic_path": str(subgroup_diagnostic_path),
        },
        "decision_gate": {
            "parent_family": subtarget.get("parent_family"),
            "subtarget_mode": subtarget.get("trajectory_mode"),
            "decision": "focus_largest_margin_bucket_first",
            "next_loop_type": "replay_only_narrowing",
            "chosen_first_margin_bucket": first_bucket,
            "chosen_first_margin_bucket_case_count": first_count,
            "chosen_first_margin_bucket_share_pct": round(
                (first_count / subgroup_case_count) * 100.0, 2
            ),
        },
        "evidence_summary": {
            "subtarget": {
                "observed_case_count": subgroup_case_count,
                "parent_family_case_count": subtarget.get("parent_family_case_count"),
                "parent_family_share_pct": _as_dict(
                    subgroup_diagnostic.get("case_summary")
                ).get("parent_family_share_pct"),
            },
            "margin_bucket_ranking": [
                {"bucket": bucket, "count": count} for bucket, count in ranked_buckets
            ],
            "proxy_drop_bucket_counts": _as_dict(margin_digest.get("proxy_drop_bucket_counts")),
            "feature_anchor": {
                "dominant_feature_family": feature_digest.get("dominant_family"),
                "dominant_feature": feature_digest.get("dominant_feature"),
                "top_absolute_feature": _as_dict(feature_digest.get("top_absolute_feature")).get(
                    "feature"
                ),
            },
        },
        "decision_rationale": [
            (
                "Choose the largest margin bucket first so the next replay-only loop can "
                "test one dense subgroup inside `threshold_duration_sensitive`."
            ),
            (
                f"`{first_bucket}` currently contains {first_count}/{subgroup_case_count} "
                "subgroup cases, so it is the smallest dense first target."
            ),
            (
                "This keeps the next loop on non-edge separation rather than drifting back "
                "to threshold widening."
            ),
            (
                "The dominant feature family remains `intercept`, so the next pass should "
                "still be treated as replay-side narrowing, not training."
            ),
        ],
        "deferred_subtargets": [
            {
                "margin_bucket": second_bucket,
                "count": second_count,
                "reason": (
                    "second bucket only; keep as follow-up if the first bucket does not move "
                    "enough"
                ),
            },
            {
                "mode": "single_feature_target",
                "feature": _as_dict(feature_digest.get("top_absolute_feature")).get("feature"),
                "reason": (
                    "do not target a single feature first while the subgroup still has one "
                    "clear dominant margin bucket"
                ),
            },
        ],
        "required_success_evidence": [
            (
                f"A replay artifact showing `{first_bucket}` cases decrease from {first_count} "
                "without increasing total `threshold_duration_sensitive` cases."
            ),
            (
                "A replay artifact showing the subgroup remains non-CGM and does not spill "
                "back into threshold-edge widening."
            ),
        ],
        "summary_findings": [
            (
                "The next bounded replay-only pass should focus on the "
                f"`{first_bucket}` bucket inside `threshold_duration_sensitive`."
            ),
            (
                f"`{second_bucket}` stays as the deferred bucket if the first pass does not "
                "move enough."
            ),
            "Do not reopen training or single-feature tweaking for this pass.",
        ],
    }
    decision["validation_issues"] = (
        validate_non_cgm_threshold_duration_sensitive_narrowing_decision(decision)
    )
    return decision


def validate_non_cgm_threshold_duration_sensitive_narrowing_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    feature_anchor = _as_dict(evidence.get("feature_anchor"))

    if gate.get("decision") != "focus_largest_margin_bucket_first":
        issues.append("unexpected_narrowing_decision")
    if gate.get("subtarget_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_subtarget_mode")
    if gate.get("chosen_first_margin_bucket") != TARGET_BUCKET:
        issues.append("unexpected_first_margin_bucket")
    if int(gate.get("chosen_first_margin_bucket_case_count", 0)) <= 0:
        issues.append("missing_first_margin_bucket_case_count")
    if feature_anchor.get("dominant_feature_family") != "intercept":
        issues.append("dominant_feature_family_not_intercept")
    if len(_as_list(decision.get("required_success_evidence"))) < 2:
        issues.append("required_success_evidence_missing")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_non_cgm_threshold_duration_sensitive_narrowing_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        "# non-cgm threshold-duration-sensitive narrowing decision v1",
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


def write_non_cgm_threshold_duration_sensitive_narrowing_decision_files(
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
        render_non_cgm_threshold_duration_sensitive_narrowing_decision_markdown(decision),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_non_cgm_threshold_duration_sensitive_narrowing_decision",
    "load_json_artifact",
    "render_non_cgm_threshold_duration_sensitive_narrowing_decision_markdown",
    "validate_non_cgm_threshold_duration_sensitive_narrowing_decision",
    "write_non_cgm_threshold_duration_sensitive_narrowing_decision_files",
]
