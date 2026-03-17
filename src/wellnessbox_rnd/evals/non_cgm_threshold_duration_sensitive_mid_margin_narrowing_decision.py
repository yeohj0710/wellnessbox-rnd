from __future__ import annotations

import json
from pathlib import Path

TARGET_PROXY_DROP_BUCKET = "small_drop"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision(
    *,
    bucket_diagnostic: dict[str, object],
    bucket_diagnostic_path: str | Path,
) -> dict[str, object]:
    bucket_target = _as_dict(bucket_diagnostic.get("bucket_target"))
    readable_summary = _as_dict(bucket_diagnostic.get("readable_summary"))
    margin_digest = _as_dict(readable_summary.get("margin_digest"))
    feature_digest = _as_dict(readable_summary.get("feature_digest"))
    proxy_drop_bucket_counts = {
        str(key): int(value)
        for key, value in _as_dict(margin_digest.get("proxy_drop_bucket_counts")).items()
    }
    ranked_proxy_drop_buckets = sorted(
        proxy_drop_bucket_counts.items(),
        key=lambda item: int(item[1]),
        reverse=True,
    )
    first_bucket, first_count = ranked_proxy_drop_buckets[0]
    second_bucket, second_count = ranked_proxy_drop_buckets[1]
    bucket_case_count = int(bucket_target.get("observed_case_count", 0))

    decision = {
        "audit_name": "non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_v1",
        "source_artifacts": {
            "bucket_diagnostic_path": str(bucket_diagnostic_path),
        },
        "decision_gate": {
            "parent_family": bucket_target.get("parent_family"),
            "subtarget_mode": bucket_target.get("trajectory_mode"),
            "margin_bucket": bucket_target.get("margin_bucket"),
            "decision": "focus_largest_proxy_drop_bucket_first",
            "next_loop_type": "replay_only_narrowing",
            "chosen_first_proxy_drop_bucket": first_bucket,
            "chosen_first_proxy_drop_bucket_case_count": first_count,
            "chosen_first_proxy_drop_bucket_share_pct": round(
                (first_count / bucket_case_count) * 100.0, 2
            ),
        },
        "evidence_summary": {
            "bucket_target": {
                "observed_case_count": bucket_case_count,
                "parent_family_case_count": bucket_target.get("parent_family_case_count"),
                "parent_family_share_pct": _as_dict(
                    bucket_diagnostic.get("case_summary")
                ).get("parent_family_share_pct"),
            },
            "proxy_drop_bucket_ranking": [
                {"proxy_drop_bucket": bucket, "count": count}
                for bucket, count in ranked_proxy_drop_buckets
            ],
            "reference_continue_margin_mean": margin_digest.get("reference_continue_margin_mean"),
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
                "Choose the largest proxy-drop bucket first so the next replay-only loop "
                "targets one dense slice inside the current 9-case mid-margin bucket."
            ),
            (
                f"`{first_bucket}` currently contains {first_count}/{bucket_case_count} "
                "cases, so it is the smallest dense next target."
            ),
            (
                "This keeps the next pass on replay-side separation rather than reopening "
                "the wider subgroup or training."
            ),
            (
                "The dominant feature family remains `intercept`, so the next pass should "
                "still be treated as replay-side narrowing."
            ),
        ],
        "deferred_subtargets": [
            {
                "proxy_drop_bucket": second_bucket,
                "count": second_count,
                "reason": (
                    "second proxy-drop bucket; keep as follow-up if the first bucket does not "
                    "move enough"
                ),
            },
            {
                "mode": "single_feature_target",
                "feature": _as_dict(feature_digest.get("top_absolute_feature")).get("feature"),
                "reason": (
                    "do not target a single feature first while the bucket still has one clear "
                    "dominant proxy-drop slice"
                ),
            },
        ],
        "required_success_evidence": [
            (
                f"A replay artifact showing `{first_bucket}` cases decrease from {first_count} "
                "without increasing total `mid_margin` cases."
            ),
            (
                "A replay artifact showing the bucket remains non-CGM and does not spill back "
                "into threshold-edge widening."
            ),
        ],
        "summary_findings": [
            (
                "The next bounded replay-only pass should focus on the "
                f"`{first_bucket}` proxy-drop bucket inside the current `mid_margin` target."
            ),
            (
                f"`{second_bucket}` stays as the deferred proxy-drop follow-up if the first "
                "pass does not move enough."
            ),
            "Do not reopen training or single-feature tweaking for this pass.",
        ],
    }
    decision["validation_issues"] = (
        validate_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision(
            decision
        )
    )
    return decision


def validate_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    feature_anchor = _as_dict(evidence.get("feature_anchor"))

    if gate.get("decision") != "focus_largest_proxy_drop_bucket_first":
        issues.append("unexpected_narrowing_decision")
    if gate.get("subtarget_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_subtarget_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("chosen_first_proxy_drop_bucket") != TARGET_PROXY_DROP_BUCKET:
        issues.append("unexpected_first_proxy_drop_bucket")
    if int(gate.get("chosen_first_proxy_drop_bucket_case_count", 0)) <= 0:
        issues.append("missing_first_proxy_drop_bucket_case_count")
    if feature_anchor.get("dominant_feature_family") != "intercept":
        issues.append("dominant_feature_family_not_intercept")
    if len(_as_list(decision.get("required_success_evidence"))) < 2:
        issues.append("required_success_evidence_missing")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        "# non-cgm threshold-duration-sensitive mid-margin narrowing decision v1",
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


def write_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_files(
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
        render_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_markdown(
            decision
        ),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision",
    "load_json_artifact",
    "render_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_markdown",
    "validate_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision",
    "write_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision_files",
]
