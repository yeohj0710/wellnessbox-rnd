from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_non_cgm_threshold_cross_narrowing_decision(
    *,
    non_cgm_diagnostic: dict[str, object],
    non_cgm_diagnostic_path: str | Path,
    reject_decision: dict[str, object],
    reject_decision_path: str | Path,
) -> dict[str, object]:
    target_family = _as_dict(non_cgm_diagnostic.get("target_family"))
    workflow_summary = _as_dict(non_cgm_diagnostic.get("workflow_summary"))
    readable_summary = _as_dict(non_cgm_diagnostic.get("readable_summary"))
    interpretation = _as_dict(non_cgm_diagnostic.get("interpretation"))
    reject_hold_context = _as_dict(reject_decision.get("hold_context"))
    dominant_low_risk = _as_dict(
        _as_dict(reject_decision.get("regression_slices")).get("dominant_low_risk_slice")
    )

    workflow_mode_counts = {
        str(key): int(value)
        for key, value in _as_dict(workflow_summary.get("trajectory_mode_counts")).items()
    }
    ranked_modes = sorted(
        workflow_mode_counts.items(),
        key=lambda item: int(item[1]),
        reverse=True,
    )
    first_target_mode, first_target_count = ranked_modes[0]
    second_target_mode, second_target_count = ranked_modes[1]
    observed_case_count = int(target_family.get("observed_case_count", 0))
    focus_share_pct = round((first_target_count / observed_case_count) * 100.0, 2)

    decision = {
        "audit_name": "non_cgm_threshold_cross_narrowing_decision_v1",
        "source_artifacts": {
            "non_cgm_diagnostic_path": str(non_cgm_diagnostic_path),
            "reject_decision_path": str(reject_decision_path),
        },
        "decision_gate": {
            "decision_family": target_family.get("name"),
            "decision": "focus_largest_single_workflow_mode_first",
            "next_loop_type": "replay_only_narrowing",
            "chosen_first_target_mode": first_target_mode,
            "chosen_first_target_case_count": first_target_count,
            "chosen_first_target_share_pct": focus_share_pct,
        },
        "evidence_summary": {
            "target_family": {
                "observed_case_count": observed_case_count,
                "transition": target_family.get("transition"),
                "all_cases_non_cgm": _as_dict(readable_summary.get("case_digest")).get(
                    "all_cases_non_cgm"
                ),
                "threshold_edge_only_story_supported": _as_dict(
                    readable_summary.get("case_digest")
                ).get("threshold_edge_only_story_supported"),
            },
            "workflow_mode_ranking": [
                {"mode": mode, "count": count} for mode, count in ranked_modes
            ],
            "feature_anchor": {
                "dominant_feature_family": interpretation.get("dominant_feature_family"),
                "dominant_feature": interpretation.get("dominant_feature"),
                "reference_only_structural_feature": _as_dict(
                    _as_dict(readable_summary.get("dominant_feature_digest")).get(
                        "reference_only_structural_feature"
                    )
                ).get("feature"),
            },
            "reject_alignment": {
                "dominant_replay_regression_family": reject_hold_context.get(
                    "dominant_replay_regression_family"
                ),
                "dominant_feature_family": dominant_low_risk.get(
                    "dominant_feature_family"
                ),
                "observed_case_count": dominant_low_risk.get("observed_case_count"),
            },
        },
        "decision_rationale": [
            (
                "Choose the largest single workflow mode first so the next bounded replay "
                "loop has one narrow target instead of diffusing across the whole family."
            ),
            (
                f"`{first_target_mode}` is the largest single subgroup with "
                f"{first_target_count}/{observed_case_count} current cases."
            ),
            (
                "The blocker is still not a pure threshold-edge story, so this should stay "
                "focused on a non-edge workflow subgroup rather than threshold widening."
            ),
            (
                "The dominant feature family remains `intercept`, which supports treating "
                "the next loop as replay-side narrowing rather than reopening training."
            ),
        ],
        "deferred_subtargets": [
            {
                "mode": second_target_mode,
                "count": second_target_count,
                "reason": (
                    "second-largest subgroup; keep for the next pass if the first "
                    "target does not move enough"
                ),
            },
            {
                "mode": "reference_only_structural_feature",
                "feature": _as_dict(
                    _as_dict(readable_summary.get("dominant_feature_digest")).get(
                        "reference_only_structural_feature"
                    )
                ).get("feature"),
                "reason": (
                    "do not target a single structural feature first while synthetic-validity "
                    "risk remains the principal blocker"
                ),
            },
        ],
        "required_success_evidence": [
            (
                f"A replay artifact showing `{first_target_mode}` count decreases from "
                f"{first_target_count} without increasing total "
                "`non_cgm_continue_to_monitor_threshold_cross` cases."
            ),
            (
                "A replay artifact showing the dominant regression family stays non-CGM "
                "and does not spill into cgm final-step geometry."
            ),
        ],
        "summary_findings": [
            (
                f"The next bounded non-CGM replay loop should focus first on "
                f"`{first_target_mode}`, the largest single workflow subgroup."
            ),
            (
                f"`{second_target_mode}` remains the second follow-up target if the first "
                "subgroup does not move enough."
            ),
            "Do not reopen training or threshold widening for this narrowing pass.",
        ],
    }
    decision["validation_issues"] = validate_non_cgm_threshold_cross_narrowing_decision(
        decision
    )
    return decision


def validate_non_cgm_threshold_cross_narrowing_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    workflow_mode_ranking = _as_list(evidence.get("workflow_mode_ranking"))
    target_family = _as_dict(evidence.get("target_family"))
    feature_anchor = _as_dict(evidence.get("feature_anchor"))
    reject_alignment = _as_dict(evidence.get("reject_alignment"))

    if gate.get("decision_family") != "non_cgm_continue_to_monitor_threshold_cross":
        issues.append("unexpected_decision_family")
    if gate.get("decision") != "focus_largest_single_workflow_mode_first":
        issues.append("unexpected_narrowing_decision")
    if gate.get("chosen_first_target_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_first_target_mode")
    if int(gate.get("chosen_first_target_case_count", 0)) <= 0:
        issues.append("missing_first_target_case_count")
    if not workflow_mode_ranking:
        issues.append("workflow_mode_ranking_missing")
    if target_family.get("threshold_edge_only_story_supported") is not False:
        issues.append("threshold_edge_story_should_remain_false")
    if feature_anchor.get("dominant_feature_family") != "intercept":
        issues.append("dominant_feature_family_not_intercept")
    if (
        reject_alignment.get("dominant_replay_regression_family")
        != "non_cgm_continue_to_monitor_threshold_cross"
    ):
        issues.append("reject_alignment_family_mismatch")
    if len(_as_list(decision.get("required_success_evidence"))) < 2:
        issues.append("required_success_evidence_missing")
    return issues


def render_non_cgm_threshold_cross_narrowing_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        "# non-cgm threshold-cross narrowing decision v1",
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


def write_non_cgm_threshold_cross_narrowing_decision_files(
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
        render_non_cgm_threshold_cross_narrowing_decision_markdown(decision),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_non_cgm_threshold_cross_narrowing_decision",
    "load_json_artifact",
    "render_non_cgm_threshold_cross_narrowing_decision_markdown",
    "validate_non_cgm_threshold_cross_narrowing_decision",
    "write_non_cgm_threshold_cross_narrowing_decision_files",
]
