from wellnessbox_rnd import simulation

DATASET_PATH = "data/synthetic/synthetic_longitudinal_v2.jsonl"
MODEL_ARTIFACT_PATH = "artifacts/models/effect_model_v1.json"
POLICY_MODEL_ARTIFACT_PATH = "artifacts/models/policy_model_v1.json"
V4_DATASET_PATH = "data/synthetic/synthetic_longitudinal_v4.jsonl"
V4_MODEL_ARTIFACT_PATH = "artifacts/models/effect_model_v3.json"
V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH = "artifacts/models/policy_model_v1_uniform.json"


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
    combined_cgm = combined.cohort_slice_metrics["cgm_users"]

    assert combined.policy_effect_override_applied_count > 0
    assert combined_low_risk.user_count > 0
    assert combined_cgm.user_count > 0
    assert combined_low_risk.final_action_distribution.get("continue_plan", 0) >= 0
    assert policy_low_risk.user_count > 0
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


def test_combined_mode_can_disable_policy_effect_proxy_override() -> None:
    override_on = simulation.simulate_closed_loop_batch(
        dataset_path=V4_DATASET_PATH,
        max_cycles=5,
        max_users=96,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
        mode_name="combined_override_on",
    )
    override_off = simulation.simulate_closed_loop_batch(
        dataset_path=V4_DATASET_PATH,
        max_cycles=5,
        max_users=96,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=False,
        mode_name="combined_override_off",
    )

    assert override_on.policy_effect_override_applied_count > 0
    assert override_off.policy_effect_override_applied_count == 0
    assert any(
        step.policy_effect_proxy_override_applied
        for report in override_on.scenario_reports
        for step in report.trace
    )
    assert all(
        not step.policy_effect_proxy_override_applied
        for report in override_off.scenario_reports
        for step in report.trace
    )


def test_cgm_threshold_edge_regression_refines_continue_plan_into_monitor_only() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=V4_DATASET_PATH,
        user_id="syn-v4-user-004",
        max_cycles=5,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
    )

    reoptimize_step = report.trace[1]
    final_step = report.trace[-1]

    assert reoptimize_step.selected_policy_action == simulation.SimulationPolicyAction.RE_OPTIMIZE
    assert (
        reoptimize_step.raw_learned_policy_action
        == simulation.SimulationPolicyAction.RE_OPTIMIZE
    )
    assert reoptimize_step.deterministic_action == simulation.SimulationPolicyAction.MONITOR_ONLY
    assert reoptimize_step.policy_guard_reason is None
    assert reoptimize_step.policy_guard_applied is False

    assert final_step.selected_policy_action == simulation.SimulationPolicyAction.MONITOR_ONLY
    assert final_step.raw_learned_policy_action == simulation.SimulationPolicyAction.MONITOR_ONLY
    assert final_step.deterministic_action == simulation.SimulationPolicyAction.CONTINUE_PLAN
    assert final_step.policy_guard_reason is None
    assert final_step.policy_guard_applied is False


def test_cgm_threshold_edge_regression_keeps_followup_clamp_then_monitor_only_path() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=V4_DATASET_PATH,
        user_id="syn-v4-user-019",
        max_cycles=5,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
    )

    followup_step = report.trace[1]
    clamped_reoptimize_step = report.trace[2]
    final_step = report.trace[-1]

    assert (
        followup_step.selected_policy_action
        == simulation.SimulationPolicyAction.ASK_TARGETED_FOLLOWUP
    )
    assert followup_step.raw_learned_policy_action == simulation.SimulationPolicyAction.MONITOR_ONLY
    assert (
        followup_step.deterministic_action
        == simulation.SimulationPolicyAction.ASK_TARGETED_FOLLOWUP
    )
    assert followup_step.policy_guard_reason == "permissiveness_clamp"
    assert followup_step.policy_guard_applied is True

    assert (
        clamped_reoptimize_step.selected_policy_action
        == simulation.SimulationPolicyAction.ASK_TARGETED_FOLLOWUP
    )
    assert (
        clamped_reoptimize_step.raw_learned_policy_action
        == simulation.SimulationPolicyAction.RE_OPTIMIZE
    )
    assert clamped_reoptimize_step.policy_guard_reason == "permissiveness_clamp"
    assert clamped_reoptimize_step.policy_guard_applied is True

    assert final_step.selected_policy_action == simulation.SimulationPolicyAction.MONITOR_ONLY
    assert final_step.raw_learned_policy_action == simulation.SimulationPolicyAction.MONITOR_ONLY
    assert final_step.deterministic_action == simulation.SimulationPolicyAction.CONTINUE_PLAN
    assert final_step.policy_guard_reason is None
    assert final_step.policy_guard_applied is False


def test_cgm_safety_ceiling_and_deterministic_fallback_remain_stable() -> None:
    guarded_report = simulation.simulate_closed_loop_scenario(
        dataset_path=V4_DATASET_PATH,
        user_id="syn-v4-user-008",
        max_cycles=5,
        model_artifact_path=V4_MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=V4_UNIFORM_POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
        enable_learned_reranking=True,
        enable_policy_effect_proxy_override=True,
    )
    fallback_report = simulation.simulate_closed_loop_scenario(
        dataset_path=V4_DATASET_PATH,
        user_id="syn-v4-user-008",
        max_cycles=5,
        model_artifact_path="artifacts/models/does_not_exist.json",
        policy_model_artifact_path="artifacts/models/does_not_exist.json",
    )

    guarded_step = guarded_report.trace[0]
    fallback_step = fallback_report.trace[0]

    assert guarded_step.raw_learned_policy_action == simulation.SimulationPolicyAction.CONTINUE_PLAN
    assert (
        guarded_step.selected_policy_action
        == simulation.SimulationPolicyAction.TRIGGER_SAFETY_RECHECK
    )
    assert (
        guarded_step.deterministic_action
        == simulation.SimulationPolicyAction.TRIGGER_SAFETY_RECHECK
    )
    assert guarded_step.policy_guard_reason == "baseline_intake_kept_deterministic"
    assert guarded_step.policy_guard_applied is True

    assert (
        guarded_report.final_policy_action
        == simulation.SimulationPolicyAction.TRIGGER_SAFETY_RECHECK
    )
    assert fallback_report.model_loaded is False
    assert fallback_report.policy_model_loaded is False
    assert (
        fallback_report.final_policy_action
        == simulation.SimulationPolicyAction.TRIGGER_SAFETY_RECHECK
    )
    assert fallback_step.raw_learned_policy_action is None
    assert fallback_step.action_source == simulation.PolicyActionSource.DETERMINISTIC_POLICY
    assert fallback_step.predicted_effect_source == simulation.EffectSource.DETERMINISTIC_FALLBACK
    assert fallback_step.policy_effect_proxy_override_applied is False
