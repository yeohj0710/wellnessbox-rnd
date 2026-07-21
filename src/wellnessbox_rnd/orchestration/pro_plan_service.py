from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from wellnessbox_rnd.interim.data_lake import (
    ExecutionLedger,
    ExecutionTrace,
    IdempotencyConflictError,
)
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.pro_correction import (
    PRORecommendationEffectLineageV1,
    correct_and_recalculate_pro_followup_v1,
)
from wellnessbox_rnd.metrics.pro_followup import (
    PROAdverseEventContextV1,
    PROFollowUpEventV1,
    interpret_pro_followup_effect_v1,
    is_versioned_pro_followup_payload_v1,
    normalize_pro_followup_event_v1,
)
from wellnessbox_rnd.metrics.pro_runtime import score_and_standardize_runtime_pro_v1
from wellnessbox_rnd.metrics.pro_scoring import standardize_pro_instrument_score_v1
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import RecommendationRequest

_SCHEDULED_DAY = {"week_2": 14, "week_4": 28, "discontinuation": None}


def enroll_pro_plan_v1(
    store: InterimStore,
    *,
    recommendation_request: RecommendationRequest | dict[str, Any],
    instrument: str,
    item_scores: list[int],
    observed_at: datetime,
) -> dict[str, Any]:
    request = RecommendationRequest.model_validate(recommendation_request)
    if not request.data_source_consents.survey.allow_persistent_storage:
        raise ValueError("pro_plan_requires_survey_persistent_storage_consent")
    score, standardized = score_and_standardize_runtime_pro_v1(instrument, item_scores)
    baseline = PROFollowUpEventV1(
        schema_version="versioned_pro_followup_event_v1",
        assessment_id=f"assessment_{uuid4().hex}",
        plan_id=request.plan_id,
        data_class="SYNTHETIC_OUTCOME_PROXY",
        timepoint="pre_intake",
        scheduled_day_index=0,
        actual_day_index=0,
        observed_at=observed_at,
        instrument_scores=[score],
        standardized_scores=[standardized],
    )
    ledger = ExecutionLedger(store)
    existing_trace = ledger.get_trace_for_request(request)
    if existing_trace is not None:
        return _existing_enrollment_result(
            store,
            existing_trace,
            request,
            baseline,
        )
    response = recommend(request)
    trace = ledger.record_recommendation(request=request, response=response)
    appended = ledger.append_event(
        execution_id=trace.execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key=f"pro-baseline:{response.plan_id}",
        payload=baseline,
    )
    return {
        "schema_version": "pro_plan_enrollment_result_v1",
        "recommendation": response.model_dump(mode="json"),
        "execution_id": trace.execution_id,
        "plan_id": response.plan_id,
        "profile_id": trace.profile_id,
        "baseline_event_id": appended.event.event_id,
        "baseline": baseline.model_dump(mode="json"),
        "deduplicated": appended.deduplicated,
    }


