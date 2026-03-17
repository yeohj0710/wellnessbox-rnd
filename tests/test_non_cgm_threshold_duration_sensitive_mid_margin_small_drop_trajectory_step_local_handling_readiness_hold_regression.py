import json
from pathlib import Path


def _load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_trajectory_step_local_handling_readiness_hold_regression_stays_single_feature_first(
) -> None:
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
    readiness = _load_json(
        "artifacts/reports/"
        "non_cgm_threshold_duration_sensitive_mid_margin_small_drop_"
        "trajectory_step_local_handling_readiness_v1.json"
    )

    competition_gate = competition["decision_gate"]
    competition_deferred = competition["deferred_subtargets"]
    counterfactual_summary = counterfactual["counterfactual_summary"]
    fix_scope_gate = fix_scope["decision_gate"]
    readiness_gate = readiness["readiness_gate"]
    feature_gap_digest = readiness["evidence_summary"]["feature_gap_digest"]
    shortfall_digest = readiness["evidence_summary"]["shortfall_digest"]
    fix_scope_digest = readiness["evidence_summary"]["fix_scope_digest"]

    assert competition_gate["chosen_first_opposing_feature"] == "trajectory_step"
    assert competition_deferred[0]["feature"] == "dose::l_theanine"

    assert counterfactual["target"]["chosen_feature"] == "trajectory_step"
    assert counterfactual_summary["neutralize_clears_shortfall_case_count"] == 5
    assert counterfactual_summary["extra_penalty_worsens_case_count"] == 5

    assert fix_scope_gate["chosen_fix_scope"] == "trajectory_step_local_score_handling"
    assert fix_scope_gate["widen_to_multifeature_mix_supported"] is False

    assert readiness_gate["chosen_first_opposing_feature"] == "trajectory_step"
    assert readiness_gate["deferred_second_opposing_feature"] == "dose::l_theanine"
    assert readiness_gate["decision"] == "single_feature_local_handling_first"
    assert readiness_gate["chosen_fix_scope"] == "trajectory_step_local_score_handling"
    assert readiness_gate["single_feature_path_supported"] is True
    assert readiness_gate["widen_to_second_feature_needed_now"] is False

    assert feature_gap_digest["first_feature"] == "trajectory_step"
    assert feature_gap_digest["second_feature"] == "dose::l_theanine"
    assert feature_gap_digest["first_feature_abs_value"] == 0.31557
    assert feature_gap_digest["second_feature_abs_value"] == 0.24208
    assert feature_gap_digest["first_minus_second_abs_gap"] == 0.07349

    assert shortfall_digest["current_shortfall_mean"] == 0.010416
    assert shortfall_digest["trajectory_step_abs_value_mean"] == 0.063114
    assert shortfall_digest["trajectory_step_covers_shortfall_mean"] is True

    assert fix_scope_digest["chosen_fix_scope"] == "trajectory_step_local_score_handling"
    assert fix_scope_digest["neutralize_clears_all_cases"] is True
    assert fix_scope_digest["widen_to_multifeature_mix_supported"] is False
