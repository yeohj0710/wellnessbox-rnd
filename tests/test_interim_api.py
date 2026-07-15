import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.inference_api.main import app
from wellnessbox_rnd.interim.importer import register_retrained_package
from wellnessbox_rnd.interim.store import InterimStore

RETRAINED_PACKAGE_ROOT = Path("artifacts/tips/interim/retrained")


def _headers() -> dict[str, str]:
    return {"x-wb-rnd-token": "test-token"}


@pytest.mark.skipif(
    not RETRAINED_PACKAGE_ROOT.is_dir(),
    reason="ignored local retrained package artifacts/tips/interim/retrained is absent",
)
def test_interim_api_requires_token_and_runs_recommendation(tmp_path, monkeypatch) -> None:
    database = tmp_path / "api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)

    assert client.get("/v1/interim/status").status_code == 401
    status = client.get("/v1/interim/status", headers=_headers())
    assert status.status_code == 200
    assert status.json()["mode"] == "PROXY_GOLD_SIMULATION"
    register_retrained_package(
        InterimStore(database),
        Path("artifacts/tips/interim/retrained"),
        code_commit="test",
        rollback_model_id=None,
    )

    profile_id = "usr_" + hashlib.sha256(b"user-1").hexdigest()[:16]
    profile = client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "consent_scopes": ["followup:write"],
            "profile": {"age": 41},
        },
    )
    assert profile.status_code == 200

    response = client.post(
        "/v1/interim/recommendations",
        headers=_headers(),
        json={
            "profile_id": profile_id,
            "goals": ["sleep"],
            "ingredients": ["magnesium", "theanine"],
            "safety": {"age": 41},
        },
    )
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "READY"
    assert body["simulation"] is True
    assert body["model_id"].startswith("proxy-recommendation-")
    assert len(body["recommendations"]) >= 1


def test_serious_ae_flow_creates_review_and_review_decision_is_immutable(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    profile_id = "usr_1234567890abcdef"
    client.post(
        "/v1/interim/profiles",
        headers=_headers(),
        json={"profile_id": profile_id, "consent_scopes": ["ae:write"], "profile": {}},
    )
    run = client.post(
        "/v1/interim/agent/runs",
        headers=_headers(),
        params={"profile_id": profile_id, "idempotency_key": "ae-run"},
    ).json()
    event = client.post(
        "/v1/interim/agent/tools",
        headers=_headers(),
        json={
            "run_id": run["run_id"],
            "tool_name": "log_adverse_event",
            "arguments": {"profile_id": profile_id, "serious": True},
            "consent_scopes": ["ae:write"],
        },
    )
    assert event.status_code == 200
    review_id = event.json()["review_id"]
    with InterimStore(tmp_path / "api.sqlite3").transaction() as connection:
        connection.execute("update review_tasks set pharmacy_id=1 where review_id=?", (review_id,))
    queue = client.get("/v1/interim/admin/reviews?pharmacy_id=1", headers=_headers()).json()
    assert queue["items"][0]["simulation_badge"] == 1
    first = client.post(
        f"/v1/interim/admin/reviews/{review_id}/decision",
        headers=_headers(),
        json={"decision": "acknowledged", "pharmacy_id": 1},
    )
    second = client.post(
        f"/v1/interim/admin/reviews/{review_id}/decision",
        headers=_headers(),
        json={"decision": "changed", "pharmacy_id": 1},
    )
    assert first.status_code == 200
    assert second.status_code == 409


def test_execution_event_api_connects_conversation_and_followup_to_recommendation(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "execution-events.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    client = TestClient(app)
    payload = {
        "request_id": "execution-api-001",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": "usr_1234567890abcdef1234567890abcdef",
            "profile": {
                "age": 39,
                "sex": "female",
                "goals": ["sleep"],
            },
        },
        "user_profile": {
            "age": 39,
            "biological_sex": "female",
            "pregnant": False,
        },
        "goals": ["sleep_support"],
        "symptoms": ["difficulty_falling_asleep"],
        "conditions": [],
        "medications": [],
        "current_supplements": [],
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

    recommendation = client.post("/v1/recommend", json=payload)
    execution_id = recommendation.json()["execution_id"]
    conversation = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json={
            "event_type": "conversation",
            "source": "survey",
            "idempotency_key": "turn-1",
            "payload": {"intent": "sleep_question"},
        },
    )
    followup = client.post(
        f"/v1/interim/executions/{execution_id}/events",
        headers=_headers(),
        json={
            "event_type": "followup_evaluation",
            "source": "survey",
            "idempotency_key": "week-2",
            "payload": {"timepoint_weeks": 2, "status": "received"},
        },
    )
    trace = client.get(
        f"/v1/interim/executions/{execution_id}",
        headers=_headers(),
    )

    assert recommendation.status_code == 200
    assert conversation.status_code == 200
    assert followup.status_code == 200
    assert trace.status_code == 200
    assert [event["event_type"] for event in trace.json()["events"]] == [
        "recommendation",
        "safety",
        "optimization",
        "conversation",
        "followup_evaluation",
    ]
    assert {event["execution_id"] for event in trace.json()["events"]} == {
        execution_id
    }
