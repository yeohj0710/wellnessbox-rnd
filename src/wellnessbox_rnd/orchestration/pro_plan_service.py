from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from wellnessbox_rnd.interim.data_lake import ExecutionLedger
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
    response = recommend(request)
    trace = ExecutionLedger(store).record_recommendation(request=request, response=response)
    score, standardized = score_and_standardize_runtime_pro_v1(instrument, item_scores)
    baseline = PROFollowUpEventV1(
        schema_version="versioned_pro_followup_event_v1",
        assessment_id=f"assessment_{uuid4().hex}",
        plan_id=response.plan_id,
        data_class="SYNTHETIC_OUTCOME_PROXY",
        timepoint="pre_intake",
        scheduled_day_index=0,
        actual_day_index=0,
        observed_at=observed_at,
        instrument_scores=[score],
        standardized_scores=[standardized],
    )
    appended = ExecutionLedger(store).append_event(
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
            idempotency_key=f"pro-correction:{target_record.event_id}:{follow_up.instrument_scores[0].raw_score}",
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


__all__ = ["enroll_pro_plan_v1", "record_or_correct_pro_followup_v1"]
