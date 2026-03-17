from __future__ import annotations

from wellnessbox_rnd.schemas.recommendation import NextAction


def project_followup_closed_loop_state(
    *,
    action: NextAction,
    trajectory_step: int,
    adverse_event: bool = False,
) -> str:
    if adverse_event or action == NextAction.REDUCE_OR_STOP:
        return "stop_or_escalate"
    if action == NextAction.TRIGGER_SAFETY_RECHECK:
        return "safety_review"
    if action == NextAction.ASK_TARGETED_FOLLOWUP:
        return "baseline_questionnaire_due" if trajectory_step == 0 else "re_evaluation"
    if action == NextAction.RE_OPTIMIZE:
        return "adjust_plan"
    if action == NextAction.MONITOR_ONLY:
        return "recommendation_ready" if trajectory_step == 0 else "followup_due"
    if trajectory_step == 0:
        return "recommendation_ready"
    return "followup_due"


def project_runtime_workflow_state(*, action: NextAction) -> str:
    mapping = {
        NextAction.BLOCKED: "blocked",
        NextAction.ASK_TARGETED_FOLLOWUP: "baseline_questionnaire_due",
        NextAction.COLLECT_MORE_INPUT: "baseline_questionnaire_due",
        NextAction.TRIGGER_SAFETY_RECHECK: "safety_review",
        NextAction.START_PLAN: "recommendation_ready",
        NextAction.CONTINUE_PLAN: "followup_due",
        NextAction.MONITOR_ONLY: "followup_due",
        NextAction.RE_OPTIMIZE: "adjust_plan",
        NextAction.REDUCE_OR_STOP: "stop_or_escalate",
    }
    return mapping[action]


def next_action_state_transition_matrix() -> list[dict[str, object]]:
    matrix: list[dict[str, object]] = []
    for action in NextAction:
        followup_step0 = project_followup_closed_loop_state(
            action=action,
            trajectory_step=0,
        )
        followup_step_positive = project_followup_closed_loop_state(
            action=action,
            trajectory_step=1,
        )
        runtime_state = project_runtime_workflow_state(action=action)
        matrix.append(
            {
                "next_action": action.value,
                "runtime_workflow_state": runtime_state,
                "followup_step0_state": followup_step0,
                "followup_step_positive_state": followup_step_positive,
                "phase_sensitive": followup_step0 != followup_step_positive,
                "runtime_matches_followup_step0": runtime_state == followup_step0,
                "runtime_matches_followup_step_positive": (
                    runtime_state == followup_step_positive
                ),
            }
        )
    return matrix


def phase_sensitive_followup_actions() -> list[str]:
    excluded_actions = {
        NextAction.BLOCKED.value,
        NextAction.COLLECT_MORE_INPUT.value,
    }
    return sorted(
        item["next_action"]
        for item in next_action_state_transition_matrix()
        if item["phase_sensitive"] and item["next_action"] not in excluded_actions
    )


__all__ = [
    "next_action_state_transition_matrix",
    "phase_sensitive_followup_actions",
    "project_followup_closed_loop_state",
    "project_runtime_workflow_state",
]
