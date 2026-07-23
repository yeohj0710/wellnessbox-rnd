from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator


class ClosedLoopState(StrEnum):
    INTAKE = "INTAKE"
    CONSENT_CHECK = "CONSENT_CHECK"
    PROFILE_READY = "PROFILE_READY"
    SAFETY_CHECK = "SAFETY_CHECK"
    RANKING = "RANKING"
    EVIDENCE_RETRIEVAL = "EVIDENCE_RETRIEVAL"
    REGIMEN_OPTIMIZATION = "REGIMEN_OPTIMIZATION"
    PLAN_READY = "PLAN_READY"
    FOLLOWUP_ACTIVE = "FOLLOWUP_ACTIVE"
    FOLLOWUP_REVIEW = "FOLLOWUP_REVIEW"
    PLAN_MAINTAINED = "PLAN_MAINTAINED"
    PLAN_REOPTIMIZATION = "PLAN_REOPTIMIZATION"
    PLAN_REDUCED = "PLAN_REDUCED"
    PLAN_REPLACED = "PLAN_REPLACED"
    ESCALATED = "ESCALATED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"


class ClosedLoopOperation(StrEnum):
    LOAD_PROFILE = "load_profile"
    VERIFY_CONSENT = "verify_consent"
    CHECK_SAFETY = "check_safety"
    GENERATE_CANDIDATES = "generate_candidates"
    LOOKUP_EVIDENCE = "lookup_evidence"
    OPTIMIZE = "optimize"
    START_PLAN = "start_plan"
    SCHEDULE_FOLLOWUP = "schedule_followup"
    INGEST_FOLLOWUP = "ingest_followup"
    HOLD_FOR_REVIEW = "hold_for_review"
    MAINTAIN_PLAN = "maintain_plan"
    REOPTIMIZE_PLAN = "reoptimize_plan"
    REDUCE_PLAN = "reduce_plan"
    REPLACE_PLAN = "replace_plan"
    ESCALATE = "escalate"
    STOP = "stop"
    COMPLETE = "complete"


class ClosedLoopExecutionStepV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: ClosedLoopOperation
    state_before: ClosedLoopState
    state_after: ClosedLoopState

    @model_validator(mode="after")
    def validate_transition(self) -> ClosedLoopExecutionStepV1:
        apply_closed_loop_transition_v1(
            current=self.state_before,
            operation=self.operation,
            target=self.state_after,
        )
        return self


class ClosedLoopExecutionTraceV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "closed_loop_ordered_execution_trace_v1"
    run_id: str
    status: ClosedLoopState
    steps: tuple[ClosedLoopExecutionStepV1, ...]
    plan_start_recorded: bool

    @model_validator(mode="after")
    def validate_trace(self) -> ClosedLoopExecutionTraceV1:
        if not self.steps or self.steps[0].state_before != ClosedLoopState.INTAKE:
            raise ValueError("closed_loop_trace_must_start_at_intake")
        for previous, current in zip(self.steps, self.steps[1:], strict=False):
            if previous.state_after != current.state_before:
                raise ValueError("closed_loop_trace_state_discontinuity")
        if self.steps[-1].state_after != self.status:
            raise ValueError("closed_loop_trace_status_mismatch")
        started = any(
            step.operation == ClosedLoopOperation.START_PLAN for step in self.steps
        )
        if started != self.plan_start_recorded:
            raise ValueError("closed_loop_trace_plan_start_mismatch")
        return self


