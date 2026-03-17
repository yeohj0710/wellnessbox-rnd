from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser_case_id_mismatch_decision(
    *,
    parser_report: dict[str, object],
    parser_report_path: str | Path,
    normalization_audit: dict[str, object],
    normalization_audit_path: str | Path,
    weakest_slice_summary: dict[str, object],
    weakest_slice_summary_path: str | Path,
) -> dict[str, object]:
    parser_case_ids = sorted(
        str(case.get("case_id"))
        for case in _as_list(parser_report.get("normalized_cases"))
        if isinstance(case, dict) and case.get("case_id") is not None
    )
    weakest_family_summary = _find_family_summary(
        weakest_slice_summary,
        family="free_text_alias",
    )
    normalization_checks = _as_dict(normalization_audit.get("consistency_checks"))
    category_join = _as_dict(normalization_audit.get("frozen_eval_category_join"))
    direct_cgm_join = _as_dict(normalization_audit.get("direct_cgm_case_family_join"))
    weakest_metric_path = _as_dict(normalization_audit.get("integration_metric_path"))
    category_case_ids = _sorted_str_list(category_join.get("case_ids"))
    direct_cgm_case_ids = _sorted_str_list(direct_cgm_join.get("case_ids"))
    parser_case_id_overlap_with_weakest = sorted(set(parser_case_ids) & set(category_case_ids))
    parser_case_id_overlap_with_direct_cgm = sorted(set(parser_case_ids) & set(direct_cgm_case_ids))
    blocks_kpi_interpretation = not (
        normalization_audit.get("normalization_drift_detected") is False
        and not _sorted_str_list(normalization_audit.get("validation_issues"))
        and normalization_checks.get("integration_path_connected") is True
        and category_join.get("pooled_score_matches_weakest_metric") is True
        and direct_cgm_join.get("join_status") == "connected"
        and weakest_family_summary.get("coverage_status") == "connected"
    )

    decision = {
        "audit_name": "parser_case_id_mismatch_decision_v1",
        "source_artifacts": {
            "parser_report_path": str(parser_report_path),
            "normalization_audit_path": str(normalization_audit_path),
            "weakest_slice_summary_path": str(weakest_slice_summary_path),
        },
        "decision_gate": {
            "blocks_kpi_interpretation": blocks_kpi_interpretation,
            "decision": (
                "mismatch_not_blocking_current_kpi_interpretation"
                if not blocks_kpi_interpretation
                else "mismatch_still_blocks_current_kpi_interpretation"
            ),
            "reason_codes": _reason_codes(
                normalization_audit=normalization_audit,
                normalization_checks=normalization_checks,
                category_join=category_join,
                direct_cgm_join=direct_cgm_join,
                parser_case_id_overlap_with_weakest=parser_case_id_overlap_with_weakest,
                parser_case_id_overlap_with_direct_cgm=parser_case_id_overlap_with_direct_cgm,
            ),
        },
        "evidence_summary": {
            "parser_fixture_scope": {
                "cases_json_path": parser_report.get("cases_json_path"),
                "parser_case_ids": parser_case_ids,
                "parser_case_count": parser_report.get("case_count"),
                "supported_failure_type_count": len(
                    _sorted_str_list(parser_report.get("supported_failure_types"))
                ),
            },
            "weakest_metric_anchor": {
                "family": "free_text_alias",
                "coverage_status": weakest_family_summary.get("coverage_status"),
                "case_count": weakest_family_summary.get("case_count"),
                "weakest_metrics": _sorted_str_list(
                    weakest_family_summary.get("weakest_metrics")
                ),
                "score": weakest_metric_path.get("weakest_metric_score"),
                "required_component_statuses": _as_dict(
                    weakest_metric_path.get("required_component_statuses")
                ),
            },
            "category_join_proof": {
                "weakest_category": category_join.get("weakest_category"),
                "case_ids": category_case_ids,
                "modality_attempted_success": _as_dict(
                    category_join.get("modality_attempted_success")
                ),
                "pooled_score_matches_weakest_metric": category_join.get(
                    "pooled_score_matches_weakest_metric"
                ),
            },
            "direct_cgm_join_proof": {
                "selected_family": direct_cgm_join.get("selected_family"),
                "case_ids": direct_cgm_case_ids,
                "join_status": direct_cgm_join.get("join_status"),
                "selection_rule": direct_cgm_join.get("selection_rule"),
                "modality_attempted_success": _as_dict(
                    direct_cgm_join.get("modality_attempted_success")
                ),
            },
            "case_id_mismatch_summary": {
                "parser_case_id_overlap_with_weakest_family": parser_case_id_overlap_with_weakest,
                "parser_case_id_overlap_with_direct_cgm_family": (
                    parser_case_id_overlap_with_direct_cgm
                ),
                "parser_case_ids_match_frozen_eval_case_ids_one_by_one": (
                    bool(parser_case_id_overlap_with_weakest)
                    or bool(parser_case_id_overlap_with_direct_cgm)
                ),
            },
            "normalization_validation": {
                "normalization_drift_detected": normalization_audit.get(
                    "normalization_drift_detected"
                ),
                "validation_issues": _sorted_str_list(
                    normalization_audit.get("validation_issues")
                ),
                "integration_path_connected": normalization_checks.get(
                    "integration_path_connected"
                ),
            },
        },
        "decision_rationale": [
            (
                "The parser sample fixtures still do not share frozen-eval case_ids one by one, "
                "so case-level lineage remains indirect."
            ),
            (
                "That mismatch does not currently block KPI interpretation because the weakest "
                "sensor/genetic score is reproduced at category level and the direct CGM-carrying "
                "family join is already connected."
            ),
            (
                "This leaves the mismatch as an attribution/readability limitation rather than "
                "a current KPI-path break."
            ),
        ],
        "summary_findings": [
            (
                "Current parser case-id mismatch is real, but it is not blocking the present "
                "`sensor_genetic_integration_rate_pct` interpretation."
            ),
            (
                "Category-level weakest-family proof and direct CGM family proof are enough "
                "to keep the KPI path readable for now."
            ),
            (
                "Only revisit the mismatch if one-to-one parser-to-eval lineage becomes "
                "necessary for a narrower KPI or failure-family claim."
            ),
        ],
    }
    decision["validation_issues"] = validate_parser_case_id_mismatch_decision(decision)
    return decision


