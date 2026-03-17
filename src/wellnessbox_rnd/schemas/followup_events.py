from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.next_action_state_machine import (
    project_followup_closed_loop_state,
)
from wellnessbox_rnd.schemas.recommendation import (
    NextAction,
    RecommendationGoal,
    RecommendationStatus,
)

FOLLOWUP_TRANSITION_EVENT_SCHEMA_VERSION_V1 = "followup_transition_event_v1"


class FollowUpTransitionEventV1(BaseModel):
    schema_version: str = FOLLOWUP_TRANSITION_EVENT_SCHEMA_VERSION_V1
    record_id: str
    user_id: str
    cohort_version: str
    trajectory_step: int = Field(ge=0)
    day_index: int = Field(ge=0)
    recommendation_goals: list[RecommendationGoal] = Field(default_factory=list)
    next_action: NextAction
    reason_code: str
    safety_status: RecommendationStatus
    risk_tier: Literal["low", "moderate", "high"]
    adverse_event: bool = False
    closed_loop_state: Literal[
        "baseline_questionnaire_due",
        "safety_review",
        "recommendation_ready",
        "intake_active",
        "followup_due",
        "re_evaluation",
        "adjust_plan",
        "stop_or_escalate",
    ]


def build_followup_transition_event_v1(
    record: Any,
) -> FollowUpTransitionEventV1:
    request = _read_value(record, "request")
    labels = _read_value(record, "labels")
    return FollowUpTransitionEventV1(
        record_id=_read_value(record, "record_id"),
        user_id=_read_value(record, "user_id"),
        cohort_version=_read_value(record, "cohort_version"),
        trajectory_step=_read_value(record, "trajectory_step"),
        day_index=_read_value(record, "day_index"),
        recommendation_goals=list(_read_value(request, "goals")),
        next_action=_read_value(labels, "next_action"),
        reason_code=_read_value(labels, "reason_code"),
        safety_status=_read_value(labels, "safety_status"),
        risk_tier=_read_value(labels, "risk_tier"),
        adverse_event=_read_value(labels, "adverse_event"),
        closed_loop_state=_read_value(labels, "closed_loop_state"),
    )


def validate_followup_transition_event_v1(
    event: FollowUpTransitionEventV1 | dict[str, object],
) -> list[str]:
    model = (
        event
        if isinstance(event, FollowUpTransitionEventV1)
        else FollowUpTransitionEventV1.model_validate(event)
    )
    issues: list[str] = []
    expected_state = _expected_closed_loop_state(model)
    if model.closed_loop_state != expected_state:
        issues.append(
            "closed_loop_state_mismatch::"
            f"{model.next_action.value}::{model.trajectory_step}::"
            f"{expected_state}::{model.closed_loop_state}"
        )
    if model.adverse_event and model.closed_loop_state != "stop_or_escalate":
        issues.append("adverse_event_requires_stop_or_escalate")
    return issues


def summarize_followup_transition_event_contract_v1(
    records: list[Any],
    *,
    dataset_path: str | Path,
) -> dict[str, object]:
    events = [build_followup_transition_event_v1(record) for record in records]
    invalid_records: dict[str, list[str]] = {}
    for event in events:
        issues = validate_followup_transition_event_v1(event)
        if issues:
            invalid_records[event.record_id] = issues

    sample_event = events[0] if events else None
    return {
        "contract_id": FOLLOWUP_TRANSITION_EVENT_SCHEMA_VERSION_V1,
        "dataset_path": str(dataset_path),
        "case_count": len(records),
        "user_count": len({_read_value(record, "user_id") for record in records}),
        "schema_version": FOLLOWUP_TRANSITION_EVENT_SCHEMA_VERSION_V1,
        "valid_case_count": len(records) - len(invalid_records),
        "invalid_case_count": len(invalid_records),
        "invalid_record_ids": sorted(invalid_records),
        "connected_flows": {
            "recommendation": [
                "recommendation_goals",
                "next_action",
                "reason_code",
            ],
            "safety": [
                "safety_status",
                "risk_tier",
                "adverse_event",
            ],
            "follow_up_state_machine": [
                "trajectory_step",
                "day_index",
                "next_action",
                "closed_loop_state",
            ],
            "pro_and_outcome_linkage": [
                "record_id",
                "user_id",
                "next_action",
            ],
        },
        "not_directly_connected_in_this_contract": [
            "recommendation_evidence_payload",
            "sensor_genetic_normalized_event",
        ],
        "example_record_id": sample_event.record_id if sample_event else None,
        "example_event": sample_event.model_dump(mode="json") if sample_event else None,
    }


def write_followup_transition_event_contract_report_v1(
    report: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
    output_example_json_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    example_path = Path(output_example_json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    example_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(
        render_followup_transition_event_contract_markdown_v1(report),
        encoding="utf-8",
    )
    example_path.write_text(
        json.dumps(report["example_event"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_followup_transition_event_contract_markdown_v1(report: dict[str, object]) -> str:
    lines = [
        "# follow-up transition event contract v1",
        "",
        f"- dataset_path: {report['dataset_path']}",
        f"- case_count: {report['case_count']}",
        f"- user_count: {report['user_count']}",
        f"- schema_version: {report['schema_version']}",
        f"- valid_case_count: {report['valid_case_count']}",
        f"- invalid_case_count: {report['invalid_case_count']}",
        f"- example_record_id: {report['example_record_id']}",
        "",
        "## connected flows",
        "",
    ]
    for flow_name, fields in report["connected_flows"].items():
        lines.append(f"- {flow_name}: {', '.join(fields)}")

    lines.extend(
        [
            "",
            "## not directly connected in this contract",
            "",
            "- " + ", ".join(report["not_directly_connected_in_this_contract"]),
            "",
            "## validation",
            "",
            f"- invalid_record_ids: {report['invalid_record_ids']}",
            "",
            "## example event preview",
            "",
            f"- next_action: {report['example_event']['next_action']}",
            f"- closed_loop_state: {report['example_event']['closed_loop_state']}",
            f"- safety_status: {report['example_event']['safety_status']}",
            f"- adverse_event: {report['example_event']['adverse_event']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _expected_closed_loop_state(event: FollowUpTransitionEventV1) -> str:
    return project_followup_closed_loop_state(
        action=event.next_action,
        trajectory_step=event.trajectory_step,
        adverse_event=event.adverse_event,
    )


def _read_value(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        return payload[key]
    return getattr(payload, key)


__all__ = [
    "FOLLOWUP_TRANSITION_EVENT_SCHEMA_VERSION_V1",
    "FollowUpTransitionEventV1",
    "build_followup_transition_event_v1",
    "render_followup_transition_event_contract_markdown_v1",
    "summarize_followup_transition_event_contract_v1",
    "validate_followup_transition_event_v1",
    "write_followup_transition_event_contract_report_v1",
]
