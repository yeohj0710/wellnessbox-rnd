from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.next_action_state_machine import (
    phase_sensitive_followup_actions,
    project_runtime_workflow_state,
)
from wellnessbox_rnd.schemas.recommendation import (
    NextAction,
    RecommendationResponse,
    RecommendationStatus,
)

NEXT_ACTION_WORKFLOW_CONTRACT_SCHEMA_VERSION_V1 = "next_action_workflow_contract_v1"


class NextActionWorkflowEventV1(BaseModel):
    schema_version: str = NEXT_ACTION_WORKFLOW_CONTRACT_SCHEMA_VERSION_V1
    request_id: str
    decision_id: str
    response_status: RecommendationStatus
    next_action: NextAction
    reason_code: str
    supporting_codes: list[str] = Field(default_factory=list)
    missing_information_codes: list[str] = Field(default_factory=list)
    safety_rule_ids: list[str] = Field(default_factory=list)
    recommendation_keys: list[str] = Field(default_factory=list)
    projected_workflow_state: Literal[
        "blocked",
        "baseline_questionnaire_due",
        "safety_review",
        "recommendation_ready",
        "followup_due",
        "adjust_plan",
        "stop_or_escalate",
    ]


def build_next_action_workflow_event_v1(
    response: RecommendationResponse,
) -> NextActionWorkflowEventV1:
    return NextActionWorkflowEventV1(
        request_id=response.request_id,
        decision_id=response.decision_id,
        response_status=response.status,
        next_action=response.next_action,
        reason_code=response.next_action_rationale.reason_code,
        supporting_codes=list(response.next_action_rationale.supporting_codes),
        missing_information_codes=[item.code for item in response.missing_information],
        safety_rule_ids=[item.rule_id for item in response.safety_summary.rule_refs],
        recommendation_keys=[item.ingredient_key for item in response.recommendations],
        projected_workflow_state=project_runtime_workflow_state(action=response.next_action),
    )


def validate_next_action_workflow_event_v1(
    event: NextActionWorkflowEventV1 | dict[str, object],
) -> list[str]:
    model = (
        event
        if isinstance(event, NextActionWorkflowEventV1)
        else NextActionWorkflowEventV1.model_validate(event)
    )
    issues: list[str] = []
    expected_state = project_runtime_workflow_state(action=model.next_action)
    if model.projected_workflow_state != expected_state:
        issues.append(
            "projected_workflow_state_mismatch::"
            f"{model.next_action.value}::{expected_state}::{model.projected_workflow_state}"
        )
    if not model.reason_code:
        issues.append("missing_reason_code")
    if model.next_action == NextAction.COLLECT_MORE_INPUT and not model.missing_information_codes:
        issues.append("collect_more_input_requires_missing_information")
    if model.next_action == NextAction.TRIGGER_SAFETY_RECHECK and not model.safety_rule_ids:
        issues.append("trigger_safety_recheck_requires_safety_rule_ids")
    if (
        model.next_action == NextAction.START_PLAN
        and model.response_status == RecommendationStatus.BLOCKED
    ):
        issues.append("start_plan_requires_non_blocked_status")
    if model.next_action in {
        NextAction.START_PLAN,
        NextAction.TRIGGER_SAFETY_RECHECK,
        NextAction.COLLECT_MORE_INPUT,
    } and not model.supporting_codes:
        issues.append(f"missing_supporting_codes::{model.next_action.value}")
    return issues


def summarize_next_action_workflow_contract_v1(
    event: NextActionWorkflowEventV1,
    *,
    request_fixture_path: str | Path | None = None,
) -> dict[str, object]:
    issues = validate_next_action_workflow_event_v1(event)
    return {
        "schema_version": NEXT_ACTION_WORKFLOW_CONTRACT_SCHEMA_VERSION_V1,
        "request_fixture_path": (
            str(request_fixture_path) if request_fixture_path is not None else None
        ),
        "response_status": event.response_status.value,
        "next_action": event.next_action.value,
        "projected_workflow_state": event.projected_workflow_state,
        "reason_code": event.reason_code,
        "state_machine_scope": "runtime_request_decision",
        "phase_sensitive_followup_actions": phase_sensitive_followup_actions(),
        "issue_count": len(issues),
        "issues": issues,
        "connection_map": {
            "recommendation": ["recommendation_keys", "supporting_codes"],
            "safety": ["response_status", "safety_rule_ids"],
            "follow_up_state_machine": [
                "next_action",
                "projected_workflow_state",
                "reason_code",
            ],
            "intake_follow_up": ["missing_information_codes"],
        },
        "example_event": event.model_dump(mode="json"),
    }


def write_next_action_workflow_contract_report_v1(
    report: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
    output_example_json_path: str | Path | None = None,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_next_action_workflow_contract_markdown_v1(report), encoding="utf-8")
    if output_example_json_path is not None:
        example_path = Path(output_example_json_path)
        example_path.parent.mkdir(parents=True, exist_ok=True)
        example_path.write_text(
            json.dumps(report["example_event"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def render_next_action_workflow_contract_markdown_v1(report: dict[str, object]) -> str:
    event = report["example_event"]
    lines = [
        "# next-action workflow contract v1",
        "",
        "## summary",
        f"- request_fixture_path: `{report['request_fixture_path']}`",
        f"- response_status: `{report['response_status']}`",
        f"- next_action: `{report['next_action']}`",
        f"- projected_workflow_state: `{report['projected_workflow_state']}`",
        f"- reason_code: `{report['reason_code']}`",
        f"- state_machine_scope: `{report['state_machine_scope']}`",
        f"- phase_sensitive_followup_actions: `{report['phase_sensitive_followup_actions']}`",
        f"- issue_count: `{report['issue_count']}`",
        "",
        "## connection map",
        f"- recommendation: `{report['connection_map']['recommendation']}`",
        f"- safety: `{report['connection_map']['safety']}`",
        f"- follow_up_state_machine: `{report['connection_map']['follow_up_state_machine']}`",
        f"- intake_follow_up: `{report['connection_map']['intake_follow_up']}`",
        "",
        "## example event",
        f"- supporting_codes: `{event['supporting_codes']}`",
        f"- safety_rule_ids: `{event['safety_rule_ids']}`",
        f"- missing_information_codes: `{event['missing_information_codes']}`",
        f"- recommendation_keys: `{event['recommendation_keys']}`",
    ]
    if report["issues"]:
        lines.extend(["", "## issues"])
        lines.extend(f"- `{issue}`" for issue in report["issues"])
    return "\n".join(lines) + "\n"

__all__ = [
    "NEXT_ACTION_WORKFLOW_CONTRACT_SCHEMA_VERSION_V1",
    "NextActionWorkflowEventV1",
    "build_next_action_workflow_event_v1",
    "render_next_action_workflow_contract_markdown_v1",
    "summarize_next_action_workflow_contract_v1",
    "validate_next_action_workflow_event_v1",
    "write_next_action_workflow_contract_report_v1",
]
