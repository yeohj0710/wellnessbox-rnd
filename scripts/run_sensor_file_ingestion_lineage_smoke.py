from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from wellnessbox_rnd.interim.store import InterimStore

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from apps.inference_api.main import app  # noqa: E402

DATASET_PATH = ROOT / "data/original_plan/op095_op096_sensor_file_ingestion_cases_v1.json"
SOURCE_PATHS = (
    ROOT / "scripts/run_sensor_file_ingestion_lineage_smoke.py",
    DATASET_PATH,
    ROOT / "apps/inference_api/routes/interim.py",
    ROOT / "src/wellnessbox_rnd/interim/sensor_file_ingestion.py",
    ROOT / "src/wellnessbox_rnd/interim/store.py",
    ROOT / "src/wellnessbox_rnd/domain/sensor_parser.py",
    ROOT / "src/wellnessbox_rnd/schemas/recommendation.py",
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


def _consents(case: dict[str, Any]) -> dict[str, dict[str, bool]]:
    denied = {
        "use_for_recommendation": False,
        "allow_persistent_storage": False,
    }
    source_consent = {
        "use_for_recommendation": bool(case["use_for_recommendation"]),
        "allow_persistent_storage": bool(case["allow_persistent_storage"]),
    }
    return {
        "survey": denied,
        "nhis": denied,
        "wearable": source_consent,
        "cgm": source_consent,
        "genetic": source_consent,
    }


def _request(case: dict[str, Any]) -> dict[str, Any]:
    files = []
    for item in case["files"]:
        content_base64 = item.get("content_base64")
        if content_base64 is None:
            content_base64 = base64.b64encode(str(item["content"]).encode("utf-8")).decode("ascii")
        files.append(
            {
                "file_id": item["file_id"],
                "source": item["source"],
                "content_base64": content_base64,
            }
        )
    return {
        "profile_id": case["profile_id"],
        "files": files,
        "data_source_consents": _consents(case),
    }


def _project_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload["status"],
        "total_file_count": payload["total_file_count"],
        "success_file_count": payload["success_file_count"],
        "failure_file_count": payload["failure_file_count"],
        "normalized_record_count": payload["normalized_record_count"],
        "persisted_file_count": payload["persisted_file_count"],
        "files": [
            {
                "file_id": item["file_id"],
                "source": item["source"],
                "status": item["status"],
                "failure_types": item["failure_types"],
                "normalized_record_count": item["normalized_record_count"],
                "raw_file_sha256": item["raw_file_sha256"],
                "normalized_payload_sha256": item["normalized_payload_sha256"],
                "ingestion_id": item["ingestion_id"],
                "persisted": item["persisted"],
                "deduplicated": item["deduplicated"],
            }
            for item in payload["files"]
        ],
    }


