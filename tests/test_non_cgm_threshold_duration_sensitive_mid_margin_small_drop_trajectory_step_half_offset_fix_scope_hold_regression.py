import json
from pathlib import Path


def _load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_trajectory_step_half_offset_fix_scope_hold_regression_stays_direct_and_bounded(
) -> None:
    mode_decision = _load_json(
        "artifacts/reports/"
        "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_local_handling_mode_decision_v1.json"
    )
    probe_decision = _load_json(
        "artifacts/reports/"
        "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_fixed_uniform_offset_probe_decision_v1.json"
    )
    half_offset_counterfactual = _load_json(
        "artifacts/reports/"
        "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_half_offset_counterfactual_v1.json"
    )
    fix_scope = _load_json(
        "artifacts/reports/"
        "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_half_offset_fix_scope_decision_v1.json"
    )

    mode_gate = mode_decision["decision_gate"]
    probe_gate = probe_decision["decision_gate"]
    summary = half_offset_counterfactual["counterfactual_summary"]
    fix_scope_gate = fix_scope["decision_gate"]
    mode_anchor = fix_scope["evidence_summary"]["mode_anchor"]
    probe_anchor = fix_scope["evidence_summary"]["probe_anchor"]
    counterfactual_read = fix_scope["evidence_summary"]["counterfactual_read"]

    assert mode_gate["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert mode_gate["cycle_conditioned_mode_needed_now"] is False
    assert mode_gate["second_feature_widening_needed_now"] is False

    assert probe_gate["chosen_first_opposing_feature"] == "trajectory_step"
    assert probe_gate["chosen_probe_fraction"] == 0.5
    assert probe_gate["chosen_probe_offset_abs_value"] == 0.031557
    assert probe_gate["chosen_probe_clears_all_cases"] is True

    assert summary["cleared_case_count"] == 5
    assert summary["all_cases_cleared"] is True
    assert summary["mean_residual_clearance"] == 0.021141
    assert summary["min_residual_clearance"] == 0.0145
    assert summary["max_residual_clearance"] == 0.026514

    assert fix_scope_gate["chosen_first_opposing_feature"] == "trajectory_step"
    assert (
        fix_scope_gate["decision"]
        == "treat_as_direct_half_offset_local_handling_ready"
    )
    assert (
        fix_scope_gate["chosen_fix_scope"]
        == "trajectory_step_half_offset_local_score_handling"
    )
    assert fix_scope_gate["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert fix_scope_gate["chosen_probe_fraction"] == 0.5
    assert fix_scope_gate["chosen_probe_offset_abs_value"] == 0.031557
    assert fix_scope_gate["observed_case_count"] == 5
    assert fix_scope_gate["all_cases_cleared"] is True
    assert fix_scope_gate["min_residual_clearance_positive"] is True
    assert fix_scope_gate["cycle_conditioned_mode_needed_now"] is False
    assert fix_scope_gate["second_feature_widening_needed_now"] is False

    assert mode_anchor["chosen_fix_scope"] == "trajectory_step_local_score_handling"
    assert mode_anchor["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert mode_anchor["trajectory_step_value_uniform"] is True
    assert mode_anchor["final_cycle_index_uniform"] is True

    assert probe_anchor["chosen_probe_fraction"] == 0.5
    assert probe_anchor["chosen_probe_offset_abs_value"] == 0.031557
    assert probe_anchor["chosen_probe_clears_all_cases"] is True

    assert counterfactual_read["cleared_case_count"] == 5
    assert counterfactual_read["all_cases_cleared"] is True
    assert counterfactual_read["mean_residual_clearance"] == 0.021141
    assert counterfactual_read["min_residual_clearance"] == 0.0145
    assert counterfactual_read["max_residual_clearance"] == 0.026514
    assert counterfactual_read["residual_clearance_vector"] == [
        0.0145,
        0.019182,
        0.020641,
        0.024869,
        0.026514,
    ]