_ORDERED_TRANSITIONS: dict[
    tuple[ClosedLoopState, ClosedLoopOperation], ClosedLoopState
] = {
    (ClosedLoopState.INTAKE, ClosedLoopOperation.LOAD_PROFILE): (
        ClosedLoopState.CONSENT_CHECK
    ),
    (ClosedLoopState.CONSENT_CHECK, ClosedLoopOperation.VERIFY_CONSENT): (
        ClosedLoopState.PROFILE_READY
    ),
    (ClosedLoopState.PROFILE_READY, ClosedLoopOperation.CHECK_SAFETY): (
        ClosedLoopState.SAFETY_CHECK
    ),
    (ClosedLoopState.SAFETY_CHECK, ClosedLoopOperation.GENERATE_CANDIDATES): (
        ClosedLoopState.RANKING
    ),
    (ClosedLoopState.RANKING, ClosedLoopOperation.LOOKUP_EVIDENCE): (
        ClosedLoopState.EVIDENCE_RETRIEVAL
    ),
    (ClosedLoopState.EVIDENCE_RETRIEVAL, ClosedLoopOperation.OPTIMIZE): (
        ClosedLoopState.REGIMEN_OPTIMIZATION
    ),
    (ClosedLoopState.REGIMEN_OPTIMIZATION, ClosedLoopOperation.START_PLAN): (
        ClosedLoopState.PLAN_READY
    ),
    (ClosedLoopState.PLAN_READY, ClosedLoopOperation.SCHEDULE_FOLLOWUP): (
        ClosedLoopState.FOLLOWUP_ACTIVE
    ),
    (ClosedLoopState.FOLLOWUP_ACTIVE, ClosedLoopOperation.INGEST_FOLLOWUP): (
        ClosedLoopState.FOLLOWUP_ACTIVE
    ),
    (ClosedLoopState.FOLLOWUP_ACTIVE, ClosedLoopOperation.HOLD_FOR_REVIEW): (
        ClosedLoopState.FOLLOWUP_REVIEW
    ),
    (ClosedLoopState.FOLLOWUP_ACTIVE, ClosedLoopOperation.MAINTAIN_PLAN): (
        ClosedLoopState.PLAN_MAINTAINED
    ),
    (ClosedLoopState.FOLLOWUP_ACTIVE, ClosedLoopOperation.REOPTIMIZE_PLAN): (
        ClosedLoopState.PLAN_REOPTIMIZATION
    ),
    (ClosedLoopState.FOLLOWUP_ACTIVE, ClosedLoopOperation.REDUCE_PLAN): (
        ClosedLoopState.PLAN_REDUCED
    ),
    (ClosedLoopState.FOLLOWUP_ACTIVE, ClosedLoopOperation.REPLACE_PLAN): (
        ClosedLoopState.PLAN_REPLACED
    ),
    (ClosedLoopState.FOLLOWUP_ACTIVE, ClosedLoopOperation.ESCALATE): (
        ClosedLoopState.ESCALATED
    ),
    (ClosedLoopState.FOLLOWUP_REVIEW, ClosedLoopOperation.INGEST_FOLLOWUP): (
        ClosedLoopState.FOLLOWUP_ACTIVE
    ),
    (ClosedLoopState.PLAN_MAINTAINED, ClosedLoopOperation.SCHEDULE_FOLLOWUP): (
        ClosedLoopState.FOLLOWUP_ACTIVE
    ),
    (ClosedLoopState.PLAN_REDUCED, ClosedLoopOperation.SCHEDULE_FOLLOWUP): (
        ClosedLoopState.FOLLOWUP_ACTIVE
    ),
    (ClosedLoopState.PLAN_REPLACED, ClosedLoopOperation.SCHEDULE_FOLLOWUP): (
        ClosedLoopState.FOLLOWUP_ACTIVE
    ),
    (ClosedLoopState.PLAN_REOPTIMIZATION, ClosedLoopOperation.OPTIMIZE): (
        ClosedLoopState.REGIMEN_OPTIMIZATION
    ),
    (ClosedLoopState.ESCALATED, ClosedLoopOperation.STOP): ClosedLoopState.STOPPED,
    (ClosedLoopState.PLAN_READY, ClosedLoopOperation.COMPLETE): ClosedLoopState.COMPLETED,
    (ClosedLoopState.FOLLOWUP_ACTIVE, ClosedLoopOperation.COMPLETE): (
        ClosedLoopState.COMPLETED
    ),
}

for _state in (
    ClosedLoopState.INTAKE,
    ClosedLoopState.CONSENT_CHECK,
    ClosedLoopState.PROFILE_READY,
    ClosedLoopState.SAFETY_CHECK,
    ClosedLoopState.RANKING,
    ClosedLoopState.EVIDENCE_RETRIEVAL,
    ClosedLoopState.REGIMEN_OPTIMIZATION,
    ClosedLoopState.PLAN_READY,
    ClosedLoopState.FOLLOWUP_ACTIVE,
    ClosedLoopState.FOLLOWUP_REVIEW,
    ClosedLoopState.PLAN_MAINTAINED,
    ClosedLoopState.PLAN_REOPTIMIZATION,
    ClosedLoopState.PLAN_REDUCED,
    ClosedLoopState.PLAN_REPLACED,
    ClosedLoopState.ESCALATED,
):
    _ORDERED_TRANSITIONS[(_state, ClosedLoopOperation.STOP)] = ClosedLoopState.STOPPED


CLOSED_LOOP_ALLOWED_OPERATIONS_V1: dict[
    ClosedLoopState, frozenset[ClosedLoopOperation]
] = {
    state: frozenset(
        operation
        for (source, operation), _target in _ORDERED_TRANSITIONS.items()
        if source == state
    )
    for state in ClosedLoopState
}

CLOSED_LOOP_TRANSITIONS_V1: dict[ClosedLoopState, frozenset[ClosedLoopState]] = {
    state: frozenset(
        target
        for (source, _operation), target in _ORDERED_TRANSITIONS.items()
        if source == state
    )
    for state in ClosedLoopState
}


def apply_closed_loop_transition_v1(
    *,
    current: ClosedLoopState,
    operation: ClosedLoopOperation,
    target: ClosedLoopState,
) -> ClosedLoopState:
    expected = _ORDERED_TRANSITIONS.get((current, operation))
    if expected != target:
        raise ValueError(
            "forbidden_closed_loop_transition:"
            f"{current.value}:{operation.value}:{target.value}"
        )
    return target


def closed_loop_contract_snapshot_v1() -> dict[str, object]:
    return {
        "schema_version": "closed_loop_state_operation_contract_v1",
        "states": sorted(state.value for state in ClosedLoopState),
        "operations": sorted(operation.value for operation in ClosedLoopOperation),
        "allowed_operations": {
            state.value: sorted(
                operation.value for operation in CLOSED_LOOP_ALLOWED_OPERATIONS_V1[state]
            )
            for state in sorted(ClosedLoopState, key=lambda item: item.value)
        },
        "allowed_transitions": {
            state.value: sorted(
                target.value for target in CLOSED_LOOP_TRANSITIONS_V1[state]
            )
            for state in sorted(ClosedLoopState, key=lambda item: item.value)
        },
        "terminal_states": [ClosedLoopState.COMPLETED.value, ClosedLoopState.STOPPED.value],
    }


__all__ = [
    "CLOSED_LOOP_ALLOWED_OPERATIONS_V1",
    "CLOSED_LOOP_TRANSITIONS_V1",
    "ClosedLoopOperation",
    "ClosedLoopExecutionStepV1",
    "ClosedLoopExecutionTraceV1",
    "ClosedLoopState",
    "apply_closed_loop_transition_v1",
    "closed_loop_contract_snapshot_v1",
]
