from __future__ import annotations

import pytest

from wellnessbox_rnd.interim.workflow_contract import (
    CLOSED_LOOP_ALLOWED_OPERATIONS_V1,
    CLOSED_LOOP_TRANSITIONS_V1,
    ClosedLoopOperation,
    ClosedLoopState,
    apply_closed_loop_transition_v1,
    closed_loop_contract_snapshot_v1,
)


def test_closed_loop_contract_has_one_complete_state_and_operation_registry() -> None:
    snapshot = closed_loop_contract_snapshot_v1()

    assert snapshot["schema_version"] == "closed_loop_state_operation_contract_v1"
    assert snapshot["states"] == sorted(state.value for state in ClosedLoopState)
    assert snapshot["operations"] == sorted(operation.value for operation in ClosedLoopOperation)
    assert set(CLOSED_LOOP_ALLOWED_OPERATIONS_V1) == set(ClosedLoopState)
    assert set(CLOSED_LOOP_TRANSITIONS_V1) == set(ClosedLoopState)
    assert "manual_review" not in snapshot["operations"]
    assert "human_handoff" not in snapshot["operations"]


def test_closed_loop_contract_pins_safety_to_plan_order() -> None:
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[ClosedLoopState.PROFILE_READY] == frozenset(
        {ClosedLoopOperation.CHECK_SAFETY, ClosedLoopOperation.STOP}
    )
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[ClosedLoopState.SAFETY_CHECK] == frozenset(
        {ClosedLoopOperation.GENERATE_CANDIDATES, ClosedLoopOperation.STOP}
    )
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[ClosedLoopState.RANKING] == frozenset(
        {ClosedLoopOperation.LOOKUP_EVIDENCE, ClosedLoopOperation.STOP}
    )
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[ClosedLoopState.EVIDENCE_RETRIEVAL] == frozenset(
        {ClosedLoopOperation.OPTIMIZE, ClosedLoopOperation.STOP}
    )
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[
        ClosedLoopState.REGIMEN_OPTIMIZATION
    ] == frozenset({ClosedLoopOperation.START_PLAN, ClosedLoopOperation.STOP})


def test_closed_loop_contract_rejects_forbidden_transition() -> None:
    assert (
        apply_closed_loop_transition_v1(
            current=ClosedLoopState.PROFILE_READY,
            operation=ClosedLoopOperation.CHECK_SAFETY,
            target=ClosedLoopState.SAFETY_CHECK,
        )
        == ClosedLoopState.SAFETY_CHECK
    )
    with pytest.raises(ValueError, match="forbidden_closed_loop_transition"):
        apply_closed_loop_transition_v1(
            current=ClosedLoopState.PROFILE_READY,
            operation=ClosedLoopOperation.START_PLAN,
            target=ClosedLoopState.PLAN_READY,
        )


@pytest.mark.parametrize("terminal", [ClosedLoopState.STOPPED, ClosedLoopState.COMPLETED])
def test_closed_loop_terminal_states_allow_no_operations(terminal: ClosedLoopState) -> None:
    assert CLOSED_LOOP_ALLOWED_OPERATIONS_V1[terminal] == frozenset()
    assert CLOSED_LOOP_TRANSITIONS_V1[terminal] == frozenset()
