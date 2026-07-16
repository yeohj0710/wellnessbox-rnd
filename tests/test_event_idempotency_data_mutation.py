import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from apps.inference_api.main import app
from wellnessbox_rnd.interim.data_mutation import (
    DataMutationLedger,
    EventMutationTargetType,
)
from wellnessbox_rnd.interim.store import InterimStore

PROFILE_ID = "usr_abcdef0123456789abcdef0123456789"


def _headers() -> dict[str, str]:
    return {"x-wb-rnd-token": "test-token"}


def _recommendation_payload() -> dict[str, object]:
    return {
        "request_id": "op027-op028-recommendation",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": PROFILE_ID,
            "profile": {
                "age": 58,
                "sex": "male",
                "goals": ["heart_health"],
            },
        },
        "user_profile": {
            "age": 58,
            "biological_sex": "male",
            "pregnant": False,
        },
        "goals": ["heart_health"],
        "symptoms": ["low_activity_tolerance"],
        "conditions": [],
        "medications": [{"name": "warfarin", "dose": "5mg"}],
        "current_supplements": [{"name": "glucosamine"}],
        "lifestyle": {
            "sleep_hours": 7.0,
            "stress_level": 2,
            "activity_level": "lightly_active",
        },
        "input_availability": {
            "survey": True,
            "nhis": False,
            "wearable": False,
            "cgm": False,
            "genetic": False,
        },
        "data_source_consents": {
            source: {
                "use_for_recommendation": source == "survey",
                "allow_persistent_storage": source == "survey",
            }
            for source in ("survey", "nhis", "wearable", "cgm", "genetic")
        },
    }


def _stored_execution(client: TestClient) -> tuple[str, dict[str, object]]:
    recommendation = client.post("/v1/recommend", json=_recommendation_payload())
    assert recommendation.status_code == 200
    execution_id = recommendation.json()["execution_id"]
    trace = client.get(
        f"/v1/interim/executions/{execution_id}", headers=_headers()
    )
    assert trace.status_code == 200
    return execution_id, trace.json()


def test_event_endpoints_deduplicate_replays_and_reject_changed_payloads(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "idempotency.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    execution_id, _trace = _stored_execution(client)

    conversation_request = {
        "event_type": "conversation",
        "source": "survey",
        "idempotency_key": "conversation-1",
        "payload": {"message_count": 2},
    }
    first_conversation = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json=conversation_request,
    )
    replayed_conversation = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json=conversation_request,
    )
    changed_conversation = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json={
            **conversation_request,
            "payload": {"message_count": 3},
        },
    )

    behavior_request = {
        "profile_id": PROFILE_ID,
        "event_name": "page_view",
        "occurred_at": "2026-07-16T09:00:00+09:00",
        "idempotency_key": "page-view-1",
        "payload": {"path": "/tips"},
    }
    first_behavior = client.post(
        "/v1/interim/behavior-events", headers=_headers(), json=behavior_request
    )
    replayed_behavior = client.post(
        "/v1/interim/behavior-events", headers=_headers(), json=behavior_request
    )
    changed_behavior = client.post(
        "/v1/interim/behavior-events",
        headers=_headers(),
        json={**behavior_request, "payload": {"path": "/other"}},
    )

    assert first_conversation.status_code == 200
    assert first_conversation.json()["deduplicated"] is False
    assert replayed_conversation.status_code == 200
    assert replayed_conversation.json()["deduplicated"] is True
    assert changed_conversation.status_code == 409
    assert first_behavior.status_code == 200
    assert first_behavior.json()["deduplicated"] is False
    assert replayed_behavior.status_code == 200
    assert replayed_behavior.json()["deduplicated"] is True
    assert changed_behavior.status_code == 409
    store = InterimStore(database)
    assert store.scalar(
        "select count(*) from execution_events "
        "where execution_id=? and idempotency_key='conversation-1'",
        (execution_id,),
    ) == 1
    assert store.scalar(
        "select count(*) from behavior_events "
        "where profile_id=? and idempotency_key='page-view-1'",
        (PROFILE_ID,),
    ) == 1

    behavior_deletion = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json={
            "profile_id": PROFILE_ID,
            "target_type": "behavior_event",
            "target_event_id": first_behavior.json()["event"]["behavior_event_id"],
            "operation": "deletion",
            "idempotency_key": "delete-page-view-1",
        },
    )
    assert behavior_deletion.status_code == 200
    deleted_behavior = store.rows(
        "select payload_json, payload_state from behavior_events "
        "where behavior_event_id=?",
        (first_behavior.json()["event"]["behavior_event_id"],),
    )[0]
    assert deleted_behavior["payload_state"] == "DELETED"
    assert '"/tips"' not in deleted_behavior["payload_json"]
    replay_after_deletion = client.post(
        "/v1/interim/behavior-events", headers=_headers(), json=behavior_request
    )
    changed_after_deletion = client.post(
        "/v1/interim/behavior-events",
        headers=_headers(),
        json={**behavior_request, "payload": {"path": "/deleted-tombstone"}},
    )
    assert replay_after_deletion.status_code == 200
    assert replay_after_deletion.json()["deduplicated"] is True
    assert replay_after_deletion.json()["event"]["payload_state"] == "DELETED"
    assert changed_after_deletion.status_code == 409


