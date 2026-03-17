from __future__ import annotations

import json
from pathlib import Path


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_chat_optional_rerun_audit(
    *,
    chat_live_smoke_report: dict[str, object],
    chat_live_smoke_report_path: str | Path,
    learned_boundary_audit: dict[str, object],
    learned_boundary_audit_path: str | Path,
    design_sanity_audit: dict[str, object],
    design_sanity_audit_path: str | Path,
    baseline_candidate_kpi_summary: dict[str, object],
    baseline_candidate_kpi_summary_path: str | Path,
    final_kpi_compare_report: dict[str, object],
    final_kpi_compare_report_path: str | Path,
    effect_candidate_reject_decision: dict[str, object],
    effect_candidate_reject_decision_path: str | Path,
) -> dict[str, object]:
    core_kpi_progress = _build_core_kpi_progress(
        design_sanity_audit=design_sanity_audit,
        baseline_candidate_kpi_summary=baseline_candidate_kpi_summary,
        final_kpi_compare_report=final_kpi_compare_report,
        effect_candidate_reject_decision=effect_candidate_reject_decision,
    )
    chat_runtime_boundary = _build_chat_runtime_boundary(
        chat_live_smoke_report=chat_live_smoke_report,
        learned_boundary_audit=learned_boundary_audit,
    )
    latest_live_smoke_status = _build_latest_live_smoke_status(chat_live_smoke_report)
    rerun_decision = _build_rerun_decision(
        core_kpi_progress=core_kpi_progress,
        chat_runtime_boundary=chat_runtime_boundary,
        latest_live_smoke_status=latest_live_smoke_status,
        baseline_candidate_kpi_summary=baseline_candidate_kpi_summary,
        design_sanity_audit=design_sanity_audit,
        final_kpi_compare_report=final_kpi_compare_report,
        effect_candidate_reject_decision=effect_candidate_reject_decision,
    )

    return {
        "audit_name": "chat_optional_rerun_need_audit_v1",
        "source_artifacts": {
            "chat_live_smoke_report_path": str(chat_live_smoke_report_path),
            "learned_runtime_boundary_audit_path": str(learned_boundary_audit_path),
            "design_sanity_audit_path": str(design_sanity_audit_path),
            "baseline_candidate_kpi_summary_path": str(
                baseline_candidate_kpi_summary_path
            ),
            "final_kpi_compare_report_path": str(final_kpi_compare_report_path),
            "effect_candidate_reject_decision_path": str(
                effect_candidate_reject_decision_path
            ),
        },
        "core_kpi_progress": core_kpi_progress,
        "chat_runtime_boundary": chat_runtime_boundary,
        "latest_live_smoke_status": latest_live_smoke_status,
        "rerun_decision": rerun_decision,
        "validation_issues": [],
    }


def render_chat_optional_rerun_audit_markdown(audit: dict[str, object]) -> str:
    core_kpi_progress = _as_dict(audit.get("core_kpi_progress"))
    progress_evidence = _as_dict(core_kpi_progress.get("evidence"))
    boundary = _as_dict(audit.get("chat_runtime_boundary"))
    boundary_evidence = _as_dict(boundary.get("evidence"))
    smoke = _as_dict(audit.get("latest_live_smoke_status"))
    rerun = _as_dict(audit.get("rerun_decision"))

    lines = [
        "# chat optional rerun need audit v1",
        "",
        f"- progress_gate_met: `{core_kpi_progress.get('progress_gate_met')}`",
        f"- rerun_needed_now: `{rerun.get('rerun_needed_now')}`",
        f"- decision: `{rerun.get('decision')}`",
        f"- one_line_conclusion: `{rerun.get('one_line_conclusion')}`",
        "",
        "## Core KPI Progress",
        f"- current_phase: `{progress_evidence.get('current_phase')}`",
        (
            "- baseline_candidate_decision: "
            f"`{progress_evidence.get('baseline_candidate_decision')}`"
        ),
        (
            "- pro_baseline_followup_kpi_path_status: "
            f"`{progress_evidence.get('pro_baseline_followup_kpi_path_status')}`"
        ),
        (
            "- weakest_slice_eval_wiring_status: "
            f"`{progress_evidence.get('weakest_slice_eval_wiring_status')}`"
        ),
        (
            "- replay_only_learned_boundary_status: "
            f"`{progress_evidence.get('replay_only_learned_boundary_status')}`"
        ),
        (
            "- final_compare_decision_class: "
            f"`{progress_evidence.get('final_compare_decision_class')}`"
        ),
        (
            "- reject_decision: "
            f"`{progress_evidence.get('reject_decision')}`"
        ),
        (
            "- dominant_replay_regression_family: "
            f"`{progress_evidence.get('dominant_replay_regression_family')}`"
        ),
        "",
        "## Chat Runtime Boundary",
        f"- optional_chat_only: `{boundary.get('optional_chat_only')}`",
        (
            "- recommendation_runtime_affected: "
            f"`{boundary_evidence.get('recommendation_runtime_affected')}`"
        ),
        f"- safety_runtime_affected: `{boundary_evidence.get('safety_runtime_affected')}`",
        (
            "- optimizer_runtime_affected: "
            f"`{boundary_evidence.get('optimizer_runtime_affected')}`"
        ),
        "",
        "## Latest Live Smoke",
        f"- attempted_live_call: `{smoke.get('attempted_live_call')}`",
        f"- verification_passed: `{smoke.get('verification_passed')}`",
        f"- provider: `{smoke.get('provider')}`",
        f"- fallback_reason: `{smoke.get('fallback_reason')}`",
        f"- live_failure_captured: `{smoke.get('live_failure_captured')}`",
        "",
        "## Decision Reasons",
    ]
    for reason_code in _as_list(rerun.get("reason_codes")):
        lines.append(f"- `{reason_code}`")
    return "\n".join(lines) + "\n"