def validate_parser_case_id_mismatch_decision(
    decision: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    weakest_metric_anchor = _as_dict(evidence.get("weakest_metric_anchor"))
    category_join_proof = _as_dict(evidence.get("category_join_proof"))
    direct_cgm_join_proof = _as_dict(evidence.get("direct_cgm_join_proof"))
    normalization_validation = _as_dict(evidence.get("normalization_validation"))

    if gate.get("blocks_kpi_interpretation") is True:
        issues.append("parser_case_id_mismatch_still_marked_blocking")
    if gate.get("decision") != "mismatch_not_blocking_current_kpi_interpretation":
        issues.append("unexpected_parser_case_id_mismatch_decision")
    if weakest_metric_anchor.get("coverage_status") != "connected":
        issues.append("weakest_metric_anchor_not_connected")
    if category_join_proof.get("pooled_score_matches_weakest_metric") is not True:
        issues.append("category_join_does_not_match_metric")
    if direct_cgm_join_proof.get("join_status") != "connected":
        issues.append("direct_cgm_join_not_connected")
    if normalization_validation.get("normalization_drift_detected") is not False:
        issues.append("normalization_drift_detected")
    if normalization_validation.get("integration_path_connected") is not True:
        issues.append("integration_path_not_connected")
    return issues


def render_parser_case_id_mismatch_decision_markdown(
    decision: dict[str, object],
) -> str:
    lines = [
        "# parser case-id mismatch decision v1",
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


def write_parser_case_id_mismatch_decision_files(
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
        render_parser_case_id_mismatch_decision_markdown(decision),
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
    normalization_audit: dict[str, object],
    normalization_checks: dict[str, object],
    category_join: dict[str, object],
    direct_cgm_join: dict[str, object],
    parser_case_id_overlap_with_weakest: list[str],
    parser_case_id_overlap_with_direct_cgm: list[str],
) -> list[str]:
    reason_codes: list[str] = []
    if normalization_audit.get("normalization_drift_detected") is False:
        reason_codes.append("no_normalization_drift_detected")
    if normalization_checks.get("integration_path_connected") is True:
        reason_codes.append("category_level_kpi_anchor_connected")
    if category_join.get("pooled_score_matches_weakest_metric") is True:
        reason_codes.append("weakest_metric_score_reproduced")
    if direct_cgm_join.get("join_status") == "connected":
        reason_codes.append("direct_cgm_family_join_present")
    if not parser_case_id_overlap_with_weakest and not parser_case_id_overlap_with_direct_cgm:
        reason_codes.append("fixture_case_ids_do_not_match_eval_case_ids")
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
    "build_parser_case_id_mismatch_decision",
    "load_json_artifact",
    "render_parser_case_id_mismatch_decision_markdown",
    "validate_parser_case_id_mismatch_decision",
    "write_parser_case_id_mismatch_decision_files",
]
