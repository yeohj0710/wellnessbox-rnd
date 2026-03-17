import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_chat_optional_rerun_defer_hold_regression() -> None:
    audit = _load_json("artifacts/reports/chat_optional_rerun_need_audit_v1.json")
    live_smoke = _load_json("artifacts/reports/chat_openai_adapter_smoke_live_v1.json")

    assert audit["core_kpi_progress"]["progress_gate_met"] is True
    assert audit["chat_runtime_boundary"]["optional_chat_only"] is True
    assert audit["rerun_decision"]["rerun_needed_now"] is False
    assert audit["rerun_decision"]["decision"] == "defer_live_rerun_optional_only"
    assert audit["core_kpi_progress"]["evidence"]["final_compare_decision_class"] == (
        "hold_baseline_candidate_not_ready"
    )
    assert audit["core_kpi_progress"]["evidence"]["reject_decision"] == (
        "reject_candidate_keep_baseline"
    )
    assert "chat_only_boundary_preserved" in audit["rerun_decision"]["reason_codes"]
    assert "final_compare_still_holds_baseline" in audit["rerun_decision"][
        "reason_codes"
    ]
    assert "latest_reject_decision_stays_analysis_only" in audit["rerun_decision"][
        "reason_codes"
    ]
    assert (
        "higher_roi_core_blocker_remains_in_data_validity"
        in audit["rerun_decision"]["reason_codes"]
    )
    assert (
        "current_candidate_regression_is_not_chat_path_related"
        in audit["rerun_decision"]["reason_codes"]
    )

    assert live_smoke["attempted_live_call"] is True
    assert live_smoke["verification_passed"] is True
    assert live_smoke["provider"] == "deterministic_template_fallback"
    assert live_smoke["fallback_reason"] == "openai_call_failed"
    assert live_smoke["live_failure"] is None

    runtime_boundary = live_smoke["preflight"]["runtime_boundary"]
    assert runtime_boundary["chat_only_boundary"] is True
    assert runtime_boundary["recommendation_runtime_affected"] is False
    assert runtime_boundary["safety_runtime_affected"] is False
    assert runtime_boundary["optimizer_runtime_affected"] is False
