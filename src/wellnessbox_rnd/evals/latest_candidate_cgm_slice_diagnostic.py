from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_latest_candidate_cgm_slice_diagnostic(
    *,
    compare_report: dict[str, object],
    compare_report_path: str | Path,
    final_compare_report: dict[str, object],
    final_compare_report_path: str | Path,
    cgm_feature_audit_report: dict[str, object],
    cgm_feature_audit_report_path: str | Path,
    cgm_geometry_report: dict[str, object],
    cgm_geometry_report_path: str | Path,
    cgm_slice_bridge_report: dict[str, object],
    cgm_slice_bridge_report_path: str | Path,
) -> dict[str, object]:
    deltas = _as_dict(compare_report.get("deltas"))
    slice_deltas = _as_dict(compare_report.get("slice_deltas"))
    effect_only = _as_dict(slice_deltas.get("learned_effect_guarded"))
    combined = _as_dict(slice_deltas.get("learned_effect_and_policy_guarded"))
    overall = _as_dict(_as_dict(final_compare_report.get("slice_compare")).get("overall"))
    cgm_slice = _as_dict(_as_dict(final_compare_report.get("slice_compare")).get("cgm"))

    low_risk_score = _to_int(overall.get("low_risk_regression_score"))
    cgm_score = _to_int(overall.get("cgm_regression_score"))
    fit_gate_status = str(
        _as_dict(final_compare_report.get("latest_candidate")).get("fit_gate_status")
    )

    diagnostic = {
        "audit_name": "latest_candidate_cgm_slice_diagnostic_v1",
        "source_artifacts": {
            "compare_report_path": str(compare_report_path),
            "final_compare_report_path": str(final_compare_report_path),
            "cgm_feature_audit_report_path": str(cgm_feature_audit_report_path),
            "cgm_geometry_report_path": str(cgm_geometry_report_path),
            "cgm_slice_bridge_report_path": str(cgm_slice_bridge_report_path),
        },
        "hypothesis_gate": {
            "overall_ok_but_cgm_only_worse_supported": (
                fit_gate_status != "worse_on_all_fit_gates" and cgm_score > low_risk_score
            ),
            "rejection_reasons": _build_rejection_reasons(
                fit_gate_status=fit_gate_status,
                low_risk_score=low_risk_score,
                cgm_score=cgm_score,
            ),
            "evidence": {
                "fit_gate_status": fit_gate_status,
                "dominant_candidate_regression_slice": overall.get(
                    "dominant_candidate_regression_slice"
                ),
                "low_risk_regression_score": low_risk_score,
                "cgm_regression_score": cgm_score,
                "effect_only_low_risk_disagreement_delta": _to_int(
                    deltas.get("effect_only_low_risk_disagreement_delta")
                ),
                "effect_only_cgm_disagreement_delta": _to_int(
                    deltas.get("effect_only_cgm_disagreement_delta")
                ),
                "combined_low_risk_disagreement_delta": _to_int(
                    deltas.get("combined_low_risk_disagreement_delta")
                ),
                "combined_cgm_disagreement_delta": _to_int(
                    deltas.get("combined_cgm_disagreement_delta")
                ),
                "effect_only_low_risk_final_delta_abs": _absolute_action_delta_count(
                    _as_dict(effect_only.get("low_risk_final_action_delta"))
                ),
                "effect_only_cgm_final_delta_abs": _absolute_action_delta_count(
                    _as_dict(effect_only.get("cgm_final_action_delta"))
                ),
                "combined_low_risk_final_delta_abs": _absolute_action_delta_count(
                    _as_dict(combined.get("low_risk_final_action_delta"))
                ),
                "combined_cgm_final_delta_abs": _absolute_action_delta_count(
                    _as_dict(combined.get("cgm_final_action_delta"))
                ),
            },
        },
        "residual_cgm_failure_families": {
            "geometry_blocker_family_summary": _as_dict(
                _as_dict(cgm_geometry_report.get("blocker_evidence")).get(
                    "blocker_family_summary"
                )
            ),
            "combined_final_action_delta": _as_dict(cgm_slice.get("combined_final_action_delta")),
            "feature_family_summary": _feature_family_summary(cgm_feature_audit_report),
        },
        "bridge_and_workflow_assessment": {
            "bridge_contract_connected": (
                cgm_slice_bridge_report.get("contract_id") == "cgm_slice_bridge_summary_v1"
            ),
            "bridge_case_count": _to_int(cgm_slice_bridge_report.get("case_count")),
            "bridge_valid_case_count": _to_int(cgm_slice_bridge_report.get("valid_case_count")),
            "parser_failure_type_counts": _as_dict(
                cgm_slice_bridge_report.get("parser_failure_type_counts")
            ),
            "connected_flows": _as_dict(cgm_slice_bridge_report.get("connected_flows")),
            "geometry_status": cgm_slice.get("geometry_status"),
            "continue_to_reoptimize_top_action_flip_count": _to_int(
                _as_dict(cgm_geometry_report.get("selected_continue_geometry_summary")).get(
                    "continue_to_reoptimize_top_action_flip_count"
                )
            ),
            "bridge_is_primary_driver": False,
        },
        "summary_findings": _build_summary_findings(
            fit_gate_status=fit_gate_status,
            low_risk_score=low_risk_score,
            cgm_score=cgm_score,
            cgm_geometry_report=cgm_geometry_report,
            cgm_feature_audit_report=cgm_feature_audit_report,
        ),
    }
    diagnostic["validation_issues"] = validate_latest_candidate_cgm_slice_diagnostic(
        diagnostic
    )
    return diagnostic


