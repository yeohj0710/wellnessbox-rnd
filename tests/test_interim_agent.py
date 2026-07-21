from pathlib import Path

import pytest

from wellnessbox_rnd.interim.agent import TOOL_NAMES, AgentState, BoundedAgent, transition
from wellnessbox_rnd.interim.store import InterimStore


def _agent(tmp_path: Path) -> BoundedAgent:
    store = InterimStore(tmp_path / "agent.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            """
            insert into user_profiles values (
              'usr_1234567890abcdef', 'PROXY_GOLD_SIMULATION',
              '["followup:write","pro:write","ae:write","device:write"]', '{}', 'hash', 'now'
            )
            """
        )
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_agent', 'usr_1234567890abcdef', 1, 'v1', '{}', "
            "'consent-agent', 'now')"
        )
        connection.execute(
            "insert into executions values "
            "('execution_agent', 'request_agent', 'usr_1234567890abcdef', null, "
            "'consent_agent', 'request-agent', 'COMPLETE', 'now', 'now')"
        )
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values (
              'event_agent', 'execution_agent', 'consent_agent', 0, 'recommendation',
              'system', 'plan', '{"plan_id":"plan_agent_job"}', 'plan-agent',
              'plan-agent', 'now'
            )
            """
        )
    return BoundedAgent(store)


def _seed_run_state(agent: BoundedAgent, run_id: str, state: AgentState) -> None:
    with agent.store.transaction() as connection:
        connection.execute("update agent_runs set state_after=? where run_id=?", (state, run_id))


def test_state_machine_uses_authoritative_states_and_rejects_unknown_transition() -> None:
    assert len(AgentState) == 11
    assert transition(AgentState.INTAKE, AgentState.CONSENT_CHECK) == AgentState.CONSENT_CHECK
    with pytest.raises(ValueError, match="invalid_agent_transition"):
        transition(AgentState.INTAKE, AgentState.PLAN_READY)


def test_exact_ten_typed_tool_names() -> None:
    assert len(TOOL_NAMES) == 9
    assert "start_plan" in TOOL_NAMES
    assert "log_adverse_event" not in TOOL_NAMES


def test_run_creation_is_idempotent_and_tool_is_audited(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    first = agent.create_run(profile_id="usr_1234567890abcdef", idempotency_key="request-1")
    second = agent.create_run(profile_id="usr_1234567890abcdef", idempotency_key="request-1")
    assert first["run_id"] == second["run_id"]
    assert second["deduplicated"] is True
    _seed_run_state(agent, first["run_id"], AgentState.PROFILE_READY)
    result = agent.execute_tool(
        run_id=first["run_id"],
        tool_name="check_safety",
        arguments={"age": 40, "ingredients": []},
    )
    assert result["action"] == "PASS"
    assert agent.store.scalar("select count(*) from agent_steps") == 1


def test_missing_consent_blocks_side_effect_tool(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    with agent.store.transaction() as connection:
        connection.execute(
            """
            update user_profiles set consent_scopes_json='[]'
            where profile_id='usr_1234567890abcdef'
            """
        )
    run = agent.create_run(profile_id="usr_1234567890abcdef", idempotency_key="request-2")
    _seed_run_state(agent, run["run_id"], AgentState.PLAN_READY)
    with pytest.raises(PermissionError, match="missing_followup_consent"):
        agent.execute_tool(
            run_id=run["run_id"],
            tool_name="create_followup",
            arguments={"profile_id": "usr_1234567890abcdef"},
        )


def test_create_followup_stores_reminder_in_shared_workflow_queue(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    run = agent.create_run(profile_id="usr_1234567890abcdef", idempotency_key="followup-job")
    _seed_run_state(agent, run["run_id"], AgentState.PLAN_READY)

    result = agent.execute_tool(
        run_id=run["run_id"],
        tool_name="create_followup",
        arguments={
            "plan_id": "plan_agent_job",
            "execution_id": "execution_agent",
            "followup_id": "fu_agent_job",
            "due_at": "2026-08-04T12:00:00+00:00",
            "requested_data": ["PRO", "ADHERENCE"],
        },
        consent_scopes={"followup:write"},
    )

    assert result["reminder_job"]["job_type"] == "FOLLOWUP_REMINDER"
    assert agent.store.scalar("select plan_id from followups") == "plan_agent_job"
    assert agent.store.scalar("select count(*) from workflow_jobs") == 1


def test_unknown_run_cannot_commit_side_effect(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    with pytest.raises(ValueError, match="unknown_agent_run"):
        agent.execute_tool(
            run_id="run_missing",
            tool_name="create_followup",
            arguments={"profile_id": "usr_1234567890abcdef"},
            consent_scopes={"followup:write"},
        )
    assert agent.store.scalar("select count(*) from followups") == 0


def test_idempotency_key_is_namespaced_by_profile(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    with agent.store.transaction() as connection:
        connection.execute(
            """
            insert into user_profiles values (
              'usr_fedcba0987654321', 'PROXY_GOLD_SIMULATION', '[]', '{}', 'hash2', 'now'
            )
            """
        )
    first = agent.create_run(profile_id="usr_1234567890abcdef", idempotency_key="same")
    second = agent.create_run(profile_id="usr_fedcba0987654321", idempotency_key="same")
    assert first["run_id"] != second["run_id"]


def test_serious_ae_atomically_stops_plan_and_creates_review(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    with agent.store.transaction() as connection:
        connection.execute(
            """
            insert into recommendation_runs values (
              'rec1', 'usr_1234567890abcdef', null, 'READY', 'hash', '{}', 'now', null
            )
            """
        )
    run = agent.create_run(profile_id="usr_1234567890abcdef", idempotency_key="request-3")
    _seed_run_state(agent, run["run_id"], AgentState.FOLLOWUP_ACTIVE)
    result = agent._log_adverse_event(
        run["run_id"],
        {"profile_id": "usr_1234567890abcdef", "serious": True},
    )
    assert result["plan_stopped"] is True
    assert (
        agent.store.scalar("select status from recommendation_runs where run_id='rec1'")
        == "STOPPED"
    )
    assert agent.store.scalar("select count(*) from review_tasks") == 1
    assert (
        agent.store.scalar("select status from agent_runs where run_id=?", (run["run_id"],))
        == "COMPLETED"
    )
    with pytest.raises(ValueError, match="agent_run_not_active"):
        agent.execute_tool(run_id=run["run_id"], tool_name="check_safety", arguments={"age": 40})
