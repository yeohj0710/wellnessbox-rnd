from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from apps.inference_api.main import app
from wellnessbox_rnd.interim.data_lake import ExecutionLedger
from wellnessbox_rnd.interim.session_replay import (
    SessionReplayLedger,
    SessionReplayUnavailableError,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

SUBJECT_ID = "usr_abcdef0123456789abcdef0123456789"


def _payload(*, allow_storage: bool = True) -> dict[str, object]:
    return {
        "request_id": f"session-replay-{int(allow_storage)}",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": SUBJECT_ID,
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
            "survey": {
                "use_for_recommendation": True,
                "allow_persistent_storage": allow_storage,
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


def _store(tmp_path) -> InterimStore:
    store = InterimStore(tmp_path / "session-replay.sqlite3")
    store.migrate()
    return store


def _record(store: InterimStore, *, allow_storage: bool = True):
    request = RecommendationRequest.model_validate(_payload(allow_storage=allow_storage))
    response = recommend(request)
    trace = ExecutionLedger(store).record_recommendation(request=request, response=response)
    return request, response, trace


def test_replay_snapshot_is_stored_only_with_persistent_storage_consent(tmp_path) -> None:
    store = _store(tmp_path)
    allowed_request, allowed_response, allowed = _record(store)
    _denied_request, _denied_response, denied = _record(store, allow_storage=False)

    rows = store.rows("select * from execution_replay_snapshots")
    assert len(rows) == 1
    assert rows[0]["execution_id"] == allowed.execution_id
    stored_request = json.loads(rows[0]["request_json"])
    assert stored_request["request_id"] == allowed_request.request_id
    assert stored_request["user_profile"] == allowed_request.user_profile.model_dump(
        mode="json", exclude_none=False
    )
    assert stored_request["source_profile"] == allowed_request.source_profile.model_dump(
        mode="json", exclude_none=False
    )
    expected = json.loads(rows[0]["expected_output_json"])
    assert expected["request_id"] == allowed_response.request_id
    assert "execution_id" not in expected
    assert "decision_id" not in expected
    assert "generated_at" not in expected["metadata"]
    assert denied.profile_snapshot_id is None

    summary = SessionReplayLedger(store).summary(limit=10)
    assert summary.total_saved_sessions == 2
    assert summary.replayable_sessions == 1
    assert summary.unavailable_sessions == 1
    assert summary.replay_run_count == 0
    assert [item.execution_id for item in summary.items] == [
        denied.execution_id,
        allowed.execution_id,
    ]
    assert summary.items[0].replay_available is False
    assert summary.items[1].replay_available is True

    with pytest.raises(SessionReplayUnavailableError, match=denied.execution_id):
        SessionReplayLedger(store).replay(denied.execution_id)


def test_replay_snapshot_rejects_a_represented_source_without_storage_consent(
    tmp_path,
) -> None:
    store = _store(tmp_path)
    payload = _payload()
    payload["input_availability"]["nhis"] = True  # type: ignore[index]
    payload["data_source_consents"]["nhis"] = {  # type: ignore[index]
        "use_for_recommendation": False,
        "allow_persistent_storage": False,
    }
    payload["laboratory_observations"] = [
        {
            "code": "private-nhis-lab",
            "value": 101,
            "unit": "mg/dL",
            "reference_range": {"low": 70, "high": 99},
            "measured_at": "2026-07-16T09:00:00+09:00",
            "source": "nhis",
        }
    ]
    request = RecommendationRequest.model_validate(payload)
    trace = ExecutionLedger(store).record_recommendation(
        request=request,
        response=recommend(request),
    )

    assert store.scalar(
        "select count(*) from execution_replay_snapshots where execution_id=?",
        (trace.execution_id,),
    ) == 0
    database_text = "\n".join(
        str(row[0])
        for table in ("profile_snapshots", "execution_events")
        for row in store.rows(f"select payload_json from {table}")
    )
    assert "private-nhis-lab" not in database_text


def test_replay_matches_same_input_and_runtime_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WB_RND_CODE_COMMIT", "replay-test-commit")
    store = _store(tmp_path)
    _request, _response, trace = _record(store)

    first = SessionReplayLedger(store).replay(trace.execution_id)
    second = SessionReplayLedger(store).replay(trace.execution_id)

    assert first.status == "MATCH"
    assert first.input_match is True
    assert first.version_match is True
    assert first.output_match is True
    assert first.expected_output_sha256 == first.actual_output_sha256
    assert second.status == "MATCH"
    assert second.replay_id != first.replay_id
    assert second.actual_output_sha256 == first.actual_output_sha256
    assert store.scalar("select count(*) from execution_replay_runs") == 2
    summary = SessionReplayLedger(store).summary(limit=1)
    assert summary.replay_run_count == 2
    assert summary.items[0].last_replay_status == "MATCH"

    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        with store.transaction() as connection:
            connection.execute(
                "update execution_replay_snapshots set request_json='{}' where execution_id=?",
                (trace.execution_id,),
            )
    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        with store.transaction() as connection:
            connection.execute(
                "update execution_replay_runs set status='MISMATCH' where replay_id=?",
                (first.replay_id,),
            )


def test_replay_fails_closed_before_recommendation_when_version_changed(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("WB_RND_CODE_COMMIT", "original-commit")
    store = _store(tmp_path)
    _request, _response, trace = _record(store)
    monkeypatch.setenv("WB_RND_CODE_COMMIT", "changed-commit")
    called = False

    def must_not_run(_request):
        nonlocal called
        called = True
        raise AssertionError("recommendation runner must not execute")

    result = SessionReplayLedger(store, recommendation_runner=must_not_run).replay(
        trace.execution_id
    )

    assert called is False
    assert result.status == "VERSION_MISMATCH"
    assert result.input_match is True
    assert result.version_match is False
    assert result.output_match is None
    assert "code_commit" in result.mismatch_fields
    assert result.actual_output_sha256 is None


def test_replay_fails_closed_when_code_identity_is_unresolved(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("WB_RND_CODE_COMMIT", raising=False)
    monkeypatch.setattr(
        "wellnessbox_rnd.interim.execution_identity.resolve_code_commit",
        lambda _repository_root=None: ("unresolved", "unresolved"),
    )
    store = _store(tmp_path)
    _request, _response, trace = _record(store)
    called = False

    def must_not_run(_request):
        nonlocal called
        called = True
        raise AssertionError("recommendation runner must not execute")

    result = SessionReplayLedger(store, recommendation_runner=must_not_run).replay(
        trace.execution_id
    )

    assert called is False
    assert result.status == "VERSION_MISMATCH"
    assert result.version_match is False
    assert result.output_match is None
    assert result.mismatch_fields == ["code_commit"]


def test_replay_reports_stable_output_mismatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WB_RND_CODE_COMMIT", "replay-output-test")
    store = _store(tmp_path)
    request, _response, trace = _record(store)

    def changed_runner(value: RecommendationRequest):
        assert value == request
        response = recommend(value)
        return response.model_copy(update={"follow_up_window_days": 90})

    result = SessionReplayLedger(store, recommendation_runner=changed_runner).replay(
        trace.execution_id
    )

    assert result.status == "MISMATCH"
    assert result.input_match is True
    assert result.version_match is True
    assert result.output_match is False
    assert result.expected_output_sha256 != result.actual_output_sha256
    assert "follow_up_window_days" in result.mismatch_fields


def test_replay_records_runner_failure_without_exposing_error_details(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("WB_RND_CODE_COMMIT", "replay-runner-failure-test")
    store = _store(tmp_path)
    _request, _response, trace = _record(store)

    def failed_runner(_request):
        raise RuntimeError("private-upstream-detail")

    with pytest.raises(RuntimeError, match="private-upstream-detail"):
        SessionReplayLedger(store, recommendation_runner=failed_runner).replay(
            trace.execution_id
        )

    row = store.rows("select * from execution_replay_runs")[0]
    assert row["status"] == "MISMATCH"
    assert row["output_match"] == 0
    assert row["actual_output_sha256"] is None
    assert json.loads(row["mismatch_fields_json"]) == ["recommendation_execution"]
    assert "private-upstream-detail" not in "\n".join(str(value) for value in row)


def test_authenticated_replay_api_lists_sessions_and_returns_bounded_result(
    tmp_path, monkeypatch
) -> None:
    database = tmp_path / "session-replay-api.sqlite3"
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(database))
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setenv("WB_RND_CODE_COMMIT", "replay-api-test")
    client = TestClient(app)
    recommendation = client.post("/v1/recommend", json=_payload())
    execution_id = recommendation.json()["execution_id"]

    assert client.get("/v1/interim/executions").status_code == 401
    listed = client.get(
        "/v1/interim/executions?limit=10",
        headers={"x-wb-rnd-token": "test-token"},
    )
    replayed = client.post(
        f"/v1/interim/executions/{execution_id}/replay",
        headers={"x-wb-rnd-token": "test-token"},
    )
    missing = client.post(
        "/v1/interim/executions/exec_00000000000000000000000000000000/replay",
        headers={"x-wb-rnd-token": "test-token"},
    )
    invalid = client.post(
        "/v1/interim/executions/exec_invalid/replay",
        headers={"x-wb-rnd-token": "test-token"},
    )

    assert recommendation.status_code == 200
    assert listed.status_code == 200
    assert listed.json()["total_saved_sessions"] == 1
    assert listed.json()["replayable_sessions"] == 1
    assert listed.json()["items"][0]["execution_id"] == execution_id
    assert replayed.status_code == 200
    assert replayed.json()["status"] == "MATCH"
    assert replayed.json()["input_match"] is True
    assert replayed.json()["version_match"] is True
    assert replayed.json()["output_match"] is True
    assert "request" not in replayed.json()
    assert "response" not in replayed.json()
    assert missing.status_code == 404
    assert invalid.status_code == 422
