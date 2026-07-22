from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.interim.device_evaluation import (
    DeviceRecommendationAssessmentRequest,
    assess_device_recommendation,
    calculate_device_score_changes,
)
from wellnessbox_rnd.interim.store import InterimStore


def _recommendation_payload(*, sleep_hours: float) -> dict[str, object]:
    return {
        "request_id": "device-followup-subject-001",
        "plan_id": "plan_device_followup_001",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": "usr_0123456789abcdef",
            "profile": {},
        },
        "user_profile": {
            "age": 41,
            "biological_sex": "female",
            "pregnant": False,
        },
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
    *, phase: str, sleep_hours: float, data_class: str = "SIMULATED_DEVICE_SESSION"
) -> DeviceRecommendationAssessmentRequest:
    return DeviceRecommendationAssessmentRequest.model_validate(
        {
            "assessment_id": f"device_assessment_{phase.lower()}_001",
            "phase": phase,
            "baseline_assessment_id": (
                None if phase == "BASELINE" else "device_assessment_baseline_001"
            ),
            "data_class": data_class,
            "session_origin": (
                "SIMULATION_FIXTURE"
                if data_class == "SIMULATED_DEVICE_SESSION"
                else "DEVICE_PROVIDER"
            ),
            "recommendation_request": _recommendation_payload(
                sleep_hours=sleep_hours
            ),
        }
    )


def test_device_values_change_recommendation_score_and_followup(tmp_path) -> None:
    store = InterimStore(tmp_path / "device.sqlite3")
    store.migrate()

    baseline = assess_device_recommendation(
        _assessment(phase="BASELINE", sleep_hours=5.0), store=store
    )
    follow_up = assess_device_recommendation(
        _assessment(phase="FOLLOW_UP", sleep_hours=8.0), store=store
    )

    assert baseline.score_snapshot["magnesium_glycinate"]["wearable_adjustment"] == 4.0
    assert follow_up.sensor_changes["sleep_hours"] == {
        "baseline": 5.0,
        "follow_up": 8.0,
        "delta": 3.0,
    }
    assert (
        follow_up.score_changes["magnesium_glycinate"]["wearable_adjustment_delta"]
        == -4.0
    )
    assert store.scalar("select count(*) from device_recommendation_assessments") == 2


def test_score_changes_preserve_candidate_entry_exit_and_null_delta() -> None:
    changes = calculate_device_score_changes(
        {
            "exited": {
                "wearable_adjustment": 4.0,
                "cgm_adjustment": 0.0,
                "total": 20.0,
            }
        },
        {
            "entered": {
                "wearable_adjustment": 0.0,
                "cgm_adjustment": 3.0,
                "total": 19.0,
            }
        },
    )

    assert changes["exited"] == {
        "selected_at_baseline": True,
        "selected_at_follow_up": False,
        "wearable_adjustment_delta": None,
        "cgm_adjustment_delta": None,
        "total_delta": None,
    }
    assert changes["entered"] == {
        "selected_at_baseline": False,
        "selected_at_follow_up": True,
        "wearable_adjustment_delta": None,
        "cgm_adjustment_delta": None,
        "total_delta": None,
    }


def test_exact_replay_deduplicates_and_identity_conflict_fails(tmp_path) -> None:
    store = InterimStore(tmp_path / "device.sqlite3")
    store.migrate()
    payload = _assessment(phase="BASELINE", sleep_hours=5.0)

    first = assess_device_recommendation(payload, store=store)
    second = assess_device_recommendation(payload, store=store)

    assert first.deduplicated is False
    assert second.deduplicated is True
    with pytest.raises(ValueError, match="device_assessment_identity_conflict"):
        assess_device_recommendation(
            payload.model_copy(
                update={
                    "recommendation_request": payload.recommendation_request.model_copy(
                        update={"request_id": "different-subject"}
                    )
                }
            ),
            store=store,
        )


