from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.inference_api.main import app  # noqa: E402
from wellnessbox_rnd.interim.store import InterimStore  # noqa: E402

OUTPUT = (
    ROOT
    / "data"
    / "original_plan"
    / "evidence"
    / "op029_op030_session_replay_service_ui_smoke_v1.json"
)
TOKEN = "op029-op030-smoke-token"
_RAW_HEALTH_KEYS = {
    "allergies",
    "conditions",
    "current_supplements",
    "data_source_consents",
    "dietary_patterns",
    "goals",
    "input_availability",
    "laboratory_observations",
    "lifestyle",
    "medications",
    "preferences",
    "risk_flags",
    "source_profile",
    "symptoms",
    "user_profile",
}


def contains_raw_health_payload(value: object) -> bool:
    if isinstance(value, dict):
        return bool(_RAW_HEALTH_KEYS.intersection(value)) or any(
            contains_raw_health_payload(item) for item in value.values()
        )
    if isinstance(value, list):
        return any(contains_raw_health_payload(item) for item in value)
    return False


def payload() -> dict[str, object]:
    return {
        "request_id": "op029-op030-smoke-request",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": "usr_029030abcdef0123456789abcdef0123",
            "profile": {
                "age": 43,
                "sex": "female",
                "goals": ["sleep"],
            },
        },
        "user_profile": {
            "age": 43,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": ["sleep_support"],
        "symptoms": ["difficulty_falling_asleep"],
        "conditions": [],
        "allergies": [],
        "risk_flags": [],
        "medications": [],
        "current_supplements": [],
        "dietary_patterns": [],
        "laboratory_observations": [],
        "lifestyle": {
            "sleep_hours": 5.5,
            "stress_level": 4,
            "activity_level": "lightly_active",
            "smoker": False,
            "alcohol_per_week": 0,
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
        "preferences": {
            "budget_level": "medium",
            "max_products": 2,
            "avoid_ingredients": [],
        },
    }


def main() -> None:
    original = {
        name: os.environ.get(name)
        for name in (
            "WB_RND_INTERIM_DATABASE",
            "WB_RND_INTERIM_INTERNAL_TOKEN",
            "WB_RND_CODE_COMMIT",
        )
    }
    try:
        with TemporaryDirectory(prefix="wb-rnd-session-replay-") as directory:
            database = Path(directory) / "interim.sqlite3"
            os.environ["WB_RND_INTERIM_DATABASE"] = str(database)
            os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = TOKEN
            os.environ["WB_RND_CODE_COMMIT"] = "op029-op030-smoke-version"
            client = TestClient(app)
            unauthorized = client.get("/v1/interim/executions")
            recommendation = client.post("/v1/recommend", json=payload())
            recommendation.raise_for_status()
            execution_id = recommendation.json()["execution_id"]
            headers = {"x-wb-rnd-token": TOKEN}
            summary = client.get(
                "/v1/interim/executions?limit=20", headers=headers
            )
            matched = client.post(
                f"/v1/interim/executions/{execution_id}/replay", headers=headers
            )
            os.environ["WB_RND_CODE_COMMIT"] = "op029-op030-changed-version"
            version_mismatch = client.post(
                f"/v1/interim/executions/{execution_id}/replay", headers=headers
            )
            summary.raise_for_status()
            matched.raise_for_status()
            version_mismatch.raise_for_status()
            summary_body = summary.json()
            matched_body = matched.json()
            mismatch_body = version_mismatch.json()
            store = InterimStore(database)
            raw_health_payload_returned = any(
                contains_raw_health_payload(body)
                for body in (summary_body, matched_body, mismatch_body)
            )
            execution_count = int(store.scalar("select count(*) from executions"))
            replay_snapshot_count = int(
                store.scalar("select count(*) from execution_replay_snapshots")
            )
            replay_run_count = int(
                store.scalar("select count(*) from execution_replay_runs")
            )
            assert unauthorized.status_code == 401
            assert recommendation.status_code == 200
            assert summary.status_code == 200
            assert matched.status_code == 200
            assert version_mismatch.status_code == 200
            assert summary_body["total_saved_sessions"] == 1
            assert summary_body["replayable_sessions"] == 1
            assert matched_body["status"] == "MATCH"
            assert matched_body["input_match"] is True
            assert matched_body["version_match"] is True
            assert matched_body["output_match"] is True
            assert (
                matched_body["expected_output_sha256"]
                == matched_body["actual_output_sha256"]
            )
            assert mismatch_body["status"] == "VERSION_MISMATCH"
            assert mismatch_body["version_match"] is False
            assert mismatch_body["actual_output_sha256"] is None
            assert execution_count == 1
            assert replay_snapshot_count == 1
            assert replay_run_count == 2
            assert raw_health_payload_returned is False
            result = {
                "schema_version": int(
                    store.scalar("select max(version) from schema_migrations")
                ),
                "actual_route_cases": 4,
                "security": {
                    "list_without_token_status": unauthorized.status_code,
                    "internal_token_required": unauthorized.status_code == 401,
                },
                "saved_sessions": {
                    "total": summary_body["total_saved_sessions"],
                    "replayable": summary_body["replayable_sessions"],
                    "unavailable": summary_body["unavailable_sessions"],
                    "visible_items": len(summary_body["items"]),
                },
                "same_input_and_version": {
                    "status": matched_body["status"],
                    "input_match": matched_body["input_match"],
                    "version_match": matched_body["version_match"],
                    "output_match": matched_body["output_match"],
                    "output_hashes_equal": (
                        matched_body["expected_output_sha256"]
                        == matched_body["actual_output_sha256"]
                    ),
                },
                "changed_version": {
                    "status": mismatch_body["status"],
                    "input_match": mismatch_body["input_match"],
                    "version_match": mismatch_body["version_match"],
                    "output_match": mismatch_body["output_match"],
                    "recommendation_execution_skipped": (
                        mismatch_body["actual_output_sha256"] is None
                    ),
                    "mismatch_fields": mismatch_body["mismatch_fields"],
                },
                "database_rows": {
                    "executions": execution_count,
                    "replay_snapshots": replay_snapshot_count,
                    "replay_runs": replay_run_count,
                },
                "raw_health_payload_returned": raw_health_payload_returned,
                "required_stage": "OPERATED",
                "proven_stage": "IMPLEMENTED",
            }
            OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            OUTPUT.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    finally:
        for name, value in original.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    main()
