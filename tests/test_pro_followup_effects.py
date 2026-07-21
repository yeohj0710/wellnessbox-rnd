from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.inference_api.main import app
from wellnessbox_rnd.interim.data_lake import ExecutionLedger
from wellnessbox_rnd.interim.data_mutation import DataMutationLedger
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.pro_correction import (
    PROCorrectionRecalculationResultV1,
    correct_and_recalculate_pro_followup_v1,
)
from wellnessbox_rnd.metrics.pro_followup import (
    PROFollowUpEventV1,
    interpret_pro_followup_effect_v1,
    is_versioned_pro_followup_payload_v1,
    load_pro_followup_interpretation_contract_v1,
)
from wellnessbox_rnd.metrics.pro_scoring import (
    PROBaselineScoreObservationV1,
    build_pro_baseline_distribution_v1,
    score_pro_instrument_response_v1,
    standardize_pro_instrument_score_v1,
)
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

SUBJECT_ID = "usr_1234567890abcdef1234567890abcdef"
SCHEDULED_DAYS = {
    "pre_intake": 0,
    "week_2": 14,
    "week_4": 28,
    "discontinuation": None,
}
ACTUAL_DAYS = {
    "pre_intake": 0,
    "week_2": 14,
    "week_4": 28,
    "discontinuation": 35,
}
CONTRACT_PATH = Path("data/contracts/pro_followup_interpretation_v1.json")
OBSERVED_AT = {
    "pre_intake": "2026-01-01T00:00:00Z",
    "week_2": "2026-01-15T00:00:00Z",
    "week_4": "2026-01-29T00:00:00Z",
    "discontinuation": "2026-02-05T00:00:00Z",
}


def _request() -> RecommendationRequest:
    return RecommendationRequest.model_validate(
        {
            "request_id": "op053-op054-followup",
            "plan_id": "plan_op053_001",
            "source_profile": {
                "schema_version": "wellnessbox.chat.UserProfile.v1",
                "subject_id": SUBJECT_ID,
                "profile": {"age": 41, "sex": "female", "goals": ["sleep"]},
            },
            "user_profile": {
                "age": 41,
                "biological_sex": "female",
                "pregnant": False,
            },
            "goals": ["sleep_support"],
            "data_source_consents": {
                "survey": {
                    "use_for_recommendation": True,
                    "allow_persistent_storage": True,
                },
                "nhis": {},
                "wearable": {},
                "cgm": {},
                "genetic": {},
            },
        }
    )


def test_strict_pro_event_rejects_plan_not_bound_to_recommendation(tmp_path) -> None:
    store, trace = _store_with_execution(tmp_path)

    with pytest.raises(ValueError, match="pro_followup_plan_id_mismatch"):
        ExecutionLedger(store).append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key="cross-plan-baseline",
            payload=_event_payload("pre_intake", 9, plan_id="plan_other"),
        )


def _psqi_score(raw_score: int):
    values = [0] * 7
    remaining = raw_score
    for index in range(7):
        values[index] = min(3, remaining)
        remaining -= values[index]
    return score_pro_instrument_response_v1(
        {
            "schema_version": "pro_instrument_response_v1",
            "instrument": "PSQI",
            "item_scores": values,
        }
    )


def _distribution(*, cohort_id: str = "op052-psqi-baseline"):
    return build_pro_baseline_distribution_v1(
        [
            PROBaselineScoreObservationV1(
                schema_version="pro_baseline_score_observation_v1",
                observation_role="BASELINE",
                score=_psqi_score(raw_score),
            )
            for raw_score in (6, 9, 12)
        ],
        cohort_id=cohort_id,
        data_class="SYNTHETIC_OUTCOME_PROXY",
    )


def _event_payload(
    timepoint: str,
    raw_score: int,
    *,
    plan_id: str = "plan_op053_001",
    planned: int = 14,
    taken: int = 14,
    adverse_events: list[dict[str, object]] | None = None,
    distribution_cohort_id: str = "op052-psqi-baseline",
) -> dict[str, object]:
    score = _psqi_score(raw_score)
    standardized = standardize_pro_instrument_score_v1(
        score,
        _distribution(cohort_id=distribution_cohort_id),
    )
    adherence = None
    if timepoint != "pre_intake":
        missed = planned - taken
        adherence = {
            "planned_dose_count": planned,
            "taken_dose_count": taken,
            "missed_dose_count": missed,
            "adherence_rate": round(taken / planned, 6),
        }
    return {
        "schema_version": "versioned_pro_followup_event_v1",
        "assessment_id": f"assessment_{timepoint}",
        "plan_id": plan_id,
        "data_class": "SYNTHETIC_OUTCOME_PROXY",
        "timepoint": timepoint,
        "scheduled_day_index": SCHEDULED_DAYS[timepoint],
        "actual_day_index": ACTUAL_DAYS[timepoint],
        "observed_at": OBSERVED_AT[timepoint],
        "instrument_scores": [score.model_dump(mode="json")],
        "standardized_scores": [standardized.model_dump(mode="json")],
        "adherence": adherence,
        "adverse_events": adverse_events or [],
        "discontinuation_reason": (
            "user_stopped_plan" if timepoint == "discontinuation" else None
        ),
    }


