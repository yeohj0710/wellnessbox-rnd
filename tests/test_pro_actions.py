from types import SimpleNamespace

import pytest

from wellnessbox_rnd.metrics.pro_actions import decide_pro_plan_action_v1
from wellnessbox_rnd.schemas.recommendation import NextAction


def _interpretation(
    *,
    status: str = "worsened",
    interpretation_status: str = "observed_change_interpretable",
    adverse_event_count: int = 0,
    serious: bool = False,
):
    return SimpleNamespace(
        observed_change_status=status,
        interpretation_status=interpretation_status,
        adverse_event_count=adverse_event_count,
        serious_adverse_event_present=serious,
        causal_effect_claim_allowed=False,
    )


@pytest.mark.parametrize(
    ("interpretation", "action", "next_action", "workflow_state", "reason"),
    [
        (
            _interpretation(adverse_event_count=1, serious=True),
            "stop",
            NextAction.REDUCE_OR_STOP,
            "stop_or_escalate",
            "serious_adverse_event_stop",
        ),
        (
            _interpretation(adverse_event_count=1),
            "reduce",
            NextAction.REDUCE_OR_STOP,
            "stop_or_escalate",
            "adverse_event_reduce",
        ),
        (
            _interpretation(interpretation_status="limited_by_low_adherence"),
            "maintain",
            NextAction.CONTINUE_PLAN,
            "followup_due",
            "worsening_confounded_maintain",
        ),
        (
            _interpretation(interpretation_status="limited_by_missed_doses"),
            "maintain",
            NextAction.CONTINUE_PLAN,
            "followup_due",
            "worsening_confounded_maintain",
        ),
        (
            _interpretation(),
            "re_optimize",
            NextAction.RE_OPTIMIZE,
            "adjust_plan",
            "interpretable_worsening_re_optimize",
        ),
        (
            _interpretation(status="improved"),
            "maintain",
            NextAction.CONTINUE_PLAN,
            "followup_due",
            "non_worsening_maintain",
        ),
    ],
)
def test_pro_action_policy_selects_exact_closed_loop_action(
    interpretation,
    action,
    next_action,
    workflow_state,
    reason,
) -> None:
    result = decide_pro_plan_action_v1(interpretation)

    assert result.action == action
    assert result.next_action == next_action
    assert result.projected_workflow_state == workflow_state
    assert result.reason_code == reason
    assert result.causal_effect_claim_allowed is False


def test_pro_action_decision_rejects_derived_field_mutation() -> None:
    result = decide_pro_plan_action_v1(_interpretation())
    payload = result.model_dump(mode="json")
    payload["action"] = "maintain"

    with pytest.raises(ValueError, match="does not match source interpretation"):
        type(result).model_validate(payload)
