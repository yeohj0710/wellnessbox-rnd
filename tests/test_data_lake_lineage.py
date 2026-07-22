from __future__ import annotations

import json
from copy import deepcopy

import pytest

from wellnessbox_rnd.interim.data_lake import (
    ConsentStorageDeniedError,
    ExecutionLedger,
    IdempotencyConflictError,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

SUBJECT_ID = "usr_0123456789abcdef0123456789abcdef"


def _payload(*, age: int = 41, allow_survey_storage: bool = True) -> dict[str, object]:
    return {
        "request_id": f"lineage-{age}-{int(allow_survey_storage)}",
        "source_profile": {
            "schema_version": "wellnessbox.chat.UserProfile.v1",
            "subject_id": SUBJECT_ID,
            "profile": {
                "name": "계보 검증 사용자",
                "age": age,
                "sex": "female",
                "goals": ["sleep"],
            },
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


def _request(*, age: int = 41, allow_survey_storage: bool = True) -> RecommendationRequest:
    return RecommendationRequest.model_validate(
        _payload(age=age, allow_survey_storage=allow_survey_storage)
    )


def _store(tmp_path) -> InterimStore:
    store = InterimStore(tmp_path / "lineage.sqlite3")
    store.migrate()
    return store


def _record(
    store: InterimStore,
    *,
    age: int = 41,
    allow_survey_storage: bool = True,
):
    request = _request(age=age, allow_survey_storage=allow_survey_storage)
    response = recommend(request)
    return ExecutionLedger(store).record_recommendation(
        request=request,
        response=response,
    )


def test_profile_and_consent_snapshots_are_versioned_and_deduplicated(tmp_path) -> None:
    store = _store(tmp_path)

    first = _record(store, age=41)
    duplicate = _record(store, age=41)
    changed = _record(store, age=42)

    assert first.profile_id == duplicate.profile_id == changed.profile_id == SUBJECT_ID
    assert first.profile_version == duplicate.profile_version == 1
    assert changed.profile_version == 2
    assert first.profile_snapshot_id == duplicate.profile_snapshot_id
    assert changed.profile_snapshot_id != first.profile_snapshot_id
    assert first.consent_version == duplicate.consent_version == changed.consent_version == 1
    assert store.scalar("select count(*) from profile_snapshots") == 2
    assert store.scalar("select count(*) from consent_snapshots") == 1
    assert store.scalar("select count(*) from executions") == 3


def test_recommendation_and_optimization_events_retain_plan_id(tmp_path) -> None:
    store = _store(tmp_path)
    request = _request()
    response = recommend(request)

    trace = ExecutionLedger(store).record_recommendation(
        request=request,
        response=response,
    )

    core = {
        event.event_type.value: event.payload
        for event in trace.events
        if event.event_type.value in {"recommendation", "optimization"}
    }
    assert core["recommendation"]["plan_id"] == request.plan_id
    assert core["optimization"]["plan_id"] == request.plan_id


def test_record_recommendation_rejects_response_plan_mismatch(tmp_path) -> None:
    store = _store(tmp_path)
    request = _request()
    response = recommend(request).model_copy(update={"plan_id": "plan_other"})

    with pytest.raises(ValueError, match="recommendation_plan_id_mismatch"):
        ExecutionLedger(store).record_recommendation(request=request, response=response)


def test_consent_change_versions_without_rewriting_unchanged_profile(tmp_path) -> None:
    store = _store(tmp_path)
    first = _record(store, allow_survey_storage=True)
    denied = _record(store, allow_survey_storage=False)

    assert first.profile_version == 1
    assert denied.profile_snapshot_id is None
    assert denied.profile_version is None
    assert first.consent_version == 1
    assert denied.consent_version == 2
    assert store.scalar("select count(*) from profile_snapshots") == 1
    assert store.scalar("select count(*) from consent_snapshots") == 2


def test_denied_profile_payload_is_not_persisted_but_consent_is_audited(tmp_path) -> None:
    store = _store(tmp_path)
    payload = _payload(allow_survey_storage=False)
    payload["request_id"] = "SENSITIVE-REQUEST-ID-DO-NOT-STORE"
    payload["medications"] = [{"name": "warfarin"}]
    payload["source_profile"]["profile"]["medications"] = ["warfarin"]  # type: ignore[index]
    request = RecommendationRequest.model_validate(payload)
    trace = ExecutionLedger(store).record_recommendation(
        request=request,
        response=recommend(request),
    )

    assert trace.profile_snapshot_id is None
    assert trace.profile_version is None
    assert trace.request_id != "SENSITIVE-REQUEST-ID-DO-NOT-STORE"
    assert trace.request_id.startswith("request_")
    assert store.scalar("select count(*) from profile_snapshots") == 0
    assert store.scalar("select count(*) from consent_snapshots") == 1
    persisted_payloads = [
        row[0]
        for table in ("consent_snapshots", "execution_events")
        for row in store.rows(f"select payload_json from {table}")
    ]
    persisted_text = "\n".join(persisted_payloads)
    assert "SENSITIVE-REQUEST-ID-DO-NOT-STORE" not in persisted_text
    assert "warfarin" not in persisted_text
    assert all(
        event.payload == {"storage_scope": "metadata_only"}
        for event in trace.events
    )


def test_laboratory_observation_is_partitioned_by_its_own_source_consent(tmp_path) -> None:
    store = _store(tmp_path)
    payload = _payload()
    payload["input_availability"]["nhis"] = True  # type: ignore[index]
    payload["laboratory_observations"] = [
        {
            "code": "NHIS-PRIVATE-LAB",
            "value": 101,
            "unit": "mg/dL",
            "reference_range": {"low": 70, "high": 99},
            "measured_at": "2026-07-15T09:00:00+09:00",
            "source": "nhis",
        }
    ]
    request = RecommendationRequest.model_validate(payload)

    trace = ExecutionLedger(store).record_recommendation(
        request=request,
        response=recommend(request),
    )

    assert trace.profile_snapshot_id is not None
    stored = json.loads(
        store.rows(
            "select payload_json from profile_snapshots where profile_snapshot_id=?",
            (trace.profile_snapshot_id,),
        )[0][0]
    )
    assert stored["persisted_sources"] == {"survey": stored["persisted_sources"]["survey"]}
    assert "NHIS-PRIVATE-LAB" not in json.dumps(stored, ensure_ascii=False)


def test_sensor_snapshot_is_partitioned_by_each_source_storage_consent(tmp_path) -> None:
    store = _store(tmp_path)
    payload = _payload()
    payload["input_availability"].update(  # type: ignore[union-attr]
        {"wearable": True, "cgm": True, "genetic": True}
    )
    payload["data_source_consents"]["wearable"] = {  # type: ignore[index]
        "use_for_recommendation": True,
        "allow_persistent_storage": True,
    }
    payload["sensor_genetic_snapshot"] = {
        "wearable_available": True,
        "cgm_available": True,
        "genetic_available": True,
        "sleep_hours": 5.75,
        "steps": 4321,
        "resting_heart_rate": 67,
        "mean_glucose_mg_dl": 143,
        "time_in_range_pct": 42,
        "post_meal_spike_concern": True,
        "genetic_tags": ["private_genetic_tag"],
        "genetic_variants": [
            {
                "gene_symbol": "LPL",
                "variant_id": "rs328",
                "genotype": "C/G",
                "interpretation": "increased_risk",
                "interpretation_criterion": "private-panel-v1",
                "testing_laboratory": "Private Genetics Lab",
                "tested_on": "2026-06-30",
            }
        ],
    }
    request = RecommendationRequest.model_validate(payload)

    trace = ExecutionLedger(store).record_recommendation(
        request=request,
        response=recommend(request),
    )

    stored = json.loads(
        store.rows(
            "select payload_json from profile_snapshots where profile_snapshot_id=?",
            (trace.profile_snapshot_id,),
        )[0][0]
    )
    sources = stored["persisted_sources"]
    assert sources["wearable"]["sensor_genetic_snapshot"] == {
        "sleep_hours": 5.75,
        "steps": 4321,
        "resting_heart_rate": 67,
    }
    assert "cgm" not in sources
    assert "genetic" not in sources
    stored_text = json.dumps(stored, ensure_ascii=False)
    assert "143" not in stored_text
    assert "private_genetic_tag" not in stored_text
    assert "private-panel-v1" not in stored_text
    assert "Private Genetics Lab" not in stored_text


def test_core_and_delayed_events_share_the_response_execution_id(tmp_path) -> None:
    store = _store(tmp_path)
    trace = _record(store)
    ledger = ExecutionLedger(store)

    conversation = ledger.append_event(
        execution_id=trace.execution_id,
        event_type="conversation",
        source="survey",
        idempotency_key="conversation-turn-1",
        payload={"turn_id": "turn-1", "intent": "sleep_question"},
    )
    followup = ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="followup-week-2",
        payload={"timepoint_weeks": 2, "status": "received"},
    )
    complete = ledger.get_trace(trace.execution_id)

    assert trace.execution_id == trace.response_execution_id
    assert conversation.event.execution_id == trace.execution_id
    assert followup.event.execution_id == trace.execution_id
    assert [event.event_type for event in complete.events] == [
        "recommendation",
        "safety",
        "optimization",
        "conversation",
        "followup_evaluation",
    ]
    assert {event.execution_id for event in complete.events} == {trace.execution_id}


def test_delayed_event_requires_saved_storage_consent(tmp_path) -> None:
    store = _store(tmp_path)
    trace = _record(store, allow_survey_storage=False)

    with pytest.raises(ConsentStorageDeniedError, match="survey"):
        ExecutionLedger(store).append_event(
            execution_id=trace.execution_id,
            event_type="conversation",
            source="survey",
            idempotency_key="conversation-denied",
            payload={"text": "must not persist"},
        )

    assert store.scalar(
        "select count(*) from execution_events where event_type='conversation'"
    ) == 0


def test_delayed_event_requires_latest_storage_consent(tmp_path) -> None:
    store = _store(tmp_path)
    allowed = _record(store, allow_survey_storage=True)
    withdrawn = _record(store, allow_survey_storage=False)

    assert withdrawn.consent_version == allowed.consent_version + 1
    with pytest.raises(ConsentStorageDeniedError):
        ExecutionLedger(store).append_event(
            execution_id=allowed.execution_id,
            event_type="conversation",
            source="survey",
            idempotency_key="conversation-after-withdrawal",
            payload={"message": "must not persist"},
        )
    assert store.scalar(
        "select count(*) from execution_events where event_type='conversation'"
    ) == 0


def test_reused_denied_consent_snapshot_becomes_active_again(tmp_path) -> None:
    store = _store(tmp_path)
    first_denial = _record(store, allow_survey_storage=False)
    allowed = _record(store, allow_survey_storage=True)
    second_denial = _record(store, allow_survey_storage=False)

    assert second_denial.consent_snapshot_id == first_denial.consent_snapshot_id
    assert second_denial.consent_version == first_denial.consent_version
    assert store.scalar(
        "select consent_snapshot_id from active_profile_consents where profile_id=?",
        (allowed.profile_id,),
    ) == first_denial.consent_snapshot_id
    with pytest.raises(ConsentStorageDeniedError):
        ExecutionLedger(store).append_event(
            execution_id=allowed.execution_id,
            event_type="conversation",
            source="survey",
            idempotency_key="conversation-after-repeat-withdrawal",
            payload={"message": "must not persist"},
        )


def test_conversation_cannot_relabel_source_to_bypass_survey_storage_consent(
    tmp_path,
) -> None:
    store = _store(tmp_path)
    payload = _payload(allow_survey_storage=False)
    payload["data_source_consents"]["nhis"][  # type: ignore[index]
        "allow_persistent_storage"
    ] = True
    request = RecommendationRequest.model_validate(payload)
    trace = ExecutionLedger(store).record_recommendation(
        request=request,
        response=recommend(request),
    )

    with pytest.raises(ValueError, match="conversation_event_source_must_be_survey"):
        ExecutionLedger(store).append_event(
            execution_id=trace.execution_id,
            event_type="conversation",
            source="nhis",
            idempotency_key="conversation-source-bypass",
            payload={"text": "must not persist"},
        )

    assert store.scalar(
        "select count(*) from execution_events where event_type='conversation'"
    ) == 0


def test_delayed_event_replay_is_idempotent_and_conflicts_fail_closed(tmp_path) -> None:
    store = _store(tmp_path)
    trace = _record(store)
    ledger = ExecutionLedger(store)
    arguments = {
        "execution_id": trace.execution_id,
        "event_type": "conversation",
        "source": "survey",
        "idempotency_key": "turn-1",
        "payload": {"intent": "sleep_question"},
    }

    first = ledger.append_event(**arguments)
    duplicate = ledger.append_event(**deepcopy(arguments))

    assert duplicate.deduplicated is True
    assert duplicate.event.event_id == first.event.event_id
    with pytest.raises(IdempotencyConflictError):
        ledger.append_event(**(arguments | {"payload": {"intent": "changed"}}))
    assert store.scalar(
        "select count(*) from execution_events where event_type='conversation'"
    ) == 1


def test_delayed_event_replay_with_changed_source_fails_closed(tmp_path) -> None:
    store = _store(tmp_path)
    payload = _payload()
    payload["data_source_consents"]["nhis"]["allow_persistent_storage"] = True  # type: ignore[index]
    request = RecommendationRequest.model_validate(payload)
    trace = ExecutionLedger(store).record_recommendation(
        request=request,
        response=recommend(request),
    )
    ledger = ExecutionLedger(store)
    arguments = {
        "execution_id": trace.execution_id,
        "event_type": "followup_evaluation",
        "source": "survey",
        "idempotency_key": "followup-1",
        "payload": {"week": 2, "sleep_score": 7},
    }

    first = ledger.append_event(**arguments)

    with pytest.raises(IdempotencyConflictError):
        ledger.append_event(**(arguments | {"source": "nhis"}))
    assert ledger.get_trace(trace.execution_id).events[-1].event_id == first.event.event_id
    assert ledger.get_trace(trace.execution_id).events[-1].source.value == "survey"
