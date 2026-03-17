import json
from pathlib import Path


def _load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_trajectory_step_half_offset_hold_regression_stays_first_successful_probe() -> None:
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

    decision_gate = probe_decision["decision_gate"]
    probe_comparison = probe_decision["evidence_summary"]["probe_comparison_digest"]
    selection_digest = probe_decision["evidence_summary"]["selection_digest"]

    target = half_offset_counterfactual["target"]
    summary = half_offset_counterfactual["counterfactual_summary"]
    case_rows = half_offset_counterfactual["case_rows"]

    assert decision_gate["chosen_first_opposing_feature"] == "trajectory_step"
    assert decision_gate["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert decision_gate["decision"] == "use_half_offset_probe_first"
    assert decision_gate["chosen_probe_fraction"] == 0.5
    assert decision_gate["chosen_probe_offset_abs_value"] == 0.031557
    assert decision_gate["chosen_probe_clears_all_cases"] is True
    assert decision_gate["lower_probe_left_deferred"] is True
    assert decision_gate["higher_probe_left_deferred"] is True

    assert probe_comparison["quarter_probe"]["clears_case_count"] == 4
    assert probe_comparison["quarter_probe"]["clears_all_cases"] is False
    assert probe_comparison["half_probe"]["clears_case_count"] == 5
    assert probe_comparison["half_probe"]["clears_all_cases"] is True
    assert probe_comparison["full_probe"]["clears_case_count"] == 5
    assert selection_digest["first_grid_fraction_clearing_all"] == 0.5
    assert selection_digest["minimum_clearing_fraction_of_full_offset"] == 0.270257

    assert target["chosen_feature"] == "trajectory_step"
    assert target["chosen_local_handling_mode"] == "fixed_uniform_offset"
    assert target["chosen_probe_fraction"] == 0.5
    assert target["chosen_probe_offset_abs_value"] == 0.031557
    assert target["observed_case_count"] == 5

    assert summary["half_offset_abs_value"] == 0.031557
    assert summary["cleared_case_count"] == 5
    assert summary["all_cases_cleared"] is True
    assert summary["mean_residual_clearance"] == 0.021141
    assert summary["min_residual_clearance"] == 0.0145
    assert summary["max_residual_clearance"] == 0.026514

    assert len(case_rows) == 5
    assert all(row["cleared_by_half_offset"] is True for row in case_rows)
    assert [row["residual_clearance"] for row in case_rows] == [
        0.0145,
        0.019182,
        0.020641,
        0.024869,
        0.026514,
    ]