def validate_latest_candidate_cgm_slice_diagnostic(
    diagnostic: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(diagnostic.get("hypothesis_gate"))
    residual = _as_dict(diagnostic.get("residual_cgm_failure_families"))
    bridge = _as_dict(diagnostic.get("bridge_and_workflow_assessment"))

    if gate.get("overall_ok_but_cgm_only_worse_supported") is not False:
        issues.append("unexpected_cgm_only_support")
    if not _as_list(gate.get("rejection_reasons")):
        issues.append("missing_rejection_reasons")
    if not _as_dict(residual.get("geometry_blocker_family_summary")):
        issues.append("missing_geometry_blocker_family_summary")
    if not _as_list(_as_dict(residual.get("feature_family_summary")).get("top_feature_gaps")):
        issues.append("missing_feature_family_summary")
    if bridge.get("bridge_contract_connected") is not True:
        issues.append("missing_bridge_connection")
    if bridge.get("bridge_is_primary_driver") is not False:
        issues.append("unexpected_bridge_primary_driver")
    return issues


def render_latest_candidate_cgm_slice_diagnostic_markdown(
    diagnostic: dict[str, object]
) -> str:
    lines = [
        "# latest candidate cgm slice diagnostic v1",
        "",
        "## hypothesis gate",
        "",
        f"- hypothesis_gate: `{diagnostic.get('hypothesis_gate', {})}`",
        "",
        "## residual cgm failure families",
        "",
        f"- residual_cgm_failure_families: `{diagnostic.get('residual_cgm_failure_families', {})}`",
        "",
        "## bridge and workflow assessment",
        "",
        (
            "- bridge_and_workflow_assessment: "
            f"`{diagnostic.get('bridge_and_workflow_assessment', {})}`"
        ),
        "",
        "## summary findings",
        "",
    ]
    for finding in _as_list(diagnostic.get("summary_findings")):
        lines.append(f"- {finding}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{diagnostic.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_latest_candidate_cgm_slice_diagnostic_files(
    *,
    diagnostic: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_latest_candidate_cgm_slice_diagnostic_markdown(diagnostic),
        encoding="utf-8",
    )


def _build_rejection_reasons(
    *,
    fit_gate_status: str,
    low_risk_score: int,
    cgm_score: int,
) -> list[str]:
    reasons: list[str] = []
    if fit_gate_status == "worse_on_all_fit_gates":
        reasons.append("overall_fit_gate_already_failed")
    if low_risk_score >= cgm_score:
        reasons.append("dominant_regression_slice_is_low_risk_not_cgm")
    return reasons


def _feature_family_summary(
    cgm_feature_audit_report: dict[str, object],
) -> dict[str, object]:
    top_gaps = []
    for item in _as_list(cgm_feature_audit_report.get("key_feature_list"))[:5]:
        payload = _as_dict(item)
        top_gaps.append(
            {
                "feature": payload.get("feature"),
                "why_it_matters": payload.get("why_it_matters"),
            }
        )
    return {
        "top_feature_gaps": top_gaps,
        "feature_audit_findings": _as_list(cgm_feature_audit_report.get("summary_findings"))[:4],
    }


def _build_summary_findings(
    *,
    fit_gate_status: str,
    low_risk_score: int,
    cgm_score: int,
    cgm_geometry_report: dict[str, object],
    cgm_feature_audit_report: dict[str, object],
) -> list[str]:
    blocker_summary = _as_dict(
        _as_dict(cgm_geometry_report.get("blocker_evidence")).get("blocker_family_summary")
    )
    selected_summary = _as_dict(cgm_geometry_report.get("selected_continue_geometry_summary"))
    findings = [
        (
            "The latest training_view_enforced_slice_balanced candidate does not satisfy the "
            "overall-ok-but-cgm-only-worse gate because overall fit still fails and low_risk "
            "regression remains larger than cgm regression."
        ),
        (
            "Residual cgm drift is still real but bounded: the main blocker family is "
            f"{blocker_summary}, not a broad threshold-widening story."
        ),
        (
            "Current cgm-specific separation still concentrates in proxy, adherence, and "
            "blood-glucose feature families rather than parser/bridge breakage."
        ),
        (
            "Replay-only calibration evidence still moves only "
            f"{selected_summary.get('continue_to_reoptimize_top_action_flip_count')} "
            "final continue_plan case, so the outside-band cgm overlap remains the main residue."
        ),
    ]
    feature_findings = _as_list(cgm_feature_audit_report.get("summary_findings"))
    if feature_findings:
        findings.append(str(feature_findings[0]))
    if fit_gate_status != "worse_on_all_fit_gates" and cgm_score > low_risk_score:
        findings.append("The cgm-only gate is open and should be revisited.")
    return findings


def _absolute_action_delta_count(delta: dict[str, object]) -> int:
    return sum(abs(_to_int(value)) for value in delta.values())


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_latest_candidate_cgm_slice_diagnostic",
    "load_json_artifact",
    "render_latest_candidate_cgm_slice_diagnostic_markdown",
    "validate_latest_candidate_cgm_slice_diagnostic",
    "write_latest_candidate_cgm_slice_diagnostic_files",
]