def test_correction_and_deletion_preserve_lineage_and_append_hash_audits(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "mutations.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    execution_id, trace = _stored_execution(client)
    safety_event = next(
        event for event in trace["events"] if event["event_type"] == "safety"
    )
    lineage_before = len(trace["knowledge_lineage"])
    assert lineage_before > 0
    assert EventMutationTargetType.EXECUTION_EVENT.value == "execution_event"

    correction_request = {
        "profile_id": PROFILE_ID,
        "target_type": "execution_event",
        "target_event_id": safety_event["event_id"],
        "operation": "correction",
        "idempotency_key": "safety-correction-1",
        "replacement_payload": {
            "status": "blocked",
            "corrected_reason": "source_record_correction",
        },
    }
    correction = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json=correction_request,
    )
    correction_replay = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json=correction_request,
    )
    correction_conflict = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json={
            **correction_request,
            "replacement_payload": {"status": "changed-again"},
        },
    )

    assert correction.status_code == 200
    assert correction.json()["deduplicated"] is False
    assert correction_replay.status_code == 200
    assert correction_replay.json()["deduplicated"] is True
    assert correction_conflict.status_code == 409
    mutation_id = correction.json()["mutation"]["mutation_id"]
    persisted_mutation = client.get(
        f"/v1/interim/event-mutations/{mutation_id}", headers=_headers()
    )
    assert persisted_mutation.status_code == 200
    assert persisted_mutation.json()["operation"] == "correction"

    corrected_trace = client.get(
        f"/v1/interim/executions/{execution_id}", headers=_headers()
    ).json()
    corrected_event = next(
        event
        for event in corrected_trace["events"]
        if event["event_id"] == safety_event["event_id"]
    )
    assert corrected_event["payload_state"] == "CORRECTED"
    assert corrected_event["payload"]["corrected_reason"] == "source_record_correction"
    assert len(corrected_trace["knowledge_lineage"]) == lineage_before

    deletion_request = {
        "profile_id": PROFILE_ID,
        "target_type": "execution_event",
        "target_event_id": safety_event["event_id"],
        "operation": "deletion",
        "idempotency_key": "safety-deletion-1",
    }
    deletion = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json=deletion_request,
    )
    deletion_replay = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json=deletion_request,
    )
    correction_after_deletion = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json={
            **correction_request,
            "idempotency_key": "correction-after-deletion",
        },
    )

    assert deletion.status_code == 200
    assert deletion.json()["deduplicated"] is False
    assert deletion_replay.status_code == 200
    assert deletion_replay.json()["deduplicated"] is True
    assert correction_after_deletion.status_code == 409
    deleted_trace = client.get(
        f"/v1/interim/executions/{execution_id}", headers=_headers()
    ).json()
    deleted_event = next(
        event
        for event in deleted_trace["events"]
        if event["event_id"] == safety_event["event_id"]
    )
    assert deleted_event["payload_state"] == "DELETED"
    assert deleted_event["payload"] == {
        "deleted": True,
        "mutation_id": deletion.json()["mutation"]["mutation_id"],
    }
    assert len(deleted_trace["knowledge_lineage"]) == lineage_before

    store = InterimStore(database)
    mutations = store.rows(
        "select * from event_mutations order by created_at, mutation_id"
    )
    assert len(mutations) == 2
    assert mutations[1]["prior_payload_sha256"] == mutations[0]["result_payload_sha256"]
    assert mutations[1]["previous_mutation_id"] == mutations[0]["mutation_id"]
    assert (
        mutations[1]["previous_mutation_sha256"]
        == mutations[0]["mutation_sha256"]
    )
    assert [row["mutation_index"] for row in mutations] == [0, 1]
    assert DataMutationLedger(store).verify_chain(
        target_type="execution_event",
        target_event_id=safety_event["event_id"],
    )
    assert store.scalar(
        "select count(*) from audit_events "
        "where event_type in ('data_correction', 'data_deletion')"
    ) == 2
    audit_rows = store.rows(
        "select * from audit_events "
        "where event_type in ('data_correction', 'data_deletion')"
    )
    for audit_row in audit_rows:
        canonical_metadata = json.dumps(
            json.loads(audit_row["metadata_json"]),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        assert audit_row["payload_sha256"] == hashlib.sha256(
            canonical_metadata.encode("utf-8")
        ).hexdigest()
    assert store.scalar(
        "select count(*) from execution_knowledge_lineage where event_id=?",
        (safety_event["event_id"],),
    ) > 0
    with store.transaction() as connection:
        connection.execute(
            "update execution_events set payload_json='{}' where event_id=?",
            (safety_event["event_id"],),
        )
    assert not DataMutationLedger(store).verify_chain(
        target_type="execution_event",
        target_event_id=safety_event["event_id"],
    )


def test_mutation_api_requires_authentication_ownership_and_valid_payload_shape(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "mutation-boundaries.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    _execution_id, trace = _stored_execution(client)
    event_id = trace["events"][0]["event_id"]
    request = {
        "profile_id": PROFILE_ID,
        "target_type": "execution_event",
        "target_event_id": event_id,
        "operation": "deletion",
        "idempotency_key": "delete-1",
    }

    assert client.post("/v1/interim/event-mutations", json=request).status_code == 401
    wrong_owner = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json={**request, "profile_id": "usr_1111111111111111"},
    )
    deletion_with_payload = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json={**request, "replacement_payload": {"must": "reject"}},
    )

    assert wrong_owner.status_code == 404
    assert deletion_with_payload.status_code == 422


