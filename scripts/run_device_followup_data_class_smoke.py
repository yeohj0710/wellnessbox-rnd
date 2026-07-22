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
from wellnessbox_rnd.interim.store import InterimStore  # noqa: E402

DATASET_PATH = ROOT / "data/original_plan/op097_op098_device_followup_data_class_cases_v1.json"
OUTPUT_PATH = (
    ROOT
    / "data/original_plan/evidence/op097_op098_device_followup_data_class_smoke_v1.json"
)
SOURCE_PATHS = (
    ROOT / "scripts/run_device_followup_data_class_smoke.py",
    DATASET_PATH,
    ROOT / "apps/inference_api/routes/interim.py",
    ROOT / "src/wellnessbox_rnd/interim/device_evaluation.py",
    ROOT / "src/wellnessbox_rnd/interim/contracts.py",
    ROOT / "src/wellnessbox_rnd/interim/data_lake.py",
    ROOT / "src/wellnessbox_rnd/interim/store.py",
    ROOT / "src/wellnessbox_rnd/orchestration/recommendation_service.py",
    ROOT / "src/wellnessbox_rnd/efficacy/service.py",
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


def _recommendation(*, sleep_hours: float) -> dict[str, Any]:
    return {
        "request_id": "device-followup-canonical-subject",
        "plan_id": "plan_device_followup_canonical",
        "user_profile": {"age": 41, "biological_sex": "female", "pregnant": False},
        "goals": ["sleep_support"],
        "input_availability": {"wearable": True},
        "sensor_genetic_snapshot": {
            "wearable_available": True,
            "sleep_hours": sleep_hours,
        },
        "data_source_consents": {
            "survey": {
                "use_for_recommendation": True,
                "allow_persistent_storage": True,
            },
            "wearable": {
                "use_for_recommendation": True,
                "allow_persistent_storage": True,
            },
        },
    }


def _assessment(
    assessment_id: str,
    *,
    phase: str,
    sleep_hours: float,
    data_class: str,
    session_origin: str,
    baseline_assessment_id: str | None = None,
) -> dict[str, Any]:
    return {
        "assessment_id": assessment_id,
        "phase": phase,
        "baseline_assessment_id": baseline_assessment_id,
        "data_class": data_class,
        "session_origin": session_origin,
        "recommendation_request": _recommendation(sleep_hours=sleep_hours),
    }


def _post(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(
        "/v1/interim/device-assessments",
        json=payload,
        headers={"x-wb-rnd-token": "canonical-token"},
    )
    if response.status_code != 200:
        raise AssertionError(f"unexpected_api_response:{response.status_code}:{response.text}")
    return response.json()


def main() -> int:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        database_path = Path(temporary) / "device-assessments.sqlite3"
        os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = "canonical-token"
        os.environ["WB_RND_DATA_LAKE_PATH"] = str(database_path)
        client = TestClient(app)
        baseline_payload = _assessment(
            "device_assessment_canonical_baseline",
            phase="BASELINE",
            sleep_hours=5.0,
            data_class="SIMULATED_DEVICE_SESSION",
            session_origin="SIMULATION_FIXTURE",
        )
        baseline = _post(client, baseline_payload)
        follow_up = _post(
            client,
            _assessment(
                "device_assessment_canonical_followup",
                phase="FOLLOW_UP",
                sleep_hours=8.0,
                data_class="SIMULATED_DEVICE_SESSION",
                session_origin="SIMULATION_FIXTURE",
                baseline_assessment_id="device_assessment_canonical_baseline",
            ),
        )
        production = _post(
            client,
            _assessment(
                "device_assessment_production_boundary",
                phase="BASELINE",
                sleep_hours=5.0,
                data_class="PRODUCTION_DEVICE_SESSION",
                session_origin="DEVICE_PROVIDER",
            ),
        )
        mismatch = client.post(
            "/v1/interim/device-assessments",
            json=_assessment(
                "device_assessment_mismatch_boundary",
                phase="BASELINE",
                sleep_hours=5.0,
                data_class="PRODUCTION_DEVICE_SESSION",
                session_origin="SIMULATION_FIXTURE",
            ),
            headers={"x-wb-rnd-token": "canonical-token"},
        )
        replay = _post(client, baseline_payload)
        store = InterimStore(database_path)
        cross_class = client.post(
            "/v1/interim/device-assessments",
            json=_assessment(
                "device_assessment_cross_class",
                phase="FOLLOW_UP",
                sleep_hours=8.0,
                data_class="PRODUCTION_DEVICE_SESSION",
                session_origin="DEVICE_PROVIDER",
                baseline_assessment_id="device_assessment_canonical_baseline",
            ),
            headers={"x-wb-rnd-token": "canonical-token"},
        )
        tamper_errors = []
        for statement in (
            "update device_recommendation_assessments set phase='FOLLOW_UP'",
            "delete from device_recommendation_assessments",
        ):
            try:
                with store.transaction() as connection:
                    connection.execute(statement)
            except sqlite3.IntegrityError as error:
                tamper_errors.append(str(error))
        observed = {
            "baseline_magnesium_wearable_adjustment": baseline["score_snapshot"][
                "magnesium_glycinate"
            ]["wearable_adjustment"],
            "follow_up_sleep_delta": follow_up["sensor_changes"]["sleep_hours"]["delta"],
            "follow_up_magnesium_wearable_delta": follow_up["score_changes"][
                "magnesium_glycinate"
            ]["wearable_adjustment_delta"],
            "production_data_class": production["data_class"],
            "production_session_origin": production["session_origin"],
            "mismatch_http_status": mismatch.status_code,
            "mismatch_detail": mismatch.json()["detail"][0]["ctx"]["error"],
            "cross_class_http_status": cross_class.status_code,
            "cross_class_detail": cross_class.json()["detail"],
            "exact_replay_deduplicated": replay["deduplicated"],
            "persisted_row_count": int(
                store.scalar("select count(*) from device_recommendation_assessments")
            ),
            "distinct_data_classes": [
                row[0]
                for row in store.rows(
                    "select distinct data_class from device_recommendation_assessments order by data_class"
                )
            ],
            "tamper_errors": tamper_errors,
        }
        checks = {
            "authenticated_real_api": True,
            "baseline_value_changes_recommendation_score": observed[
                "baseline_magnesium_wearable_adjustment"
            ]
            == 4.0,
            "follow_up_value_delta_recorded": observed["follow_up_sleep_delta"] == 3.0,
            "follow_up_score_delta_recorded": observed[
                "follow_up_magnesium_wearable_delta"
            ]
            == -4.0,
            "production_and_simulation_classes_distinct": observed["distinct_data_classes"]
            == ["PRODUCTION_DEVICE_SESSION", "SIMULATED_DEVICE_SESSION"],
            "origin_mislabel_rejected": observed["mismatch_http_status"] == 422,
            "cross_class_followup_rejected": observed["cross_class_http_status"] == 422,
            "exact_replay_deduplicated": observed["exact_replay_deduplicated"] is True,
            "append_only_tamper_rejected": len(observed["tamper_errors"]) == 2,
        }
        if not all(checks.values()):
            raise AssertionError(f"device_followup_smoke_failed:{checks}")
        report = {
            "schema_version": "op097_op098_device_followup_data_class_smoke_v1",
            "requirements": {
                "OP-097": {
                    "required_stage": "INTEGRATED",
                    "claimed_stage": "INTEGRATED",
                },
                "OP-098": {
                    "required_stage": "OPERATED",
                    "claimed_stage": "IMPLEMENTED",
                },
            },
            "dataset": {
                "path": DATASET_PATH.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest(),
                "case_count": len(dataset["cases"]),
            },
            "checks": checks,
            "observed": observed,
            "stage_boundary": {
                "local_authenticated_api_and_sqlite_integration_proven": True,
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
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
