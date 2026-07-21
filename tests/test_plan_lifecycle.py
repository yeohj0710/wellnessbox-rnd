from __future__ import annotations

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from wellnessbox_rnd.interim.data_mutation import DataMutationLedger, EventMutationStateError
from wellnessbox_rnd.interim.jobs import WorkflowJobQueue
from wellnessbox_rnd.interim.plan_lifecycle import (
    PlanLifecycleAction,
    PlanLifecycleService,
    PlanLifecycleState,
    PlanLifecycleTransitionRequestV1,
)
from wellnessbox_rnd.interim.store import InterimStore

NOW = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)


def _service(
    tmp_path, *, plan_id: str = "plan_lifecycle", replacement_plan_id: str | None = None
) -> PlanLifecycleService:
    store = InterimStore(tmp_path / "lifecycle.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            "insert into user_profiles values (?, 'PROXY_GOLD_SIMULATION', '[]', '{}', 'p', ?)",
            ("usr_lifecycle", NOW.isoformat()),
        )
        connection.execute(
            "insert into consent_snapshots values (?, ?, 1, 'v1', '{}', 'c', ?)",
            ("consent_lifecycle", "usr_lifecycle", NOW.isoformat()),
        )
        connection.execute(
            "insert into active_profile_consents values (?, ?, ?)",
            ("usr_lifecycle", "consent_lifecycle", NOW.isoformat()),
        )
        connection.execute(
            "insert into executions values "
            "(?, 'request_lifecycle', ?, null, ?, 'r', 'COMPLETE', ?, ?)",
            (
                "execution_lifecycle",
                "usr_lifecycle",
                "consent_lifecycle",
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
        connection.execute(
            """
            insert into execution_events(
              event_id, execution_id, consent_snapshot_id, event_index, event_type,
              source, idempotency_key, payload_json, payload_sha256,
              effective_payload_sha256, created_at
            ) values ('event_plan_seed', 'execution_lifecycle', 'consent_lifecycle', 0,
              'recommendation', 'system', 'seed-plan', ?, 'seed', 'seed', ?)
            """,
            (f'{{"plan_id":"{plan_id}"}}', NOW.isoformat()),
        )
        if replacement_plan_id:
            payload = {
                "plan_id": replacement_plan_id,
                "lifecycle_role": "replacement_candidate",
                "replaces_plan_id": plan_id,
            }
            candidate_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            connection.execute(
                """
                insert into execution_events(
                  event_id, execution_id, consent_snapshot_id, event_index, event_type,
                  source, idempotency_key, payload_json, payload_sha256,
                  effective_payload_sha256, created_at
                ) values ('event_replacement_candidate', 'execution_lifecycle',
                  'consent_lifecycle', 1, 'optimization', 'system',
                  'replacement-candidate', ?, ?, ?, ?)
                """,
                (
                    json.dumps(payload, sort_keys=True),
                    candidate_hash,
                    candidate_hash,
                    NOW.isoformat(),
                ),
            )
    return PlanLifecycleService(store)


def _request(
    *,
    action: str = "maintain",
    expected_state: str = "ACTIVE",
    plan_id: str = "plan_lifecycle",
    replacement_plan_id: str | None = None,
    idempotency_key: str | None = None,
) -> PlanLifecycleTransitionRequestV1:
    return PlanLifecycleTransitionRequestV1(
        execution_id="execution_lifecycle",
        profile_id="usr_lifecycle",
        plan_id=plan_id,
        expected_state=expected_state,
        action=action,
        reason_code=f"TEST_{action.upper()}",
        idempotency_key=idempotency_key or f"lifecycle-{action}",
        occurred_at=NOW,
        replacement_plan_id=replacement_plan_id,
    )


def test_contract_covers_required_actions_and_forbids_order_fields() -> None:
    assert {item.value for item in PlanLifecycleAction} == {
        "maintain",
        "adjust",
        "replace",
        "stop",
        "monitor",
    }
    with pytest.raises(ValidationError, match="order_status"):
        PlanLifecycleTransitionRequestV1.model_validate(
            _request().model_dump() | {"order_status": "PAID"}
        )


def test_replace_requires_distinct_replacement_plan() -> None:
    with pytest.raises(ValidationError, match="replacement_plan_id_required"):
        _request(action="replace")
    with pytest.raises(ValidationError, match="replacement_plan_id_must_be_distinct"):
        _request(action="replace", replacement_plan_id="plan_lifecycle")


@pytest.mark.parametrize(
    ("action", "target"),
    [
        ("maintain", "MAINTAINED"),
        ("adjust", "ADJUSTED"),
        ("monitor", "MONITORING"),
        ("stop", "STOPPED"),
    ],
)
def test_transition_persists_in_existing_execution_events(tmp_path, action, target) -> None:
    service = _service(tmp_path)

    result = service.transition(_request(action=action))

    assert result.state_after == PlanLifecycleState(target)
    assert result.order_state_effect == "NONE"
    assert result.order_state_mutation_allowed is False
    assert (
        service.store.scalar(
            "select count(*) from execution_events where event_type='followup_evaluation'"
        )
        == 1
    )
    assert (
        service.store.scalar(
            "select count(*) from sqlite_master where type='table' and name like '%lifecycle%'"
        )
        == 0
    )


def test_replace_deactivates_old_plan_and_activates_replacement(tmp_path) -> None:
    service = _service(tmp_path, replacement_plan_id="plan_replacement")
    result = service.transition(_request(action="replace", replacement_plan_id="plan_replacement"))

    assert result.state_after == PlanLifecycleState.REPLACED
    assert result.replacement_state == PlanLifecycleState.ACTIVE
    stored = json.loads(
        service.store.scalar(
            "select payload_json from execution_events where event_id=?", (result.event_id,)
        )
    )
    assert stored["replacement_candidate_event_id"] == "event_replacement_candidate"
    assert len(stored["replacement_candidate_payload_sha256"]) == 64
    followup = service.transition(
        _request(
            action="monitor",
            plan_id="plan_replacement",
            idempotency_key="monitor-replacement",
        )
    )
    assert followup.state_after == PlanLifecycleState.MONITORING
    with service.store.transaction() as connection:
        assert not WorkflowJobQueue._execution_plan_is_active(
            connection,
            execution_id="execution_lifecycle",
            profile_id="usr_lifecycle",
            plan_id="plan_lifecycle",
        )
        assert WorkflowJobQueue._execution_plan_is_active(
            connection,
            execution_id="execution_lifecycle",
            profile_id="usr_lifecycle",
            plan_id="plan_replacement",
        )


def test_replace_rejects_phantom_or_wrong_lineage_candidate(tmp_path) -> None:
    phantom = _service(tmp_path / "phantom")
    with pytest.raises(ValueError, match="replacement_plan_candidate_required"):
        phantom.transition(_request(action="replace", replacement_plan_id="plan_replacement"))

    wrong = _service(tmp_path / "wrong", replacement_plan_id="plan_replacement")
    with wrong.store.transaction() as connection:
        payload = json.loads(
            connection.execute(
                "select payload_json from execution_events "
                "where event_id='event_replacement_candidate'"
            ).fetchone()[0]
        )
        payload["replaces_plan_id"] = "another_plan"
        connection.execute(
            "update execution_events set payload_json=? "
            "where event_id='event_replacement_candidate'",
            (json.dumps(payload, sort_keys=True),),
        )
    with pytest.raises(ValueError, match="replacement_plan_candidate_required"):
        wrong.transition(_request(action="replace", replacement_plan_id="plan_replacement"))


def test_replacement_candidate_is_inactive_before_transition(tmp_path) -> None:
    service = _service(tmp_path, replacement_plan_id="plan_replacement")
    with service.store.transaction() as connection:
        assert not WorkflowJobQueue._execution_plan_is_active(
            connection,
            execution_id="execution_lifecycle",
            profile_id="usr_lifecycle",
            plan_id="plan_replacement",
        )


def test_lifecycle_event_rejects_ledger_and_direct_database_mutation(tmp_path) -> None:
    service = _service(tmp_path)
    result = service.transition(_request(action="stop"))
    ledger = DataMutationLedger(service.store)
    for operation, replacement in (("correction", {"changed": True}), ("deletion", None)):
        with pytest.raises(EventMutationStateError, match="plan_lifecycle_event_immutable"):
            ledger.apply(
                profile_id="usr_lifecycle",
                target_type="execution_event",
                target_event_id=result.event_id,
                operation=operation,
                idempotency_key=f"immutable-{operation}",
                replacement_payload=replacement,
            )
    with service.store.transaction() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="plan_lifecycle_event_immutable"):
            connection.execute(
                "update execution_events set payload_state='DELETED' where event_id=?",
                (result.event_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="plan_lifecycle_event_immutable"):
            connection.execute("delete from execution_events where event_id=?", (result.event_id,))


def test_consumed_replacement_candidate_is_immutable(tmp_path) -> None:
    service = _service(tmp_path, replacement_plan_id="plan_replacement")
    service.transition(_request(action="replace", replacement_plan_id="plan_replacement"))
    ledger = DataMutationLedger(service.store)
    with pytest.raises(EventMutationStateError, match="consumed_replacement_candidate_immutable"):
        ledger.apply(
            profile_id="usr_lifecycle",
            target_type="execution_event",
            target_event_id="event_replacement_candidate",
            operation="deletion",
            idempotency_key="delete-consumed-candidate",
        )
    with service.store.transaction() as connection:
        with pytest.raises(sqlite3.IntegrityError, match="plan_lifecycle_event_immutable"):
            connection.execute(
                "delete from execution_events where event_id='event_replacement_candidate'"
            )


def test_migration_adds_consumed_candidate_guards_to_existing_database(tmp_path) -> None:
    service = _service(tmp_path, replacement_plan_id="plan_replacement")
    with service.store.transaction() as connection:
        connection.execute("drop trigger plan_lifecycle_dependencies_no_update_v2")
        connection.execute("drop trigger plan_lifecycle_dependencies_no_delete_v2")
    service.store.migrate()
    service.transition(_request(action="replace", replacement_plan_id="plan_replacement"))
    with service.store.transaction() as connection:
        names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='trigger' "
                "and name like 'plan_lifecycle_dependencies_%'"
            )
        }
        assert names == {
            "plan_lifecycle_dependencies_no_update_v2",
            "plan_lifecycle_dependencies_no_delete_v2",
        }
        with pytest.raises(sqlite3.IntegrityError, match="plan_lifecycle_event_immutable"):
            connection.execute(
                "delete from execution_events where event_id='event_replacement_candidate'"
            )


