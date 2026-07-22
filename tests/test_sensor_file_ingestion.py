from __future__ import annotations

import base64
import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.interim.sensor_file_ingestion import (
    SensorFileBatchRequest,
    SensorFileBatchStatus,
    ingest_sensor_file_batch,
)
from wellnessbox_rnd.interim.store import SCHEMA_VERSION, InterimStore

client = TestClient(app)


def _encoded(value: str | bytes) -> str:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return base64.b64encode(raw).decode("ascii")


def _consents(*, use: bool = True, store: bool = True) -> dict[str, dict[str, bool]]:
    denied = {
        "use_for_recommendation": False,
        "allow_persistent_storage": False,
    }
    return {
        "survey": denied,
        "nhis": denied,
        "wearable": {
            "use_for_recommendation": use,
            "allow_persistent_storage": store,
        },
        "cgm": {
            "use_for_recommendation": use,
            "allow_persistent_storage": store,
        },
        "genetic": {
            "use_for_recommendation": use,
            "allow_persistent_storage": store,
        },
    }


def _store(tmp_path) -> InterimStore:
    store = InterimStore(tmp_path / "sensor-files.sqlite3")
    store.migrate()
    return store


def _batch(*, use: bool = True, store: bool = True) -> SensorFileBatchRequest:
    return SensorFileBatchRequest.model_validate(
        {
            "profile_id": "usr_sensor_file_test",
            "data_source_consents": _consents(use=use, store=store),
            "files": [
                {
                    "file_id": "wearable-01",
                    "source": "wearable",
                    "content_base64": _encoded(
                        "date,steps,resting_hr,sleep_minutes\n"
                        "2026-07-20,8000,61,420\n"
                        "2026-07-21,9100,59,450\n"
                    ),
                },
                {
                    "file_id": "cgm-invalid-01",
                    "source": "cgm",
                    "content_base64": _encoded(
                        "date,mean_glucose_mg_dl,time_in_range_70_180_pct\n2026-07-21,120,78\n"
                    ),
                },
                {
                    "file_id": "genetic-01",
                    "source": "genetic",
                    "content_base64": _encoded(
                        json.dumps(
                            {
                                "variants": [
                                    {
                                        "gene": "CYP1A2",
                                        "rsid": "rs762551",
                                        "call": "A/C",
                                        "classification": "high risk",
                                        "basis": "panel-v2",
                                        "lab": "Example Genomics",
                                        "test_date": "2026-06-30",
                                    }
                                ]
                            }
                        )
                    ),
                },
            ],
        }
    )