def _store_with_execution(tmp_path):
    store = InterimStore(tmp_path / "followup.sqlite3")
    store.migrate()
    request = _request()
    trace = ExecutionLedger(store).record_recommendation(
        request=request,
        response=recommend(request),
    )
    return store, trace


def test_followup_event_contract_reuses_versioned_score_trace() -> None:
    payload = _event_payload("week_2", 7, planned=14, taken=12)

    event = PROFollowUpEventV1.model_validate(payload)

    assert event.timepoint == "week_2"
    assert event.scheduled_day_index == 14
    assert event.instrument_scores[0].raw_score == 7
    assert event.standardized_scores[0].raw_score == 7
    assert event.adherence is not None
    assert event.adherence.missed_dose_count == 2
    assert event.adherence.adherence_rate == pytest.approx(0.857143, abs=1e-6)


def test_followup_interpretation_contract_fixes_schedule_policy_and_claim_scope(
    tmp_path: Path,
) -> None:
    contract = load_pro_followup_interpretation_contract_v1()

    assert contract.contract_version == "2026-07-17.1"
    assert contract.timepoint_order == [
        "pre_intake",
        "week_2",
        "week_4",
        "discontinuation",
    ]
    assert contract.scheduled_day_index_by_timepoint == SCHEDULED_DAYS
    assert contract.adherence.minimum_interpretable_rate == 0.8
    assert contract.policy_kind == "conservative_internal_interpretation_policy"
    assert "not a clinical cutoff" in contract.limitation
    assert contract.causal_effect_claim_allowed is False
    assert contract.persistence.table == "execution_events"

    changed = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    changed["adherence"]["minimum_interpretable_rate"] = 0.5
    changed_path = tmp_path / "changed-contract.json"
    changed_path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="policy_drift"):
        load_pro_followup_interpretation_contract_v1(changed_path)


def test_existing_execution_ledger_persists_all_four_timepoints_in_order(tmp_path) -> None:
    store, trace = _store_with_execution(tmp_path)
    ledger = ExecutionLedger(store)

    for timepoint, raw_score in (
        ("pre_intake", 10),
        ("week_2", 8),
        ("week_4", 7),
        ("discontinuation", 7),
    ):
        result = ledger.append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key=f"pro-{timepoint}",
            payload=_event_payload(timepoint, raw_score),
        )
        assert result.deduplicated is False

    stored = ledger.get_trace(trace.execution_id)
    followups = [
        event for event in stored.events if event.event_type == "followup_evaluation"
    ]
    assert [event.payload["timepoint"] for event in followups] == [
        "pre_intake",
        "week_2",
        "week_4",
        "discontinuation",
    ]
    assert all(event.execution_id == trace.execution_id for event in followups)
    assert store.scalar(
        "select count(*) from execution_events where event_type='followup_evaluation'"
    ) == 4


def test_generic_followup_with_shared_identity_keys_remains_legacy_compatible(
    tmp_path,
) -> None:
    store, trace = _store_with_execution(tmp_path)
    generic_payload = {
        "assessment_id": "legacy_assessment",
        "plan_id": "legacy_plan",
        "status": "received",
    }

    assert is_versioned_pro_followup_payload_v1(generic_payload) is False
    result = ExecutionLedger(store).append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="legacy-generic-followup",
        payload=generic_payload,
    )

    assert result.event.payload == generic_payload


def test_strict_pro_payload_cannot_be_persisted_as_conversation(tmp_path) -> None:
    store, trace = _store_with_execution(tmp_path)

    with pytest.raises(ValueError, match="followup_evaluation"):
        ExecutionLedger(store).append_event(
            execution_id=trace.execution_id,
            event_type="conversation",
            source="survey",
            idempotency_key="strict-pro-disguised-as-conversation",
            payload=_event_payload("week_2", 8),
        )


