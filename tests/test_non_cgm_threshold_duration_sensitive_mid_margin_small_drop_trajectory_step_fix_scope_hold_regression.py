import json
from pathlib import Path


def _load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_trajectory_step_fix_scope_hold_regression_stays_local_and_consistent() -> None:
    competition = _load_json(
        "artifacts/reports/"
        "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "regimen_count_score_competition_decision_v1.json"
    )
    counterfactual = _load_json(
        "artifacts/reports/"
        "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_counterfactual_v1.json"
    )
    fix_scope = _load_json(
        "artifacts/reports/"
        "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_fix_scope_decision_v1.json"
    )

    competition_gate = competition["decision_gate"]
    counterfactual_summary = counterfactual["counterfactual_summary"]
    fix_scope_gate = fix_scope["decision_gate"]
    per_case_surface = fix_scope["evidence_summary"]["per_case_surface"]

    assert competition_gate["chosen_first_opposing_feature"] == "trajectory_step"
    assert competition_gate["chosen_first_opposing_feature_family"] == "workflow_timing"

    assert counterfactual["target"]["chosen_feature"] == "trajectory_step"
    assert counterfactual["target"]["observed_case_count"] == 5
    assert counterfactual_summary["neutralize_clears_shortfall_case_count"] == 5
    assert counterfactual_summary["extra_penalty_worsens_case_count"] == 5

    assert fix_scope_gate["chosen_first_opposing_feature"] == "trajectory_step"
    assert (
        fix_scope_gate["decision"]
        == "treat_as_direct_opposing_lever_not_multifeature_mix"
    )
    assert fix_scope_gate["chosen_fix_scope"] == "trajectory_step_local_score_handling"
    assert fix_scope_gate["neutralize_clears_all_cases"] is True
    assert fix_scope_gate["extra_penalty_worsens_all_cases"] is True
    assert fix_scope_gate["widen_to_multifeature_mix_supported"] is False
    assert fix_scope_gate["per_case_value_uniform"] is True
    assert fix_scope_gate["per_case_abs_value_uniform"] is True

    assert per_case_surface["trajectory_step_values"] == [
        -0.063114,
        -0.063114,
        -0.063114,
        -0.063114,
        -0.063114,
    ]
    assert per_case_surface["trajectory_step_abs_values"] == [
        0.063114,
        0.063114,
        0.063114,
        0.063114,
        0.063114,
    ]
