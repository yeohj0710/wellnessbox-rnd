import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.inference_api.main import app
from wellnessbox_rnd.interim.agent import BoundedAgent
from wellnessbox_rnd.interim.data_lake import IdempotencyConflictError
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.pro_runtime import (
    load_pro_runtime_reference_v1,
    score_and_standardize_runtime_pro_v1,
)
from wellnessbox_rnd.orchestration.pro_plan_service import (
    enroll_pro_plan_v1,
    record_or_correct_pro_followup_v1,
)


def _store(tmp_path) -> InterimStore:
    store = InterimStore(tmp_path / "pro-plan.sqlite3")
    store.migrate()
    return store


def _recommendation_request() -> dict[str, object]:
    payload = json.loads(
        Path("data/samples/api_recommend_start_plan_request_v1.json").read_text(
            encoding="utf-8"
        )
    )
    payload.update(
        {
            "request_id": "runtime-pro-plan-request",
            "plan_id": "plan_runtime_001",
            "source_profile": {
                "schema_version": "wellnessbox.chat.UserProfile.v1",
                "subject_id": "usr_0123456789abcdef",
                "profile": {"age": 41, "sex": "female", "goals": ["sleep"]},
            },
            "data_source_consents": {
                "survey": {
                    "use_for_recommendation": True,
                    "allow_persistent_storage": True,
                }
            },
        }
    )
    return payload


def _enroll(
    store: InterimStore,
    *,
    data_class: str = "SYNTHETIC_OUTCOME_PROXY",
) -> dict[str, object]:
    return enroll_pro_plan_v1(
        store,
        recommendation_request=_recommendation_request(),
        instrument="PSQI",
        item_scores=[2, 2, 2, 2, 2, 2, 2],
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        data_class=data_class,
    )


def test_runtime_reference_is_explicit_synthetic_proxy() -> None:
    contract = load_pro_runtime_reference_v1()
    assert contract["data_class"] == "SYNTHETIC_OUTCOME_PROXY"
    assert [item["instrument"] for item in contract["instruments"]] == [
        "PSQI",
        "ISI",
        "PSS10",
    ]
    assert "not clinical norms" in contract["limitation"]


@pytest.mark.parametrize(
    ("instrument", "item_scores"),
    [("PSQI", [1] * 7), ("ISI", [1] * 7), ("PSS10", [1] * 10)],
)
def test_runtime_scoring_reuses_versioned_contract(instrument, item_scores) -> None:
    score, standardized = score_and_standardize_runtime_pro_v1(
        instrument, item_scores
    )
    assert score.instrument == instrument
    assert standardized.instrument == instrument
    assert standardized.baseline_distribution.data_class == "SYNTHETIC_OUTCOME_PROXY"


def test_runtime_scoring_rejects_wrong_item_count_and_range() -> None:
    with pytest.raises(ValueError, match="item_count"):
        score_and_standardize_runtime_pro_v1("PSQI", [1] * 6)
    with pytest.raises(ValueError, match="item_range"):
        score_and_standardize_runtime_pro_v1("PSQI", [4] * 7)


def test_enrollment_persists_one_bound_baseline_and_core_plan_ids(tmp_path) -> None:
    store = _store(tmp_path)
    result = _enroll(store)
    rows = store.rows(
        """select event_type, payload_json from execution_events
        where execution_id=? order by event_index""",
        (result["execution_id"],),
    )
    payloads = {row["event_type"]: json.loads(row["payload_json"]) for row in rows}
    assert result["plan_id"] == "plan_runtime_001"
    assert payloads["recommendation"]["plan_id"] == result["plan_id"]
    assert payloads["optimization"]["plan_id"] == result["plan_id"]
    assert payloads["followup_evaluation"]["plan_id"] == result["plan_id"]
    assert payloads["followup_evaluation"]["timepoint"] == "pre_intake"


