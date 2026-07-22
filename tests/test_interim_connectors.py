from pathlib import Path

import pytest

from wellnessbox_rnd.interim.connectors import ingest_device_session, source_adapters
from wellnessbox_rnd.interim.store import InterimStore


def _store(tmp_path: Path) -> InterimStore:
    store = InterimStore(tmp_path / "connectors.sqlite3")
    store.migrate()
    with store.transaction() as connection:
        connection.execute(
            """
            insert into user_profiles values (
              'usr_1234567890abcdef', 'PROXY_GOLD_SIMULATION', '[]', '{}', 'hash', 'now'
            )
            """
        )
    return store


def test_eight_official_adapters_remain_environment_gated() -> None:
    adapters = source_adapters({"pubmed", "mfds"})
    assert len(adapters) == 8
    assert {item.name for item in adapters if item.enabled} == {"pubmed", "mfds"}
    assert all(item.gate == "environment_gate" for item in adapters if not item.enabled)


def test_device_requires_consent_and_valid_postconditions(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = {
        "observed_at": "2026-07-10T12:00:00+09:00",
        "value": 72,
        "unit": "bpm",
        "timezone": "Asia/Seoul",
        "source_record_id": "watch-1",
    }
    with pytest.raises(PermissionError, match="missing_device_consent"):
        ingest_device_session(
            store,
            session_id="s1",
            profile_id="usr_1234567890abcdef",
            source="W",
            consent_scopes=set(),
            payload=payload,
        )
    result = ingest_device_session(
        store,
        session_id="s1",
        profile_id="usr_1234567890abcdef",
        source="W",
        consent_scopes={"device:write"},
        payload=payload,
    )
    assert result["success"] is True
    assert all(result["postconditions"].values())


def test_device_session_is_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    kwargs = {
        "store": store,
        "session_id": "s1",
        "profile_id": "usr_1234567890abcdef",
        "source": "G",
        "consent_scopes": {"device:write"},
        "payload": {
            "observed_at": "2026-07-10T12:00:00+09:00",
            "value": "AA",
            "unit": "genotype",
            "timezone": "+09:00",
            "source_record_id": "gene-1",
        },
    }
    assert ingest_device_session(**kwargs)["deduplicated"] is False
    assert ingest_device_session(**kwargs)["deduplicated"] is True
    assert store.scalar("select count(*) from connector_sessions") == 1
    assert store.scalar("select count(*) from device_event_receipts") == 1


def test_device_event_is_deduplicated_across_session_ids(tmp_path: Path) -> None:
    store = _store(tmp_path)
    arguments = {
        "store": store,
        "profile_id": "usr_1234567890abcdef",
        "source": "W",
        "consent_scopes": {"device:write"},
        "payload": {
            "observed_at": "2026-07-10T12:00:00+09:00",
            "value": 72,
            "unit": "bpm",
            "timezone": "Asia/Seoul",
            "source_record_id": "watch-global-1",
        },
    }

    first = ingest_device_session(session_id="session-original", **arguments)
    replay = ingest_device_session(session_id="session-retry", **arguments)

    assert first["deduplicated"] is False
    assert replay["deduplicated"] is True
    assert replay["session_id"] == "session-original"
    assert replay["event_identity"] == first["event_identity"]
    assert store.scalar("select count(*) from connector_sessions") == 1


def test_device_event_rejects_conflicting_replay_and_session_reuse(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = {
        "observed_at": "2026-07-10T12:00:00+09:00",
        "value": 72,
        "unit": "bpm",
        "timezone": "Asia/Seoul",
        "source_record_id": "watch-conflict-1",
    }
    common = {
        "store": store,
        "profile_id": "usr_1234567890abcdef",
        "source": "W",
        "consent_scopes": {"device:write"},
    }
    ingest_device_session(session_id="session-1", payload=payload, **common)

    with pytest.raises(ValueError, match="duplicate_device_event_conflict"):
        ingest_device_session(
            session_id="session-2", payload=payload | {"value": 99}, **common
        )
    with pytest.raises(ValueError, match="device_session_identity_conflict"):
        ingest_device_session(
            session_id="session-1",
            payload=payload | {"source_record_id": "watch-conflict-2"},
            **common,
        )


def test_device_environment_controls_data_class(tmp_path: Path) -> None:
    store = _store(tmp_path)
    payload = {
        "observed_at": "2026-07-10T12:00:00+09:00",
        "value": 72,
        "unit": "bpm",
        "timezone": "Asia/Seoul",
        "source_record_id": "watch-production-1",
    }
    result = ingest_device_session(
        store,
        session_id="production-session",
        profile_id="usr_1234567890abcdef",
        source="W",
        consent_scopes={"device:write"},
        payload=payload,
        environment="production",
    )
    assert result["data_class"] == "PRODUCTION_DEVICE_SESSION"

    with pytest.raises(ValueError, match="device_environment_data_class_mismatch"):
        ingest_device_session(
            store,
            session_id="mismatch-session",
            profile_id="usr_1234567890abcdef",
            source="W",
            consent_scopes={"device:write"},
            payload=payload | {"source_record_id": "watch-mismatch-1"},
            environment="production",
            data_class="SIMULATED_DEVICE_SESSION",
        )


def test_device_event_receipts_are_append_only(tmp_path: Path) -> None:
    store = _store(tmp_path)
    ingest_device_session(
        store,
        session_id="append-only-session",
        profile_id="usr_1234567890abcdef",
        source="C",
        consent_scopes={"device:write"},
        payload={
            "observed_at": "2026-07-10T12:00:00+09:00",
            "value": 1,
            "unit": "count",
            "timezone": "+09:00",
            "source_record_id": "clinic-append-only-1",
        },
    )

    with pytest.raises(Exception, match="device_event_receipts_append_only"):
        with store.transaction() as connection:
            connection.execute("update device_event_receipts set success=0")