def test_mutation_api_is_disabled_when_internal_token_is_not_configured(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv(
        "WB_RND_INTERIM_DATABASE", str(tmp_path / "mutation-auth.sqlite3")
    )
    monkeypatch.delenv("WB_RND_INTERIM_INTERNAL_TOKEN", raising=False)
    monkeypatch.delenv("WB_RND_INTERIM_ENABLED", raising=False)
    monkeypatch.setenv("WB_RND_APP_ENV", "local")

    response = TestClient(app).get(
        "/v1/interim/event-mutations/mutation_missing"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "internal_token_not_configured"


def test_deletion_removes_raw_payload_bytes_from_sqlite_files(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "secure-deletion.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    execution_id, _trace = _stored_execution(client)
    marker = "".join(f"OP028-{index:08x}-" for index in range(1600))
    event_request = {
        "event_type": "conversation",
        "source": "survey",
        "idempotency_key": "secure-deletion-source",
        "payload": {"raw_note": marker},
    }
    event = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json=event_request,
    )
    assert event.status_code == 200

    deletion = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json={
            "profile_id": PROFILE_ID,
            "target_type": "execution_event",
            "target_event_id": event.json()["event"]["event_id"],
            "operation": "deletion",
            "idempotency_key": "secure-delete-1",
        },
    )

    assert deletion.status_code == 200
    marker_fragments = [
        marker[offset : offset + 512].encode("utf-8")
        for offset in range(0, len(marker), 4096)
    ]
    for sqlite_file in tmp_path.glob(f"{database.name}*"):
        sqlite_bytes = sqlite_file.read_bytes()
        assert all(fragment not in sqlite_bytes for fragment in marker_fragments)


def test_event_replay_uses_immutable_ingestion_fingerprint_after_mutation(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "immutable-fingerprint.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    execution_id, _trace = _stored_execution(client)
    event_request = {
        "event_type": "conversation",
        "source": "survey",
        "idempotency_key": "immutable-ingestion-1",
        "payload": {"message_count": 2},
    }
    first = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json=event_request,
    )
    event_id = first.json()["event"]["event_id"]
    correction = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json={
            "profile_id": PROFILE_ID,
            "target_type": "execution_event",
            "target_event_id": event_id,
            "operation": "correction",
            "idempotency_key": "correct-immutable-ingestion-1",
            "replacement_payload": {"message_count": 3},
        },
    )
    assert correction.status_code == 200

    original_replay = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json=event_request,
    )
    corrected_payload_replay = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json={**event_request, "payload": {"message_count": 3}},
    )

    assert original_replay.status_code == 200
    assert original_replay.json()["deduplicated"] is True
    assert original_replay.json()["event"]["payload_state"] == "CORRECTED"
    assert corrected_payload_replay.status_code == 409


