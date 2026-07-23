from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from wellnessbox_rnd.interim.workflow_contract import (
    ClosedLoopOperation,
    ClosedLoopState,
)


class NextAction(StrEnum):
    REQUEST_FOLLOWUP = "request_followup"
    REQUEST_MEASUREMENT = "request_measurement"
    REQUEST_SAFETY_REVIEW = "request_safety_review"
    HOLD_FOR_REVIEW = "hold_for_review"
    MAINTAIN = "maintain"
    REOPTIMIZE = "reoptimize"
    REDUCE = "reduce"
    REPLACE = "replace"
    STOP_AND_ESCALATE = "stop_and_escalate"


@dataclass(frozen=True)
class NextActionDecision:
    rule_id: str
    action: NextAction
    operation: ClosedLoopOperation
    target_state: ClosedLoopState
    reason_code: str


_ACTION_TRANSITIONS = {
    NextAction.REQUEST_FOLLOWUP: (
        ClosedLoopOperation.HOLD_FOR_REVIEW,
        ClosedLoopState.FOLLOWUP_REVIEW,
    ),
    NextAction.REQUEST_MEASUREMENT: (
        ClosedLoopOperation.HOLD_FOR_REVIEW,
        ClosedLoopState.FOLLOWUP_REVIEW,
    ),
    NextAction.REQUEST_SAFETY_REVIEW: (
        ClosedLoopOperation.HOLD_FOR_REVIEW,
        ClosedLoopState.FOLLOWUP_REVIEW,
    ),
    NextAction.HOLD_FOR_REVIEW: (
        ClosedLoopOperation.HOLD_FOR_REVIEW,
        ClosedLoopState.FOLLOWUP_REVIEW,
    ),
    NextAction.MAINTAIN: (
        ClosedLoopOperation.MAINTAIN_PLAN,
        ClosedLoopState.PLAN_MAINTAINED,
    ),
    NextAction.REOPTIMIZE: (
        ClosedLoopOperation.REOPTIMIZE_PLAN,
        ClosedLoopState.PLAN_REOPTIMIZATION,
    ),
    NextAction.REDUCE: (
        ClosedLoopOperation.REDUCE_PLAN,
        ClosedLoopState.PLAN_REDUCED,
    ),
    NextAction.REPLACE: (
        ClosedLoopOperation.REPLACE_PLAN,
        ClosedLoopState.PLAN_REPLACED,
    ),
    NextAction.STOP_AND_ESCALATE: (
        ClosedLoopOperation.ESCALATE,
        ClosedLoopState.ESCALATED,
    ),
}


def default_policy_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "data/original_plan/closed_loop_next_action_policy_v1.json"
    )


def load_next_action_policy(path: Path | None = None) -> dict[str, Any]:
    policy = json.loads((path or default_policy_path()).read_text(encoding="utf-8"))
    if policy.get("schema_version") != "closed_loop_next_action_policy_v1":
        raise ValueError("next_action_policy_schema_invalid")
    if not policy.get("rules"):
        raise ValueError("next_action_policy_rules_required")
    return policy


def _matches(conditions: dict[str, Any], event: dict[str, Any]) -> bool:
    for key, expected in conditions.items():
        if key.endswith("_gt"):
            if float(event.get(key[:-3], float("-inf"))) <= float(expected):
                return False
        elif key.endswith("_lte"):
            if float(event.get(key[:-4], float("inf"))) > float(expected):
                return False
        elif key.endswith("_in"):
            if event.get(key[:-3]) not in expected:
                return False
        elif event.get(key) != expected:
            return False
    return True


def decide_next_action(
    *,
    state: ClosedLoopState,
    event: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> NextActionDecision:
    document = policy or load_next_action_policy()
    normalized = dict(event) | {"state": state.value}
    for rule in sorted(document["rules"], key=lambda item: int(item["priority"])):
        if _matches(dict(rule["when"]), normalized):
            action = NextAction(rule["action"])
            operation, target = _ACTION_TRANSITIONS[action]
            return NextActionDecision(
                rule_id=str(rule["rule_id"]),
                action=action,
                operation=operation,
                target_state=target,
                reason_code=str(rule["reason_code"]),
            )
    raise ValueError("next_action_policy_no_match")


__all__ = [
    "NextAction",
    "NextActionDecision",
    "decide_next_action",
    "default_policy_path",
    "load_next_action_policy",
]
