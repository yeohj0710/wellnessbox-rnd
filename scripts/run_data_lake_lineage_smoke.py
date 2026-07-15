from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.inference_api.main import app  # noqa: E402
from wellnessbox_rnd.interim.store import InterimStore  # noqa: E402

AUTHORIZED_SUBJECT_ID = "usr_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
DENIED_SUBJECT_ID = "usr_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
INTERNAL_TOKEN = "op021-op022-operational-smoke-token"


def _request(
    *,
    request_id: str,
    subject_id: str,
    age: int,
    allow_survey_storage: bool,
    medication_name: str | None = None,
) -> dict[str, Any]:
    source_profile: dict[str, Any] = {
        "name": "운영 계보 검증 사용자",
        "age": age,
        "sex": "female",
        "goals": ["sleep"],
    }
    medications = []
    if medication_name is not None:
        source_profile["medications"] = [medication_name]
        medications = [{"name": medication_name}]
    return {
        "request_id": request_id,
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": subject_id,
            "profile": source_profile,
        },
        "user_profile": {
            "age": age,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": ["sleep_support"],
        "symptoms": ["difficulty_falling_asleep"],
        "conditions": [],
        "allergies": [],
        "risk_flags": [],
        "medications": medications,
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
                "allow_persistent_storage": (
                    source == "survey" and allow_survey_storage
                ),
            }
            for source in ("survey", "nhis", "wearable", "cgm", "genetic")
        },
        "preferences": {
            "budget_level": "medium",
            "max_products": 2,
            "avoid_ingredients": [],
        },
    }


def _require_status(response, expected: int, label: str) -> dict[str, Any]:
    if response.status_code != expected:
        raise RuntimeError(
            f"{label}_failed:{response.status_code}:{response.text[:500]}"
        )
    return response.json()


def run_smoke() -> dict[str, Any]:
    previous_database = os.environ.get("WB_RND_INTERIM_DATABASE")
    previous_token = os.environ.get("WB_RND_INTERIM_INTERNAL_TOKEN")
    sensitive_value = "DENIED-PROFILE-PAYLOAD-MUST-NOT-PERSIST"

    try:
        with tempfile.TemporaryDirectory(prefix="wb-rnd-lineage-") as temporary_directory:
            database_path = Path(temporary_directory) / "lineage.sqlite3"
            os.environ["WB_RND_INTERIM_DATABASE"] = str(database_path)
            os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = INTERNAL_TOKEN
            client = TestClient(app)
            headers = {"x-wb-rnd-token": INTERNAL_TOKEN}

            first = _require_status(
                client.post(
                    "/v1/recommend",
                    json=_request(
                        request_id="op021-op022-smoke-profile-v1",
                        subject_id=AUTHORIZED_SUBJECT_ID,
                        age=41,
                        allow_survey_storage=True,
                    ),
                ),
                200,
                "first_recommendation",
            )
            execution_id = str(first["execution_id"])
            _require_status(
                client.post(
                    f"/v1/interim/executions/{execution_id}/events",
                    headers=headers,
                    json={
                        "event_type": "conversation",
                        "source": "survey",
                        "idempotency_key": "smoke-turn-1",
                        "payload": {
                            "turn_id": "turn-1",
                            "intent": "sleep_question",
                        },
                    },
                ),
                200,
                "conversation_event",
            )
            _require_status(
                client.post(
                    f"/v1/interim/executions/{execution_id}/events",
                    headers=headers,
                    json={
                        "event_type": "followup_evaluation",
                        "source": "survey",
                        "idempotency_key": "smoke-followup-week-2",
                        "payload": {
                            "timepoint_weeks": 2,
                            "status": "received",
                        },
                    },
                ),
                200,
                "followup_event",
            )
            trace = _require_status(
                client.get(
                    f"/v1/interim/executions/{execution_id}",
                    headers=headers,
                ),
                200,
                "execution_trace",
            )
            _require_status(
                client.post(
                    "/v1/recommend",
                    json=_request(
                        request_id="op021-op022-smoke-profile-v2",
                        subject_id=AUTHORIZED_SUBJECT_ID,
                        age=42,
                        allow_survey_storage=True,
                    ),
                ),
                200,
                "second_recommendation",
            )
            _require_status(
                client.post(
                    "/v1/recommend",
                    json=_request(
                        request_id="op021-op022-smoke-denied",
                        subject_id=DENIED_SUBJECT_ID,
                        age=43,
                        allow_survey_storage=False,
                        medication_name=sensitive_value,
                    ),
                ),
                200,
                "denied_storage_recommendation",
            )

            store = InterimStore(database_path)
            store.migrate()
            event_types = [str(event["event_type"]) for event in trace["events"]]
            event_execution_ids = {
                str(event["execution_id"]) for event in trace["events"]
            }
            profile_versions = [
                int(row[0])
                for row in store.rows(
                    """
                    select version from profile_snapshots
                    where profile_id=? order by version
                    """,
                    (AUTHORIZED_SUBJECT_ID,),
                )
            ]
            denied_profile_payload_count = int(
                store.scalar(
                    "select count(*) from profile_snapshots where profile_id=?",
                    (DENIED_SUBJECT_ID,),
                )
            )
            persisted_payload_text = "\n".join(
                str(row[0])
                for table in (
                    "profile_snapshots",
                    "consent_snapshots",
                    "execution_events",
                )
                for row in store.rows(f"select payload_json from {table}")
            )

            expected_event_types = [
                "recommendation",
                "safety",
                "optimization",
                "conversation",
                "followup_evaluation",
            ]
            checks = {
                "database_schema_version_is_5": (
                    store.scalar("select max(version) from schema_migrations") == 5
                ),
                "authorized_profile_versions_are_1_and_2": profile_versions == [1, 2],
                "denied_profile_payload_count_is_0": denied_profile_payload_count == 0,
                "denied_raw_value_absent": sensitive_value not in persisted_payload_text,
                "all_five_event_types_connected": event_types == expected_event_types,
                "all_events_share_execution_id": event_execution_ids == {execution_id},
                "response_execution_id_matches_trace": trace["execution_id"] == execution_id,
            }
            if not all(checks.values()):
                raise RuntimeError(f"lineage_smoke_checks_failed:{checks}")

            return {
                "schema_version": "op021_op022_data_lake_lineage_smoke_v1",
                "status": "passed",
                "data_class": "INTERIM_RUNTIME_EVENT",
                "case_count": 3,
                "database_schema_version": 5,
                "profile_version_count": len(profile_versions),
                "profile_versions": profile_versions,
                "consent_snapshot_count": int(
                    store.scalar("select count(*) from consent_snapshots")
                ),
                "denied_profile_payload_count": denied_profile_payload_count,
                "execution_count": int(store.scalar("select count(*) from executions")),
                "linked_execution_event_types": event_types,
                "all_event_execution_ids_match": event_execution_ids == {execution_id},
                "checks": checks,
            }
    finally:
        if previous_database is None:
            os.environ.pop("WB_RND_INTERIM_DATABASE", None)
        else:
            os.environ["WB_RND_INTERIM_DATABASE"] = previous_database
        if previous_token is None:
            os.environ.pop("WB_RND_INTERIM_INTERNAL_TOKEN", None)
        else:
            os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = previous_token


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_smoke()
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