def test_mutation_and_audit_history_are_append_only(tmp_path, monkeypatch) -> None:
    database = tmp_path / "append-only-mutations.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    _execution_id, trace = _stored_execution(client)
    event_id = trace["events"][0]["event_id"]
    mutation = client.post(
        "/v1/interim/event-mutations",
        headers=_headers(),
        json={
            "profile_id": PROFILE_ID,
            "target_type": "execution_event",
            "target_event_id": event_id,
            "operation": "correction",
            "idempotency_key": "append-only-1",
            "replacement_payload": {"corrected": True},
        },
    )
    assert mutation.status_code == 200

    store = InterimStore(database)
    with pytest.raises(sqlite3.IntegrityError, match="event_mutations_append_only"):
        with store.transaction() as connection:
            connection.execute(
                "update event_mutations set result_payload_sha256='tampered'"
            )
    with pytest.raises(sqlite3.IntegrityError, match="event_mutations_append_only"):
        with store.transaction() as connection:
            connection.execute("delete from event_mutations")
    with pytest.raises(sqlite3.IntegrityError, match="data_mutation_audits_append_only"):
        with store.transaction() as connection:
            connection.execute(
                "update audit_events set payload_sha256='tampered' "
                "where event_type='data_correction'"
            )
    with pytest.raises(sqlite3.IntegrityError, match="data_mutation_audits_append_only"):
        with store.transaction() as connection:
            connection.execute(
                "delete from audit_events where event_type='data_correction'"
            )