def test_execution_event_correction_cannot_convert_generic_event_to_strict_pro(
    tmp_path,
) -> None:
    store, trace = _store_with_execution(tmp_path)
    generic = ExecutionLedger(store).append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="legacy-generic-followup",
        payload={
            "assessment_id": "legacy_assessment",
            "plan_id": "legacy_plan",
            "status": "received",
        },
    )

    with pytest.raises(ValueError, match="cannot_change_contract_kind"):
        DataMutationLedger(store).apply(
            profile_id=SUBJECT_ID,
            target_type="execution_event",
            target_event_id=generic.event.event_id,
            operation="correction",
            idempotency_key="generic-to-pro",
            replacement_payload=_event_payload("week_2", 8),
        )


def test_followup_sequence_and_schema_fail_closed_inside_ledger(tmp_path) -> None:
    _store, trace = _store_with_execution(tmp_path)
    ledger = ExecutionLedger(_store)

    with pytest.raises(ValueError, match="pre_intake"):
        ledger.append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key="week-2-first",
            payload=_event_payload("week_2", 8),
        )

    baseline = PROFollowUpEventV1.model_validate(_event_payload("pre_intake", 10))
    changed_instance = baseline.model_copy(update={"scheduled_day_index": 999})
    with pytest.raises(ValidationError):
        ledger.append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key="changed-model",
            payload=changed_instance,
        )

    extra = _event_payload("pre_intake", 10)
    extra["unexpected"] = True
    with pytest.raises(ValidationError):
        ledger.append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key="extra-field",
            payload=extra,
        )

    missing_version = _event_payload("pre_intake", 10)
    missing_version.pop("schema_version")
    with pytest.raises(ValidationError):
        ledger.append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key="missing-version",
            payload=missing_version,
        )

    with pytest.raises(ValueError, match="source_must_be_survey"):
        ledger.append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="cgm",
            idempotency_key="wrong-source",
            payload=_event_payload("pre_intake", 10),
        )

    ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="valid-baseline",
        payload=_event_payload("pre_intake", 10),
    )
    with pytest.raises(ValueError, match="score_identity_mismatch"):
        ledger.append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key="different-distribution",
            payload=_event_payload(
                "week_2",
                8,
                distribution_cohort_id="different-baseline",
            ),
        )
    duplicate_assessment = _event_payload("week_2", 8)
    duplicate_assessment["assessment_id"] = "assessment_pre_intake"
    with pytest.raises(ValueError, match="duplicate_pro_followup_assessment_id"):
        ledger.append_event(
            execution_id=trace.execution_id,
            event_type="followup_evaluation",
            source="survey",
            idempotency_key="duplicate-assessment",
            payload=duplicate_assessment,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload["adherence"].update({"adherence_rate": 1.0}),
        lambda payload: payload["adherence"].update({"taken_dose_count": True}),
        lambda payload: payload.update({"scheduled_day_index": 28}),
        lambda payload: payload.update({"actual_day_index": 7}),
        lambda payload: payload["instrument_scores"].append(
            deepcopy(payload["instrument_scores"][0])
        ),
    ],
)
def test_followup_event_rejects_inconsistent_counts_schedule_and_scores(mutation) -> None:
    payload = _event_payload("week_2", 7, planned=14, taken=12)
    mutation(payload)

    with pytest.raises(ValidationError):
        PROFollowUpEventV1.model_validate(payload)


def test_execution_event_correction_cannot_remove_pro_contract(tmp_path) -> None:
    store, trace = _store_with_execution(tmp_path)
    stored = ExecutionLedger(store).append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="pro-pre-intake",
        payload=_event_payload("pre_intake", 10),
    )
    changed = _event_payload("pre_intake", 10)
    changed["scheduled_day_index"] = 999

    with pytest.raises(ValidationError):
        DataMutationLedger(store).apply(
            profile_id=SUBJECT_ID,
            target_type="execution_event",
            target_event_id=stored.event.event_id,
            operation="correction",
            idempotency_key="invalid-pro-correction",
            replacement_payload=changed,
        )