def record_or_correct_pro_followup_v1(
    store: InterimStore,
    *,
    execution_id: str,
    profile_id: str,
    plan_id: str,
    timepoint: Literal["week_2", "week_4", "discontinuation"],
    instrument: str,
    item_scores: list[int],
    observed_at: datetime,
    actual_day_index: int,
    planned_dose_count: int,
    taken_dose_count: int,
    adverse_events: list[dict[str, Any]] | None = None,
    discontinuation_reason: str | None = None,
) -> dict[str, Any]:
    ledger = ExecutionLedger(store)
    trace = ledger.get_trace(execution_id)
    if trace.profile_id != profile_id:
        raise ValueError("pro_followup_execution_owner_mismatch")
    strict = [
        (event, normalize_pro_followup_event_v1(event.payload))
        for event in trace.events
        if event.event_type == "followup_evaluation"
        and is_versioned_pro_followup_payload_v1(event.payload)
    ]
    baselines = [item for item in strict if item[1].timepoint == "pre_intake"]
    if len(baselines) != 1:
        raise ValueError("exactly_one_pro_baseline_required")
    baseline_record, baseline = baselines[0]
    if baseline.plan_id != plan_id:
        raise ValueError("pro_followup_plan_id_mismatch")
    baseline_standardized = next(
        (item for item in baseline.standardized_scores if item.instrument == instrument),
        None,
    )
    if baseline_standardized is None:
        raise ValueError("pro_followup_instrument_mismatch")
    score, _unused = score_and_standardize_runtime_pro_v1(instrument, item_scores)
    standardized = standardize_pro_instrument_score_v1(
        score,
        baseline_standardized.baseline_distribution,
    )
    missed = planned_dose_count - taken_dose_count
    follow_up = PROFollowUpEventV1(
        schema_version="versioned_pro_followup_event_v1",
        assessment_id=f"assessment_{uuid4().hex}",
        plan_id=plan_id,
        data_class=baseline.data_class,
        timepoint=timepoint,
        scheduled_day_index=_SCHEDULED_DAY[timepoint],
        actual_day_index=actual_day_index,
        observed_at=observed_at,
        instrument_scores=[score],
        standardized_scores=[standardized],
        adherence={
            "planned_dose_count": planned_dose_count,
            "taken_dose_count": taken_dose_count,
            "missed_dose_count": missed,
            "adherence_rate": round(taken_dose_count / planned_dose_count, 6),
        },
        adverse_events=[
            PROAdverseEventContextV1.model_validate(item)
            for item in adverse_events or []
        ],
        discontinuation_reason=discontinuation_reason,
    )
    existing = next((item for item in strict if item[1].timepoint == timepoint), None)
    if existing is not None:
        target_record, target_payload = existing
        follow_up = follow_up.model_copy(
            update={
                "assessment_id": target_payload.assessment_id,
                "observed_at": target_payload.observed_at,
                "actual_day_index": target_payload.actual_day_index,
            }
        )
        corrected = correct_and_recalculate_pro_followup_v1(
            store,
            execution_id=execution_id,
            profile_id=trace.profile_id,
            target_event_id=target_record.event_id,
            idempotency_key=_correction_idempotency_key(
                target_record.event_id,
                follow_up,
            ),
            replacement_payload=follow_up,
        )
        return {
            "schema_version": "pro_followup_record_result_v1",
            "operation": "corrected",
            "event_id": target_record.event_id,
            "raw_score": score.raw_score,
            "interpretation": corrected.interpretation.model_dump(mode="json"),
            "lineage": corrected.lineage.model_dump(mode="json"),
            "recalculated_immediately": True,
        }
    appended = ledger.append_event(
        execution_id=execution_id,
        event_type="followup_evaluation",
        source="survey",
        idempotency_key=f"pro-followup:{plan_id}:{timepoint}",
        payload=follow_up,
    )
    interpretation = interpret_pro_followup_effect_v1(baseline, follow_up)
    recommendation = next(item for item in trace.events if item.event_type == "recommendation")
    optimization = next(item for item in trace.events if item.event_type == "optimization")
    lineage = PRORecommendationEffectLineageV1(
        schema_version="pro_recommendation_effect_lineage_v1",
        execution_id=execution_id,
        plan_id=plan_id,
        recommendation_event_id=recommendation.event_id,
        optimization_event_id=optimization.event_id,
        selected_ingredient_keys=optimization.payload["selected_ingredient_keys"],
        baseline_event_id=baseline_record.event_id,
        follow_up_event_id=appended.event.event_id,
        causal_effect_claim_allowed=False,
    )
    return {
        "schema_version": "pro_followup_record_result_v1",
        "operation": "created",
        "event_id": appended.event.event_id,
        "raw_score": score.raw_score,
        "interpretation": interpretation.model_dump(mode="json"),
        "lineage": lineage.model_dump(mode="json"),
        "recalculated_immediately": True,
    }


def _correction_idempotency_key(
    target_event_id: str,
    replacement: PROFollowUpEventV1,
) -> str:
    canonical = json.dumps(
        replacement.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    suffix = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"pro-correction:{target_event_id}:{suffix}"


def _existing_enrollment_result(
    store: InterimStore,
    trace: ExecutionTrace,
    request: RecommendationRequest,
    candidate_baseline: PROFollowUpEventV1,
) -> dict[str, Any]:
    plan_id = request.plan_id
    recommendation_event = next(
        (event for event in trace.events if event.event_type == "recommendation"),
        None,
    )
    baselines = [
        event
        for event in trace.events
        if event.event_type == "followup_evaluation"
        and is_versioned_pro_followup_payload_v1(event.payload)
        and event.payload.get("timepoint") == "pre_intake"
    ]
    if recommendation_event is None or len(baselines) != 1:
        raise ValueError("incomplete_existing_pro_enrollment")
    if recommendation_event.payload.get("plan_id") != plan_id:
        raise ValueError("existing_pro_enrollment_plan_id_mismatch")
    existing_baseline = normalize_pro_followup_event_v1(baselines[0].payload)
    if _baseline_idempotency_identity(existing_baseline) != (
        _baseline_idempotency_identity(candidate_baseline)
    ):
        raise IdempotencyConflictError(
            f"pro_enrollment_baseline_conflict:{request.request_id}"
        )
    snapshots = store.rows(
        "select expected_output_json from execution_replay_snapshots where execution_id=?",
        (trace.execution_id,),
    )
    if len(snapshots) == 1:
        response = json.loads(snapshots[0]["expected_output_json"])
        response.update(
            {
                "execution_id": trace.execution_id,
                "decision_id": recommendation_event.payload["decision_id"],
            }
        )
        response["metadata"]["generated_at"] = trace.created_at
        response["safety_summary"]["applied_at"] = trace.created_at
    else:
        response = recommend(request).model_copy(
            update={
                "execution_id": trace.execution_id,
                "decision_id": recommendation_event.payload["decision_id"],
            }
        ).model_dump(mode="json")
    return {
        "schema_version": "pro_plan_enrollment_result_v1",
        "recommendation": response,
        "execution_id": trace.execution_id,
        "plan_id": plan_id,
        "profile_id": trace.profile_id,
        "baseline_event_id": baselines[0].event_id,
        "baseline": existing_baseline.model_dump(mode="json"),
        "deduplicated": True,
    }


def _baseline_idempotency_identity(event: PROFollowUpEventV1) -> dict[str, Any]:
    payload = event.model_dump(mode="json")
    payload.pop("assessment_id")
    return payload


__all__ = ["enroll_pro_plan_v1", "record_or_correct_pro_followup_v1"]