def test_batch_reports_partial_success_and_persists_hash_lineage(tmp_path) -> None:
    store = _store(tmp_path)
    request = _batch()

    response = ingest_sensor_file_batch(request, store=store)

    assert response.status == SensorFileBatchStatus.PARTIAL_SUCCESS
    assert response.total_file_count == 3
    assert response.success_file_count == 2
    assert response.failure_file_count == 1
    assert response.normalized_record_count == 3
    assert response.persisted_file_count == 3
    cgm = next(item for item in response.files if item.source == "cgm")
    assert cgm.failure_types == ["missing_required_field::cgm_summary::postprandial_summary"]
    assert store.scalar("select count(*) from sensor_file_ingestions") == 3

    wearable_input = request.files[0]
    wearable_raw = base64.b64decode(wearable_input.content_base64)
    row = store.rows("select * from sensor_file_ingestions where file_id='wearable-01'")[0]
    assert row["raw_file_sha256"] == hashlib.sha256(wearable_raw).hexdigest()
    assert row["normalized_record_count"] == 2
    normalized_payload = json.loads(row["normalized_payload_json"])
    encoded = json.dumps(
        normalized_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert row["normalized_payload_sha256"] == hashlib.sha256(encoded).hexdigest()
    assert "8000" not in row["schema_validation_json"]


def test_exact_replay_is_deduplicated_without_new_lineage_rows(tmp_path) -> None:
    store = _store(tmp_path)
    request = _batch()

    first = ingest_sensor_file_batch(request, store=store)
    second = ingest_sensor_file_batch(request, store=store)

    assert all(not item.deduplicated for item in first.files)
    assert all(item.deduplicated for item in second.files)
    assert [item.ingestion_id for item in second.files] == [
        item.ingestion_id for item in first.files
    ]
    assert store.scalar("select count(*) from sensor_file_ingestions") == 3


def test_use_denial_does_not_decode_hash_normalize_or_persist(tmp_path) -> None:
    store = _store(tmp_path)
    request = SensorFileBatchRequest.model_validate(
        {
            "profile_id": "usr_denied",
            "data_source_consents": _consents(use=False, store=True),
            "files": [
                {
                    "file_id": "private-genetic",
                    "source": "genetic",
                    "content_base64": "not-base64-private-content",
                }
            ],
        }
    )

    response = ingest_sensor_file_batch(request, store=store)

    assert response.status == SensorFileBatchStatus.FAILED
    assert response.files[0].failure_types == ["source_use_consent_required"]
    assert response.files[0].raw_file_sha256 is None
    assert response.files[0].normalized_payload_sha256 is None
    assert response.persisted_file_count == 0
    assert store.scalar("select count(*) from sensor_file_ingestions") == 0


def test_storage_denial_returns_ephemeral_result_without_database_row(tmp_path) -> None:
    store = _store(tmp_path)
    request = _batch(store=False)

    response = ingest_sensor_file_batch(request, store=store)

    assert response.status == SensorFileBatchStatus.PARTIAL_SUCCESS
    assert response.persisted_file_count == 0
    assert all(item.ingestion_id is None for item in response.files)
    assert all(not item.persisted for item in response.files)
    assert store.scalar("select count(*) from sensor_file_ingestions") == 0


def test_malformed_files_report_exact_schema_or_decode_failures(tmp_path) -> None:
    store = _store(tmp_path)
    request = SensorFileBatchRequest.model_validate(
        {
            "profile_id": "usr_malformed",
            "data_source_consents": _consents(),
            "files": [
                {
                    "file_id": "duplicate-header",
                    "source": "wearable",
                    "content_base64": _encoded(
                        "date,steps,steps,resting_hr,sleep_hours\n2026-07-21,10,20,60,7\n"
                    ),
                },
                {
                    "file_id": "duplicate-json-key",
                    "source": "genetic",
                    "content_base64": _encoded('{"markers":["a"],"markers":["b"]}'),
                },
                {
                    "file_id": "bad-utf8",
                    "source": "cgm",
                    "content_base64": _encoded(b"\xff\xfe"),
                },
            ],
        }
    )

    response = ingest_sensor_file_batch(request, store=store)

    assert response.status == SensorFileBatchStatus.FAILED
    assert response.success_file_count == 0
    assert response.failure_file_count == 3
    assert response.files[0].failure_types == ["duplicate_csv_header::steps"]
    assert response.files[1].failure_types == ["gene_profile_duplicate_json_key::markers"]
    assert response.files[2].failure_types == ["sensor_file_utf8_required"]
    assert response.persisted_file_count == 3


def test_lineage_rows_are_append_only(tmp_path) -> None:
    store = _store(tmp_path)
    ingest_sensor_file_batch(_batch(), store=store)

    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        with store.transaction(immediate=True) as connection:
            connection.execute(
                "update sensor_file_ingestions set status='FAILED' where file_id='wearable-01'"
            )
    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        with store.transaction(immediate=True) as connection:
            connection.execute("delete from sensor_file_ingestions where file_id='wearable-01'")


def test_schema_migration_adds_sensor_lineage_to_existing_database(tmp_path) -> None:
    path = tmp_path / "existing.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        "create table schema_migrations(version integer primary key, applied_at text not null)"
    )
    connection.execute(
        "insert into schema_migrations(version, applied_at) values (11, '2026-07-21T00:00:00Z')"
    )
    connection.commit()
    connection.close()

    store = InterimStore(path)
    store.migrate()

    assert store.is_migrated()
    assert store.scalar("select max(version) from schema_migrations") == SCHEMA_VERSION
    assert "sensor_file_ingestions" in store.table_names()


def test_request_rejects_duplicate_file_ids() -> None:
    payload = _batch().model_dump(mode="json")
    payload["files"].append(dict(payload["files"][0]))

    with pytest.raises(ValidationError, match="sensor_file_ids_must_be_unique"):
        SensorFileBatchRequest.model_validate(payload)


def test_authenticated_api_returns_partial_counts_and_persists_lineage(
    tmp_path, monkeypatch
) -> None:
    database_path = tmp_path / "api-sensor-files.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database_path))
    monkeypatch.setenv("WB_RND_INTERIM_ENABLED", "true")
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "sensor-secret")

    denied = client.post(
        "/v1/interim/sensor-files/ingest",
        json=_batch().model_dump(mode="json"),
    )
    response = client.post(
        "/v1/interim/sensor-files/ingest",
        headers={"x-wb-rnd-token": "sensor-secret"},
        json=_batch().model_dump(mode="json"),
    )

    assert denied.status_code == 401
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PARTIAL_SUCCESS"
    assert payload["success_file_count"] == 2
    assert payload["failure_file_count"] == 1
    store = InterimStore(database_path)
    assert store.scalar("select count(*) from sensor_file_ingestions") == 3