def test_enrollment_retry_reuses_execution_and_baseline(tmp_path) -> None:
    store = _store(tmp_path)
    first = _enroll(store)
    second = _enroll(store)

    assert second["deduplicated"] is True
    assert second["execution_id"] == first["execution_id"]
    assert second["baseline_event_id"] == first["baseline_event_id"]
    assert store.scalar("select count(*) from executions") == 1


@pytest.mark.parametrize(
    ("item_scores", "observed_at"),
    [
        ([1] * 7, datetime(2026, 1, 1, tzinfo=UTC)),
        ([2] * 7, datetime(2026, 1, 2, tzinfo=UTC)),
    ],
)
def test_enrollment_retry_rejects_changed_baseline_identity(
    tmp_path,
    item_scores,
    observed_at,
) -> None:
    store = _store(tmp_path)
    _enroll(store)

    with pytest.raises(IdempotencyConflictError, match="baseline_conflict"):
        enroll_pro_plan_v1(
            store,
            recommendation_request=_recommendation_request(),
            instrument="PSQI",
            item_scores=item_scores,
            observed_at=observed_at,
        )
    assert store.scalar("select count(*) from executions") == 1


def test_invalid_baseline_does_not_leave_orphan_execution(tmp_path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="item_count"):
        enroll_pro_plan_v1(
            store,
            recommendation_request=_recommendation_request(),
            instrument="PSQI",
            item_scores=[1] * 6,
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    assert store.scalar("select count(*) from executions") == 0


def test_followup_create_then_same_timepoint_correction_recalculates(tmp_path) -> None:
    store = _store(tmp_path)
    enrolled = _enroll(store)
    common = {
        "execution_id": enrolled["execution_id"],
        "profile_id": enrolled["profile_id"],
        "plan_id": enrolled["plan_id"],
        "timepoint": "week_2",
        "instrument": "PSQI",
        "observed_at": datetime(2026, 1, 15, tzinfo=UTC),
        "actual_day_index": 14,
        "planned_dose_count": 14,
        "taken_dose_count": 13,
    }
    created = record_or_correct_pro_followup_v1(
        store, **common, item_scores=[1, 1, 1, 1, 1, 1, 1]
    )
    corrected = record_or_correct_pro_followup_v1(
        store, **common, item_scores=[0, 1, 1, 1, 1, 1, 1]
    )
    assert created["operation"] == "created"
    assert corrected["operation"] == "corrected"
    assert corrected["event_id"] == created["event_id"]
    assert corrected["raw_score"] != created["raw_score"]
    assert corrected["recalculated_immediately"] is True
    assert corrected["lineage"]["plan_id"] == enrolled["plan_id"]
    assert created["action_decision"]["action"] == "maintain"
    assert corrected["action_decision"]["action"] == "maintain"


def test_correction_can_change_adherence_without_changing_score(tmp_path) -> None:
    store = _store(tmp_path)
    enrolled = _enroll(store)
    common = {
        "execution_id": enrolled["execution_id"],
        "profile_id": enrolled["profile_id"],
        "plan_id": enrolled["plan_id"],
        "timepoint": "week_2",
        "instrument": "PSQI",
        "item_scores": [1] * 7,
        "observed_at": datetime(2026, 1, 15, tzinfo=UTC),
        "actual_day_index": 14,
        "planned_dose_count": 14,
    }
    created = record_or_correct_pro_followup_v1(
        store, **common, taken_dose_count=14
    )
    corrected = record_or_correct_pro_followup_v1(
        store, **common, taken_dose_count=10
    )
    assert corrected["operation"] == "corrected"
    assert corrected["raw_score"] == created["raw_score"]
    assert corrected["interpretation"]["adherence_rate"] == pytest.approx(10 / 14)


def test_followup_rejects_cross_plan_and_cross_instrument(tmp_path) -> None:
    store = _store(tmp_path)
    enrolled = _enroll(store)
    arguments = {
        "execution_id": enrolled["execution_id"],
        "profile_id": enrolled["profile_id"],
        "timepoint": "week_2",
        "item_scores": [1] * 7,
        "observed_at": datetime(2026, 1, 15, tzinfo=UTC),
        "actual_day_index": 14,
        "planned_dose_count": 14,
        "taken_dose_count": 14,
    }
    with pytest.raises(ValueError, match="plan_id_mismatch"):
        record_or_correct_pro_followup_v1(
            store, plan_id="plan_other", instrument="PSQI", **arguments
        )
    with pytest.raises(ValueError, match="instrument_mismatch"):
        record_or_correct_pro_followup_v1(
            store,
            plan_id=enrolled["plan_id"],
            instrument="ISI",
            **arguments,
        )


def test_pro_plan_and_followup_api_require_token_and_persist(tmp_path, monkeypatch) -> None:
    store = _store(tmp_path)
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr("apps.inference_api.routes.interim._store", lambda: store)
    client = TestClient(app)
    enrollment_payload = {
        "recommendation_request": _recommendation_request(),
        "baseline": {"instrument": "PSQI", "item_scores": [2] * 7},
        "observed_at": "2026-01-01T00:00:00Z",
    }
    assert client.post("/v1/interim/pro/plans", json=enrollment_payload).status_code == 401
    enrolled_response = client.post(
        "/v1/interim/pro/plans",
        headers={"x-wb-rnd-token": "test-token"},
        json=enrollment_payload,
    )
    assert enrolled_response.status_code == 200
    enrolled = enrolled_response.json()

    followup_response = client.post(
        "/v1/interim/pro/followups",
        headers={"x-wb-rnd-token": "test-token"},
        json={
            "execution_id": enrolled["execution_id"],
            "profile_id": enrolled["profile_id"],
            "plan_id": enrolled["plan_id"],
            "timepoint": "week_2",
            "answers": {"instrument": "PSQI", "item_scores": [1] * 7},
            "observed_at": "2026-01-15T00:00:00Z",
            "actual_day_index": 14,
            "planned_dose_count": 14,
            "taken_dose_count": 13,
        },
    )
    assert followup_response.status_code == 200
    assert followup_response.json()["operation"] == "created"
    assert followup_response.json()["action_decision"]["action"] == "maintain"
    assert followup_response.json()["next_job_decision"]["decision"] == "REEVALUATE_PLAN"
    corrected_payload = {
        "execution_id": enrolled["execution_id"],
        "profile_id": enrolled["profile_id"],
        "plan_id": enrolled["plan_id"],
        "timepoint": "week_2",
        "answers": {"instrument": "PSQI", "item_scores": [0, 1, 1, 1, 1, 1, 1]},
        "observed_at": "2026-01-15T00:00:00Z",
        "actual_day_index": 14,
        "planned_dose_count": 14,
        "taken_dose_count": 13,
    }
    corrected_response = client.post(
        "/v1/interim/pro/followups",
        headers={"x-wb-rnd-token": "test-token"},
        json=corrected_payload,
    )
    assert corrected_response.status_code == 200
    assert corrected_response.json()["operation"] == "corrected"
    assert corrected_response.json()["next_job_decision"]["deduplicated"] is False

    device_payload = {
        "session_id": "device_pro_plan_1",
        "profile_id": enrolled["profile_id"],
        "source": "W",
        "consent_scopes": ["device:write"],
        "execution_id": enrolled["execution_id"],
        "plan_id": enrolled["plan_id"],
        "payload": {
            "observed_at": "2026-01-16T00:00:00Z",
            "value": 7000,
            "unit": "steps",
            "timezone": "UTC",
            "source_record_id": "wearable-1",
        },
    }
    device_response = client.post(
        "/v1/interim/connectors/device",
        headers={"x-wb-rnd-token": "test-token"},
        json=device_payload,
    )
    assert device_response.status_code == 200
    assert device_response.json()["next_job_decision"]["reason_code"] == (
        "DEVICE_INPUT_RECEIVED"
    )
    invalid_response = client.post(
        "/v1/interim/connectors/device",
        headers={"x-wb-rnd-token": "test-token"},
        json=device_payload
        | {
            "session_id": "device_pro_plan_invalid",
            "payload": device_payload["payload"]
            | {"unit": "unknown", "source_record_id": "wearable-invalid-1"},
        },
    )
    assert invalid_response.status_code == 200
    assert invalid_response.json()["success"] is False
    assert "next_job_decision" not in invalid_response.json()
    assert store.scalar("select count(*) from workflow_jobs") == 3


def test_same_plan_api_accepts_real_world_outcome_data_class(tmp_path) -> None:
    store = _store(tmp_path)
    enrolled = _enroll(store, data_class="REAL_WORLD_OUTCOME")
    assert enrolled["baseline"]["data_class"] == "REAL_WORLD_OUTCOME"

    followed = record_or_correct_pro_followup_v1(
        store,
        execution_id=enrolled["execution_id"],
        profile_id=enrolled["profile_id"],
        plan_id=enrolled["plan_id"],
        timepoint="week_2",
        instrument="PSQI",
        item_scores=[3] * 7,
        observed_at=datetime(2026, 1, 15, tzinfo=UTC),
        actual_day_index=14,
        planned_dose_count=14,
        taken_dose_count=14,
    )

    assert followed["interpretation"]["baseline_event"]["data_class"] == (
        "REAL_WORLD_OUTCOME"
    )
    assert followed["interpretation"]["follow_up_event"]["data_class"] == (
        "REAL_WORLD_OUTCOME"
    )
    assert followed["action_decision"]["action"] == "re_optimize"


def test_serious_pro_followup_stops_plan_and_cancels_prior_next_job(
    tmp_path, monkeypatch
) -> None:
    store = _store(tmp_path)
    enrolled = _enroll(store)
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr("apps.inference_api.routes.interim._store", lambda: store)
    client = TestClient(app)
    headers = {"x-wb-rnd-token": "test-token"}
    common = {
        "execution_id": enrolled["execution_id"],
        "profile_id": enrolled["profile_id"],
        "plan_id": enrolled["plan_id"],
        "answers": {"instrument": "PSQI", "item_scores": [1] * 7},
        "planned_dose_count": 14,
        "taken_dose_count": 14,
    }
    first = client.post(
        "/v1/interim/pro/followups",
        headers=headers,
        json=common
        | {
            "timepoint": "week_2",
            "observed_at": "2026-01-15T00:00:00Z",
            "actual_day_index": 14,
        },
    )
    assert first.status_code == 200
    assert first.json()["next_job_decision"]["decision"] == "REEVALUATE_PLAN"

    serious = client.post(
        "/v1/interim/pro/followups",
        headers=headers,
        json=common
        | {
            "timepoint": "week_4",
            "observed_at": "2026-01-29T00:00:00Z",
            "actual_day_index": 28,
            "adverse_events": [
                {
                    "adverse_event_id": "ae_pro_serious",
                    "severity": "serious",
                    "relatedness": "possible",
                    "ongoing": True,
                }
            ],
        },
    )

    assert serious.status_code == 200
    assert serious.json()["action_decision"]["action"] == "stop"
    assert serious.json()["next_job_decision"]["plan_stopped"] is True
    assert store.scalar("select status from workflow_jobs") == "CANCELLED"
    assert store.scalar(
        "select count(*) from execution_events where idempotency_key='serious-ae:ae_pro_serious'"
    ) == 1


def test_serious_pro_conflict_does_not_persist_unstopped_followup(
    tmp_path, monkeypatch
) -> None:
    store = _store(tmp_path)
    enrolled = _enroll(store)
    BoundedAgent(store).record_adverse_event(
        run_id=None,
        arguments={
            "case_id": "ae_pro_conflict",
            "profile_id": enrolled["profile_id"],
            "execution_id": enrolled["execution_id"],
            "plan_id": enrolled["plan_id"],
            "serious": False,
            "observed_at": "2026-01-15T00:00:00Z",
        },
    )
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr("apps.inference_api.routes.interim._store", lambda: store)
    response = TestClient(app).post(
        "/v1/interim/pro/followups",
        headers={"x-wb-rnd-token": "test-token"},
        json={
            "execution_id": enrolled["execution_id"],
            "profile_id": enrolled["profile_id"],
            "plan_id": enrolled["plan_id"],
            "timepoint": "week_2",
            "answers": {"instrument": "PSQI", "item_scores": [1] * 7},
            "observed_at": "2026-01-15T00:00:00Z",
            "actual_day_index": 14,
            "planned_dose_count": 14,
            "taken_dose_count": 14,
            "adverse_events": [
                {
                    "adverse_event_id": "ae_pro_conflict",
                    "severity": "serious",
                    "relatedness": "possible",
                    "ongoing": True,
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "adverse_event_idempotency_payload_conflict"
    assert store.scalar(
        "select count(*) from execution_events "
        "where event_type='followup_evaluation' and idempotency_key like 'pro-followup:%'"
    ) == 0


def test_pro_correction_job_uses_stored_effective_observed_at(
    tmp_path, monkeypatch
) -> None:
    store = _store(tmp_path)
    enrolled = _enroll(store)
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr("apps.inference_api.routes.interim._store", lambda: store)
    client = TestClient(app)
    common = {
        "execution_id": enrolled["execution_id"],
        "profile_id": enrolled["profile_id"],
        "plan_id": enrolled["plan_id"],
        "timepoint": "week_2",
        "actual_day_index": 14,
        "planned_dose_count": 14,
        "taken_dose_count": 14,
    }
    headers = {"x-wb-rnd-token": "test-token"}
    created = client.post(
        "/v1/interim/pro/followups",
        headers=headers,
        json=common
        | {
            "answers": {"instrument": "PSQI", "item_scores": [1] * 7},
            "observed_at": "2026-01-15T00:00:00Z",
        },
    )
    corrected = client.post(
        "/v1/interim/pro/followups",
        headers=headers,
        json=common
        | {
            "answers": {"instrument": "PSQI", "item_scores": [0] * 7},
            "observed_at": "2026-02-15T00:00:00Z",
        },
    )

    assert created.status_code == corrected.status_code == 200
    job = corrected.json()["next_job_decision"]["next_job"]
    assert job["scheduled_at"] == "2026-01-15T00:00:00Z"
    assert job["payload"]["received_at"] == "2026-01-15T00:00:00+00:00"


def test_enrollment_retry_rejects_changed_data_class(tmp_path) -> None:
    store = _store(tmp_path)
    _enroll(store)

    with pytest.raises(IdempotencyConflictError, match="baseline_conflict"):
        _enroll(store, data_class="REAL_WORLD_OUTCOME")


def test_pro_plan_api_accepts_only_outcome_data_classes(tmp_path, monkeypatch) -> None:
    store = _store(tmp_path)
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr("apps.inference_api.routes.interim._store", lambda: store)
    client = TestClient(app)
    payload = {
        "recommendation_request": _recommendation_request(),
        "baseline": {"instrument": "PSQI", "item_scores": [2] * 7},
        "observed_at": "2026-01-01T00:00:00Z",
        "data_class": "REAL_WORLD_OUTCOME",
    }

    accepted = client.post(
        "/v1/interim/pro/plans",
        headers={"x-wb-rnd-token": "test-token"},
        json=payload,
    )
    assert accepted.status_code == 200
    assert accepted.json()["baseline"]["data_class"] == "REAL_WORLD_OUTCOME"
    drafts = client.get(
        "/v1/interim/admin/ai-drafts",
        headers={"x-wb-rnd-token": "test-token"},
    ).json()
    assert drafts["summary"]["pending"] == 1
    assert drafts["items"][0]["record_type"] == "actual_recommendation_review"
    assert drafts["items"][0]["rationale"]["source_execution_id"] == accepted.json()["execution_id"]

    payload["recommendation_request"]["request_id"] = "other-request"
    payload["recommendation_request"]["plan_id"] = "plan_other_001"
    payload["data_class"] = "PHARMACIST_GOLD"
    rejected = client.post(
        "/v1/interim/pro/plans",
        headers={"x-wb-rnd-token": "test-token"},
        json=payload,
    )
    assert rejected.status_code == 422
