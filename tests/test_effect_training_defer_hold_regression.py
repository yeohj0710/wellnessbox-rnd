import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_effect_training_defer_hold_regression_matches_current_replay_evidence() -> None:
    prior_decision = _load_json("artifacts/reports/effect_training_revisit_decision_v1.json")
    stability_decision = _load_json(
        "artifacts/reports/effect_training_revisit_stability_decision_v1.json"
    )
    baseline_summary = _load_json("artifacts/reports/baseline_candidate_kpi_summary_v1.json")
    replay_split = _load_json("artifacts/reports/policy_proxy_replay_split_audit_v1.json")
    non_cgm_diagnostic = _load_json(
        "artifacts/reports/"
        "effect_model_v3_training_view_enforced_slice_balanced_candidate_"
        "non_cgm_threshold_cross_diagnostic_v1.json"
    )

    assert prior_decision["decision_gate"]["decision"] == "defer_new_effect_training_loop"
    assert prior_decision["decision_gate"]["revisit_justified_now"] is False

    assert (
        stability_decision["decision_gate"]["decision"]
        == "current_defer_decision_still_holds"
    )
    assert stability_decision["decision_gate"]["material_replay_change_detected"] is False
    assert stability_decision["decision_gate"]["revisit_justified_now"] is False
    assert "fit_gate_status_unchanged" in stability_decision["decision_gate"]["reason_codes"]
    assert (
        "dominant_non_cgm_replay_family_still_unresolved"
        in stability_decision["decision_gate"]["reason_codes"]
    )

    assert baseline_summary["candidate_comparison"]["fit_gate_status"] == "worse_on_all_fit_gates"
    assert baseline_summary["adoption_summary"]["decision"] == "hold_baseline_candidate_not_ready"

    assert (
        replay_split["assessment"]["effect_only_shift_concentration"]
        == "supported_effect_enriched"
    )
    assert (
        replay_split["assessment"]["combined_shift_concentration"]
        == "supported_effect_enriched"
    )
    assert replay_split["assessment"]["supported_effect_only_changed_trace_user_count"] == 10
    assert replay_split["assessment"]["unsupported_effect_only_changed_trace_user_count"] == 0

    assert (
        non_cgm_diagnostic["target_family"]["name"]
        == "non_cgm_continue_to_monitor_threshold_cross"
    )
    assert non_cgm_diagnostic["target_family"]["observed_case_count"] == 26
