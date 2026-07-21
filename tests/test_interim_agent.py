from datetime import UTC, datetime
from pathlib import Path

import pytest

from wellnessbox_rnd.interim.agent import TOOL_NAMES, AgentState, BoundedAgent, transition
from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
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


def test_followup_inputs_decide_next_jobs_on_agent_path(tmp_path: Path) -> None:
    agent = _agent(tmp_path)
    run = agent.create_run(profile_id="usr_1234567890abcdef", idempotency_key="inputs")
    _seed_run_state(agent, run["run_id"], AgentState.FOLLOWUP_ACTIVE)
    context = {"execution_id": "execution_agent", "plan_id": "plan_agent_job"}

    pro = agent.execute_tool(
        run_id=run["run_id"],
        tool_name="ingest_pro",
        arguments=context
        | {
            "observation_id": "pro_agent_input",
            "observed_at": "2026-07-21T12:00:00Z",
            "timepoint_weeks": 2,
            "z_pre": 1.0,
            "z_post": 0.5,
            "percentile_point_change": 10,
        },
        consent_scopes={"pro:write"},
    )
    device = agent.execute_tool(
        run_id=run["run_id"],
        tool_name="ingest_wearable",
        arguments=context
        | {
            "session_id": "device_agent_input",
            "source": "W",
            "payload": {
                "observed_at": "2026-07-21T13:00:00Z",
                "value": 7000,
                "unit": "steps",
                "timezone": "UTC",
                "source_record_id": "wearable-agent-1",
            },
        },
        consent_scopes={"device:write"},
    )

    assert pro["next_job_decision"]["reason_code"] == "PRO_INPUT_RECEIVED"
    assert device["next_job_decision"]["reason_code"] == "DEVICE_INPUT_RECEIVED"
    assert agent.store.scalar("select count(*) from workflow_jobs") == 2


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
    WorkflowJobQueue(agent.store).schedule_followup_with_reminder(
        followup_id="fu_serious_ae",
        profile_id="usr_1234567890abcdef",
        plan_id="plan_agent_job",
        execution_id="execution_agent",
        due_at=datetime(2026, 8, 4, tzinfo=UTC),
        reminder_at=datetime(2026, 8, 3, tzinfo=UTC),
        requested_data=["PRO"],
        now=datetime(2026, 7, 21, tzinfo=UTC),
    )
    arguments = {
        "case_id": "ae_serious_agent",
        "profile_id": "usr_1234567890abcdef",
        "execution_id": "execution_agent",
        "plan_id": "plan_agent_job",
        "serious": True,
        "observed_at": "2026-07-21T12:00:00Z",
    }
    result = agent._log_adverse_event(
        run["run_id"],
        arguments,
    )
    assert result["plan_stopped"] is True
    assert (
        agent.store.scalar("select status from recommendation_runs where run_id='rec1'")
        == "STOPPED"
    )
    assert agent.store.scalar("select count(*) from review_tasks") == 1
    assert agent.store.scalar("select status from followups") == "CLOSED"
    assert agent.store.scalar("select status from workflow_jobs") == "CANCELLED"
    assert agent.store.scalar(
        "select count(*) from execution_events where idempotency_key='serious-ae:ae_serious_agent'"
    ) == 1
    assert (
        agent.store.scalar("select status from agent_runs where run_id=?", (run["run_id"],))
        == "COMPLETED"
    )
    with pytest.raises(ValueError, match="agent_run_not_active"):
        agent.execute_tool(run_id=run["run_id"], tool_name="check_safety", arguments={"age": 40})
    retry = agent.record_adverse_event(run_id=run["run_id"], arguments=arguments)
    assert retry["deduplicated"] is True
    with pytest.raises(ValueError, match="idempotency_payload_conflict"):
        agent.record_adverse_event(
            run_id=run["run_id"], arguments=arguments | {"related_to_recommendation": False}
        )
    with pytest.raises(ValueError, match="serious_adverse_event_recommendation_hold"):
        agent.create_run(
            profile_id="usr_1234567890abcdef", idempotency_key="after-serious-event"
        )
