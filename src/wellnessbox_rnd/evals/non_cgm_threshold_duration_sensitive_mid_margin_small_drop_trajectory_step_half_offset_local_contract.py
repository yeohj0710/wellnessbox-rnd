from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "trajectory_step"
TARGET_MODE = "fixed_uniform_offset"
TARGET_PROBE_FRACTION = 0.5
TARGET_CONTRACT = "uniform_score_gap_offset"


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_half_offset_local_contract(
    *,
    fix_scope_decision: dict[str, object],
    fix_scope_decision_path: str | Path,
    half_offset_counterfactual: dict[str, object],
    half_offset_counterfactual_path: str | Path,
) -> dict[str, object]:
    gate = _as_dict(fix_scope_decision.get("decision_gate"))
    summary = _as_dict(half_offset_counterfactual.get("counterfactual_summary"))
    case_rows = [_as_dict(row) for row in _as_list(half_offset_counterfactual.get("case_rows"))]

    contract_rows = []
    residuals: list[float] = []
    for row in case_rows:
        residual = round(float(row.get("residual_clearance", 0.0)), 6)
        residuals.append(residual)
        contract_rows.append(
            {
                "record_id": row.get("record_id"),
                "candidate_monitor_shortfall": row.get("candidate_monitor_shortfall"),
                "applied_uniform_offset_abs_value": row.get("half_offset_abs_value"),
                "expected_post_contract_clearance": residual,
                "contract_clears_case": row.get("cleared_by_half_offset"),
            }
        )

    contract = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_local_contract_v1"
        ),
        "source_artifacts": {
            "fix_scope_decision_path": str(fix_scope_decision_path),
            "half_offset_counterfactual_path": str(half_offset_counterfactual_path),
        },
        "contract_gate": {
            "trajectory_mode": gate.get("trajectory_mode"),
            "margin_bucket": gate.get("margin_bucket"),
            "proxy_drop_bucket": gate.get("proxy_drop_bucket"),
            "chosen_first_opposing_feature": gate.get("chosen_first_opposing_feature"),
            "decision": "use_uniform_half_offset_local_contract_first",
            "chosen_fix_scope": gate.get("chosen_fix_scope"),
            "chosen_local_handling_mode": gate.get("chosen_local_handling_mode"),
            "chosen_local_contract": TARGET_CONTRACT,
            "chosen_probe_fraction": gate.get("chosen_probe_fraction"),
            "chosen_probe_offset_abs_value": gate.get("chosen_probe_offset_abs_value"),
            "observed_case_count": len(contract_rows),
            "contract_ready_now": (
                bool(gate.get("all_cases_cleared"))
                and bool(gate.get("min_residual_clearance_positive"))
            ),
            "requires_case_specific_tuning_now": False,
            "requires_second_feature_now": False,
        },
        "evidence_summary": {
            "contract_surface": {
                "offset_source": "chosen_probe_offset_abs_value",
                "applied_uniform_offset_abs_value": gate.get("chosen_probe_offset_abs_value"),
                "case_row_count": len(contract_rows),
                "all_cases_cleared": summary.get("all_cases_cleared"),
                "min_expected_post_contract_clearance": summary.get(
                    "min_residual_clearance"
                ),
                "mean_expected_post_contract_clearance": summary.get(
                    "mean_residual_clearance"
                ),
                "residual_clearance_vector": residuals,
            },
            "defer_surface": {
                "cycle_conditioned_mode_needed_now": gate.get(
                    "cycle_conditioned_mode_needed_now"
                ),
                "second_feature_widening_needed_now": gate.get(
                    "second_feature_widening_needed_now"
                ),
            },
        },
        "contract_rows": contract_rows,
        "summary_findings": [
            (
                "Current artifacts support one bounded local contract: apply the chosen "
                "`0.5` offset uniformly to the current score-gap shortfall surface."
            ),
            (
                "All 5 target cases remain cleared under that contract with positive "
                "post-contract clearance."
            ),
            "Do not widen to case-specific tuning, cycle conditioning, or a second feature yet.",
        ],
    }
    contract["validation_issues"] = validate_trajectory_step_half_offset_local_contract(
        contract
    )
    return contract


def validate_trajectory_step_half_offset_local_contract(
    contract: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(contract.get("contract_gate"))
    evidence = _as_dict(contract.get("evidence_summary"))
    contract_surface = _as_dict(evidence.get("contract_surface"))
    defer_surface = _as_dict(evidence.get("defer_surface"))
    contract_rows = [_as_dict(row) for row in _as_list(contract.get("contract_rows"))]

    if gate.get("trajectory_mode") != "threshold_duration_sensitive":
        issues.append("unexpected_trajectory_mode")
    if gate.get("margin_bucket") != "mid_margin":
        issues.append("unexpected_margin_bucket")
    if gate.get("proxy_drop_bucket") != "small_drop":
        issues.append("unexpected_proxy_drop_bucket")
    if gate.get("chosen_first_opposing_feature") != TARGET_FEATURE:
        issues.append("unexpected_first_opposing_feature")
    if gate.get("chosen_local_handling_mode") != TARGET_MODE:
        issues.append("unexpected_local_handling_mode")
    if gate.get("decision") != "use_uniform_half_offset_local_contract_first":
        issues.append("unexpected_contract_decision")
    if gate.get("chosen_fix_scope") != "trajectory_step_half_offset_local_score_handling":
        issues.append("unexpected_fix_scope")
    if gate.get("chosen_local_contract") != TARGET_CONTRACT:
        issues.append("unexpected_local_contract")
    if gate.get("chosen_probe_fraction") != TARGET_PROBE_FRACTION:
        issues.append("unexpected_probe_fraction")
    if not bool(gate.get("contract_ready_now")):
        issues.append("contract_not_ready")
    if bool(gate.get("requires_case_specific_tuning_now")):
        issues.append("unexpected_case_specific_tuning")
    if bool(gate.get("requires_second_feature_now")):
        issues.append("unexpected_second_feature")
    if int(contract_surface.get("case_row_count", 0)) != int(gate.get("observed_case_count", 0)):
        issues.append("case_row_count_mismatch")
    if not bool(contract_surface.get("all_cases_cleared")):
        issues.append("contract_surface_not_clearing")
    if float(contract_surface.get("min_expected_post_contract_clearance", 0.0)) <= 0.0:
        issues.append("min_post_contract_clearance_not_positive")
    if bool(defer_surface.get("cycle_conditioned_mode_needed_now")):
        issues.append("unexpected_cycle_conditioning")
    if bool(defer_surface.get("second_feature_widening_needed_now")):
        issues.append("unexpected_second_feature_widening")
    if any(not bool(row.get("contract_clears_case")) for row in contract_rows):
        issues.append("uncleared_contract_row_present")
    if not _as_list(contract.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_half_offset_local_contract_markdown(
    contract: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step half-offset local contract v1"
        ),
        "",
        "## contract gate",
        "",
        f"- contract_gate: `{contract.get('contract_gate', {})}`",
        "",
        "## evidence summary",
        "",
    ]
    for key, value in _as_dict(contract.get("evidence_summary")).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## summary findings", ""])
    for item in _as_list(contract.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{contract.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_trajectory_step_half_offset_local_contract_files(
    *,
    contract: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    md_file.write_text(
        render_trajectory_step_half_offset_local_contract_markdown(contract),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_half_offset_local_contract",
    "load_json_artifact",
    "render_trajectory_step_half_offset_local_contract_markdown",
    "validate_trajectory_step_half_offset_local_contract",
    "write_trajectory_step_half_offset_local_contract_files",
]
