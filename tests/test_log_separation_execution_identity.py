from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.inference_api.main import app
from wellnessbox_rnd.interim.behavior_log import (
    BEHAVIOR_EVENT_NAMES,
    RESEARCH_EVENT_TYPES,
    BehaviorLogRecorder,
)
from wellnessbox_rnd.interim.execution_identity import (
    RUNTIME_DATASET_ARTIFACTS,
    resolve_code_commit,
)
from wellnessbox_rnd.interim.store import InterimStore

SUBJECT_ID = "usr_feedfacefeedfacefeedfacefeedface"
INTERNAL_TOKEN = "log-separation-identity-test-token"
CODE_COMMIT_OVERRIDE = "0123456789abcdef0123456789abcdef01234567"


def _headers() -> dict[str, str]:
    return {"x-wb-rnd-token": INTERNAL_TOKEN}


def _recommend_payload(
    *,
    request_id: str,
    allow_survey_storage: bool = True,
) -> dict[str, object]:
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
            "survey": {
                "use_for_recommendation": True,
                "allow_persistent_storage": allow_survey_storage,
            },
            "nhis": {
                "use_for_recommendation": False,
                "allow_persistent_storage": False,
            },
            "wearable": {
                "use_for_recommendation": False,
                "allow_persistent_storage": False,
            },
            "cgm": {
                "use_for_recommendation": False,
                "allow_persistent_storage": False,
            },
            "genetic": {
                "use_for_recommendation": False,
                "allow_persistent_storage": False,
            },
        },
        "preferences": {
            "budget_level": "medium",
            "max_products": 2,
            "avoid_ingredients": [],
        },
    }


def _behavior_payload(
    *,
    event_name: str = "page_view",
    idempotency_key: str = "behavior-1",
    occurred_at: str = "2026-07-15T10:00:00+09:00",
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "profile_id": SUBJECT_ID,
        "event_name": event_name,
        "occurred_at": occurred_at,
        "idempotency_key": idempotency_key,
        "payload": {"screen": "/explore"} if payload is None else payload,
    }


@pytest.fixture()
def api_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(tmp_path / "log-identity.sqlite3"))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", INTERNAL_TOKEN)
    monkeypatch.setenv("WB_RND_CODE_COMMIT", CODE_COMMIT_OVERRIDE)
    return TestClient(app)


def _run_recommendation(client: TestClient, *, request_id: str) -> str:
    response = client.post("/v1/recommend", json=_recommend_payload(request_id=request_id))
    assert response.status_code == 200
    return str(response.json()["execution_id"])


def _trace(client: TestClient, execution_id: str) -> dict[str, object]:
    response = client.get(f"/v1/interim/executions/{execution_id}", headers=_headers())
    assert response.status_code == 200
    return response.json()


def test_vocabularies_are_disjoint() -> None:
    assert not (BEHAVIOR_EVENT_NAMES & RESEARCH_EVENT_TYPES)


def test_recommendation_execution_records_full_identity(api_client, tmp_path) -> None:
    execution_id = _run_recommendation(api_client, request_id="identity-run-1")

    identity = _trace(api_client, execution_id)["execution_identity"]
    assert identity is not None
    assert identity["execution_id"] == execution_id
    assert identity["model_id"] == "deterministic_baseline_v1"
    assert identity["engine_version"]
    assert identity["code_commit"] == CODE_COMMIT_OVERRIDE
    assert identity["code_commit_source"] == "environment"
    dataset_ids = {item["dataset_id"] for item in identity["datasets"]}
    assert dataset_ids == {dataset_id for dataset_id, _ in RUNTIME_DATASET_ARTIFACTS}
    for item in identity["datasets"]:
        assert len(item["sha256"]) == 64
    assert len(identity["config_sha256"]) == 64
    assert identity["config"]["model_id"] == "deterministic_baseline_v1"
    assert identity["config"]["datasets"] == {
        item["dataset_id"]: item["sha256"] for item in identity["datasets"]
    }

    store = InterimStore(tmp_path / "log-identity.sqlite3")
    assert store.scalar("select count(*) from execution_identities") == 1


def test_identical_runs_share_config_hash_and_dataset_identities(api_client) -> None:
    first = _run_recommendation(api_client, request_id="identity-run-a")
    second = _run_recommendation(api_client, request_id="identity-run-b")

    first_identity = _trace(api_client, first)["execution_identity"]
    second_identity = _trace(api_client, second)["execution_identity"]
    assert first != second
    assert first_identity["config_sha256"] == second_identity["config_sha256"]
    assert first_identity["datasets"] == second_identity["datasets"]