def main() -> int:
    output = Path(
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/original_plan/evidence/op095_op096_sensor_file_ingestion_lineage_smoke_v1.json"
    )
    output = output if output.is_absolute() else ROOT / output
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in dataset["cases"]}
    case_requests: dict[str, dict[str, Any]] = {}
    case_results: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "sensor-file-evidence.sqlite3"
        previous_environment = {
            key: os.environ.get(key)
            for key in (
                "WB_RND_INTERIM_DATABASE",
                "WB_RND_INTERIM_ENABLED",
                "WB_RND_INTERIM_INTERNAL_TOKEN",
            )
        }
        os.environ["WB_RND_INTERIM_DATABASE"] = str(database_path)
        os.environ["WB_RND_INTERIM_ENABLED"] = "true"
        os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = "op095-op096-evidence-token"
        try:
            client = TestClient(app)
            for case in dataset["cases"]:
                kind = case["kind"]
                if kind == "api":
                    request = _request(case)
                    case_requests[case["case_id"]] = request
                    response = client.post(
                        "/v1/interim/sensor-files/ingest",
                        headers={"x-wb-rnd-token": "op095-op096-evidence-token"},
                        json=request,
                    )
                    if response.status_code != 200:
                        raise AssertionError(
                            f"unexpected_status:{case['case_id']}:{response.status_code}"
                        )
                    payload = response.json()
                    for key, value in case["expected"].items():
                        if payload[key] != value:
                            raise AssertionError(f"unexpected_{key}:{case['case_id']}")
                    if case["case_id"] == "use_consent_denied_without_hash":
                        if payload["files"][0]["raw_file_sha256"] is not None:
                            raise AssertionError("denied_file_was_hashed")
                    case_results.append(
                        {
                            "case_id": case["case_id"],
                            "result": "PASS",
                            "response": _project_response(payload),
                        }
                    )
                elif kind == "replay":
                    replay_case = cases_by_id[case["replay_case_id"]]
                    request = deepcopy(case_requests[replay_case["case_id"]])
                    response = client.post(
                        "/v1/interim/sensor-files/ingest",
                        headers={"x-wb-rnd-token": "op095-op096-evidence-token"},
                        json=request,
                    )
                    payload = response.json()
                    deduplicated_count = sum(
                        bool(item["deduplicated"]) for item in payload["files"]
                    )
                    if deduplicated_count != case["expected_deduplicated_file_count"]:
                        raise AssertionError("unexpected_deduplicated_file_count")
                    case_results.append(
                        {
                            "case_id": case["case_id"],
                            "result": "PASS",
                            "deduplicated_file_count": deduplicated_count,
                        }
                    )
                elif kind == "tamper":
                    store = InterimStore(database_path)
                    try:
                        with store.transaction(immediate=True) as connection:
                            connection.execute(
                                "update sensor_file_ingestions set status='FAILED' "
                                "where status='SUCCESS'"
                            )
                    except sqlite3.IntegrityError as error:
                        if case["expected_error"] not in str(error):
                            raise
                    else:
                        raise AssertionError("append_only_tamper_not_rejected")
                    case_results.append(
                        {
                            "case_id": case["case_id"],
                            "result": "PASS",
                            "error": case["expected_error"],
                        }
                    )
                else:
                    raise AssertionError(f"unsupported_case_kind:{kind}")
            store = InterimStore(database_path)
            final_lineage_row_count = int(
                store.scalar("select count(*) from sensor_file_ingestions")
            )
            raw_content_column_count = sum(
                "content" in str(row["name"]).casefold()
                for row in store.rows("pragma table_info(sensor_file_ingestions)")
            )
        finally:
            for key, value in previous_environment.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    if len(case_results) != dataset["case_count"]:
        raise AssertionError("dataset_case_count_mismatch")
    if final_lineage_row_count != 6:
        raise AssertionError("unexpected_final_lineage_row_count")
    if raw_content_column_count != 0:
        raise AssertionError("raw_file_content_column_forbidden")
    report = {
        "schema_version": "op095_op096_sensor_file_ingestion_lineage_smoke_v1",
        "requirements": ["OP-095", "OP-096"],
        "result": "PASS",
        "dataset": {
            "path": DATASET_PATH.relative_to(ROOT).as_posix(),
            "schema_version": dataset["schema_version"],
            "case_count": dataset["case_count"],
            "sha256": _git_blob_sha256(DATASET_PATH),
        },
        "checks": {
            "cases": case_results,
            "authenticated_fastapi_route_observed": True,
            "actual_sqlite_requery_observed": True,
            "partial_success_counts_observed": True,
            "raw_bytes_sha256_preserved": True,
            "normalized_payload_sha256_preserved": True,
            "append_only_lineage_observed": True,
            "exact_replay_deduplicated": True,
            "nonconsented_source_not_hashed_or_persisted": True,
            "raw_file_content_persisted": False,
            "final_lineage_row_count": final_lineage_row_count,
            "deployed_process_observed": False,
            "production_database_observed": False,
            "production_operation_observed": False,
        },
        "source_identity": {
            "commit": _source_commit(),
            "files": {
                path.relative_to(ROOT).as_posix(): _git_blob_sha256(path) for path in SOURCE_PATHS
            },
        },
        "stage_boundary": {
            "OP-095": (
                "Authenticated local API partial-success responses are implemented; "
                "no production traffic is claimed."
            ),
            "OP-096": (
                "Append-only local SQLite hash lineage is implemented; required "
                "OPERATED evidence remains absent."
            ),
        },
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
