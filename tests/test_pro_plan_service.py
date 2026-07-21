import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.inference_api.main import app
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


def _enroll(store: InterimStore) -> dict[str, object]:
    return enroll_pro_plan_v1(
        store,
        recommendation_request=_recommendation_request(),
        instrument="PSQI",
        item_scores=[2, 2, 2, 2, 2, 2, 2],
        observed_at=datetime(2026, 1, 1, tzinfo=UTC),
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
