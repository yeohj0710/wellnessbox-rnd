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

INTERNAL_TOKEN = "op025-op026-log-separation-identity-smoke-token"
CODE_COMMIT_OVERRIDE = "op025op026fixedcommitfixedcommitfixedco0"
SUBJECT_ID = "usr_ab12ab12ab12ab12ab12ab12ab12ab12"


def _recommend_request(request_id: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": SUBJECT_ID,
            "profile": {
                "age": 41,
                "sex": "female",
                "goals": ["sleep"],
            },
        },
        "user_profile": {
            "age": 41,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": ["sleep_support"],
        "symptoms": ["difficulty_falling_asleep"],
        "conditions": [],
        "medications": [],
        "current_supplements": [],
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


def _behavior_request(
    *,
    event_name: str = "page_view",
    idempotency_key: str = "smoke-behavior-1",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "profile_id": SUBJECT_ID,
        "event_name": event_name,
        "occurred_at": "2026-07-15T10:00:00+09:00",
        "idempotency_key": idempotency_key,
        "payload": {"screen": "/explore"} if payload is None else payload,
    }


def _require_status(response, expected: int, label: str) -> dict[str, Any]:
    if response.status_code != expected:
        raise RuntimeError(
            f"{label}_failed:{response.status_code}:{response.text[:500]}"
        )
    return response.json()


def run_smoke() -> dict[str, Any]:
    previous_environment = {
        name: os.environ.get(name)
        for name in (
            "WB_RND_INTERIM_DATABASE",
            "WB_RND_INTERIM_INTERNAL_TOKEN",
            "WB_RND_CODE_COMMIT",
        )
    }
    try:
        with tempfile.TemporaryDirectory(prefix="wb-rnd-log-identity-") as temp_dir:
            database_path = Path(temp_dir) / "log-identity.sqlite3"
            os.environ["WB_RND_INTERIM_DATABASE"] = str(database_path)
            os.environ["WB_RND_INTERIM_INTERNAL_TOKEN"] = INTERNAL_TOKEN
            os.environ["WB_RND_CODE_COMMIT"] = CODE_COMMIT_OVERRIDE
            client = TestClient(app)
            headers = {"x-wb-rnd-token": INTERNAL_TOKEN}

            first = _require_status(
                client.post("/v1/recommend", json=_recommend_request("op025-op026-run-1")),
                200,
                "first_recommendation",
            )
            second = _require_status(
                client.post("/v1/recommend", json=_recommend_request("op025-op026-run-2")),
                200,
                "second_recommendation",
            )
            first_execution = str(first["execution_id"])
            second_execution = str(second["execution_id"])

            first_trace = _require_status(
                client.get(f"/v1/interim/executions/{first_execution}", headers=headers),
                200,
                "first_trace",
            )
            second_trace = _require_status(
                client.get(f"/v1/interim/executions/{second_execution}", headers=headers),
                200,
                "second_trace",
            )
            first_identity = first_trace["execution_identity"]
            second_identity = second_trace["execution_identity"]

            behavior_first = _require_status(
                client.post(
                    "/v1/interim/behavior-events",
                    headers=headers,
                    json=_behavior_request(),
                ),
                200,
                "behavior_append",
            )
            behavior_replay = _require_status(
                client.post(
                    "/v1/interim/behavior-events",
                    headers=headers,
                    json=_behavior_request(),
                ),
                200,
                "behavior_replay",
            )
            behavior_conflict = client.post(
                "/v1/interim/behavior-events",
                headers=headers,
                json=_behavior_request(payload={"screen": "/cart"}),
            )
            research_in_behavior = client.post(
                "/v1/interim/behavior-events",
                headers=headers,
                json=_behavior_request(
                    event_name="safety",
                    idempotency_key="smoke-research-name",
                ),
            )
            behavior_in_research = client.post(
                f"/v1/interim/executions/{first_execution}/events",
                headers=headers,
                json={
                    "event_type": "page_view",
                    "source": "survey",
                    "idempotency_key": "smoke-behavior-name",
                    "payload": {},
                },
            )
            summary = _require_status(
                client.get("/v1/interim/log-classes", headers=headers),
                200,
                "log_class_summary",
            )

            store = InterimStore(database_path)
            identity_count = int(store.scalar("select count(*) from execution_identities"))
            behavior_count = int(store.scalar("select count(*) from behavior_events"))
            research_count = int(store.scalar("select count(*) from execution_events"))

            dataset_ids = sorted(
                item["dataset_id"] for item in first_identity["datasets"]
            )
            checks = {
                "database_schema_version_is_6": (
                    store.scalar("select max(version) from schema_migrations") == 6
                ),
                "identity_recorded_for_every_execution": identity_count == 2,
                "model_id_is_deterministic_baseline": (
                    first_identity["model_id"] == "deterministic_baseline_v1"
                ),
                "code_commit_uses_environment_override": (
                    first_identity["code_commit_source"] == "environment"
                    and first_identity["code_commit"] == CODE_COMMIT_OVERRIDE
                ),
                "dataset_identities_are_hashed": (
                    dataset_ids
                    == [
                        "ingredient_catalog_v1",
                        "reference_knowledge_base_v1",
                        "runtime_knowledge_db_v1",
                        "safety_rules_v1",
                    ]
                    and all(
                        len(str(item["sha256"])) == 64
                        for item in first_identity["datasets"]
                    )
                ),
                "identical_runs_share_config_hash": (
                    first_identity["config_sha256"] == second_identity["config_sha256"]
                    and len(str(first_identity["config_sha256"])) == 64
                ),
                "behavior_event_persisted_once": (
                    behavior_first["deduplicated"] is False
                    and behavior_replay["deduplicated"] is True
                    and behavior_count == 1
                ),
                "behavior_conflict_rejected": behavior_conflict.status_code == 409,
                "research_type_rejected_in_behavior_log": (
                    research_in_behavior.status_code == 422
                ),
                "behavior_name_rejected_in_research_log": (
                    behavior_in_research.status_code == 422
                ),
                "log_classes_separated_without_contamination": (
                    summary["research_event_table"] == "execution_events"
                    and summary["behavior_event_table"] == "behavior_events"
                    and summary["research_evaluation_event_count"] == research_count
                    and summary["user_behavior_event_count"] == behavior_count
                    and summary["cross_contamination_count"] == 0
                ),
                "trace_contains_no_behavior_events": all(
                    event["event_type"]
                    in {
                        "conversation",
                        "recommendation",
                        "safety",
                        "optimization",
                        "followup_evaluation",
                    }
                    for event in first_trace["events"]
                ),
            }
            if not all(checks.values()):
                raise RuntimeError(f"log_separation_identity_smoke_checks_failed:{checks}")

            return {
                "schema_version": "op025_op026_log_separation_identity_smoke_v1",
                "status": "passed",
                "data_class": "INTERIM_RUNTIME_EVENT",
                "case_count": 2,
                "database_schema_version": 6,
                "execution_identity_count": identity_count,
                "research_event_count": research_count,
                "behavior_event_count": behavior_count,
                "dataset_identity_ids": dataset_ids,
                "code_commit_source": "environment",
                "checks": checks,
            }
    finally:
        for name, value in previous_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


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
