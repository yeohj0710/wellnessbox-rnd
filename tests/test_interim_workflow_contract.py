from __future__ import annotations

import pytest

from wellnessbox_rnd.interim.agent import BoundedAgent
from wellnessbox_rnd.interim.evidence import EvidenceRegistry
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.interim.workflow_contract import (
    CLOSED_LOOP_ALLOWED_OPERATIONS_V1,
    CLOSED_LOOP_TRANSITIONS_V1,
    ClosedLoopExecutionTraceV1,
    ClosedLoopOperation,
    ClosedLoopState,
    apply_closed_loop_transition_v1,
    closed_loop_contract_snapshot_v1,
)


def test_closed_loop_contract_has_one_complete_state_and_operation_registry() -> None:
    snapshot = closed_loop_contract_snapshot_v1()

    assert snapshot["schema_version"] == "closed_loop_state_operation_contract_v1"
    assert snapshot["states"] == sorted(state.value for state in ClosedLoopState)
    assert snapshot["operations"] == sorted(operation.value for operation in ClosedLoopOperation)
    assert set(CLOSED_LOOP_ALLOWED_OPERATIONS_V1) == set(ClosedLoopState)
    assert set(CLOSED_LOOP_TRANSITIONS_V1) == set(ClosedLoopState)
    assert "manual_review" not in snapshot["operations"]
    assert "human_handoff" not in snapshot["operations"]


def test_closed_loop_contract_pins_safety_to_plan_order() -> None:
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[ClosedLoopState.PROFILE_READY] == frozenset(
        {ClosedLoopOperation.CHECK_SAFETY, ClosedLoopOperation.STOP}
    )
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[ClosedLoopState.SAFETY_CHECK] == frozenset(
        {ClosedLoopOperation.GENERATE_CANDIDATES, ClosedLoopOperation.STOP}
    )
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[ClosedLoopState.RANKING] == frozenset(
        {ClosedLoopOperation.LOOKUP_EVIDENCE, ClosedLoopOperation.STOP}
    )
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[ClosedLoopState.EVIDENCE_RETRIEVAL] == frozenset(
        {ClosedLoopOperation.OPTIMIZE, ClosedLoopOperation.STOP}
    )
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[
        ClosedLoopState.REGIMEN_OPTIMIZATION
    ] == frozenset({ClosedLoopOperation.START_PLAN, ClosedLoopOperation.STOP})


def test_closed_loop_contract_rejects_forbidden_transition() -> None:
    assert (
        apply_closed_loop_transition_v1(
            current=ClosedLoopState.PROFILE_READY,
            operation=ClosedLoopOperation.CHECK_SAFETY,
            target=ClosedLoopState.SAFETY_CHECK,
        )
        == ClosedLoopState.SAFETY_CHECK
    )
    with pytest.raises(ValueError, match="forbidden_closed_loop_transition"):
        apply_closed_loop_transition_v1(
            current=ClosedLoopState.PROFILE_READY,
            operation=ClosedLoopOperation.START_PLAN,
            target=ClosedLoopState.PLAN_READY,
        )


def test_execution_trace_rejects_discontinuous_or_false_plan_start() -> None:
    with pytest.raises(ValueError, match="closed_loop_trace_state_discontinuity"):
        ClosedLoopExecutionTraceV1.model_validate(
            {
                "run_id": "run_contract",
                "status": "SAFETY_CHECK",
                "steps": [
                    {
                        "operation": "load_profile",
                        "state_before": "INTAKE",
                        "state_after": "CONSENT_CHECK",
                    },
                    {
                        "operation": "check_safety",
                        "state_before": "PROFILE_READY",
                        "state_after": "SAFETY_CHECK",
                    },
                ],
                "plan_start_recorded": False,
            }
        )
    with pytest.raises(ValueError, match="closed_loop_trace_plan_start_mismatch"):
        ClosedLoopExecutionTraceV1.model_validate(
            {
                "run_id": "run_contract",
                "status": "CONSENT_CHECK",
                "steps": [
                    {
                        "operation": "load_profile",
                        "state_before": "INTAKE",
                        "state_after": "CONSENT_CHECK",
                    }
                ],
                "plan_start_recorded": True,
            }
        )


@pytest.mark.parametrize("terminal", [ClosedLoopState.STOPPED, ClosedLoopState.COMPLETED])
def test_closed_loop_terminal_states_allow_no_operations(terminal: ClosedLoopState) -> None:
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[terminal] == frozenset()
    assert CLOSED_LOOP_TRANSITIONS_V1[terminal] == frozenset()


