from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_bone_joint_weakest_family_decision(
    *,
    weakest_slice_summary: dict[str, object],
    weakest_slice_summary_path: str | Path,
    eval_report: dict[str, object],
    eval_report_path: str | Path,
    training_revisit_decision: dict[str, object],
    training_revisit_decision_path: str | Path,
) -> dict[str, object]:
    family_summary = _find_bone_joint_family_summary(weakest_slice_summary)
    anchor = _as_dict(weakest_slice_summary.get("frozen_eval_anchor"))
    by_metric = _as_dict(anchor.get("weakest_category_by_metric"))
    recommendation_metric = _as_dict(by_metric.get("recommendation_coverage_pct"))
    adverse_metric = _as_dict(by_metric.get("adverse_event_count_yearly"))
    case_detail = _find_bone_joint_case(eval_report)
    case_metrics = _as_dict(case_detail.get("case_metrics"))
    actual = _as_dict(case_detail.get("actual"))
    training_gate = _as_dict(training_revisit_decision.get("decision_gate"))

    case_count = _to_int(family_summary.get("case_count"))
    weakest_metrics = _sorted_str_list(family_summary.get("weakest_metrics"))
    all_family_metrics_pass = (
        recommendation_metric.get("passed") is True and adverse_metric.get("passed") is True
    )
    case_runtime_ok = (
        case_metrics.get("recommendation_coverage_pct") == 100.0
        and case_metrics.get("next_action_accuracy_pct") == 100.0
        and case_metrics.get("explanation_quality_accuracy_pct") == 100.0
        and case_metrics.get("safety_reference_accuracy_pct") == 100.0
        and actual.get("status") == "ok"
        and actual.get("next_action") == "start_plan"
    )
    current_training_revisit_deferred = (
        training_gate.get("decision") == "defer_new_effect_training_loop"
    )
    keep_empty_anchor = (
        case_count <= 1
        and all_family_metrics_pass
        and case_runtime_ok
        and current_training_revisit_deferred
        and family_summary.get("coverage_status") == "empty"
    )

    decision = {
        "audit_name": "bone_joint_weakest_family_decision_v1",
        "source_artifacts": {
            "weakest_slice_summary_path": str(weakest_slice_summary_path),
            "eval_report_path": str(eval_report_path),
            "training_revisit_decision_path": str(training_revisit_decision_path),
        },
        "decision_gate": {
            "keep_explicit_empty_anchor": keep_empty_anchor,
            "decision": (
                "keep_explicit_empty_anchor"
                if keep_empty_anchor
                else "dedicated_bone_joint_bundle_worth_scoping"
            ),
            "reason_codes": _reason_codes(
                case_count=case_count,
                all_family_metrics_pass=all_family_metrics_pass,
                case_runtime_ok=case_runtime_ok,
                current_training_revisit_deferred=current_training_revisit_deferred,
            ),
        },
        "evidence_summary": {
            "family_summary": {
                "case_count": case_count,
                "coverage_status": family_summary.get("coverage_status"),
                "weakest_metrics": weakest_metrics,
                "remaining_gaps": _sorted_str_list(family_summary.get("remaining_gaps")),
            },
            "metric_anchor": {
                "recommendation_coverage_pct": recommendation_metric,
                "adverse_event_count_yearly": adverse_metric,
                "all_family_metrics_pass": all_family_metrics_pass,
            },
            "case_detail": {
                "case_id": case_detail.get("case_id"),
                "description": case_detail.get("description"),
                "case_metrics": case_metrics,
                "status": actual.get("status"),
                "next_action": actual.get("next_action"),
                "recommendation_keys": _sorted_str_list(actual.get("recommendation_keys")),
            },
            "training_context": {
                "training_revisit_decision": training_gate.get("decision"),
                "training_revisit_reason_codes": _sorted_str_list(
                    training_gate.get("reason_codes")
                ),
            },
        },
        "decision_rationale": [
            (
                "Do not add a dedicated bone_joint weakest-family audit bundle now because the "
                "family has only one frozen-eval case and its weakest metrics still pass."
            ),
            (
                "The actual bone_joint eval case already has full recommendation coverage, "
                "correct next action, correct explanation, and correct safety reference."
            ),
            (
                "The current higher-value blocker is still replay/data-validity evidence for "
                "effect training, so adding a bone_joint bundle now would be lower ROI."
            ),
        ],
        "revisit_triggers": [
            (
                "Add a dedicated bone_joint audit bundle only if bone_joint starts failing a "
                "KPI metric or appears in more than one weakest-family case."
            ),
            (
                "Revisit if a future weakest-slice report shows bone_joint as an actual blocker "
                "rather than a single passing anchor."
            ),
        ],
        "summary_findings": [
            (
                "bone_joint should remain an explicit empty weakest-family anchor for now."
            ),
            (
                "This is not a hidden failure family today; it is a single-case, passing, "
                "low-ROI anchor."
            ),
            (
                "Current effort should stay on larger replay/data-validity gaps before adding "
                "a bone_joint-specific contract bundle."
            ),
        ],
    }
    decision["validation_issues"] = validate_bone_joint_weakest_family_decision(decision)
    return decision