def test_execution_event_correction_preserves_identity_and_revalidates_scores(
    tmp_path,
) -> None:
    store, trace = _store_with_execution(tmp_path)
    ledger = ExecutionLedger(store)
    ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="pro-pre-intake",
        payload=_event_payload("pre_intake", 10),
    )
    week_2 = ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="pro-week-2",
        payload=_event_payload("week_2", 8),
    )

    with pytest.raises(ValueError, match="cannot_change_score_identity"):
        DataMutationLedger(store).apply(
            profile_id=SUBJECT_ID,
            target_type="execution_event",
            target_event_id=week_2.event.event_id,
            operation="correction",
            idempotency_key="change-week-2-distribution",
            replacement_payload=_event_payload(
                "week_2",
                7,
                distribution_cohort_id="different-baseline",
            ),
        )

    result = DataMutationLedger(store).apply(
        profile_id=SUBJECT_ID,
        target_type="execution_event",
        target_event_id=week_2.event.event_id,
        operation="correction",
        idempotency_key="correct-week-2-score",
        replacement_payload=_event_payload("week_2", 7),
    )

    assert result.deduplicated is False
    corrected = ledger.get_trace(trace.execution_id).events[-1]
    assert corrected.payload_state == "CORRECTED"
    assert corrected.payload["instrument_scores"][0]["raw_score"] == 7


def test_user_correction_recalculates_effect_and_links_recommendation_plan(tmp_path) -> None:
    store, trace = _store_with_execution(tmp_path)
    ledger = ExecutionLedger(store)
    baseline = ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="pro-pre-intake",
        payload=_event_payload("pre_intake", 10),
    )
    week_2 = ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="pro-week-2",
        payload=_event_payload("week_2", 8),
    )

    result = correct_and_recalculate_pro_followup_v1(
        store,
        execution_id=trace.execution_id,
        profile_id=SUBJECT_ID,
        target_event_id=week_2.event.event_id,
        idempotency_key="user-correct-week-2",
        replacement_payload=_event_payload("week_2", 7),
    )
    replay = correct_and_recalculate_pro_followup_v1(
        store,
        execution_id=trace.execution_id,
        profile_id=SUBJECT_ID,
        target_event_id=week_2.event.event_id,
        idempotency_key="user-correct-week-2",
        replacement_payload=_event_payload("week_2", 7),
    )

    assert result.recalculated_immediately is True
    assert result.interpretation.follow_up_event.instrument_scores[0].raw_score == 7
    assert result.interpretation.mean_health_z_change != interpret_pro_followup_effect_v1(
        _event_payload("pre_intake", 10), _event_payload("week_2", 8)
    ).mean_health_z_change
    assert result.lineage.plan_id == "plan_op053_001"
    assert result.lineage.baseline_event_id == baseline.event.event_id
    assert result.lineage.follow_up_event_id == week_2.event.event_id
    assert result.lineage.selected_ingredient_keys
    assert result.lineage.causal_effect_claim_allowed is False
    assert replay.mutation.deduplicated is True
    assert replay.interpretation == result.interpretation

    forged = result.model_dump(mode="json")
    forged["lineage"]["plan_id"] = "plan_forged"
    with pytest.raises(ValidationError):
        PROCorrectionRecalculationResultV1.model_validate(forged)


def test_pro_correction_api_returns_immediate_recalculation(
    tmp_path, monkeypatch
) -> None:
    store, trace = _store_with_execution(tmp_path)
    ledger = ExecutionLedger(store)
    ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="api-pre-intake",
        payload=_event_payload("pre_intake", 10),
    )
    week_2 = ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="api-week-2",
        payload=_event_payload("week_2", 8),
    )
    monkeypatch.setenv("WB_RND_INTERIM_INTERNAL_TOKEN", "test-token")
    monkeypatch.setattr("apps.inference_api.routes.interim._store", lambda: store)

    response = TestClient(app).post(
        "/v1/interim/pro/followups/correct-and-recalculate",
        headers={"x-wb-rnd-token": "test-token"},
        json={
            "execution_id": trace.execution_id,
            "profile_id": SUBJECT_ID,
            "target_event_id": week_2.event.event_id,
            "idempotency_key": "api-user-correction",
            "replacement_payload": _event_payload("week_2", 7),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recalculated_immediately"] is True
    assert body["interpretation"]["follow_up_event"]["instrument_scores"][0][
        "raw_score"
    ] == 7
    assert body["lineage"]["selected_ingredient_keys"]


def test_failed_recalculation_does_not_commit_correction(tmp_path) -> None:
    store, trace = _store_with_execution(tmp_path)
    ledger = ExecutionLedger(store)
    ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="atomic-baseline",
        payload=_event_payload("pre_intake", 10),
    )
    week_2 = ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key="atomic-week-2",
        payload=_event_payload("week_2", 8),
    )
    with store.transaction() as connection:
        connection.execute(
            "delete from execution_events where execution_id=? and event_type='optimization'",
            (trace.execution_id,),
        )

    with pytest.raises(ValueError, match="recommendation_lineage_events"):
        correct_and_recalculate_pro_followup_v1(
            store,
            execution_id=trace.execution_id,
            profile_id=SUBJECT_ID,
            target_event_id=week_2.event.event_id,
            idempotency_key="must-not-commit",
            replacement_payload=_event_payload("week_2", 7),
        )

    unchanged = next(
        event
        for event in ExecutionLedger(store).get_trace(trace.execution_id).events
        if event.event_id == week_2.event.event_id
    )
    assert unchanged.payload_state == "ACTIVE"
    assert unchanged.payload["instrument_scores"][0]["raw_score"] == 8
    assert store.scalar("select count(*) from event_mutations") == 0