def test_transition_rejects_time_before_existing_lineage(tmp_path) -> None:
    service = _service(tmp_path)
    request = _request().model_copy(update={"occurred_at": NOW - timedelta(seconds=1)})
    with pytest.raises(ValueError, match="plan_lifecycle_occurred_at_before_lineage"):
        service.transition(request)


def test_terminal_transition_closes_followup_and_jobs_without_order_table(tmp_path) -> None:
    service = _service(tmp_path)
    with service.store.transaction() as connection:
        connection.execute(
            """
            insert into followups(
              followup_id, profile_id, plan_id, execution_id, due_at,
              requested_data_json, status, created_at
            ) values ('fu_lifecycle', 'usr_lifecycle', 'plan_lifecycle',
              'execution_lifecycle', ?, '[]', 'OPEN', ?)
            """,
            (NOW.isoformat(), NOW.isoformat()),
        )
        connection.execute(
            """
            insert into workflow_jobs(
              job_id, job_type, status, idempotency_key, profile_id, plan_id,
              followup_id, execution_id, scheduled_at, payload_json,
              payload_sha256, created_at, attempt_count
            ) values ('job_lifecycle', 'PLAN_REEVALUATION', 'READY',
              'job-lifecycle', 'usr_lifecycle', 'plan_lifecycle', 'fu_lifecycle',
              'execution_lifecycle', ?, '{}', 'job-hash', ?, 0)
            """,
            (NOW.isoformat(), NOW.isoformat()),
        )

    result = service.transition(_request(action="stop"))

    assert result.terminal_work_closed is True
    assert service.store.scalar("select status from followups") == "CLOSED"
    assert service.store.scalar("select status from workflow_jobs") == "CANCELLED"
    assert service.store.scalar("select last_error from workflow_jobs") == (
        "PLAN_LIFECYCLE_STOPPED"
    )
    assert (
        service.store.scalar(
            "select count(*) from sqlite_master where type='table' and name like '%order%'"
        )
        == 0
    )


