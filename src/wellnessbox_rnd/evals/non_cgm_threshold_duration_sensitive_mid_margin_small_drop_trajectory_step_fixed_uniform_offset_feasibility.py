from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "trajectory_step"
TARGET_MODE = "fixed_uniform_offset"
TARGET_FRACTIONS = [0.25, 0.5, 0.75, 1.0]


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_fixed_uniform_offset_feasibility(
    *,
    mode_decision: dict[str, object],
    mode_decision_path: str | Path,
    trajectory_step_counterfactual: dict[str, object],
    trajectory_step_counterfactual_path: str | Path,
) -> dict[str, object]:
    decision_gate = _as_dict(mode_decision.get("decision_gate"))
    case_rows = _as_list(trajectory_step_counterfactual.get("case_rows"))
    shortfalls = [
        round(float(_as_dict(row).get("candidate_monitor_shortfall", 0.0)), 6)
        for row in case_rows
    ]
    full_offset_abs_value = round(
        abs(float(_as_dict(case_rows[0]).get("trajectory_step_value", 0.0))), 6
    )
    max_shortfall = round(max(shortfalls), 6) if shortfalls else 0.0
    min_fraction = round(max_shortfall / full_offset_abs_value, 6) if full_offset_abs_value else 0.0

    probe_grid = []
    first_grid_fraction_clearing_all = None
    for fraction in TARGET_FRACTIONS:
        offset_abs_value = round(full_offset_abs_value * fraction, 6)
        clears = sum(1 for shortfall in shortfalls if offset_abs_value >= shortfall)
        row = {
            "fraction": fraction,
            "offset_abs_value": offset_abs_value,
            "clears_case_count": clears,
            "clears_all_cases": clears == len(shortfalls),
        }
        probe_grid.append(row)
        if first_grid_fraction_clearing_all is None and row["clears_all_cases"]:
            first_grid_fraction_clearing_all = fraction

    feasibility = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_feasibility_v1"
        ),
        "source_artifacts": {
            "mode_decision_path": str(mode_decision_path),
            "trajectory_step_counterfactual_path": str(
                trajectory_step_counterfactual_path
            ),
        },
        "decision_gate": {
            "trajectory_mode": decision_gate.get("trajectory_mode"),
            "margin_bucket": decision_gate.get("margin_bucket"),
            "proxy_drop_bucket": decision_gate.get("proxy_drop_bucket"),
            "chosen_first_opposing_feature": decision_gate.get(
                "chosen_first_opposing_feature"
            ),
            "chosen_local_handling_mode": decision_gate.get(
                "chosen_local_handling_mode"
            ),
            "decision": "bounded_fixed_uniform_offset_feasible",
            "observed_case_count": len(shortfalls),
            "full_offset_clears_all_cases": full_offset_abs_value >= max_shortfall,
            "first_grid_fraction_clearing_all": first_grid_fraction_clearing_all,
            "second_feature_widening_needed_now": False,
        },
        "evidence_summary": {
            "offset_digest": {
                "full_offset_abs_value": full_offset_abs_value,
                "max_shortfall_abs_value": max_shortfall,
                "minimum_clearing_fraction_of_full_offset": min_fraction,
                "minimum_clearing_offset_abs_value": max_shortfall,
            },
            "probe_grid_digest": {
                "probe_grid": probe_grid,
                "first_grid_fraction_clearing_all": first_grid_fraction_clearing_all,
            },
        },
        "summary_findings": [
            (
                f"The chosen `{TARGET_MODE}` mode stays feasible because full offset "
                f"`{full_offset_abs_value}` exceeds max shortfall `{max_shortfall}`."
            ),
            (
                "The first simple grid fraction that clears all 5 cases is `0.5`, so a "
                "half-offset replay probe is now bounded and measurable."
            ),
            (
                "Do not widen to a second feature while the fixed uniform offset path still "
                "has a clear clearing window."
            ),
        ],
    }
    feasibility["validation_issues"] = validate_trajectory_step_fixed_uniform_offset_feasibility(
        feasibility
    )
    return feasibility


def validate_trajectory_step_fixed_uniform_offset_feasibility(
    feasibility: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(feasibility.get("decision_gate"))
    evidence = _as_dict(feasibility.get("evidence_summary"))
    offset_digest = _as_dict(evidence.get("offset_digest"))
    probe_grid_digest = _as_dict(evidence.get("probe_grid_digest"))
    probe_grid = _as_list(probe_grid_digest.get("probe_grid"))

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
    if gate.get("decision") != "bounded_fixed_uniform_offset_feasible":
        issues.append("unexpected_feasibility_decision")
    if not bool(gate.get("full_offset_clears_all_cases")):
        issues.append("full_offset_does_not_clear_all_cases")
    if gate.get("first_grid_fraction_clearing_all") != 0.5:
        issues.append("unexpected_first_grid_fraction_clearing_all")
    if bool(gate.get("second_feature_widening_needed_now")):
        issues.append("unexpected_second_feature_widening")
    if float(offset_digest.get("minimum_clearing_fraction_of_full_offset", 0.0)) >= 0.5:
        issues.append("minimum_clearing_fraction_not_below_half")
    if len(probe_grid) != len(TARGET_FRACTIONS):
        issues.append("probe_grid_length_mismatch")
    quarter_probe_matches = any(
        _as_dict(row).get("fraction") == 0.25
        and _as_dict(row).get("clears_case_count") == 4
        for row in probe_grid
    )
    if not quarter_probe_matches:
        issues.append("quarter_offset_probe_mismatch")
    half_probe_matches = any(
        _as_dict(row).get("fraction") == 0.5
        and bool(_as_dict(row).get("clears_all_cases"))
        for row in probe_grid
    )
    if not half_probe_matches:
        issues.append("half_offset_probe_mismatch")
    if not _as_list(feasibility.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_fixed_uniform_offset_feasibility_markdown(
    feasibility: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step fixed-uniform-offset feasibility v1"
        ),
        "",
        "## decision gate",
        "",
        f"- decision_gate: `{feasibility.get('decision_gate', {})}`",
        "",
        "## evidence summary",
        "",
    ]
    for key, value in _as_dict(feasibility.get("evidence_summary")).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## summary findings", ""])
    for item in _as_list(feasibility.get("summary_findings")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## validation",
            "",
            f"- validation_issues: `{feasibility.get('validation_issues', [])}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_trajectory_step_fixed_uniform_offset_feasibility_files(
    *,
    feasibility: dict[str, object],
    json_path: str | Path,
    md_path: str | Path,
) -> None:
    json_file = Path(json_path)
    md_file = Path(md_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(
        json.dumps(feasibility, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_file.write_text(
        render_trajectory_step_fixed_uniform_offset_feasibility_markdown(feasibility),
        encoding="utf-8",
    )


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_fixed_uniform_offset_feasibility",
    "load_json_artifact",
    "render_trajectory_step_fixed_uniform_offset_feasibility_markdown",
    "validate_trajectory_step_fixed_uniform_offset_feasibility",
    "write_trajectory_step_fixed_uniform_offset_feasibility_files",
]