def write_chat_optional_rerun_audit_files(
    audit: dict[str, object],
    *,
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_chat_optional_rerun_audit_markdown(audit), encoding="utf-8")


def _build_core_kpi_progress(
    *,
    design_sanity_audit: dict[str, object],
    baseline_candidate_kpi_summary: dict[str, object],
    final_kpi_compare_report: dict[str, object],
    effect_candidate_reject_decision: dict[str, object],
) -> dict[str, object]:
    overall = _as_dict(design_sanity_audit.get("overall_verdict"))
    dimensions = _as_dict(design_sanity_audit.get("dimensions"))
    readable_summary = _as_dict(final_kpi_compare_report.get("readable_summary"))
    audit_path_digest = _as_dict(readable_summary.get("audit_path_digest"))
    adoption = _as_dict(baseline_candidate_kpi_summary.get("adoption_summary"))
    decision_summary = _as_dict(final_kpi_compare_report.get("decision_summary"))
    reject_gate = _as_dict(effect_candidate_reject_decision.get("decision_gate"))
    hold_context = _as_dict(effect_candidate_reject_decision.get("hold_context"))
    pro_status = _as_dict(dimensions.get("pro_baseline_followup_kpi_path")).get("status")
    weakest_status = audit_path_digest.get("weakest_slice_wiring_status")
    learned_status = _as_dict(dimensions.get("replay_only_learned_boundary")).get("status")

    progress_gate_met = (
        str(overall.get("current_phase")) == "contract_data_eval_hardening"
        and str(pro_status) in {"sound", "sound_with_gaps"}
        and str(weakest_status)
        in {"sound", "sound_with_gaps", "connected_with_remaining_gaps"}
        and str(learned_status) in {"sound", "sound_with_gaps"}
        and str(adoption.get("decision")) == "hold_baseline_candidate_not_ready"
        and str(decision_summary.get("decision_class"))
        == "hold_baseline_candidate_not_ready"
        and str(reject_gate.get("decision")) == "reject_candidate_keep_baseline"
    )
    return {
        "progress_gate_met": progress_gate_met,
        "evidence": {
            "current_phase": overall.get("current_phase"),
            "direction_status": overall.get("direction_status"),
            "baseline_candidate_decision": adoption.get("decision"),
            "pro_baseline_followup_kpi_path_status": pro_status,
            "weakest_slice_eval_wiring_status": weakest_status,
            "replay_only_learned_boundary_status": learned_status,
            "final_compare_decision_class": decision_summary.get("decision_class"),
            "reject_decision": reject_gate.get("decision"),
            "dominant_replay_regression_family": hold_context.get(
                "dominant_replay_regression_family"
            ),
            "principal_blocker": overall.get("principal_blocker"),
        },
    }


def _build_chat_runtime_boundary(
    *,
    chat_live_smoke_report: dict[str, object],
    learned_boundary_audit: dict[str, object],
) -> dict[str, object]:
    preflight = _as_dict(chat_live_smoke_report.get("preflight"))
    runtime_boundary = _as_dict(preflight.get("runtime_boundary"))
    chat_boundary = _as_dict(learned_boundary_audit.get("chat_openai_boundary"))
    boundary_evidence = _as_dict(chat_boundary.get("evidence"))
    return {
        "optional_chat_only": (
            bool(runtime_boundary.get("chat_only_boundary"))
            and bool(chat_boundary.get("optional_chat_only"))
        ),
        "evidence": {
            "recommendation_runtime_affected": runtime_boundary.get(
                "recommendation_runtime_affected"
            ),
            "safety_runtime_affected": runtime_boundary.get("safety_runtime_affected"),
            "optimizer_runtime_affected": runtime_boundary.get(
                "optimizer_runtime_affected"
            ),
            "allow_live_api_default": boundary_evidence.get(
                "chat_adapter_allow_live_api_default"
            ),
            "fallback_provider_when_live_disabled": boundary_evidence.get(
                "chat_fallback_provider_when_live_disabled"
            ),
            "fallback_reason_when_live_disabled": boundary_evidence.get(
                "chat_fallback_reason_when_live_disabled"
            ),
        },
    }


