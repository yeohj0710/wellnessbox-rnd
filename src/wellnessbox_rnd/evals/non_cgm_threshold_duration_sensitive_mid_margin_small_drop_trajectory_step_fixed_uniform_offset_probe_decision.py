from __future__ import annotations

import json
from pathlib import Path

TARGET_FEATURE = "trajectory_step"
TARGET_MODE = "fixed_uniform_offset"
TARGET_PROBE_FRACTION = 0.5
DEFERRED_LOWER_FRACTION = 0.25
DEFERRED_HIGHER_FRACTION = 1.0


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_trajectory_step_fixed_uniform_offset_probe_decision(
    *,
    feasibility: dict[str, object],
    feasibility_path: str | Path,
    mode_decision: dict[str, object],
    mode_decision_path: str | Path,
) -> dict[str, object]:
    feasibility_gate = _as_dict(feasibility.get("decision_gate"))
    feasibility_evidence = _as_dict(feasibility.get("evidence_summary"))
    probe_grid_digest = _as_dict(feasibility_evidence.get("probe_grid_digest"))
    probe_grid = [_as_dict(row) for row in _as_list(probe_grid_digest.get("probe_grid"))]
    mode_gate = _as_dict(mode_decision.get("decision_gate"))

    half_probe = _find_probe(probe_grid, TARGET_PROBE_FRACTION)
    quarter_probe = _find_probe(probe_grid, DEFERRED_LOWER_FRACTION)
    full_probe = _find_probe(probe_grid, DEFERRED_HIGHER_FRACTION)

    decision = {
        "audit_name": (
            "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
            "trajectory_step_fixed_uniform_offset_probe_decision_v1"
        ),
        "source_artifacts": {
            "feasibility_path": str(feasibility_path),
            "mode_decision_path": str(mode_decision_path),
        },
        "decision_gate": {
            "trajectory_mode": feasibility_gate.get("trajectory_mode"),
            "margin_bucket": feasibility_gate.get("margin_bucket"),
            "proxy_drop_bucket": feasibility_gate.get("proxy_drop_bucket"),
            "chosen_first_opposing_feature": feasibility_gate.get(
                "chosen_first_opposing_feature"
            ),
            "chosen_local_handling_mode": feasibility_gate.get(
                "chosen_local_handling_mode"
            ),
            "decision": "use_half_offset_probe_first",
            "chosen_probe_fraction": TARGET_PROBE_FRACTION,
            "chosen_probe_offset_abs_value": half_probe.get("offset_abs_value"),
            "chosen_probe_clears_all_cases": half_probe.get("clears_all_cases"),
            "lower_probe_left_deferred": True,
            "higher_probe_left_deferred": True,
        },
        "evidence_summary": {
            "probe_comparison_digest": {
                "quarter_probe": quarter_probe,
                "half_probe": half_probe,
                "full_probe": full_probe,
            },
            "selection_digest": {
                "first_grid_fraction_clearing_all": feasibility_gate.get(
                    "first_grid_fraction_clearing_all"
                ),
                "minimum_clearing_fraction_of_full_offset": _as_dict(
                    feasibility_evidence.get("offset_digest")
                ).get("minimum_clearing_fraction_of_full_offset"),
                "trajectory_step_value_uniform": mode_gate.get(
                    "trajectory_step_value_uniform"
                ),
                "final_cycle_index_uniform": mode_gate.get("final_cycle_index_uniform"),
            },
        },
        "summary_findings": [
            (
                "The first bounded clearing probe should be `0.5` because `0.25` leaves one "
                "case uncleared while `0.5` clears all 5."
            ),
            (
                "Keep `1.0` deferred because it is larger than needed for the current 5-case "
                "slice."
            ),
            "Do not widen to cycle-conditioned handling or a second feature before this probe.",
        ],
    }
    decision["validation_issues"] = validate_trajectory_step_fixed_uniform_offset_probe_decision(
        decision
    )
    return decision


def validate_trajectory_step_fixed_uniform_offset_probe_decision(
    decision: dict[str, object]
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    probe_comparison = _as_dict(evidence.get("probe_comparison_digest"))
    quarter_probe = _as_dict(probe_comparison.get("quarter_probe"))
    half_probe = _as_dict(probe_comparison.get("half_probe"))
    full_probe = _as_dict(probe_comparison.get("full_probe"))
    selection_digest = _as_dict(evidence.get("selection_digest"))

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
    if gate.get("decision") != "use_half_offset_probe_first":
        issues.append("unexpected_probe_decision")
    if gate.get("chosen_probe_fraction") != TARGET_PROBE_FRACTION:
        issues.append("unexpected_probe_fraction")
    if not bool(gate.get("chosen_probe_clears_all_cases")):
        issues.append("chosen_probe_does_not_clear_all_cases")
    if not bool(gate.get("lower_probe_left_deferred")):
        issues.append("lower_probe_not_deferred")
    if not bool(gate.get("higher_probe_left_deferred")):
        issues.append("higher_probe_not_deferred")
    if quarter_probe.get("fraction") != DEFERRED_LOWER_FRACTION:
        issues.append("quarter_probe_missing")
    if quarter_probe.get("clears_case_count") != 4:
        issues.append("quarter_probe_case_count_mismatch")
    if half_probe.get("fraction") != TARGET_PROBE_FRACTION:
        issues.append("half_probe_missing")
    if not bool(half_probe.get("clears_all_cases")):
        issues.append("half_probe_not_clearing")
    if full_probe.get("fraction") != DEFERRED_HIGHER_FRACTION:
        issues.append("full_probe_missing")
    if full_probe.get("offset_abs_value") <= half_probe.get("offset_abs_value", 0.0):
        issues.append("full_probe_not_larger_than_half_probe")
    if selection_digest.get("first_grid_fraction_clearing_all") != TARGET_PROBE_FRACTION:
        issues.append("unexpected_first_grid_fraction")
    if not bool(selection_digest.get("trajectory_step_value_uniform")):
        issues.append("trajectory_step_value_not_uniform")
    if not bool(selection_digest.get("final_cycle_index_uniform")):
        issues.append("final_cycle_not_uniform")
    if not _as_list(decision.get("summary_findings")):
        issues.append("summary_findings_missing")
    return issues


def render_trajectory_step_fixed_uniform_offset_probe_decision_markdown(
    decision: dict[str, object]
) -> str:
    lines = [
        (
            "# non-cgm threshold-duration-sensitive mid-margin small-drop "
            "trajectory-step fixed-uniform-offset probe decision v1"
        ),
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


def write_trajectory_step_fixed_uniform_offset_probe_decision_files(
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
        render_trajectory_step_fixed_uniform_offset_probe_decision_markdown(decision),
        encoding="utf-8",
    )


def _find_probe(
    probe_grid: list[dict[str, object]], target_fraction: float
) -> dict[str, object]:
    for row in probe_grid:
        if row.get("fraction") == target_fraction:
            return row
    return {}


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_trajectory_step_fixed_uniform_offset_probe_decision",
    "load_json_artifact",
    "render_trajectory_step_fixed_uniform_offset_probe_decision_markdown",
    "validate_trajectory_step_fixed_uniform_offset_probe_decision",
    "write_trajectory_step_fixed_uniform_offset_probe_decision_files",
]
