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
from wellnessbox_rnd.interim.data_mutation import DataMutationLedger  # noqa: E402
from wellnessbox_rnd.interim.store import SCHEMA_VERSION, InterimStore  # noqa: E402

INTERNAL_TOKEN = "op027-op028-event-mutation-smoke-token"
PROFILE_ID = "usr_27282728272827282728272827282728"


def _headers() -> dict[str, str]:
    return {"x-wb-rnd-token": INTERNAL_TOKEN}


def _recommendation_request() -> dict[str, Any]:
    return {
        "request_id": "op027-op028-event-mutation-smoke",
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


def run_smoke() -> dict[str, Any]:
    previous_database = os.getenv("WB_RND_INTERIM_DATABASE")
    previous_token = os.getenv("WB_RND_INTERIM_INTERNAL_TOKEN")
    try:
        with tempfile.TemporaryDirectory(prefix="wb-rnd-op027-op028-") as temporary:
            database = Path(temporary) / "event-mutation.sqlite3"
            os.environ["WB_RND_INTERIM_DATABASE"] = str(database)
            os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = INTERNAL_TOKEN
            client = TestClient(app)

            recommendation = client.post(
                "/v1/recommend", json=_recommendation_request()
            )
            execution_id = str(recommendation.json()["execution_id"])
            trace_before_response = client.get(
                f"/v1/interim/executions/{execution_id}", headers=_headers()
            )
            trace_before = trace_before_response.json()
            safety_event = next(
                event
                for event in trace_before["events"]
                if event["event_type"] == "safety"
            )
            safety_event_id = str(safety_event["event_id"])
            lineage_before = len(trace_before["knowledge_lineage"])

            conversation_request = {
                "event_type": "conversation",
                "source": "survey",
                "idempotency_key": "conversation-replay-1",
                "payload": {"message_count": 2},
            }
            conversation_first = client.post(
                f"/v1/interim/executions/{execution_id}/events",
                headers=_headers(),
                json=conversation_request,
            )
            conversation_replay = client.post(
                f"/v1/interim/executions/{execution_id}/events",
                headers=_headers(),
                json=conversation_request,
            )
            conversation_conflict = client.post(
                f"/v1/interim/executions/{execution_id}/events",
                headers=_headers(),
                json={**conversation_request, "payload": {"message_count": 3}},
            )

            behavior_request = {
                "profile_id": PROFILE_ID,
                "event_name": "page_view",
                "occurred_at": "2026-07-16T09:00:00+09:00",
                "idempotency_key": "page-view-replay-1",
                "payload": {"path": "/tips"},
            }
            behavior_first = client.post(
                "/v1/interim/behavior-events",
                headers=_headers(),
                json=behavior_request,
            )
            behavior_replay = client.post(
                "/v1/interim/behavior-events",
                headers=_headers(),
                json=behavior_request,
            )
            behavior_conflict = client.post(
                "/v1/interim/behavior-events",
                headers=_headers(),
                json={**behavior_request, "payload": {"path": "/changed"}},
            )

            correction_request = {
                "profile_id": PROFILE_ID,
                "target_type": "execution_event",
                "target_event_id": safety_event_id,
                "operation": "correction",
                "idempotency_key": "safety-correction-1",
                "replacement_payload": {
                    "status": "blocked",
                    "corrected_reason": "source_record_correction",
                },
            }
            correction_first = client.post(
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
                    "replacement_payload": {"status": "changed"},
                },
            )
            correction_mutation_id = correction_first.json()["mutation"][
                "mutation_id"
            ]
            correction_requery = client.get(
                f"/v1/interim/event-mutations/{correction_mutation_id}",
                headers=_headers(),
            )

            deletion_request = {
                "profile_id": PROFILE_ID,
                "target_type": "execution_event",
                "target_event_id": safety_event_id,
                "operation": "deletion",
                "idempotency_key": "safety-deletion-1",
            }
            deletion_first = client.post(
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

            trace_after_response = client.get(
                f"/v1/interim/executions/{execution_id}", headers=_headers()
            )
            trace_after = trace_after_response.json()
            deleted_safety_event = next(
                event
                for event in trace_after["events"]
                if event["event_id"] == safety_event_id
            )
            store = InterimStore(database)
            mutations = store.rows(
                "select * from event_mutations order by mutation_index"
            )
            conversation_count = int(
                store.scalar(
                    "select count(*) from execution_events "
                    "where execution_id=? and idempotency_key='conversation-replay-1'",
                    (execution_id,),
                )
            )
            behavior_count = int(
                store.scalar(
                    "select count(*) from behavior_events "
                    "where profile_id=? and idempotency_key='page-view-replay-1'",
                    (PROFILE_ID,),
                )
            )
            mutation_count = int(store.scalar("select count(*) from event_mutations"))
            audit_count = int(
                store.scalar(
                    "select count(*) from audit_events "
                    "where event_type in ('data_correction', 'data_deletion')"
                )
            )
            lineage_after = int(
                store.scalar(
                    "select count(*) from execution_knowledge_lineage where event_id=?",
                    (safety_event_id,),
                )
            )
            original_lineage_for_event = sum(
                1
                for item in trace_before["knowledge_lineage"]
                if item["event_id"] == safety_event_id
            )
            checks = {
                "database_schema_version_matches_current": (
                    store.scalar("select max(version) from schema_migrations")
                    == SCHEMA_VERSION
                ),
                "recommendation_and_trace_succeeded": (
                    recommendation.status_code == 200
                    and trace_before_response.status_code == 200
                    and trace_after_response.status_code == 200
                ),
                "conversation_replay_deduplicated": (
                    conversation_first.status_code == 200
                    and conversation_first.json()["deduplicated"] is False
                    and conversation_replay.status_code == 200
                    and conversation_replay.json()["deduplicated"] is True
                    and conversation_count == 1
                ),
                "conversation_changed_replay_rejected": (
                    conversation_conflict.status_code == 409
                ),
                "behavior_replay_deduplicated": (
                    behavior_first.status_code == 200
                    and behavior_first.json()["deduplicated"] is False
                    and behavior_replay.status_code == 200
                    and behavior_replay.json()["deduplicated"] is True
                    and behavior_count == 1
                ),
                "behavior_changed_replay_rejected": (
                    behavior_conflict.status_code == 409
                ),
                "correction_replay_deduplicated": (
                    correction_first.status_code == 200
                    and correction_first.json()["deduplicated"] is False
                    and correction_replay.status_code == 200
                    and correction_replay.json()["deduplicated"] is True
                    and correction_requery.status_code == 200
                ),
                "correction_changed_replay_rejected": (
                    correction_conflict.status_code == 409
                ),
                "deletion_replay_deduplicated": (
                    deletion_first.status_code == 200
                    and deletion_first.json()["deduplicated"] is False
                    and deletion_replay.status_code == 200
                    and deletion_replay.json()["deduplicated"] is True
                ),
                "correction_after_deletion_rejected": (
                    correction_after_deletion.status_code == 409
                ),
                "deleted_payload_is_tombstoned": (
                    deleted_safety_event["payload_state"] == "DELETED"
                    and deleted_safety_event["payload"]
                    == {
                        "deleted": True,
                        "mutation_id": deletion_first.json()["mutation"][
                            "mutation_id"
                        ],
                    }
                ),
                "mutation_and_audit_counts_match": (
                    mutation_count == 2 and audit_count == 2
                ),
                "mutation_hash_chain_is_contiguous": (
                    len(mutations) == 2
                    and mutations[1]["previous_mutation_id"]
                    == mutations[0]["mutation_id"]
                    and mutations[1]["previous_mutation_sha256"]
                    == mutations[0]["mutation_sha256"]
                    and mutations[1]["prior_payload_sha256"]
                    == mutations[0]["result_payload_sha256"]
                    and DataMutationLedger(store).verify_chain(
                        target_type="execution_event",
                        target_event_id=safety_event_id,
                    )
                ),
                "ingestion_fingerprint_is_immutable": (
                    deleted_safety_event["payload_sha256"]
                    == safety_event["payload_sha256"]
                    and deleted_safety_event["effective_payload_sha256"]
                    == deletion_first.json()["mutation"][
                        "result_payload_sha256"
                    ]
                ),
                "deleted_correction_payload_is_absent_from_sqlite_files": (
                    all(
                        b"source_record_correction" not in path.read_bytes()
                        for path in database.parent.glob(f"{database.name}*")
                    )
                ),
                "knowledge_lineage_is_preserved": (
                    lineage_before > 0
                    and original_lineage_for_event > 0
                    and lineage_after == original_lineage_for_event
                ),
            }
            if not all(checks.values()):
                failed = [name for name, passed in checks.items() if not passed]
                raise AssertionError(f"event_mutation_smoke_failed:{','.join(failed)}")
            return {
                "schema_version": "op027_op028_event_idempotency_data_mutation_smoke_v1",
                "status": "passed",
                "data_class": "INTERIM_RUNTIME_EVENT",
                "case_count": 3,
                "database_schema_version": SCHEMA_VERSION,
                "conversation_event_count": conversation_count,
                "behavior_event_count": behavior_count,
                "event_mutation_count": mutation_count,
                "mutation_audit_count": audit_count,
                "knowledge_lineage_count_before": lineage_before,
                "knowledge_lineage_count_for_mutated_event": lineage_after,
                "final_payload_state": deleted_safety_event["payload_state"],
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