@pytest.mark.parametrize(
    ("data_class", "origin"),
    [
        ("PRODUCTION_DEVICE_SESSION", "SIMULATION_FIXTURE"),
        ("SIMULATED_DEVICE_SESSION", "DEVICE_PROVIDER"),
    ],
)
def test_device_origin_and_data_class_cannot_be_mislabeled(
    data_class: str, origin: str
) -> None:
    with pytest.raises(ValidationError, match="device_session_origin_data_class_mismatch"):
        DeviceRecommendationAssessmentRequest.model_validate(
            {
                "assessment_id": "device_assessment_boundary_001",
                "phase": "BASELINE",
                "data_class": data_class,
                "session_origin": origin,
                "recommendation_request": _recommendation_payload(sleep_hours=5.0),
            }
        )


def test_followup_cannot_cross_data_class(tmp_path) -> None:
    store = InterimStore(tmp_path / "device.sqlite3")
    store.migrate()
    assess_device_recommendation(
        _assessment(phase="BASELINE", sleep_hours=5.0), store=store
    )

    with pytest.raises(ValueError, match="device_follow_up_data_class_mismatch"):
        assess_device_recommendation(
            _assessment(
                phase="FOLLOW_UP",
                sleep_hours=8.0,
                data_class="PRODUCTION_DEVICE_SESSION",
            ),
            store=store,
        )


def test_followup_requires_same_explicit_subject(tmp_path) -> None:
    store = InterimStore(tmp_path / "device.sqlite3")
    store.migrate()
    assess_device_recommendation(
        _assessment(phase="BASELINE", sleep_hours=5.0), store=store
    )
    follow_up = _assessment(phase="FOLLOW_UP", sleep_hours=8.0)
    different_subject = follow_up.recommendation_request.model_copy(
        update={
            "source_profile": follow_up.recommendation_request.source_profile.model_copy(
                update={"subject_id": "usr_fedcba9876543210"}
            )
        }
    )

    with pytest.raises(ValueError, match="device_follow_up_profile_mismatch"):
        assess_device_recommendation(
            follow_up.model_copy(update={"recommendation_request": different_subject}),
            store=store,
        )


def test_explicit_subject_and_all_used_source_storage_consent_are_required() -> None:
    payload = {
        "assessment_id": "device_assessment_subject_boundary",
        "phase": "BASELINE",
        "data_class": "SIMULATED_DEVICE_SESSION",
        "session_origin": "SIMULATION_FIXTURE",
        "recommendation_request": _recommendation_payload(sleep_hours=5.0),
    }
    payload["recommendation_request"].pop("source_profile")
    with pytest.raises(ValidationError, match="device_assessment_requires_explicit_subject_id"):
        DeviceRecommendationAssessmentRequest.model_validate(payload)

    payload["recommendation_request"] = _recommendation_payload(sleep_hours=5.0)
    payload["recommendation_request"]["data_source_consents"]["survey"][
        "allow_persistent_storage"
    ] = False
    with pytest.raises(
        ValidationError,
        match="device_assessment_used_source_storage_consent_required",
    ):
        DeviceRecommendationAssessmentRequest.model_validate(payload)


def test_device_assessment_rows_are_append_only(tmp_path) -> None:
    store = InterimStore(tmp_path / "device.sqlite3")
    store.migrate()
    assess_device_recommendation(
        _assessment(phase="BASELINE", sleep_hours=5.0), store=store
    )

    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        with store.transaction() as connection:
            connection.execute(
                "update device_recommendation_assessments set phase='FOLLOW_UP'"
            )
    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        with store.transaction() as connection:
            connection.execute("delete from device_recommendation_assessments")


def test_authenticated_device_assessment_api(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setenv("WB_RND_INTERIM_DATABASE", str(tmp_path / "api.sqlite3"))
    client = TestClient(app)
    payload = {
        "assessment_id": "device_assessment_api_boundary",
        "phase": "BASELINE",
        "data_class": "SIMULATED_DEVICE_SESSION",
        "session_origin": "SIMULATION_FIXTURE",
        "recommendation_request": _recommendation_payload(sleep_hours=5.0),
    }

    denied = client.post("/v1/interim/device-assessments", json=payload)
    accepted = client.post(
        "/v1/interim/device-assessments",
        json=payload,
        headers={"x-wb-rnd-token": "test-token"},
    )

    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["data_class"] == "SIMULATED_DEVICE_SESSION"
    client.close()