def test_exact_retry_deduplicates_and_changed_payload_conflicts(tmp_path) -> None:
    service = _service(tmp_path)
    request = _request()
    first = service.transition(request)
    retry = service.transition(request)

    assert retry.event_id == first.event_id
    assert retry.deduplicated is True
    with pytest.raises(ValueError, match="plan_lifecycle_idempotency_conflict"):
        service.transition(_request(action="adjust", idempotency_key=request.idempotency_key))


def test_stale_state_terminal_state_and_missing_consent_fail_closed(tmp_path) -> None:
    service = _service(tmp_path)
    service.transition(_request(action="maintain"))
    with pytest.raises(ValueError, match="plan_lifecycle_stale_state"):
        service.transition(_request(action="monitor", idempotency_key="stale-monitor"))

    terminal = _service(tmp_path / "terminal")
    terminal.transition(_request(action="stop"))
    with pytest.raises(ValueError, match="plan_lifecycle_terminal_state"):
        terminal.transition(
            _request(
                action="monitor",
                expected_state="STOPPED",
                idempotency_key="after-stop",
            )
        )

    no_consent = _service(tmp_path / "consent")
    with no_consent.store.transaction() as connection:
        connection.execute("delete from active_profile_consents")
    with pytest.raises(PermissionError, match="plan_lifecycle_active_consent_required"):
        no_consent.transition(_request())


def test_concurrent_exact_retry_creates_one_event(tmp_path) -> None:
    service = _service(tmp_path)
    request = _request()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: service.transition(request), range(2)))

    assert len({result.event_id for result in results}) == 1
    assert sorted(result.deduplicated for result in results) == [False, True]
