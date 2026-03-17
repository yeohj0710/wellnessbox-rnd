from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from wellnessbox_rnd.models import load_policy_model_v1_artifact
from wellnessbox_rnd.simulation import compare_batch_simulation_modes, simulate_closed_loop_batch
from wellnessbox_rnd.simulation.closed_loop_v0 import _load_records_by_user

V4_DATASET_PATH = "data/synthetic/synthetic_longitudinal_v4.jsonl"
V4_MODEL_ARTIFACT_PATH = "artifacts/models/effect_model_v3.json"
V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH = "artifacts/models/policy_model_v1_uniform.json"


def _load_module(script_name: str, module_name: str):
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = spec_from_file_location(module_name, script_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cgm_final_step_blocker_family_stays_outside_threshold_edge() -> None:
    module = _load_module(
        "diagnose_current_cgm_continue_plan_cases.py",
        "diagnose_current_cgm_continue_plan_cases",
    )
    comparison = compare_batch_simulation_modes(
        dataset_path=V4_DATASET_PATH,
        max_cycles=5,
        max_users=96,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH,
        enable_policy_effect_proxy_override=True,
    )
    combined = next(
        mode
        for mode in comparison.compared_modes
        if mode.mode_name == "learned_effect_and_policy_guarded"
    )
    records_by_user = _load_records_by_user(V4_DATASET_PATH)
    policy_artifact = load_policy_model_v1_artifact(
        V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH
    )

    cases = []
    for scenario in combined.scenario_reports:
        user_records = records_by_user[scenario.user_id]
        if not user_records[0].request.input_availability.cgm:
            continue
        if scenario.final_policy_action.value != "continue_plan":
            continue
        cases.append(
            module._build_case_diagnostic(
                scenario=scenario,
                user_records=user_records,
                policy_artifact=policy_artifact,
            )
        )

    threshold_edge_user_ids = [
        case["user_id"]
        for case in cases
        if case["final_threshold_edge_status"] == "monitor_band_still_continue"
    ]

    assert combined.cohort_slice_metrics["cgm_users"].final_action_distribution == {
        "ask_targeted_followup": 10,
        "continue_plan": 9,
        "monitor_only": 4,
        "trigger_safety_recheck": 10,
    }
    assert module._build_blocker_summary(cases) == {
        "monitor_band_still_continue_count": 1,
        "outside_monitor_band_count": 8,
        "final_safety_ceiling_active_count": 0,
        "final_effect_fallback_active_count": 0,
        "final_policy_fallback_active_count": 0,
        "final_distance_to_monitor_flip_le_0_05_count": 0,
        "final_distance_to_monitor_flip_gt_0_30_count": 9,
        "final_reoptimize_minus_continue_ge_0_count": 0,
    }
    assert module._build_blocker_family_summary(cases) == {
        "outside_monitor_band_large_monitor_gap": 8,
        "threshold_edge_monitor_band_continue": 1,
    }
    assert threshold_edge_user_ids == ["syn-v4-user-084"]


def test_cgm_final_step_replay_slice_keeps_current_geometry_signature() -> None:
    module = _load_module(
        "calibrate_cgm_final_step_reoptimize_geometry.py",
        "calibrate_cgm_final_step_reoptimize_geometry",
    )
    records_by_user = _load_records_by_user(V4_DATASET_PATH)
    policy_artifact = load_policy_model_v1_artifact(
        V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH
    )
    report = simulate_closed_loop_batch(
        dataset_path=V4_DATASET_PATH,
        max_cycles=5,
        max_users=96,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_and_policy_guarded",
    )

    final_cgm_cases = module._build_final_cgm_cases(
        scenario_reports=report.scenario_reports,
        records_by_user=records_by_user,
        proxy_weight_gap=module._proxy_weight_gap(policy_artifact),
        feature_gap_weights=module._feature_gap_weights(policy_artifact),
        policy_artifact=policy_artifact,
    )
    selected_continue_cases = [
        case
        for case in final_cgm_cases
        if case["selected_final_action"] == "continue_plan"
    ]

    assert module._summarize_geometry(final_cgm_cases) == {
        "final_cgm_case_count": 33,
        "selected_final_action_distribution": {
            "ask_targeted_followup": 10,
            "continue_plan": 9,
            "monitor_only": 4,
            "trigger_safety_recheck": 10,
        },
        "current_top_action_after_priors_distribution": {
            "continue_plan": 24,
            "monitor_only": 4,
            "trigger_safety_recheck": 5,
        },
        "calibrated_top_action_after_priors_distribution": {
            "continue_plan": 23,
            "monitor_only": 4,
            "re_optimize": 1,
            "trigger_safety_recheck": 5,
        },
    }
    assert module._summarize_margin_shift(selected_continue_cases) == {
        "selected_continue_case_count": 9,
        "mean_continue_minus_reoptimize_before_calibration": 1.93574,
        "mean_continue_minus_reoptimize_after_calibration": 0.835792,
        "gap_reduction_sum": 9.899525,
        "gap_reduction_mean": 1.099947,
        "case_count_gap_le_1_before": 1,
        "case_count_gap_le_1_after": 6,
        "continue_to_reoptimize_top_action_flip_count": 1,
        "continue_to_reoptimize_top_action_flip_user_ids": ["syn-v4-user-084"],
    }
    assert module._mean_feature_gap_summary(selected_continue_cases) == {
        "policy_effect_proxy_used": 2.221393,
        "trajectory_step": 2.191094,
        "baseline::blood_glucose": 1.925563,
        "delta::blood_glucose": 1.09885,
        "adherence_proxy": 0.651097,
        "side_effect_proxy": -0.028584,
        "follow_up::blood_glucose": -1.532929,
        "day_index": -2.171869,
    }
    flipped_cases = [
        case
        for case in selected_continue_cases
        if case["calibrated_top_action_after_priors"] == "re_optimize"
    ]
    assert [case["user_id"] for case in flipped_cases] == ["syn-v4-user-084"]
    assert all(
        case["positive_glucose_geometry_reoptimize_credit"] > 0.0
        for case in selected_continue_cases
    )


def test_cgm_final_step_calibration_only_flips_threshold_edge_singleton() -> None:
    diagnose_module = _load_module(
        "diagnose_current_cgm_continue_plan_cases.py",
        "diagnose_current_cgm_continue_plan_cases_for_guard",
    )
    calibrate_module = _load_module(
        "calibrate_cgm_final_step_reoptimize_geometry.py",
        "calibrate_cgm_final_step_reoptimize_geometry_for_guard",
    )
    comparison = compare_batch_simulation_modes(
        dataset_path=V4_DATASET_PATH,
        max_cycles=5,
        max_users=96,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH,
        enable_policy_effect_proxy_override=True,
    )
    combined = next(
        mode
        for mode in comparison.compared_modes
        if mode.mode_name == "learned_effect_and_policy_guarded"
    )
    replay_report = simulate_closed_loop_batch(
        dataset_path=V4_DATASET_PATH,
        max_cycles=5,
        max_users=96,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="learned_effect_and_policy_guarded",
    )
    records_by_user = _load_records_by_user(V4_DATASET_PATH)
    policy_artifact = load_policy_model_v1_artifact(
        V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH
    )

    blocker_cases = []
    for scenario in combined.scenario_reports:
        user_records = records_by_user[scenario.user_id]
        if not user_records[0].request.input_availability.cgm:
            continue
        if scenario.final_policy_action.value != "continue_plan":
            continue
        blocker_cases.append(
            diagnose_module._build_case_diagnostic(
                scenario=scenario,
                user_records=user_records,
                policy_artifact=policy_artifact,
            )
        )

    calibrated_cases = calibrate_module._build_final_cgm_cases(
        scenario_reports=replay_report.scenario_reports,
        records_by_user=records_by_user,
        proxy_weight_gap=calibrate_module._proxy_weight_gap(policy_artifact),
        feature_gap_weights=calibrate_module._feature_gap_weights(policy_artifact),
        policy_artifact=policy_artifact,
    )
    calibrated_continue_cases = {
        case["user_id"]: case
        for case in calibrated_cases
        if case["selected_final_action"] == "continue_plan"
    }

    threshold_edge_user_ids = sorted(
        case["user_id"]
        for case in blocker_cases
        if case["final_blocker_family"] == "threshold_edge_monitor_band_continue"
    )
    outside_band_user_ids = sorted(
        case["user_id"]
        for case in blocker_cases
        if case["final_blocker_family"] == "outside_monitor_band_large_monitor_gap"
    )
    flipped_user_ids = sorted(
        user_id
        for user_id, case in calibrated_continue_cases.items()
        if case["current_top_action_after_priors"] == "continue_plan"
        and case["calibrated_top_action_after_priors"] == "re_optimize"
    )
    outside_band_flipped_user_ids = sorted(
        user_id for user_id in outside_band_user_ids if user_id in flipped_user_ids
    )

    assert threshold_edge_user_ids == ["syn-v4-user-084"]
    assert flipped_user_ids == threshold_edge_user_ids
    assert len(outside_band_user_ids) == 8
    assert outside_band_flipped_user_ids == []
    assert all(
        calibrated_continue_cases[user_id]["calibrated_top_action_after_priors"]
        == "continue_plan"
        for user_id in outside_band_user_ids
    )
