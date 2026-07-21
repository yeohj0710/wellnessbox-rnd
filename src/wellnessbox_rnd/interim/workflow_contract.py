from __future__ import annotations

from enum import StrEnum


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
    STOP = "stop"
    COMPLETE = "complete"


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
    "ClosedLoopState",
    "apply_closed_loop_transition_v1",
    "closed_loop_contract_snapshot_v1",
]
