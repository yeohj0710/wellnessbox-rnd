from pathlib import Path

import pytest

from wellnessbox_rnd.interim.agent import AgentState, BoundedAgent
from wellnessbox_rnd.interim.next_action import (
    NextAction,
    decide_next_action,
    load_next_action_policy,
)
from wellnessbox_rnd.interim.plan_lifecycle import (
    PlanLifecycleAction,
    PlanLifecycleService,
    PlanLifecycleState,
    PlanLifecycleTransitionRequestV1,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.interim.workflow_contract import ClosedLoopState


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        ({"adverse_event": True}, NextAction.STOP_AND_ESCALATE),
        ({"adverse_event": False, "ingredient_intolerance": True}, NextAction.REPLACE),
        ({"adverse_event": False, "dose_related_issue": True}, NextAction.REDUCE),
        (
            {"adverse_event": False, "safety_review_required": True},
            NextAction.REQUEST_SAFETY_REVIEW,
        ),
        ({"adverse_event": False, "followup_submitted": False}, NextAction.REQUEST_FOLLOWUP),
        ({"adverse_event": False, "measurement_complete": False}, NextAction.REQUEST_MEASUREMENT),
        ({"adverse_event": False, "ambiguous": True}, NextAction.HOLD_FOR_REVIEW),
        ({"adverse_event": False, "score_delta": 0.1}, NextAction.MAINTAIN),
        ({"adverse_event": False, "score_delta": 0.0}, NextAction.REOPTIMIZE),
    ],
)
def test_policy_selects_declared_action(event, expected) -> None:
    defaults = {
        "ingredient_intolerance": False,
        "dose_related_issue": False,
        "safety_review_required": False,
        "followup_submitted": True,
        "measurement_complete": True,
        "ambiguous": False,
        "score_delta": 1.0,
    }
    decision = decide_next_action(
        state=ClosedLoopState.FOLLOWUP_ACTIVE,
        event=defaults | event,
    )
    assert decision.action == expected


def test_policy_is_declared_data() -> None:
    policy = load_next_action_policy()
    assert len(policy["rules"]) == 9
    assert policy["source"].endswith("#19.2-19.3")


def test_bounded_agent_persists_authoritative_followup_transition(tmp_path: Path) -> None:
    store = InterimStore(tmp_path / "next-action.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values ('usr_policy', 'PROXY_GOLD_SIMULATION', "
            "'[]', '{}', 'hash', 'now')"
        )
    agent = BoundedAgent(store)
    run = agent.create_run(profile_id="usr_policy", idempotency_key="policy")
    with store.transaction() as connection:
        connection.execute(
            "update agent_runs set state_after=? where run_id=?",
            (AgentState.FOLLOWUP_ACTIVE, run["run_id"]),
        )
    result = agent.decide_followup_action(
        run_id=run["run_id"],
        event={"score_delta": -0.2},
    )
    assert result["action"] == "reoptimize"
    assert result["state_after"] == "PLAN_REOPTIMIZATION"
    assert store.scalar("select state_after from agent_runs") == "PLAN_REOPTIMIZATION"


def test_adverse_event_stops_after_escalation(tmp_path: Path) -> None:
    store = InterimStore(tmp_path / "next-action-stop.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values ('usr_stop', 'PROXY_GOLD_SIMULATION', "
            "'[]', '{}', 'hash', 'now')"
        )
    agent = BoundedAgent(store)
    run = agent.create_run(profile_id="usr_stop", idempotency_key="stop")
    with store.transaction() as connection:
        connection.execute(
            "update agent_runs set state_after=? where run_id=?",
            (AgentState.FOLLOWUP_ACTIVE, run["run_id"]),
        )
    result = agent.decide_followup_action(
        run_id=run["run_id"],
        event={"adverse_event": True},
    )
    assert result["action"] == "stop_and_escalate"
    assert result["state_after"] == "STOPPED"
    assert store.scalar("select status from agent_runs") == "COMPLETED"


def test_legacy_lifecycle_cannot_write_alongside_active_closed_loop(tmp_path: Path) -> None:
    store = InterimStore(tmp_path / "single-authority.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values ('usr_single', 'PROXY_GOLD_SIMULATION', "
            "'[]', '{}', 'hash', '2026-07-23T00:00:00+00:00')"
        )
        connection.execute(
            "insert into consent_snapshots values "
            "('consent_single', 'usr_single', 1, 'v1', '{}', 'hash', "
            "'2026-07-23T00:00:00+00:00')"
        )
        connection.execute(
            "insert into active_profile_consents values "
            "('usr_single', 'consent_single', '2026-07-23T00:00:00+00:00')"
        )
        connection.execute(
            "insert into executions values "
            "('exec_single', 'request_single', 'usr_single', null, 'consent_single', "
            "'hash', 'COMPLETE', '2026-07-23T00:00:00+00:00', "
            "'2026-07-23T00:00:00+00:00')"
        )
        connection.execute(
            "insert into execution_events(event_id, execution_id, consent_snapshot_id, "
            "event_index, event_type, source, idempotency_key, payload_json, payload_sha256, "
            "effective_payload_sha256, created_at) values "
            "('event_single', 'exec_single', 'consent_single', 0, 'recommendation', 'system', "
            "'plan', '{\"plan_id\":\"plan_single\"}', 'hash', 'hash', "
            "'2026-07-23T00:00:00+00:00')"
        )
    agent = BoundedAgent(store)
    agent.create_run(profile_id="usr_single", idempotency_key="active")
    request = PlanLifecycleTransitionRequestV1(
        execution_id="exec_single",
        profile_id="usr_single",
        plan_id="plan_single",
        expected_state=PlanLifecycleState.ACTIVE,
        action=PlanLifecycleAction.MAINTAIN,
        reason_code="FOLLOWUP_IMPROVED",
        idempotency_key="manual",
        occurred_at="2026-07-23T01:00:00+00:00",
    )
    with pytest.raises(ValueError, match="forbidden_use_closed_loop_policy"):
        PlanLifecycleService(store).transition(request)