def _workflow_agent(tmp_path) -> BoundedAgent:
    store = InterimStore(tmp_path / "workflow.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            """
            insert into user_profiles values (
              'usr_workflow0001', 'PROXY_GOLD_SIMULATION', '[]', '{}', 'hash', 'now'
            )
            """
        )
    registry = EvidenceRegistry(store)
    registry.register_source(
        source_id="workflow-source",
        source_tier="official",
        title="Workflow evidence",
        canonical_uri="https://example.test/workflow",
        license_status="OPEN",
    )
    registry.add_passage(
        source_id="workflow-source",
        passage_text="magnesium sleep support evidence",
        approved_for_safety=True,
    )
    return BoundedAgent(store)


def test_ordered_workflow_runs_safety_candidate_evidence_optimization_then_plan(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)

    trace = agent.execute_recommendation_workflow(
        profile_id="usr_workflow0001",
        idempotency_key="ordered-success",
        safety_arguments={"age": 40, "ingredients": ["magnesium"]},
        ingredients=["magnesium"],
        evidence_query="magnesium",
        max_items=1,
    )

    assert trace["status"] == "PLAN_READY"
    assert trace["plan_start_recorded"] is True
    assert [step["operation"] for step in trace["steps"]] == [
        "load_profile",
        "verify_consent",
        "check_safety",
        "generate_candidates",
        "lookup_evidence",
        "optimize",
        "start_plan",
    ]
    assert agent.store.scalar("select count(*) from agent_steps") == 7


def test_ordered_workflow_stops_after_hard_safety_result(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)

    trace = agent.execute_recommendation_workflow(
        profile_id="usr_workflow0001",
        idempotency_key="ordered-block",
        safety_arguments={"age": 40, "pregnant": True, "ingredients": ["magnesium"]},
        ingredients=["magnesium"],
        evidence_query="magnesium",
        max_items=1,
    )

    assert trace["status"] == "STOPPED"
    assert trace["plan_start_recorded"] is False
    assert [step["operation"] for step in trace["steps"]] == [
        "load_profile",
        "verify_consent",
        "check_safety",
        "stop",
    ]


def test_ordered_workflow_stops_before_optimization_when_evidence_is_missing(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)

    trace = agent.execute_recommendation_workflow(
        profile_id="usr_workflow0001",
        idempotency_key="ordered-no-evidence",
        safety_arguments={"age": 40, "ingredients": ["magnesium"]},
        ingredients=["magnesium"],
        evidence_query="not-present",
        max_items=1,
    )

    assert trace["status"] == "STOPPED"
    assert trace["plan_start_recorded"] is False
    assert "optimize" not in [step["operation"] for step in trace["steps"]]


def test_direct_optimization_before_evidence_is_rejected(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)
    run = agent.create_run(profile_id="usr_workflow0001", idempotency_key="out-of-order")

    with pytest.raises(ValueError, match="workflow_operation_not_allowed"):
        agent.execute_tool(
            run_id=run["run_id"],
            tool_name="optimize_regimen",
            arguments={"ranked": [{"ingredient": "magnesium", "score": 1.0}]},
        )
    assert agent.store.scalar("select count(*) from agent_steps") == 0


def test_public_move_cannot_bypass_tool_execution(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)
    run = agent.create_run(profile_id="usr_workflow0001", idempotency_key="move-bypass")

    with pytest.raises(ValueError, match="direct_agent_move_forbidden"):
        agent.move(
            run["run_id"],
            ClosedLoopState.CONSENT_CHECK,
            operation=ClosedLoopOperation.LOAD_PROFILE,
        )


def test_ordered_workflow_rejects_different_safety_candidates(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)
    with pytest.raises(ValueError, match="safety_candidate_ingredients_mismatch"):
        agent.execute_recommendation_workflow(
            profile_id="usr_workflow0001",
            idempotency_key="candidate-mismatch",
            safety_arguments={"age": 40, "ingredients": ["vitamin_d"]},
            ingredients=["magnesium"],
            evidence_query="magnesium",
            max_items=1,
        )


def test_ordered_workflow_retry_returns_same_durable_trace(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)
    arguments = {
        "profile_id": "usr_workflow0001",
        "idempotency_key": "durable-retry",
        "safety_arguments": {"age": 40},
        "ingredients": ["magnesium"],
        "evidence_query": "magnesium",
        "max_items": 1,
    }
    first = agent.execute_recommendation_workflow(**arguments)
    second = agent.execute_recommendation_workflow(**arguments)

    assert second == first
    assert agent.store.scalar("select count(*) from agent_runs") == 1
    assert agent.store.scalar("select count(*) from agent_steps") == 7


def test_same_idempotency_key_rejects_changed_payload(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)
    base = {
        "profile_id": "usr_workflow0001",
        "idempotency_key": "payload-conflict",
        "safety_arguments": {"age": 40},
        "ingredients": ["magnesium"],
        "evidence_query": "magnesium",
        "max_items": 1,
    }
    agent.execute_recommendation_workflow(**base)
    with pytest.raises(ValueError, match="workflow_idempotency_payload_conflict"):
        agent.execute_recommendation_workflow(**(base | {"max_items": 2}))


def test_failed_tool_postcondition_releases_execution_claim(tmp_path) -> None:
    agent = _workflow_agent(tmp_path)
    run = agent.create_run(profile_id="usr_workflow0001", idempotency_key="failed-tool")
    with agent.store.transaction() as connection:
        connection.execute(
            "update agent_runs set state_after='SAFETY_CHECK' where run_id=?",
            (run["run_id"],),
        )
    with pytest.raises(RuntimeError, match="tool_postcondition_failed"):
        agent.execute_tool(
            run_id=run["run_id"],
            tool_name="rank_ingredients",
            arguments={"ingredients": []},
        )
    assert agent.store.scalar(
        "select status from agent_runs where run_id=?", (run["run_id"],)
    ) == "ACTIVE"
