from wellnessbox_rnd.schemas.recommendation import NextAction


def test_next_action_enum_uses_only_system_owned_actions() -> None:
    assert {action.value for action in NextAction} == {
        "blocked",
        "collect_more_input",
        "start_plan",
        "continue_plan",
        "re_optimize",
        "reduce_or_stop",
        "monitor_only",
        "ask_targeted_followup",
        "trigger_safety_recheck",
    }
