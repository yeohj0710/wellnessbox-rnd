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
