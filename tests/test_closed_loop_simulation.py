from wellnessbox_rnd import simulation

DATASET_PATH = "data/synthetic/synthetic_longitudinal_v2.jsonl"
MODEL_ARTIFACT_PATH = "artifacts/models/effect_model_v1.json"
POLICY_MODEL_ARTIFACT_PATH = "artifacts/models/policy_model_v1.json"
V4_DATASET_PATH = "data/synthetic/synthetic_longitudinal_v4.jsonl"
V4_MODEL_ARTIFACT_PATH = "artifacts/models/effect_model_v3.json"


def test_closed_loop_simulation_exposes_guarded_trace_fields() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=DATASET_PATH,
        user_id="syn-v2-user-003",
        max_cycles=5,
        model_artifact_path=MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
        enable_learned_reranking=True,
    )

    assert report.mode_name == "learned_effect_and_policy_guarded"
    assert len(report.trace) >= 1
    first_step = report.trace[0]
    assert first_step.deterministic_action == simulation.SimulationPolicyAction.START_PLAN
    assert first_step.selected_policy_action == simulation.SimulationPolicyAction.START_PLAN
    assert first_step.policy_guard_applied is True
    assert first_step.policy_guard_reason == "baseline_intake_kept_deterministic"
    assert first_step.deterministic_top_candidate is not None
    assert first_step.selected_candidate is not None
    assert first_step.action_source == simulation.PolicyActionSource.LEARNED_POLICY_GUARDED
    assert first_step.ranking_source in {
        simulation.RankingSource.DETERMINISTIC_RANKING,
        simulation.RankingSource.LEARNED_EFFECT_GUARDED,
    }
    assert first_step.policy_effect_proxy_used >= 0.0
    assert first_step.policy_effect_proxy_override_applied is False


def test_closed_loop_simulation_falls_back_without_models() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=DATASET_PATH,
        user_id="syn-v2-user-000",
        max_cycles=3,
        model_artifact_path="artifacts/models/does_not_exist.json",
        policy_model_artifact_path="artifacts/models/does_not_exist.json",
    )

    assert report.model_loaded is False
    assert report.policy_model_loaded is False
    assert all(
        step.predicted_effect_source == simulation.EffectSource.DETERMINISTIC_FALLBACK
        for step in report.trace
    )
    assert all(
        step.action_source == simulation.PolicyActionSource.DETERMINISTIC_POLICY
        for step in report.trace
    )


def test_closed_loop_batch_simulation_reports_all_four_modes_and_slices() -> None:
    report = simulation.compare_batch_simulation_modes(
        dataset_path=DATASET_PATH,
        max_cycles=5,
        max_users=16,
        model_artifact_path=MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
    )

    mode_names = [mode.mode_name for mode in report.compared_modes]
    assert mode_names == [
        "deterministic_only",
        "learned_effect_guarded",
        "learned_policy_guarded",
        "learned_effect_and_policy_guarded",
    ]
    for mode in report.compared_modes:
        assert mode.scenario_count == 16
        assert mode.total_trace_steps >= 16
        assert set(mode.cohort_slice_metrics) == {
            "cgm_users",
            "genetic_users",
            "low_risk_users",
            "high_risk_users",
            "single_goal_users",
            "multi_goal_users",
        }

    assert set(report.differing_final_state_user_ids) == {
        "learned_effect_guarded",
        "learned_policy_guarded",
        "learned_effect_and_policy_guarded",
    }
    assert set(report.differing_trace_user_ids) == {
        "learned_effect_guarded",
        "learned_policy_guarded",
        "learned_effect_and_policy_guarded",
    }
    assert len(report.trace_samples) >= 1


def test_combined_mode_routes_learned_effect_proxy_into_policy_features() -> None:
    report = simulation.compare_batch_simulation_modes(
        dataset_path=V4_DATASET_PATH,
        max_cycles=5,
        max_users=96,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
    )

    modes = {mode.mode_name: mode for mode in report.compared_modes}
    combined = modes["learned_effect_and_policy_guarded"]
    policy_only = modes["learned_policy_guarded"]
    effect_only = modes["learned_effect_guarded"]
    combined_low_risk = combined.cohort_slice_metrics["low_risk_users"]
    policy_low_risk = policy_only.cohort_slice_metrics["low_risk_users"]

    assert combined.policy_effect_override_applied_count > 0
    assert (
        combined.final_policy_action_counts.get("trigger_safety_recheck", 0)
        < policy_only.final_policy_action_counts.get("trigger_safety_recheck", 0)
    )
    assert combined_low_risk.final_action_distribution.get("re_optimize", 0) > 0
    assert (
        combined_low_risk.final_action_distribution.get("trigger_safety_recheck", 0)
        < policy_low_risk.final_action_distribution.get("trigger_safety_recheck", 0)
    )
    combined_by_user = {scenario.user_id: scenario for scenario in combined.scenario_reports}
    policy_by_user = {scenario.user_id: scenario for scenario in policy_only.scenario_reports}
    effect_by_user = {scenario.user_id: scenario for scenario in effect_only.scenario_reports}

    combined_vs_policy_final_match = sum(
        combined_by_user[user_id].final_policy_action
        == policy_by_user[user_id].final_policy_action
        for user_id in combined_by_user
    )
    combined_vs_effect_final_match = sum(
        combined_by_user[user_id].final_policy_action
        == effect_by_user[user_id].final_policy_action
        for user_id in combined_by_user
    )
    assert combined_vs_effect_final_match >= combined_vs_policy_final_match

    assert any(
        combined_step.policy_effect_proxy_override_applied
        and combined_step.raw_learned_policy_action
        != policy_step.raw_learned_policy_action
        for user_id, combined_report in combined_by_user.items()
        for combined_step, policy_step in zip(
            combined_report.trace,
            policy_by_user[user_id].trace,
            strict=False,
        )
    )
