from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from wellnessbox_rnd.interim.data_lake import ExecutionLedger, ExecutionNotFoundError
from wellnessbox_rnd.interim.data_mutation import DataMutationLedger, EventMutationResult
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.pro_followup import (
    PROFollowUpEffectInterpretationV1,
    PROFollowUpEventV1,
    interpret_pro_followup_effect_v1,
    is_versioned_pro_followup_payload_v1,
    normalize_pro_followup_event_v1,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PRORecommendationEffectLineageV1(_StrictModel):
    schema_version: Literal["pro_recommendation_effect_lineage_v1"]
    execution_id: str
    plan_id: str
    recommendation_event_id: str
    optimization_event_id: str
    selected_ingredient_keys: list[str]
    baseline_event_id: str
    follow_up_event_id: str
    causal_effect_claim_allowed: Literal[False]

    @model_validator(mode="after")
    def validate_lineage(self) -> PRORecommendationEffectLineageV1:
        if not self.plan_id.strip():
            raise ValueError("plan_id_required")
        if len(self.selected_ingredient_keys) != len(set(self.selected_ingredient_keys)):
            raise ValueError("duplicate_selected_ingredient_key")
        return self


class PROCorrectionRecalculationResultV1(_StrictModel):
    schema_version: Literal["pro_correction_recalculation_result_v1"]
    mutation: EventMutationResult
    interpretation: PROFollowUpEffectInterpretationV1
    lineage: PRORecommendationEffectLineageV1
    recalculated_immediately: Literal[True]

    @model_validator(mode="after")
    def validate_sources(self) -> PROCorrectionRecalculationResultV1:
        if self.mutation.mutation.target_event_id != self.lineage.follow_up_event_id:
            raise ValueError("mutation_target_does_not_match_follow_up")
        if self.interpretation.baseline_event.plan_id != self.lineage.plan_id:
            raise ValueError("baseline_plan_does_not_match_lineage")
        if self.interpretation.follow_up_event.plan_id != self.lineage.plan_id:
            raise ValueError("follow_up_plan_does_not_match_lineage")
        return self


def correct_and_recalculate_pro_followup_v1(
    store: InterimStore,
    *,
    execution_id: str,
    profile_id: str,
    target_event_id: str,
    idempotency_key: str,
    replacement_payload: dict[str, Any] | PROFollowUpEventV1,
) -> PROCorrectionRecalculationResultV1:
    ledger = ExecutionLedger(store)
    trace = ledger.get_trace(execution_id)
    if trace.profile_id != profile_id:
        raise ExecutionNotFoundError(f"execution_not_found:{execution_id}")

    target = next((event for event in trace.events if event.event_id == target_event_id), None)
    if target is None:
        raise ValueError("pro_followup_target_not_in_execution")
    if target.event_type != "followup_evaluation" or not is_versioned_pro_followup_payload_v1(
        target.payload
    ):
        raise ValueError("pro_followup_target_must_be_versioned_event")

    replacement = normalize_pro_followup_event_v1(replacement_payload)
    mutation = DataMutationLedger(store).apply(
        profile_id=profile_id,
        target_type="execution_event",
        target_event_id=target_event_id,
        operation="correction",
        idempotency_key=idempotency_key,
        replacement_payload=replacement.model_dump(mode="json"),
    )

    effective = ledger.get_trace(execution_id)
    strict_events = [
        (event, normalize_pro_followup_event_v1(event.payload))
        for event in effective.events
        if event.event_type == "followup_evaluation"
        and is_versioned_pro_followup_payload_v1(event.payload)
    ]
    corrected_pair = next(
        ((event, payload) for event, payload in strict_events if event.event_id == target_event_id),
        None,
    )
    if corrected_pair is None:
        raise ValueError("corrected_pro_followup_event_missing")
    corrected_event, corrected_payload = corrected_pair
    if corrected_payload.timepoint == "pre_intake":
        raise ValueError("follow_up_target_cannot_be_pre_intake")
    baselines = [
        (event, payload)
        for event, payload in strict_events
        if payload.timepoint == "pre_intake" and payload.plan_id == corrected_payload.plan_id
    ]
    if len(baselines) != 1:
        raise ValueError("exactly_one_matching_pro_baseline_required")
    baseline_event, baseline_payload = baselines[0]

    recommendation_events = [
        event for event in effective.events if event.event_type == "recommendation"
    ]
    optimization_events = [
        event for event in effective.events if event.event_type == "optimization"
    ]
    if len(recommendation_events) != 1 or len(optimization_events) != 1:
        raise ValueError("recommendation_lineage_events_required")
    ingredient_keys = optimization_events[0].payload.get("selected_ingredient_keys")
    if not isinstance(ingredient_keys, list) or not all(
        isinstance(item, str) and item for item in ingredient_keys
    ):
        raise ValueError("selected_ingredient_lineage_required")

    interpretation = interpret_pro_followup_effect_v1(
        baseline_payload,
        corrected_payload,
    )
    return PROCorrectionRecalculationResultV1(
        schema_version="pro_correction_recalculation_result_v1",
        mutation=mutation,
        interpretation=interpretation,
        lineage=PRORecommendationEffectLineageV1(
            schema_version="pro_recommendation_effect_lineage_v1",
            execution_id=execution_id,
            plan_id=corrected_payload.plan_id,
            recommendation_event_id=recommendation_events[0].event_id,
            optimization_event_id=optimization_events[0].event_id,
            selected_ingredient_keys=ingredient_keys,
            baseline_event_id=baseline_event.event_id,
            follow_up_event_id=corrected_event.event_id,
            causal_effect_claim_allowed=False,
        ),
        recalculated_immediately=True,
    )
