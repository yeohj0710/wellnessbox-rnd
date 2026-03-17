from __future__ import annotations

import json
from pathlib import Path


def load_json_artifact(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_effect_training_revisit_stability_decision(
    *,
    prior_revisit_decision: dict[str, object],
    prior_revisit_decision_path: str | Path,
    baseline_candidate_summary: dict[str, object],
    baseline_candidate_summary_path: str | Path,
    replay_split_audit: dict[str, object],
    replay_split_audit_path: str | Path,
    non_cgm_diagnostic: dict[str, object],
    non_cgm_diagnostic_path: str | Path,
) -> dict[str, object]:
    prior_gate = _as_dict(prior_revisit_decision.get("decision_gate"))
    candidate_comparison = _as_dict(baseline_candidate_summary.get("candidate_comparison"))
    weakest_slice_delta = _as_dict(baseline_candidate_summary.get("weakest_slice_delta"))
    adoption_summary = _as_dict(baseline_candidate_summary.get("adoption_summary"))
    replay_assessment = _as_dict(replay_split_audit.get("assessment"))
    target_family = _as_dict(non_cgm_diagnostic.get("target_family"))
    workflow_summary = _as_dict(non_cgm_diagnostic.get("workflow_summary"))

    fit_gate_status = str(candidate_comparison.get("fit_gate_status") or "")
    effect_only_shift_concentration = str(
        replay_assessment.get("effect_only_shift_concentration") or ""
    )
    combined_shift_concentration = str(
        replay_assessment.get("combined_shift_concentration") or ""
    )
    unresolved_family_name = str(target_family.get("name") or "")
    unresolved_case_count = _to_int(target_family.get("observed_case_count"))

    material_replay_change_detected = any(
        (
            fit_gate_status != "worse_on_all_fit_gates",
            effect_only_shift_concentration != "supported_effect_enriched",
            combined_shift_concentration != "supported_effect_enriched",
            unresolved_family_name != "non_cgm_continue_to_monitor_threshold_cross",
            unresolved_case_count <= 0,
            adoption_summary.get("decision") != "hold_baseline_candidate_not_ready",
            prior_gate.get("decision") != "defer_new_effect_training_loop",
        )
    )

    revisit_justified_now = material_replay_change_detected
    decision = {
        "audit_name": "effect_training_revisit_stability_decision_v1",
        "source_artifacts": {
            "prior_revisit_decision_path": str(prior_revisit_decision_path),
            "baseline_candidate_summary_path": str(baseline_candidate_summary_path),
            "replay_split_audit_path": str(replay_split_audit_path),
            "non_cgm_diagnostic_path": str(non_cgm_diagnostic_path),
        },
        "decision_gate": {
            "material_replay_change_detected": material_replay_change_detected,
            "revisit_justified_now": revisit_justified_now,
            "decision": (
                "current_defer_decision_still_holds"
                if not material_replay_change_detected
                else "replay_change_detected_revisit_can_be_reconsidered"
            ),
            "reason_codes": _reason_codes(
                prior_gate=prior_gate,
                fit_gate_status=fit_gate_status,
                effect_only_shift_concentration=effect_only_shift_concentration,
                combined_shift_concentration=combined_shift_concentration,
                unresolved_family_name=unresolved_family_name,
                unresolved_case_count=unresolved_case_count,
                adoption_summary=adoption_summary,
            ),
        },
        "evidence_summary": {
            "prior_defer_gate": {
                "prior_decision": prior_gate.get("decision"),
                "prior_revisit_justified_now": prior_gate.get("revisit_justified_now"),
                "prior_reason_codes": _sorted_str_list(prior_gate.get("reason_codes")),
            },
            "current_fit_gate": {
                "adoption_decision": adoption_summary.get("decision"),
                "fit_gate_status": fit_gate_status,
                "delta_summary": _as_dict(candidate_comparison.get("delta_summary")),
                "dominant_candidate_regression_slice": weakest_slice_delta.get(
                    "dominant_candidate_regression_slice"
                ),
            },
            "current_replay_split_gate": {
                "verdict": replay_assessment.get("verdict"),
                "effect_only_shift_concentration": effect_only_shift_concentration,
                "combined_shift_concentration": combined_shift_concentration,
                "supported_effect_only_changed_trace_user_count": replay_assessment.get(
                    "supported_effect_only_changed_trace_user_count"
                ),
                "unsupported_effect_only_changed_trace_user_count": replay_assessment.get(
                    "unsupported_effect_only_changed_trace_user_count"
                ),
                "supported_combined_changed_trace_user_count": replay_assessment.get(
                    "supported_combined_changed_trace_user_count"
                ),
                "unsupported_combined_changed_trace_user_count": replay_assessment.get(
                    "unsupported_combined_changed_trace_user_count"
                ),
            },
            "current_unresolved_replay_family": {
                "target_family": unresolved_family_name,
                "observed_case_count": unresolved_case_count,
                "transition": target_family.get("transition"),
                "trajectory_mode_counts": _as_dict(
                    workflow_summary.get("trajectory_mode_counts")
                ),
            },
        },
        "decision_rationale": [
            (
                "This loop checks only whether newer replay-only evidence overturns the "
                "existing defer-new-training decision."
            ),
            (
                "It does not: baseline still wins all fit gates, replay shift remains "
                "concentrated in supported effect-enriched users, and the dominant non-cgm "
                "threshold-cross family is still unresolved."
            ),
            (
                "Because no replay-only gate moved materially, the current defer decision "
                "still holds and another training loop remains premature."
            ),
        ],
        "summary_findings": [
            (
                "No material replay-only change has appeared since the prior defer decision."
            ),
            (
                "Effect training should remain deferred until replay evidence, not just "
                "non-replay audit cleanup, materially improves."
            ),
        ],
    }
    decision["validation_issues"] = validate_effect_training_revisit_stability_decision(
        decision
    )
    return decision


def validate_effect_training_revisit_stability_decision(
    decision: dict[str, object],
) -> list[str]:
    issues: list[str] = []
    gate = _as_dict(decision.get("decision_gate"))
    evidence = _as_dict(decision.get("evidence_summary"))
    prior_gate = _as_dict(evidence.get("prior_defer_gate"))
    fit_gate = _as_dict(evidence.get("current_fit_gate"))
    replay_gate = _as_dict(evidence.get("current_replay_split_gate"))
    unresolved = _as_dict(evidence.get("current_unresolved_replay_family"))

    if gate.get("material_replay_change_detected") is not False:
        issues.append("unexpected_material_replay_change_detected")
    if gate.get("revisit_justified_now") is not False:
        issues.append("revisit_gate_should_still_be_false")
    if gate.get("decision") != "current_defer_decision_still_holds":
        issues.append("unexpected_revisit_stability_decision")
    if prior_gate.get("prior_decision") != "defer_new_effect_training_loop":
        issues.append("prior_defer_decision_missing")
    if fit_gate.get("fit_gate_status") != "worse_on_all_fit_gates":
        issues.append("fit_gate_status_changed")
    if replay_gate.get("effect_only_shift_concentration") != "supported_effect_enriched":
        issues.append("effect_only_shift_concentration_changed")
    if replay_gate.get("combined_shift_concentration") != "supported_effect_enriched":
        issues.append("combined_shift_concentration_changed")
    if unresolved.get("target_family") != "non_cgm_continue_to_monitor_threshold_cross":
        issues.append("unexpected_current_unresolved_family")
    if _to_int(unresolved.get("observed_case_count")) <= 0:
        issues.append("unresolved_family_case_count_missing")
    return issues


def render_effect_training_revisit_stability_decision_markdown(
    decision: dict[str, object],
) -> str:
    lines = [
        "# effect training revisit stability decision v1",
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


def write_effect_training_revisit_stability_decision_files(
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
        render_effect_training_revisit_stability_decision_markdown(decision),
        encoding="utf-8",
    )


def _reason_codes(
    *,
    prior_gate: dict[str, object],
    fit_gate_status: str,
    effect_only_shift_concentration: str,
    combined_shift_concentration: str,
    unresolved_family_name: str,
    unresolved_case_count: int,
    adoption_summary: dict[str, object],
) -> list[str]:
    reasons: list[str] = []
    if prior_gate.get("decision") == "defer_new_effect_training_loop":
        reasons.append("prior_defer_decision_present")
    if adoption_summary.get("decision") == "hold_baseline_candidate_not_ready":
        reasons.append("baseline_hold_still_present")
    if fit_gate_status == "worse_on_all_fit_gates":
        reasons.append("fit_gate_status_unchanged")
    if effect_only_shift_concentration == "supported_effect_enriched":
        reasons.append("effect_only_shift_still_supported_concentrated")
    if combined_shift_concentration == "supported_effect_enriched":
        reasons.append("combined_shift_still_supported_concentrated")
    if (
        unresolved_family_name == "non_cgm_continue_to_monitor_threshold_cross"
        and unresolved_case_count > 0
    ):
        reasons.append("dominant_non_cgm_replay_family_still_unresolved")
    return reasons


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
    "build_effect_training_revisit_stability_decision",
    "load_json_artifact",
    "render_effect_training_revisit_stability_decision_markdown",
    "validate_effect_training_revisit_stability_decision",
    "write_effect_training_revisit_stability_decision_files",
]
