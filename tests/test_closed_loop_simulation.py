from wellnessbox_rnd import simulation

DATASET_PATH = "data/synthetic/synthetic_longitudinal_v2.jsonl"
MODEL_ARTIFACT_PATH = "artifacts/models/effect_model_v1.json"
POLICY_MODEL_ARTIFACT_PATH = "artifacts/models/policy_model_v1.json"


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
