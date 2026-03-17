from wellnessbox_rnd.evals.chat_optional_rerun_audit import (
    build_chat_optional_rerun_audit,
    load_json,
    render_chat_optional_rerun_audit_markdown,
)


def test_build_chat_optional_rerun_audit_defer_decision_from_existing_evidence() -> None:
    audit = build_chat_optional_rerun_audit(
        chat_live_smoke_report=load_json("artifacts/reports/chat_openai_adapter_smoke_live_v1.json"),
        chat_live_smoke_report_path="artifacts/reports/chat_openai_adapter_smoke_live_v1.json",
        learned_boundary_audit=load_json("artifacts/reports/learned_runtime_boundary_audit_v1.json"),
        learned_boundary_audit_path="artifacts/reports/learned_runtime_boundary_audit_v1.json",
        design_sanity_audit=load_json("artifacts/reports/design_sanity_audit_v1.json"),
        design_sanity_audit_path="artifacts/reports/design_sanity_audit_v1.json",
        baseline_candidate_kpi_summary=load_json(
            "artifacts/reports/baseline_candidate_kpi_summary_v1.json"
        ),
        baseline_candidate_kpi_summary_path=(
            "artifacts/reports/baseline_candidate_kpi_summary_v1.json"
        ),
        final_kpi_compare_report=load_json(
            "artifacts/reports/final_kpi_compare_report_v1.json"
        ),
        final_kpi_compare_report_path="artifacts/reports/final_kpi_compare_report_v1.json",
        effect_candidate_reject_decision=load_json(
            "artifacts/reports/latest_effect_candidate_reject_decision_v1.json"
        ),
        effect_candidate_reject_decision_path=(
            "artifacts/reports/latest_effect_candidate_reject_decision_v1.json"
        ),
    )

    assert audit["core_kpi_progress"]["progress_gate_met"] is True
    assert (
        audit["core_kpi_progress"]["evidence"]["final_compare_decision_class"]
        == "hold_baseline_candidate_not_ready"
    )
    assert (
        audit["core_kpi_progress"]["evidence"]["reject_decision"]
        == "reject_candidate_keep_baseline"
    )
    assert audit["chat_runtime_boundary"]["optional_chat_only"] is True
    assert audit["latest_live_smoke_status"]["attempted_live_call"] is True
    assert audit["latest_live_smoke_status"]["verification_passed"] is True
    assert audit["latest_live_smoke_status"]["live_failure_captured"] is False
    assert audit["rerun_decision"]["rerun_needed_now"] is False
    assert audit["rerun_decision"]["decision"] == "defer_live_rerun_optional_only"
    assert "final_compare_still_holds_baseline" in audit["rerun_decision"][
        "reason_codes"
    ]
    assert "latest_reject_decision_stays_analysis_only" in audit["rerun_decision"][
        "reason_codes"
    ]
    assert "missing_live_failure_detail_is_diagnostic_only" in audit["rerun_decision"][
        "reason_codes"
    ]


def test_render_chat_optional_rerun_audit_markdown_contains_key_sections() -> None:
    markdown = render_chat_optional_rerun_audit_markdown(
        {
            "core_kpi_progress": {
                "progress_gate_met": True,
                "evidence": {
                    "current_phase": "contract_data_eval_hardening",
                    "baseline_candidate_decision": "hold_baseline_candidate_not_ready",
                    "pro_baseline_followup_kpi_path_status": "sound",
                    "weakest_slice_eval_wiring_status": "sound_with_gaps",
                    "replay_only_learned_boundary_status": "sound",
                    "final_compare_decision_class": "hold_baseline_candidate_not_ready",
                    "reject_decision": "reject_candidate_keep_baseline",
                    "dominant_replay_regression_family": (
                        "non_cgm_continue_to_monitor_threshold_cross"
                    ),
                },
            },
            "chat_runtime_boundary": {
                "optional_chat_only": True,
                "evidence": {
                    "recommendation_runtime_affected": False,
                    "safety_runtime_affected": False,
                    "optimizer_runtime_affected": False,
                },
            },
            "latest_live_smoke_status": {
                "attempted_live_call": True,
                "verification_passed": True,
                "provider": "deterministic_template_fallback",
                "fallback_reason": "openai_call_failed",
                "live_failure_captured": False,
            },
            "rerun_decision": {
                "rerun_needed_now": False,
                "decision": "defer_live_rerun_optional_only",
                "one_line_conclusion": "Do not rerun now.",
                "reason_codes": [
                    "chat_only_boundary_preserved",
                    "final_compare_still_holds_baseline",
                    "missing_live_failure_detail_is_diagnostic_only",
                ],
            },
        }
    )

    assert "# chat optional rerun need audit v1" in markdown
    assert "## Core KPI Progress" in markdown
    assert "## Chat Runtime Boundary" in markdown
    assert "## Latest Live Smoke" in markdown
    assert "reject_candidate_keep_baseline" in markdown
    assert "Do not rerun now." in markdown
