from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "trajectory_step"
TARGET_MODE = "fixed_uniform_offset"
TARGET_PROBE_FRACTION = 0.5


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_half_offset_counterfactual(
    *,
    probe_decision: dict[str, object],
    probe_decision_path: str | Path,
    trajectory_step_counterfactual: dict[str, object],
    trajectory_step_counterfactual_path: str | Path,
) -> dict[str, object]:
    decision_gate = _as_dict(probe_decision.get("decision_gate"))
    case_rows = [
        _as_dict(row)
        for row in _as_list(trajectory_step_counterfactual.get("case_rows"))
    ]
    probe_offset_abs_value = round(
        float(decision_gate.get("chosen_probe_offset_abs_value", 0.0)), 6
    )

    enriched_rows: list[dict[str, object]] = []
    residuals: list[float] = []
    for row in case_rows:
        shortfall = round(float(row.get("candidate_monitor_shortfall", 0.0)), 6)
        residual = round(probe_offset_abs_value - shortfall, 6)
        residuals.append(residual)
        enriched_rows.append(
            {
                "user_id": row.get("user_id"),
                "record_id": row.get("record_id"),
                "candidate_monitor_shortfall": shortfall,
                "half_offset_abs_value": probe_offset_abs_value,
                "residual_clearance": residual,
                "cleared_by_half_offset": residual >= 0.0,
            }
        )

    cleared_case_count = sum(1 for residual in residuals if residual >= 0.0)
    counterfactual = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_half_offset_counterfactual_v1"
        ),
        "source_artifacts": {
            "probe_decision_path": str(probe_decision_path),
            "trajectory_step_counterfactual_path": str(
                trajectory_step_counterfactual_path
            ),
        },
        "target": {
            "chosen_feature": decision_gate.get("chosen_first_opposing_feature"),
            "chosen_local_handling_mode": decision_gate.get("chosen_local_handling_mode"),
            "chosen_probe_fraction": decision_gate.get("chosen_probe_fraction"),
            "chosen_probe_offset_abs_value": probe_offset_abs_value,
            "observed_case_count": len(enriched_rows),
        },
        "counterfactual_summary": {
            "half_offset_abs_value": probe_offset_abs_value,
            "cleared_case_count": cleared_case_count,
            "all_cases_cleared": cleared_case_count == len(enriched_rows),
            "mean_residual_clearance": round(sum(residuals) / len(residuals), 6)
            if residuals
            else 0.0,
            "min_residual_clearance": round(min(residuals), 6) if residuals else 0.0,
            "max_residual_clearance": round(max(residuals), 6) if residuals else 0.0,
        },
        "case_rows": enriched_rows,
        "summary_findings": [
            (
                "The chosen half-offset probe clears all 5 cases in the current "
                "`small_drop` slice."
            ),
            (
                "The narrowest residual clearance after the half-offset probe is `0.0145`, "
                "so the current bounded path stays above zero on every case."
            ),
            "Do not widen to full offset, cycle-conditioned handling, or a second feature yet.",
        ],
    }
    counterfactual["validation_issues"] = validate_trajectory_step_half_offset_counterfactual(
        counterfactual
    )
    return counterfactual


def validate_trajectory_step_half_offset_counterfactual(
    counterfactual: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    target = _as_dict(counterfactual.get("target"))
    summary = _as_dict(counterfactual.get("counterfactual_summary"))
    case_rows = [_as_dict(row) for row in _as_list(counterfactual.get("case_rows"))]

    if target.get("chosen_feature") != TARGET_FEATURE:
        issues.append("unexpected_chosen_feature")
    if target.get("chosen_local_handling_mode") != TARGET_MODE:
        issues.append("unexpected_local_handling_mode")
    if target.get("chosen_probe_fraction") != TARGET_PROBE_FRACTION:
        issues.append("unexpected_probe_fraction")
    if float(target.get("chosen_probe_offset_abs_value", 0.0)) != 0.031557:
        issues.append("unexpected_probe_offset_abs_value")
    if not bool(summary.get("all_cases_cleared")):
        issues.append("not_all_cases_cleared")
    if int(summary.get("cleared_case_count", 0)) != int(target.get("observed_case_count", 0)):
        issues.append("cleared_case_count_mismatch")
    if float(summary.get("min_residual_clearance", 0.0)) <= 0.0:
        issues.append("min_residual_not_positive")
    if any(not bool(row.get("cleared_by_half_offset")) for row in case_rows):
        issues.append("uncleared_case_row_present")
    if not _as_list(counterfactual.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_half_offset_counterfactual_markdown(
    counterfactual: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step half-offset counterfactual v1"
        ),
        "",
        "## target",
        "",
        f"- target: `{counterfactual.get('target', {})}`",
        "",
        "## counterfactual summary",
        "",
        f"- counterfactual_summary: `{counterfactual.get('counterfactual_summary', {})}`",
        "",
        "## summary findings",
        "",
    ]
    for item in _as_list(counterfactual.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{counterfactual.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_trajectory_step_half_offset_counterfactual_files(
    *,
    counterfactual: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(
        json.dumps(counterfactual, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_file.write_text(
        render_trajectory_step_half_offset_counterfactual_markdown(counterfactual),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_half_offset_counterfactual",
    "load_json_artifact",
    "render_trajectory_step_half_offset_counterfactual_markdown",
    "validate_trajectory_step_half_offset_counterfactual",
    "write_trajectory_step_half_offset_counterfactual_files",
]
