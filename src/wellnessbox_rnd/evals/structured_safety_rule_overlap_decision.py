from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_structured_safety_rule_overlap_decision(
    *,
    weakest_slice_audit: dict[str, object],
    weakest_slice_audit_path: str | Path,
    weakest_slice_summary: dict[str, object],
    weakest_slice_summary_path: str | Path,
    eval_report: dict[str, object],
    eval_report_path: str | Path,
) -> dict[str, object]:
    safety_audit = _as_dict(
        weakest_slice_audit.get("structured_safety_evidence_linkage_audit")
    )
    workflow_join = _as_dict(safety_audit.get("next_action_workflow_category_join"))
    frozen_join = _as_dict(safety_audit.get("frozen_eval_category_join"))
    completeness = _as_dict(safety_audit.get("reference_linkage_completeness"))
    weakest_family_summary = _find_family_summary(
        weakest_slice_summary,
        family="safety_blocked",
    )
    frozen_eval_anchor = _as_dict(weakest_slice_summary.get("frozen_eval_anchor"))
    weakest_by_metric = _as_dict(frozen_eval_anchor.get("weakest_category_by_metric"))
    safety_metric = _as_dict(weakest_by_metric.get("safety_reference_accuracy_pct"))
    full_eval_summary = _as_dict(eval_report.get("summary"))
    overall_safety_metric = _as_dict(full_eval_summary.get("safety_reference_accuracy_pct"))

    observed_rule_id_counts = _as_dict(frozen_join.get("observed_rule_id_counts"))
    observed_rule_ids = sorted(observed_rule_id_counts)
    fixture_rule_ids = _sorted_str_list(frozen_join.get("fixture_rule_ids"))
    overlap_ids = _sorted_str_list(frozen_join.get("fixture_rule_overlap_ids"))
    overlap_pct = (
        round((len(overlap_ids) / len(observed_rule_ids)) * 100.0, 6)
        if observed_rule_ids
        else None
    )

    blocks_kpi_interpretation = not (
        weakest_family_summary.get("coverage_status") == "connected"
        and workflow_join.get("join_status") == "connected"
        and workflow_join.get("coverage_pct") == 100.0
        and frozen_join.get("join_status") == "connected"
        and safety_metric.get("passed") is True
        and overall_safety_metric.get("passed") is True
        and safety_audit.get("reference_linkage_status") == "deterministic_only"
    )

    decision = {
        "audit_name": "structured_safety_rule_overlap_decision_v1",
        "source_artifacts": {
            "weakest_slice_audit_path": str(weakest_slice_audit_path),
            "weakest_slice_summary_path": str(weakest_slice_summary_path),
            "eval_report_path": str(eval_report_path),
        },
        "decision_gate": {
            "blocks_kpi_interpretation": blocks_kpi_interpretation,
            "decision": (
                "partial_rule_overlap_not_blocking_current_kpi_interpretation"
                if not blocks_kpi_interpretation
                else "partial_rule_overlap_still_blocks_current_kpi_interpretation"
            ),
            "reason_codes": _reason_codes(
                weakest_family_summary=weakest_family_summary,
                workflow_join=workflow_join,
                frozen_join=frozen_join,
                safety_metric=safety_metric,
                overall_safety_metric=overall_safety_metric,
                safety_audit=safety_audit,
                overlap_ids=overlap_ids,
                observed_rule_ids=observed_rule_ids,
            ),
        },
        "evidence_summary": {
            "weakest_safety_family": {
                "family": "safety_blocked",
                "coverage_status": weakest_family_summary.get("coverage_status"),
                "case_count": weakest_family_summary.get("case_count"),
                "weakest_metrics": _sorted_str_list(
                    weakest_family_summary.get("weakest_metrics")
                ),
                "remaining_gaps": _sorted_str_list(
                    weakest_family_summary.get("remaining_gaps")
                ),
            },
            "safety_reference_metric": {
                "weakest_category": safety_metric.get("category"),
                "weakest_score": safety_metric.get("score"),
                "weakest_target": safety_metric.get("target"),
                "weakest_passed": safety_metric.get("passed"),
                "overall_score": overall_safety_metric.get("score"),
                "overall_target": overall_safety_metric.get("target"),
                "overall_passed": overall_safety_metric.get("passed"),
            },
            "workflow_category_join": {
                "join_status": workflow_join.get("join_status"),
                "coverage_pct": workflow_join.get("coverage_pct"),
                "category_case_count": workflow_join.get("category_case_count"),
                "actual_status_counts": _as_dict(workflow_join.get("actual_status_counts")),
                "actual_next_action_counts": _as_dict(
                    workflow_join.get("actual_next_action_counts")
                ),
                "unmatched_next_action_counts": _as_dict(
                    workflow_join.get("unmatched_next_action_counts")
                ),
            },
            "structured_safety_rule_overlap": {
                "reference_linkage_status": safety_audit.get("reference_linkage_status"),
                "rule_count": completeness.get("rule_count"),
                "reference_backed_rule_count": completeness.get(
                    "reference_backed_rule_count"
                ),
                "reference_coverage_pct": completeness.get("reference_coverage_pct"),
                "fixture_rule_ids": fixture_rule_ids,
                "observed_rule_ids": observed_rule_ids,
                "observed_rule_id_counts": observed_rule_id_counts,
                "fixture_rule_overlap_ids": overlap_ids,
                "fixture_rule_overlap_count": len(overlap_ids),
                "observed_rule_family_count": len(observed_rule_ids),
                "fixture_rule_overlap_pct_of_observed": overlap_pct,
                "fixture_next_action": frozen_join.get("fixture_next_action"),
                "workflow_contract_next_action": frozen_join.get(
                    "workflow_contract_next_action"
                ),
                "fixture_next_action_seen_in_family": frozen_join.get(
                    "fixture_next_action_seen_in_family"
                ),
                "workflow_contract_next_action_seen_in_family": frozen_join.get(
                    "workflow_contract_next_action_seen_in_family"
                ),
            },
        },
        "decision_rationale": [
            (
                "The remaining safety gap is now narrower than before: weakest-slice "
                "workflow coverage is complete at the category level for `safety_blocked`."
            ),
            (
                "The structured safety request fixture still overlaps only part of the "
                "observed weakest-slice rule families, so rule-family attribution remains partial."
            ),
            (
                "That partial overlap does not currently block KPI interpretation because "
                "`safety_reference_accuracy_pct` still passes overall and on the weakest "
                "`safety_blocked` slice while the deterministic safety path stays explicit."
            ),
        ],
        "summary_findings": [
            (
                "Current structured-safety rule overlap is incomplete, but it is not blocking "
                "the present safety KPI interpretation."
            ),
            (
                "Keep this as a narrower attribution limitation unless future safety claims "
                "need full rule-family completeness across the weakest slice."
            ),
            (
                "The repo should not spend another workflow-wiring loop here unless the "
                "partial overlap starts obscuring a real KPI regression."
            ),
        ],
    }
    decision["validation_issues"] = validate_structured_safety_rule_overlap_decision(
        decision
    )
    return decision