def test_code_commit_resolution_prefers_environment_then_git(monkeypatch) -> None:
    monkeypatch.setenv("WB_RND_CODE_COMMIT", "abc123def456")
    assert resolve_code_commit() == ("environment", "abc123def456")

    monkeypatch.delenv("WB_RND_CODE_COMMIT", raising=False)
    source, value = resolve_code_commit()
    assert source in {"git", "unresolved"}
    if source == "git":
        assert 7 <= len(value) <= 64
    else:
        assert value == "unresolved"


def test_behavior_event_appends_only_to_behavior_store(api_client, tmp_path) -> None:
    _run_recommendation(api_client, request_id="behavior-base")

    response = api_client.post(
        "/v1/interim/behavior-events",
        headers=_headers(),
        json=_behavior_payload(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["deduplicated"] is False
    assert body["event"]["log_class"] == "user_behavior"
    assert body["event"]["occurred_at"] == "2026-07-15T01:00:00+00:00"

    store = InterimStore(tmp_path / "log-identity.sqlite3")
    assert store.scalar("select count(*) from behavior_events") == 1
    assert (
        store.scalar(
            "select count(*) from execution_events where event_type not in "
            "('conversation','recommendation','safety','optimization','followup_evaluation')"
        )
        == 0
    )


def test_behavior_event_replay_deduplicates_and_conflicts(api_client) -> None:
    _run_recommendation(api_client, request_id="behavior-idempotency")

    first = api_client.post(
        "/v1/interim/behavior-events", headers=_headers(), json=_behavior_payload()
    )
    replay = api_client.post(
        "/v1/interim/behavior-events", headers=_headers(), json=_behavior_payload()
    )
    conflict = api_client.post(
        "/v1/interim/behavior-events",
        headers=_headers(),
        json=_behavior_payload(payload={"screen": "/cart"}),
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["deduplicated"] is True
    assert replay.json()["event"]["behavior_event_id"] == (
        first.json()["event"]["behavior_event_id"]
    )
    assert conflict.status_code == 409


def test_research_event_type_is_rejected_by_behavior_endpoint(api_client) -> None:
    _run_recommendation(api_client, request_id="behavior-reject-research")

    response = api_client.post(
        "/v1/interim/behavior-events",
        headers=_headers(),
        json=_behavior_payload(event_name="safety"),
    )
    assert response.status_code == 422
    assert "research_event_type_not_allowed_in_behavior_log" in response.json()["detail"]


def test_behavior_event_name_is_rejected_by_research_event_endpoint(api_client) -> None:
    execution_id = _run_recommendation(api_client, request_id="research-reject-behavior")

    response = api_client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json={
            "event_type": "page_view",
            "source": "survey",
            "idempotency_key": "behavior-in-research",
            "payload": {},
        },
    )
    assert response.status_code == 422


def test_behavior_event_requires_storage_consent(api_client) -> None:
    response = api_client.post(
        "/v1/recommend",
        json=_recommend_payload(
            request_id="behavior-consent-denied",
            allow_survey_storage=False,
        ),
    )
    assert response.status_code == 200

    denied = api_client.post(
        "/v1/interim/behavior-events", headers=_headers(), json=_behavior_payload()
    )
    assert denied.status_code == 403
    assert "persistent_storage_consent_denied" in denied.json()["detail"]


def test_behavior_event_requires_timezone_aware_occurrence(api_client) -> None:
    _run_recommendation(api_client, request_id="behavior-naive-time")

    response = api_client.post(
        "/v1/interim/behavior-events",
        headers=_headers(),
        json=_behavior_payload(occurred_at="2026-07-15T10:00:00"),
    )
    assert response.status_code == 422
    assert "timezone_aware" in response.json()["detail"]


def test_behavior_event_for_unknown_profile_is_rejected(api_client) -> None:
    response = api_client.post(
        "/v1/interim/behavior-events",
        headers=_headers(),
        json={**_behavior_payload(), "profile_id": "usr_00000000deadbeef"},
    )
    assert response.status_code == 404


def test_trace_and_log_summary_keep_log_classes_separate(api_client, tmp_path) -> None:
    execution_id = _run_recommendation(api_client, request_id="separation-summary")
    api_client.post(
        "/v1/interim/behavior-events", headers=_headers(), json=_behavior_payload()
    )

    trace = _trace(api_client, execution_id)
    trace_event_types = {event["event_type"] for event in trace["events"]}
    assert trace_event_types <= RESEARCH_EVENT_TYPES
    assert "behavior_events" not in trace

    summary = api_client.get("/v1/interim/log-classes", headers=_headers()).json()
    assert summary["research_evaluation_event_count"] >= 3
    assert summary["user_behavior_event_count"] == 1
    assert summary["research_event_table"] == "execution_events"
    assert summary["behavior_event_table"] == "behavior_events"
    assert summary["cross_contamination_count"] == 0

    recorder = BehaviorLogRecorder(InterimStore(tmp_path / "log-identity.sqlite3"))
    assert recorder.log_class_summary().cross_contamination_count == 0
