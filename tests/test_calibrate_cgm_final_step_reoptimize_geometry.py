from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "calibrate_cgm_final_step_reoptimize_geometry.py"
    )
    spec = spec_from_file_location(
        "calibrate_cgm_final_step_reoptimize_geometry",
        script_path,
    )
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_compute_proxy_overshoot_reoptimize_credit_only_uses_positive_overshoot():
    module = _load_module()

    bonus = module._compute_proxy_overshoot_reoptimize_credit(
        expected_effect_proxy=0.355,
        policy_effect_proxy_used=0.395,
        proxy_weight_gap=5.916678,
    )
    no_bonus = module._compute_proxy_overshoot_reoptimize_credit(
        expected_effect_proxy=0.355,
        policy_effect_proxy_used=0.34,
        proxy_weight_gap=5.916678,
    )

    assert round(bonus, 6) == 0.236667
    assert no_bonus == 0.0


def test_compute_final_step_glucose_geometry_credit_only_uses_positive_geometry():
    module = _load_module()

    bonus = module._compute_final_step_glucose_geometry_credit(
        feature_gap_contributions={
            "baseline::blood_glucose": 1.8,
            "delta::blood_glucose": 1.1,
            "follow_up::blood_glucose": -1.5,
        }
    )
    no_bonus = module._compute_final_step_glucose_geometry_credit(
        feature_gap_contributions={
            "baseline::blood_glucose": -0.2,
            "delta::blood_glucose": -0.1,
            "follow_up::blood_glucose": 3.0,
        }
    )

    assert round(bonus, 6) == 0.87
    assert no_bonus == 0.0


def test_summarize_margin_shift_reports_gap_reduction_without_forced_flip():
    module = _load_module()
    cases = [
        {
            "user_id": "u1",
            "current_top_action_after_priors": "continue_plan",
            "calibrated_top_action_after_priors": "continue_plan",
            "continue_minus_reoptimize_before_calibration": 1.2,
            "continue_minus_reoptimize_after_calibration": 0.9,
            "feature_gap_contributions": {feature: 0.0 for feature in module.TRACKED_FEATURES},
        },
        {
            "user_id": "u2",
            "current_top_action_after_priors": "continue_plan",
            "calibrated_top_action_after_priors": "re_optimize",
            "continue_minus_reoptimize_before_calibration": 0.8,
            "continue_minus_reoptimize_after_calibration": -0.05,
            "feature_gap_contributions": {feature: 0.0 for feature in module.TRACKED_FEATURES},
        },
    ]

    summary = module._summarize_margin_shift(cases)

    assert summary["selected_continue_case_count"] == 2
    assert summary["mean_continue_minus_reoptimize_before_calibration"] == 1.0
    assert summary["mean_continue_minus_reoptimize_after_calibration"] == 0.425
    assert summary["gap_reduction_sum"] == 1.15
    assert summary["case_count_gap_le_1_before"] == 1
    assert summary["case_count_gap_le_1_after"] == 2
    assert summary["continue_to_reoptimize_top_action_flip_count"] == 1
    assert summary["continue_to_reoptimize_top_action_flip_user_ids"] == ["u2"]


def test_mean_feature_gap_summary_orders_largest_positive_family_first():
    module = _load_module()
    cases = [
        {
            "feature_gap_contributions": {
                "policy_effect_proxy_used": 2.0,
                "adherence_proxy": 1.0,
                "side_effect_proxy": -0.1,
                "baseline::blood_glucose": 0.2,
                "follow_up::blood_glucose": 0.3,
                "delta::blood_glucose": 0.4,
                "trajectory_step": 0.1,
                "day_index": -0.05,
            }
        },
        {
            "feature_gap_contributions": {
                "policy_effect_proxy_used": 1.0,
                "adherence_proxy": 0.8,
                "side_effect_proxy": -0.2,
                "baseline::blood_glucose": 0.3,
                "follow_up::blood_glucose": 0.4,
                "delta::blood_glucose": 0.5,
                "trajectory_step": 0.2,
                "day_index": -0.02,
            }
        },
    ]

    summary = module._mean_feature_gap_summary(cases)

    assert list(summary)[0] == "policy_effect_proxy_used"
    assert summary["policy_effect_proxy_used"] == 1.5
    assert summary["adherence_proxy"] == 0.9