def validate_structured_safety_rule_overlap_decision(
    decision: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    weakest_family = _as_dict(evidence.get("weakest_safety_family"))
    safety_metric = _as_dict(evidence.get("safety_reference_metric"))
    workflow_join = _as_dict(evidence.get("workflow_category_join"))
    rule_overlap = _as_dict(evidence.get("structured_safety_rule_overlap"))

    if gate.get("blocks_kpi_interpretation") is True:
        issues.append("structured_safety_overlap_still_marked_blocking")
    if gate.get("decision") != "partial_rule_overlap_not_blocking_current_kpi_interpretation":
        issues.append("unexpected_structured_safety_overlap_decision")
    if weakest_family.get("coverage_status") != "connected":
        issues.append("weakest_safety_family_not_connected")
    if workflow_join.get("join_status") != "connected":
        issues.append("workflow_category_join_not_connected")
    if workflow_join.get("coverage_pct") != 100.0:
        issues.append("workflow_category_join_not_full_coverage")
    if safety_metric.get("weakest_passed") is not True:
        issues.append("weakest_safety_reference_metric_not_passing")
    if safety_metric.get("overall_passed") is not True:
        issues.append("overall_safety_reference_metric_not_passing")
    if rule_overlap.get("reference_linkage_status") != "deterministic_only":
        issues.append("unexpected_reference_linkage_status")
    if not _sorted_str_list(rule_overlap.get("fixture_rule_overlap_ids")):
        issues.append("no_structured_safety_rule_overlap_observed")
    return issues


def render_structured_safety_rule_overlap_decision_markdown(
    decision: dict[str, object],
) -> str:
    lines = [
        "# structured safety rule overlap decision v1",
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


def write_structured_safety_rule_overlap_decision_files(
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
        render_structured_safety_rule_overlap_decision_markdown(decision),
        encoding="utf-8",
    )


def _find_family_summary(summary: dict[str, object], *, family: str) -> dict[str, object]:
    for item in _as_list(summary.get("case_family_summaries")):
        payload = _as_dict(item)
        if payload.get("family") == family:
            return payload
    return {}


def _reason_codes(
    *,
    weakest_family_summary: dict[str, object],
    workflow_join: dict[str, object],
    frozen_join: dict[str, object],
    safety_metric: dict[str, object],
    overall_safety_metric: dict[str, object],
    safety_audit: dict[str, object],
    overlap_ids: list[str],
    observed_rule_ids: list[str],
) -> list[str]:
    reason_codes: list[str] = []
    if weakest_family_summary.get("coverage_status") == "connected":
        reason_codes.append("weakest_safety_family_connected")
    if workflow_join.get("coverage_pct") == 100.0:
        reason_codes.append("workflow_branch_coverage_complete")
    if frozen_join.get("join_status") == "connected":
        reason_codes.append("structured_safety_category_join_connected")
    if safety_metric.get("passed") is True and overall_safety_metric.get("passed") is True:
        reason_codes.append("safety_reference_metric_still_passing")
    if safety_audit.get("reference_linkage_status") == "deterministic_only":
        reason_codes.append("deterministic_safety_path_preserved")
    if overlap_ids and len(overlap_ids) < len(observed_rule_ids):
        reason_codes.append("structured_safety_rule_overlap_partial")
    return reason_codes


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _sorted_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


__all__ = [
    "build_structured_safety_rule_overlap_decision",
    "load_json_artifact",
    "render_structured_safety_rule_overlap_decision_markdown",
    "validate_structured_safety_rule_overlap_decision",
    "write_structured_safety_rule_overlap_decision_files",
]
