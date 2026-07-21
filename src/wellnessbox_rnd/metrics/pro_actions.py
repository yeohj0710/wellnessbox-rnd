from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from wellnessbox_rnd.schemas.next_action_state_machine import (
    project_runtime_workflow_state,
)
from wellnessbox_rnd.schemas.recommendation import NextAction

PROPlanActionV1 = Literal["maintain", "reduce", "stop", "re_optimize"]


class _InterpretationInput(Protocol):
    observed_change_status: str
    interpretation_status: str
    adverse_event_count: int
    serious_adverse_event_present: bool
    causal_effect_claim_allowed: bool


class PROPlanActionDecisionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["pro_plan_action_decision_v1"]
    policy_version: Literal["2026-07-21.1"]
    source_observed_change_status: Literal[
        "improved", "worsened", "no_material_change"
    ]
    source_interpretation_status: Literal[
        "observed_change_interpretable",
        "limited_by_missed_doses",
        "limited_by_low_adherence",
        "safety_context_required",
        "safety_escalation_required",
    ]
    source_adverse_event_count: StrictInt = Field(ge=0)
    source_serious_adverse_event_present: bool
    action: PROPlanActionV1
    next_action: NextAction
    projected_workflow_state: Literal[
        "followup_due", "adjust_plan", "stop_or_escalate"
    ]
    reason_code: Literal[
        "serious_adverse_event_stop",
        "adverse_event_reduce",
        "worsening_confounded_maintain",
        "interpretable_worsening_re_optimize",
        "non_worsening_maintain",
    ]
    causal_effect_claim_allowed: Literal[False]

    @model_validator(mode="after")
    def validate_decision(self) -> PROPlanActionDecisionV1:
        expected = _derive_action(
            observed_change_status=self.source_observed_change_status,
            interpretation_status=self.source_interpretation_status,
            adverse_event_count=self.source_adverse_event_count,
            serious_adverse_event_present=self.source_serious_adverse_event_present,
        )
        actual = (
            self.action,
            self.next_action,
            self.projected_workflow_state,
            self.reason_code,
        )
        if actual != expected:
            raise ValueError("PRO action decision does not match source interpretation")
        return self


def decide_pro_plan_action_v1(
    interpretation: _InterpretationInput,
) -> PROPlanActionDecisionV1:
    if interpretation.causal_effect_claim_allowed:
        raise ValueError("PRO action decision requires non-causal interpretation")
    action, next_action, workflow_state, reason = _derive_action(
        observed_change_status=interpretation.observed_change_status,
        interpretation_status=interpretation.interpretation_status,
        adverse_event_count=interpretation.adverse_event_count,
        serious_adverse_event_present=interpretation.serious_adverse_event_present,
    )
    return PROPlanActionDecisionV1(
        schema_version="pro_plan_action_decision_v1",
        policy_version="2026-07-21.1",
        source_observed_change_status=interpretation.observed_change_status,
        source_interpretation_status=interpretation.interpretation_status,
        source_adverse_event_count=interpretation.adverse_event_count,
        source_serious_adverse_event_present=(
            interpretation.serious_adverse_event_present
        ),
        action=action,
        next_action=next_action,
        projected_workflow_state=workflow_state,
        reason_code=reason,
        causal_effect_claim_allowed=False,
    )


def _derive_action(
    *,
    observed_change_status: str,
    interpretation_status: str,
    adverse_event_count: int,
    serious_adverse_event_present: bool,
) -> tuple[PROPlanActionV1, NextAction, str, str]:
    if serious_adverse_event_present:
        action: PROPlanActionV1 = "stop"
        next_action = NextAction.REDUCE_OR_STOP
        reason = "serious_adverse_event_stop"
    elif adverse_event_count:
        action = "reduce"
        next_action = NextAction.REDUCE_OR_STOP
        reason = "adverse_event_reduce"
    elif observed_change_status == "worsened" and interpretation_status in {
        "limited_by_low_adherence",
        "limited_by_missed_doses",
    }:
        action = "maintain"
        next_action = NextAction.CONTINUE_PLAN
        reason = "worsening_confounded_maintain"
    elif observed_change_status == "worsened":
        action = "re_optimize"
        next_action = NextAction.RE_OPTIMIZE
        reason = "interpretable_worsening_re_optimize"
    else:
        action = "maintain"
        next_action = NextAction.CONTINUE_PLAN
        reason = "non_worsening_maintain"
    return (
        action,
        next_action,
        project_runtime_workflow_state(action=next_action),
        reason,
    )


__all__ = [
    "PROPlanActionDecisionV1",
    "PROPlanActionV1",
    "decide_pro_plan_action_v1",
]
