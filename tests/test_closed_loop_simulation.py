from wellnessbox_rnd import simulation

DATASET_PATH = "data/synthetic/synthetic_longitudinal_v1.jsonl"
MODEL_ARTIFACT_PATH = "artifacts/models/efficacy_model_v0.json"
POLICY_MODEL_ARTIFACT_PATH = "artifacts/models/policy_model_v0.json"


def test_closed_loop_simulation_positive_trace_uses_learned_model() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=DATASET_PATH,
        user_id="syn-user-001",
        max_cycles=3,
        model_artifact_path=MODEL_ARTIFACT_PATH,
    )

    assert len(report.trace) == 3
    assert report.trace[0].state_after == "recommendation_ready"
    assert report.trace[0].policy_action == simulation.SimulationPolicyAction.START_PLAN
    assert report.trace[1].policy_action == simulation.SimulationPolicyAction.CONTINUE_PLAN
    assert report.trace[2].policy_action == simulation.SimulationPolicyAction.CONTINUE_PLAN
    assert any(
        step.predicted_effect_source == simulation.EffectSource.LEARNED_MODEL
        for step in report.trace
    )
    assert report.final_state == "intake_active"


def test_closed_loop_simulation_escalates_high_risk_followup() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=DATASET_PATH,
        user_id="syn-user-002",
        max_cycles=3,
        model_artifact_path=MODEL_ARTIFACT_PATH,
    )

    assert len(report.trace) == 2
    assert report.trace[0].policy_action == simulation.SimulationPolicyAction.START_PLAN
    assert report.trace[1].engine_next_action.value == "trigger_safety_recheck"
    assert report.trace[1].policy_action == simulation.SimulationPolicyAction.REDUCE_OR_STOP
    assert report.final_state == "stop_or_escalate"
    assert report.terminated_early is True


def test_closed_loop_simulation_falls_back_without_model() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=DATASET_PATH,
        user_id="syn-user-001",
        max_cycles=2,
        model_artifact_path="artifacts/models/does_not_exist.json",
    )

    assert all(
        step.predicted_effect_source == simulation.EffectSource.DETERMINISTIC_FALLBACK
        for step in report.trace
    )
    assert report.model_loaded is False


def test_closed_loop_simulation_can_enable_learned_reranking() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=DATASET_PATH,
        user_id="syn-user-009",
        max_cycles=1,
        model_artifact_path=MODEL_ARTIFACT_PATH,
        enable_learned_reranking=True,
    )

    assert report.learned_reranking_enabled is True
    assert report.trace[0].recommendation_keys[0] == "vitamin_c"


def test_closed_loop_simulation_can_enable_learned_policy() -> None:
    report = simulation.simulate_closed_loop_scenario(
        dataset_path=DATASET_PATH,
        user_id="syn-user-001",
        max_cycles=2,
        model_artifact_path=MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
        enable_learned_policy=True,
    )

    assert report.learned_policy_enabled is True
    assert report.policy_model_loaded is True
    assert all(
        step.policy_action_source == simulation.PolicyActionSource.LEARNED_POLICY_GUARDED
        for step in report.trace
    )


def test_closed_loop_batch_simulation_reports_aggregate_metrics() -> None:
    report = simulation.compare_batch_simulation_modes(
        dataset_path=DATASET_PATH,
        max_cycles=3,
        max_users=12,
        model_artifact_path=MODEL_ARTIFACT_PATH,
        policy_model_artifact_path=POLICY_MODEL_ARTIFACT_PATH,
    )

    assert len(report.compared_modes) == 2
    deterministic_mode, learned_mode = report.compared_modes
    assert deterministic_mode.scenario_count == 12
    assert learned_mode.scenario_count == 12
    assert deterministic_mode.total_trace_steps >= 12
    assert learned_mode.total_trace_steps >= 12
    assert "followup_received->intake_active" in learned_mode.state_transition_counts
    assert learned_mode.policy_action_source_counts["learned_policy_guarded"] > 0
    assert learned_mode.policy_model_loaded is True