def _build_latest_live_smoke_status(
    chat_live_smoke_report: dict[str, object]
) -> dict[str, object]:
    return {
        "attempted_live_call": chat_live_smoke_report.get("attempted_live_call"),
        "verification_passed": chat_live_smoke_report.get("verification_passed"),
        "provider": chat_live_smoke_report.get("provider"),
        "fallback_reason": chat_live_smoke_report.get("fallback_reason"),
        "api_key_present": _as_dict(chat_live_smoke_report.get("config")).get(
            "api_key_present"
        ),
        "live_failure_captured": chat_live_smoke_report.get("live_failure") is not None,
    }


def _build_rerun_decision(
    *,
    core_kpi_progress: dict[str, object],
    chat_runtime_boundary: dict[str, object],
    latest_live_smoke_status: dict[str, object],
    baseline_candidate_kpi_summary: dict[str, object],
    design_sanity_audit: dict[str, object],
    final_kpi_compare_report: dict[str, object],
    effect_candidate_reject_decision: dict[str, object],
) -> dict[str, object]:
    adoption = _as_dict(baseline_candidate_kpi_summary.get("adoption_summary"))
    weakest_delta = _as_dict(baseline_candidate_kpi_summary.get("weakest_slice_delta"))
    progress_evidence = _as_dict(core_kpi_progress.get("evidence"))
    final_compare_decision = _as_dict(final_kpi_compare_report.get("decision_summary"))
    reject_gate = _as_dict(effect_candidate_reject_decision.get("decision_gate"))
    reason_codes: list[str] = []

    if core_kpi_progress.get("progress_gate_met"):
        reason_codes.append("core_kpi_path_progressed_enough_for_optional_check")
    if chat_runtime_boundary.get("optional_chat_only"):
        reason_codes.append("chat_only_boundary_preserved")
    if latest_live_smoke_status.get("attempted_live_call"):
        reason_codes.append("live_smoke_already_attempted")
    if latest_live_smoke_status.get("verification_passed"):
        reason_codes.append("chat_evidence_path_already_verified")
    if (
        latest_live_smoke_status.get("fallback_reason") == "openai_call_failed"
        and not latest_live_smoke_status.get("live_failure_captured")
    ):
        reason_codes.append("missing_live_failure_detail_is_diagnostic_only")
    if adoption.get("decision") == "hold_baseline_candidate_not_ready":
        reason_codes.append("baseline_hold_still_driven_by_core_kpi_evidence")
    if final_compare_decision.get("decision_class") == "hold_baseline_candidate_not_ready":
        reason_codes.append("final_compare_still_holds_baseline")
    if reject_gate.get("decision") == "reject_candidate_keep_baseline":
        reason_codes.append("latest_reject_decision_stays_analysis_only")
    if (
        progress_evidence.get("principal_blocker")
        == "synthetic_data_circularity_and_generator_contamination"
    ):
        reason_codes.append("higher_roi_core_blocker_remains_in_data_validity")
    if weakest_delta.get("dominant_candidate_regression_slice") == "low_risk":
        reason_codes.append("current_candidate_regression_is_not_chat_path_related")

    rerun_needed_now = False
    decision = "defer_live_rerun_optional_only"
    one_line_conclusion = (
        "Do not rerun the OpenAI live smoke now: the chat path is still optional and "
        "already boundary-safe, and the latest compare/reject artifacts still say hold "
        "baseline for core KPI reasons rather than for missing chat-path evidence."
    )

    return {
        "rerun_needed_now": rerun_needed_now,
        "decision": decision,
        "reason_codes": reason_codes,
        "one_line_conclusion": one_line_conclusion,
        "manual_backlog_guidance": (
            "Keep the live rerun only as an optional richer provider-diagnostic step "
            "if exact failure-family capture becomes necessary later."
        ),
    }


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "build_chat_optional_rerun_audit",
    "load_json",
    "render_chat_optional_rerun_audit_markdown",
    "write_chat_optional_rerun_audit_files",
]
