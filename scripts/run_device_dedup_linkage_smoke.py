from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.inference_api.main import app  # noqa: E402
from wellnessbox_rnd.interim.contracts import DataClass  # noqa: E402
from wellnessbox_rnd.interim.kpi import device_linkage_metrics  # noqa: E402
from wellnessbox_rnd.interim.store import InterimStore  # noqa: E402

DATASET_PATH = ROOT / "data/original_plan/op099_op100_device_dedup_linkage_cases_v1.json"
OUTPUT_PATH = ROOT / (
    "data/original_plan/evidence/op099_op100_device_dedup_linkage_smoke_v1.json"
)
SOURCE_PATHS = (
    ROOT / "scripts/run_device_dedup_linkage_smoke.py",
    DATASET_PATH,
    ROOT / "apps/inference_api/routes/interim.py",
    ROOT / "src/wellnessbox_rnd/interim/connectors.py",
    ROOT / "src/wellnessbox_rnd/interim/kpi.py",
    ROOT / "src/wellnessbox_rnd/interim/store.py",
)


def _git_blob_sha256(path: Path) -> str:
    content = subprocess.check_output(
        ["git", "show", f"HEAD:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT
    )
    return hashlib.sha256(content).hexdigest()


def _source_commit() -> str:
    paths = [path.relative_to(ROOT).as_posix() for path in SOURCE_PATHS]
    return subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", *paths], cwd=ROOT, text=True
    ).strip()


def _payload(record_id: str, value: int = 1) -> dict[str, Any]:
    return {
        "observed_at": "2026-07-22T09:00:00+09:00",
        "value": value,
        "unit": "count",
        "timezone": "Asia/Seoul",
        "source_record_id": record_id,
    }


def _post(
    client: TestClient,
    session_id: str,
    source: str,
    record_id: str,
    value: int = 1,
    *,
    valid_unit: bool = True,
) -> Any:
    payload = _payload(record_id, value)
    if not valid_unit:
        payload["unit"] = "unknown"
    return client.post(
        "/v1/interim/connectors/device",
        json={
            "session_id": session_id,
            "profile_id": "usr_0123456789abcdef",
            "source": source,
            "consent_scopes": ["device:write"],
            "payload": payload,
            "environment": "production",
        },
    )


def main() -> int:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        database_path = Path(temporary) / "device-dedup.sqlite3"
        os.environ["WB_RND_INTERIM_DATABASE"] = str(database_path)
        client = TestClient(app)
        first = _post(client, "w1", "W", "watch-1")
        replay = _post(client, "w-retry", "W", "watch-1")
        changed = _post(client, "w-changed", "W", "watch-1", 99)
        session_reuse = _post(client, "w1", "W", "watch-2")
        responses = [
            _post(client, "w2", "W", "watch-2"),
            _post(client, "c1", "C", "clinic-1"),
            _post(client, "c2", "C", "clinic-2", 0, valid_unit=False),
            _post(client, "g1", "G", "gene-1"),
        ]
        if any(response.status_code != 200 for response in [first, replay, *responses]):
            raise AssertionError("unexpected_success_response")
        store = InterimStore(database_path)
        metrics = device_linkage_metrics(
            store, data_class=DataClass.PRODUCTION_DEVICE_SESSION
        )
        try:
            with store.transaction() as connection:
                connection.execute("update device_event_receipts set success=0")
        except sqlite3.IntegrityError as error:
            tamper_error = str(error)
        else:
            tamper_error = ""
        observed = {
            "first_deduplicated": first.json()["deduplicated"],
            "replay_deduplicated": replay.json()["deduplicated"],
            "replay_canonical_session_id": replay.json()["session_id"],
            "changed_payload_status": changed.status_code,
            "changed_payload_detail": changed.json()["detail"],
            "session_reuse_status": session_reuse.status_code,
            "session_reuse_detail": session_reuse.json()["detail"],
            "connector_row_count": store.scalar("select count(*) from connector_sessions"),
            "receipt_row_count": store.scalar("select count(*) from device_event_receipts"),
            "source_counts": metrics.source_counts,
            "source_rates": metrics.source_rates,
            "macro_rate": metrics.aggregate,
            "tamper_error": tamper_error,
        }
        checks = {
            "same_event_new_session_deduplicated": observed["replay_deduplicated"] is True
            and observed["replay_canonical_session_id"] == "w1",
            "changed_payload_conflict": changed.status_code == 409
            and changed.json()["detail"] == "duplicate_device_event_conflict",
            "session_identity_conflict": session_reuse.status_code == 409
            and session_reuse.json()["detail"] == "device_session_identity_conflict",
            "duplicates_not_persisted": observed["connector_row_count"] == 5
            and observed["receipt_row_count"] == 5,
            "source_rates_recomputed": metrics.source_rates
            == {"W": 100.0, "C": 50.0, "G": 100.0},
            "equal_weight_macro_recomputed": metrics.aggregate == 250.0 / 3.0,
            "append_only_receipt": tamper_error == "device_event_receipts_append_only",
        }
        if not all(checks.values()):
            raise AssertionError(f"device_dedup_linkage_smoke_failed:{checks}")
        report = {
            "schema_version": "op099_op100_device_dedup_linkage_smoke_v1",
            "requirements": {
                "OP-099": {"required_stage": "OPERATED", "claimed_stage": "IMPLEMENTED"},
                "OP-100": {"required_stage": "IMPLEMENTED", "claimed_stage": "IMPLEMENTED"},
            },
            "dataset": {
                "path": DATASET_PATH.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
                "case_count": len(dataset["cases"]),
            },
            "checks": checks,
            "observed": observed,
            "stage_boundary": {
                "local_api_and_sqlite_proven": True,
                "production_provider_traffic_proven": False,
                "production_operation_proven": False,
            },
            "source_identity": {
                "wellnessbox_rnd_commit": _source_commit(),
                "wellnessbox_rnd_source_sha256": hashlib.sha256(
                    "".join(_git_blob_sha256(path) for path in SOURCE_PATHS).encode()
                ).hexdigest(),
            },
        }
        OUTPUT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
