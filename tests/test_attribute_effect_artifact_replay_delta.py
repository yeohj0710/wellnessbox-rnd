from scripts.attribute_effect_artifact_replay_delta import (
    _classify_final_decision_family,
    _feature_family_name,
    _policy_band_name,
)


def test_feature_family_name_groups_removed_and_timing_features() -> None:
    assert _feature_family_name("adherence_proxy") == "removed_outcome_leakage"
    assert _feature_family_name("risk_tier_low") == "removed_outcome_leakage"
    assert _feature_family_name("trajectory_step") == "workflow_timing"
    assert _feature_family_name("regimen::berberine") == "regimen_composition"


def test_policy_band_name_uses_cgm_specific_upper_threshold() -> None:
    assert _policy_band_name(proxy_value=0.23, cgm_available=False) == "monitor_only_band"
    assert _policy_band_name(proxy_value=0.23, cgm_available=True) == "monitor_only_band"
    assert _policy_band_name(proxy_value=0.30, cgm_available=False) == "continue_plan_band"
    assert _policy_band_name(proxy_value=0.30, cgm_available=True) == "monitor_only_band"


def test_classify_final_decision_family_covers_key_attribution_families() -> None:
    assert (
        _classify_final_decision_family(
            mode_name="learned_effect_guarded",
            reference_action="continue_plan",
            candidate_action="monitor_only",
            reference_proxy=0.29,
            candidate_proxy=0.21,
            cgm_available=False,
            trajectory_step=4,
        )
        == "non_cgm_continue_to_monitor_threshold_cross"
    )
    assert (
        _classify_final_decision_family(
            mode_name="learned_effect_and_policy_guarded",
            reference_action="continue_plan",
            candidate_action="re_optimize",
            reference_proxy=0.29,
            candidate_proxy=0.20,
            cgm_available=False,
            trajectory_step=4,
        )
        == "policy_reoptimize_revival_window"
    )
    assert (
        _classify_final_decision_family(
            mode_name="learned_effect_and_policy_guarded",
            reference_action="monitor_only",
            candidate_action="continue_plan",
            reference_proxy=0.364,
            candidate_proxy=0.261,
            cgm_available=True,
            trajectory_step=4,
        )
        == "cgm_same_band_policy_score_flip"
    )