def test_concurrent_identical_mutations_create_one_history_and_audit_row(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "concurrent-mutations.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    _execution_id, trace = _stored_execution(client)
    event_id = trace["events"][0]["event_id"]
    request = {
        "profile_id": PROFILE_ID,
        "target_type": "execution_event",
        "target_event_id": event_id,
        "operation": "correction",
        "idempotency_key": "concurrent-correction-1",
        "replacement_payload": {"corrected": "once"},
    }

    def apply_once(_index: int) -> bool:
        return DataMutationLedger(InterimStore(database)).apply(**request).deduplicated

    with ThreadPoolExecutor(max_workers=8) as executor:
        deduplicated = list(executor.map(apply_once, range(16)))

    assert deduplicated.count(False) == 1
    assert deduplicated.count(True) == 15
    store = InterimStore(database)
    assert store.scalar("select count(*) from event_mutations") == 1
    assert store.scalar(
        "select count(*) from audit_events where event_type='data_correction'"
    ) == 1
    assert DataMutationLedger(store).verify_chain(
        target_type="execution_event", target_event_id=event_id
    )


def test_deletion_replay_retries_secure_compaction_after_cleanup_failure(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "deletion-cleanup-retry.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    _execution_id, trace = _stored_execution(client)
    event_id = trace["events"][0]["event_id"]
    store = InterimStore(database)
    original_secure_compact = store.secure_compact
    call_count = 0

    def fail_once() -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise sqlite3.OperationalError("injected_secure_compaction_failure")
        original_secure_compact()

    monkeypatch.setattr(store, "secure_compact", fail_once)
    ledger = DataMutationLedger(store)
    request = {
        "profile_id": PROFILE_ID,
        "target_type": "execution_event",
        "target_event_id": event_id,
        "operation": "deletion",
        "idempotency_key": "retry-cleanup-1",
    }

    with pytest.raises(
        sqlite3.OperationalError, match="injected_secure_compaction_failure"
    ):
        ledger.apply(**request)
    assert store.scalar(
        "select status from event_mutation_cleanup where mutation_id=("
        "select mutation_id from event_mutations limit 1)"
    ) == "PENDING"
    replay = ledger.apply(**request)

    assert replay.deduplicated is True
    assert call_count == 2
    assert store.scalar("select count(*) from event_mutations") == 1
    assert store.scalar(
        "select status from event_mutation_cleanup where mutation_id=("
        "select mutation_id from event_mutations limit 1)"
    ) == "COMPLETE"


def test_pending_deletion_cleanup_recovers_during_store_startup(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "startup-cleanup-recovery.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    execution_id, _trace = _stored_execution(client)
    marker = "".join(f"OP028-RECOVERY-{index:08x}-" for index in range(800))
    event_request = {
        "event_type": "conversation",
        "source": "survey",
        "idempotency_key": "startup-cleanup-source",
        "payload": {"raw_note": marker},
    }
    event = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json=event_request,
    ).json()["event"]
    store = InterimStore(database)
    monkeypatch.setattr(
        store,
        "secure_compact",
        lambda: (_ for _ in ()).throw(
            sqlite3.OperationalError("injected_startup_cleanup_failure")
        ),
    )
    with pytest.raises(
        sqlite3.OperationalError, match="injected_startup_cleanup_failure"
    ):
        DataMutationLedger(store).apply(
            profile_id=PROFILE_ID,
            target_type="execution_event",
            target_event_id=event["event_id"],
            operation="deletion",
            idempotency_key="startup-cleanup-delete-1",
        )
    assert store.scalar("select status from event_mutation_cleanup") == "PENDING"

    recovered_store = InterimStore(database)
    recovered_store.migrate()

    assert recovered_store.scalar("select status from event_mutation_cleanup") == "COMPLETE"
    marker_fragments = [
        marker[offset : offset + 512].encode("utf-8")
        for offset in range(0, len(marker), 4096)
    ]
    for sqlite_file in tmp_path.glob(f"{database.name}*"):
        sqlite_bytes = sqlite_file.read_bytes()
        assert all(fragment not in sqlite_bytes for fragment in marker_fragments)


def test_deletion_stays_pending_until_active_reader_allows_secure_cleanup(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "active-reader-cleanup.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    _execution_id, trace = _stored_execution(client)
    event_id = trace["events"][0]["event_id"]
    store = InterimStore(database)
    ledger = DataMutationLedger(store)
    reader = store.connect()
    reader.execute("BEGIN")
    reader.execute(
        "select payload_json from execution_events where event_id=?", (event_id,)
    ).fetchone()
    request = {
        "profile_id": PROFILE_ID,
        "target_type": "execution_event",
        "target_event_id": event_id,
        "operation": "deletion",
        "idempotency_key": "active-reader-delete-1",
    }

    try:
        with pytest.raises(sqlite3.OperationalError, match="secure_checkpoint_busy"):
            ledger.apply(**request)
        assert store.scalar("select status from event_mutation_cleanup") == "PENDING"
    finally:
        reader.close()

    replay = ledger.apply(**request)

    assert replay.deduplicated is True
    assert store.scalar("select status from event_mutation_cleanup") == "COMPLETE"