def validate_bone_joint_weakest_family_decision(
    decision: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    family_summary = _as_dict(evidence.get("family_summary"))
    metric_anchor = _as_dict(evidence.get("metric_anchor"))
    case_detail = _as_dict(evidence.get("case_detail"))
    training_context = _as_dict(evidence.get("training_context"))

    if gate.get("keep_explicit_empty_anchor") is not True:
        issues.append("bone_joint_empty_anchor_not_kept")
    if gate.get("decision") != "keep_explicit_empty_anchor":
        issues.append("unexpected_bone_joint_decision")
    if _to_int(family_summary.get("case_count")) != 1:
        issues.append("unexpected_bone_joint_case_count")
    if metric_anchor.get("all_family_metrics_pass") is not True:
        issues.append("bone_joint_family_metrics_not_all_passing")
    if case_detail.get("status") != "ok" or case_detail.get("next_action") != "start_plan":
        issues.append("bone_joint_case_runtime_not_ok")
    if training_context.get("training_revisit_decision") != "defer_new_effect_training_loop":
        issues.append("training_context_not_deferred")
    return issues


def render_bone_joint_weakest_family_decision_markdown(
    decision: dict[str, object],
) -> str:
    lines = [
        "# bone joint weakest family decision v1",
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
    for finding in _as_list(decision.get("decision_rationale")):
        lines.append(f"- {finding}")
    lines.extend(["", "## revisit triggers", ""])
    for finding in _as_list(decision.get("revisit_triggers")):
        lines.append(f"- {finding}")
    lines.extend(["", "## summary findings", ""])
    for finding in _as_list(decision.get("summary_findings")):
        lines.append(f"- {finding}")
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


def write_bone_joint_weakest_family_decision_files(
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
        render_bone_joint_weakest_family_decision_markdown(decision),
        encoding="utf-8",
    )


def _find_bone_joint_family_summary(summary: dict[str, object]) -> dict[str, object]:
    for item in _as_list(summary.get("case_family_summaries")):
        payload = _as_dict(item)
        if payload.get("family") == "bone_joint":
            return payload
    return {}


def _find_bone_joint_case(eval_report: dict[str, object]) -> dict[str, object]:
    for item in _as_list(eval_report.get("case_results")):
        payload = _as_dict(item)
        if payload.get("category") == "bone_joint":
            return payload
    return {}


def _reason_codes(
    *,
    case_count: int,
    all_family_metrics_pass: bool,
    case_runtime_ok: bool,
    current_training_revisit_deferred: bool,
) -> list[str]:
    reason_codes: list[str] = []
    if case_count <= 1:
        reason_codes.append("single_case_anchor")
    if all_family_metrics_pass:
        reason_codes.append("family_metrics_all_passing")
    if case_runtime_ok:
        reason_codes.append("eval_case_runtime_path_passing")
    if current_training_revisit_deferred:
        reason_codes.append("higher_roi_training_blockers_elsewhere")
    return reason_codes


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _sorted_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


__all__ = [
    "build_bone_joint_weakest_family_decision",
    "load_json_artifact",
    "render_bone_joint_weakest_family_decision_markdown",
    "validate_bone_joint_weakest_family_decision",
    "write_bone_joint_weakest_family_decision_files",
]