def test_effect_interpretation_reflects_adherence_missed_doses_and_adverse_events() -> None:
    baseline = _event_payload("pre_intake", 10)
    clean = interpret_pro_followup_effect_v1(
        baseline,
        _event_payload("week_2", 7),
    )
    missed = interpret_pro_followup_effect_v1(
        baseline,
        _event_payload("week_2", 7, planned=14, taken=12),
    )
    low_adherence = interpret_pro_followup_effect_v1(
        baseline,
        _event_payload("week_2", 7, planned=14, taken=10),
    )
    adverse = interpret_pro_followup_effect_v1(
        baseline,
        _event_payload(
            "week_2",
            7,
            adverse_events=[
                {
                    "adverse_event_id": "ae_mild_001",
                    "severity": "mild",
                    "relatedness": "possible",
                    "ongoing": False,
                }
            ],
        ),
    )
    serious = interpret_pro_followup_effect_v1(
        baseline,
        _event_payload(
            "week_2",
            7,
            adverse_events=[
                {
                    "adverse_event_id": "ae_serious_001",
                    "severity": "serious",
                    "relatedness": "unknown",
                    "ongoing": True,
                }
            ],
        ),
    )

    assert clean.observed_change_status == "improved"
    assert clean.interpretation_status == "observed_change_interpretable"
    assert missed.interpretation_status == "limited_by_missed_doses"
    assert "missed_doses_present" in missed.interpretation_reason_codes
    assert low_adherence.interpretation_status == "limited_by_low_adherence"
    assert "adherence_below_80_percent" in low_adherence.interpretation_reason_codes
    assert adverse.interpretation_status == "safety_context_required"
    assert serious.interpretation_status == "safety_escalation_required"
    assert serious.serious_adverse_event_present is True
    assert {
        item.mean_health_z_change
        for item in (clean, missed, low_adherence, adverse, serious)
    } == {clean.mean_health_z_change}
    assert all(
        item.causal_effect_claim_allowed is False
        for item in (clean, missed, low_adherence, adverse, serious)
    )


def test_interpretation_rejects_cross_plan_distribution_and_output_mutation() -> None:
    baseline = _event_payload("pre_intake", 10)

    with pytest.raises(ValueError, match="plan"):
        interpret_pro_followup_effect_v1(
            baseline,
            _event_payload("week_2", 7, plan_id="plan_other"),
        )
    with pytest.raises(ValueError, match="distribution"):
        interpret_pro_followup_effect_v1(
            baseline,
            _event_payload(
                "week_2",
                7,
                distribution_cohort_id="different-baseline",
            ),
        )

    interpretation = interpret_pro_followup_effect_v1(
        baseline,
        _event_payload("week_2", 7),
    )
    changed = deepcopy(interpretation.model_dump(mode="json"))
    changed["mean_health_z_change"] = 999.0
    with pytest.raises(ValidationError):
        type(interpretation).model_validate(changed)


@pytest.mark.parametrize(
    ("field_name", "field_value", "error_match"),
    [
        ("assessment_id", "assessment_pre_intake", "assessment"),
        ("observed_at", "2025-12-31T00:00:00Z", "observed_at"),
    ],
)
def test_interpretation_rejects_duplicate_assessment_or_reversed_observation_time(
    field_name: str,
    field_value: str,
    error_match: str,
) -> None:
    baseline = _event_payload("pre_intake", 10)
    follow_up = _event_payload("week_2", 7)
    follow_up[field_name] = field_value

    with pytest.raises(ValueError, match=error_match):
        interpret_pro_followup_effect_v1(baseline, follow_up)


def test_metrics_package_exports_followup_contract_api() -> None:
    from wellnessbox_rnd import metrics

    assert metrics.PRO_FOLLOWUP_INTERPRETATION_CONTRACT_VERSION_V1 == "2026-07-17.1"
    assert metrics.PROFollowUpEventV1 is PROFollowUpEventV1
    assert metrics.interpret_pro_followup_effect_v1 is interpret_pro_followup_effect_v1
