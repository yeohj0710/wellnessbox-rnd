from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import NormalizedSensorGeneticSnapshot

CGM_NORMALIZED_EVENT_SCHEMA_VERSION_V1 = "cgm_normalized_event_v1"


class CGMEvalIntegrationProjectionV1(BaseModel):
    attempted: int = Field(ge=0, default=0)
    success: int = Field(ge=0, default=0)


class CGMReplayBridgeProjectionV1(BaseModel):
    cgm_available: float
    parser_mean_glucose_mg_dl: float | None = None
    parser_time_in_range_pct: float | None = None
    parser_time_in_range_low_mg_dl: float | None = None
    parser_time_in_range_high_mg_dl: float | None = None
    parser_post_meal_spike_concern: float = 0.0


class CGMNormalizedEventV1(BaseModel):
    schema_version: str = CGM_NORMALIZED_EVENT_SCHEMA_VERSION_V1
    source_format: str = "cgm_summary.csv"
    cgm_available: bool
    mean_glucose_mg_dl: float | None = None
    time_in_range_pct: float | None = None
    time_in_range_low_mg_dl: float | None = None
    time_in_range_high_mg_dl: float | None = None
    post_meal_spike_concern: bool = False
    normalization_notes: list[str] = Field(default_factory=list)
    threshold_tags: list[str] = Field(default_factory=list)
    eval_integration_projection: dict[str, CGMEvalIntegrationProjectionV1]
    replay_bridge_projection: CGMReplayBridgeProjectionV1


def build_cgm_normalized_event_v1(
    snapshot: NormalizedSensorGeneticSnapshot | dict[str, Any],
) -> CGMNormalizedEventV1:
    model = (
        snapshot
        if isinstance(snapshot, NormalizedSensorGeneticSnapshot)
        else NormalizedSensorGeneticSnapshot.model_validate(snapshot)
    )
    integration_success = int(
        model.cgm_available
        and model.mean_glucose_mg_dl is not None
        and model.time_in_range_pct is not None
    )
    return CGMNormalizedEventV1(
        cgm_available=model.cgm_available,
        mean_glucose_mg_dl=model.mean_glucose_mg_dl,
        time_in_range_pct=model.time_in_range_pct,
        time_in_range_low_mg_dl=model.time_in_range_low_mg_dl,
        time_in_range_high_mg_dl=model.time_in_range_high_mg_dl,
        post_meal_spike_concern=model.post_meal_spike_concern,
        normalization_notes=list(model.normalization_notes),
        threshold_tags=_build_threshold_tags(model),
        eval_integration_projection={
            "cgm": CGMEvalIntegrationProjectionV1(
                attempted=int(model.cgm_available),
                success=integration_success,
            )
        },
        replay_bridge_projection=CGMReplayBridgeProjectionV1(
            cgm_available=float(model.cgm_available),
            parser_mean_glucose_mg_dl=model.mean_glucose_mg_dl,
            parser_time_in_range_pct=model.time_in_range_pct,
            parser_time_in_range_low_mg_dl=model.time_in_range_low_mg_dl,
            parser_time_in_range_high_mg_dl=model.time_in_range_high_mg_dl,
            parser_post_meal_spike_concern=float(model.post_meal_spike_concern),
        ),
    )


def validate_cgm_normalized_event_v1(
    event: CGMNormalizedEventV1 | dict[str, Any],
) -> list[str]:
    model = (
        event
        if isinstance(event, CGMNormalizedEventV1)
        else CGMNormalizedEventV1.model_validate(event)
    )
    issues: list[str] = []
    projection = model.eval_integration_projection.get("cgm")
    if projection is None:
        issues.append("missing_eval_projection::cgm")
        return issues

    expected_attempted = int(model.cgm_available)
    expected_success = int(
        model.cgm_available
        and model.mean_glucose_mg_dl is not None
        and model.time_in_range_pct is not None
    )
    if projection.attempted != expected_attempted:
        issues.append(
            f"eval_projection_mismatch::attempted::{expected_attempted}::{projection.attempted}"
        )
    if projection.success != expected_success:
        issues.append(
            f"eval_projection_mismatch::success::{expected_success}::{projection.success}"
        )
    if model.replay_bridge_projection.cgm_available != float(model.cgm_available):
        issues.append("replay_projection_mismatch::cgm_available")
    if (
        model.replay_bridge_projection.parser_time_in_range_pct
        != model.time_in_range_pct
    ):
        issues.append("replay_projection_mismatch::time_in_range_pct")
    if (
        model.replay_bridge_projection.parser_time_in_range_low_mg_dl
        != model.time_in_range_low_mg_dl
    ):
        issues.append("replay_projection_mismatch::time_in_range_low_mg_dl")
    if (
        model.replay_bridge_projection.parser_time_in_range_high_mg_dl
        != model.time_in_range_high_mg_dl
    ):
        issues.append("replay_projection_mismatch::time_in_range_high_mg_dl")
    return issues


def summarize_cgm_normalized_event_bridge_v1(
    event: CGMNormalizedEventV1 | dict[str, Any],
    *,
    source_fixture_path: str | Path,
) -> dict[str, Any]:
    model = (
        event
        if isinstance(event, CGMNormalizedEventV1)
        else CGMNormalizedEventV1.model_validate(event)
    )
    issues = validate_cgm_normalized_event_v1(model)
    return {
        "contract_id": CGM_NORMALIZED_EVENT_SCHEMA_VERSION_V1,
        "source_fixture_path": str(source_fixture_path),
        "schema_version": model.schema_version,
        "valid": not issues,
        "validation_issues": issues,
        "connected_flows": {
            "cgm_parser": [
                "mean_glucose_mg_dl",
                "time_in_range_pct",
                "time_in_range_low_mg_dl",
                "time_in_range_high_mg_dl",
                "post_meal_spike_concern",
            ],
            "cgm_eval_slice": [
                "eval_integration_projection.cgm.attempted",
                "eval_integration_projection.cgm.success",
            ],
            "cgm_replay_analysis": [
                "replay_bridge_projection.cgm_available",
                "replay_bridge_projection.parser_mean_glucose_mg_dl",
                "replay_bridge_projection.parser_time_in_range_pct",
                "replay_bridge_projection.parser_time_in_range_low_mg_dl",
                "replay_bridge_projection.parser_time_in_range_high_mg_dl",
                "threshold_tags",
            ],
        },
        "event": model.model_dump(mode="json"),
    }


def summarize_cgm_slice_bridge_v1(
    events: list[CGMNormalizedEventV1 | dict[str, Any]],
    *,
    source_cases_path: str | Path,
    case_ids: list[str] | None = None,
) -> dict[str, Any]:
    normalized_events = [
        (
            item
            if isinstance(item, CGMNormalizedEventV1)
            else CGMNormalizedEventV1.model_validate(item)
        )
        for item in events
    ]
    resolved_case_ids = case_ids or [f"cgm_case_{index}" for index in range(len(normalized_events))]
    threshold_tag_counts: dict[str, int] = {}
    parser_failure_type_counts: dict[str, int] = {}
    threshold_edge_case_ids: list[str] = []
    valid_case_count = 0

    for case_id, event in zip(resolved_case_ids, normalized_events, strict=True):
        issues = validate_cgm_normalized_event_v1(event)
        if not issues:
            valid_case_count += 1
        for tag in event.threshold_tags:
            threshold_tag_counts[tag] = threshold_tag_counts.get(tag, 0) + 1
        for note in event.normalization_notes:
            if note.endswith("_invalid_numeric_ignored"):
                parser_failure_type_counts[note] = parser_failure_type_counts.get(note, 0) + 1
        if any(
            tag in event.threshold_tags
            for tag in ("mean_glucose_near_126_mg_dl_pm_10", "time_in_range_near_70_pct_pm_5")
        ):
            threshold_edge_case_ids.append(case_id)

    return {
        "contract_id": "cgm_slice_bridge_summary_v1",
        "source_cases_path": str(source_cases_path),
        "case_count": len(normalized_events),
        "valid_case_count": valid_case_count,
        "invalid_case_count": len(normalized_events) - valid_case_count,
        "eval_attempted_count": sum(
            event.eval_integration_projection["cgm"].attempted for event in normalized_events
        ),
        "eval_success_count": sum(
            event.eval_integration_projection["cgm"].success for event in normalized_events
        ),
        "threshold_tag_counts": threshold_tag_counts,
        "parser_failure_type_counts": parser_failure_type_counts,
        "threshold_edge_case_ids": threshold_edge_case_ids,
        "connected_flows": {
            "parser_to_cgm_event": [
                "normalization_notes",
                "mean_glucose_mg_dl",
                "time_in_range_pct",
                "time_in_range_low_mg_dl",
                "time_in_range_high_mg_dl",
            ],
            "cgm_weakest_slice_audit": [
                "threshold_tag_counts",
                "parser_failure_type_counts",
                "threshold_edge_case_ids",
                "eval_success_count",
            ],
            "replay_readiness": [
                "replay_bridge_projection.parser_mean_glucose_mg_dl",
                "replay_bridge_projection.parser_time_in_range_pct",
                "replay_bridge_projection.parser_time_in_range_low_mg_dl",
                "replay_bridge_projection.parser_time_in_range_high_mg_dl",
                "replay_bridge_projection.parser_post_meal_spike_concern",
            ],
        },
        "cases": [
            {
                "case_id": case_id,
                "threshold_tags": event.threshold_tags,
                "normalization_notes": event.normalization_notes,
                "eval_success": event.eval_integration_projection["cgm"].success,
                "replay_bridge_projection": event.replay_bridge_projection.model_dump(mode="json"),
            }
            for case_id, event in zip(resolved_case_ids, normalized_events, strict=True)
        ],
    }


def write_cgm_normalized_event_bridge_report_v1(
    report: dict[str, Any],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_cgm_normalized_event_bridge_markdown_v1(report), encoding="utf-8")


def render_cgm_normalized_event_bridge_markdown_v1(report: dict[str, Any]) -> str:
    event = report["event"]
    lines = [
        "# cgm normalized event bridge v1",
        "",
        f"- source_fixture_path: {report['source_fixture_path']}",
        f"- schema_version: {report['schema_version']}",
        f"- valid: {report['valid']}",
        f"- validation_issues: {report['validation_issues']}",
        "",
        "## event summary",
        "",
        f"- cgm_available: {event['cgm_available']}",
        f"- mean_glucose_mg_dl: {event['mean_glucose_mg_dl']}",
        f"- time_in_range_pct: {event['time_in_range_pct']}",
        f"- post_meal_spike_concern: {event['post_meal_spike_concern']}",
        f"- threshold_tags: {event['threshold_tags']}",
        "",
        "## connected flows",
        "",
    ]
    for flow_name, fields in report["connected_flows"].items():
        lines.append(f"- {flow_name}: {', '.join(fields)}")
    return "\n".join(lines) + "\n"


def write_cgm_slice_bridge_report_v1(
    report: dict[str, Any],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_cgm_slice_bridge_markdown_v1(report), encoding="utf-8")


def render_cgm_slice_bridge_markdown_v1(report: dict[str, Any]) -> str:
    lines = [
        "# cgm slice bridge summary v1",
        "",
        f"- source_cases_path: {report['source_cases_path']}",
        f"- case_count: {report['case_count']}",
        f"- valid_case_count: {report['valid_case_count']}",
        f"- invalid_case_count: {report['invalid_case_count']}",
        f"- eval_attempted_count: {report['eval_attempted_count']}",
        f"- eval_success_count: {report['eval_success_count']}",
        f"- threshold_tag_counts: {report['threshold_tag_counts']}",
        f"- parser_failure_type_counts: {report['parser_failure_type_counts']}",
        f"- threshold_edge_case_ids: {report['threshold_edge_case_ids']}",
        "",
        "## connected flows",
        "",
    ]
    for flow_name, fields in report["connected_flows"].items():
        lines.append(f"- {flow_name}: {', '.join(fields)}")
    lines.extend(["", "## cases", ""])
    for case in report["cases"]:
        lines.append(
            f"- `{case['case_id']}`: tags=`{case['threshold_tags']}`, "
            f"notes=`{case['normalization_notes']}`, eval_success=`{case['eval_success']}`"
        )
    return "\n".join(lines) + "\n"


def _build_threshold_tags(snapshot: NormalizedSensorGeneticSnapshot) -> list[str]:
    tags: list[str] = []
    if not snapshot.cgm_available:
        return tags
    tags.append("cgm_available")
    if snapshot.mean_glucose_mg_dl is not None:
        if abs(snapshot.mean_glucose_mg_dl - 126.0) <= 10.0:
            tags.append("mean_glucose_near_126_mg_dl_pm_10")
        if snapshot.mean_glucose_mg_dl >= 140.0:
            tags.append("mean_glucose_high_ge_140")
    if (
        snapshot.time_in_range_pct is not None
        and snapshot.time_in_range_low_mg_dl == 70.0
        and snapshot.time_in_range_high_mg_dl == 180.0
        and abs(snapshot.time_in_range_pct - 70.0) <= 5.0
    ):
        tags.append("time_in_range_near_70_pct_pm_5")
    if snapshot.post_meal_spike_concern:
        tags.append("post_meal_spike_flagged")
    return tags


__all__ = [
    "CGM_NORMALIZED_EVENT_SCHEMA_VERSION_V1",
    "CGMEvalIntegrationProjectionV1",
    "CGMNormalizedEventV1",
    "CGMReplayBridgeProjectionV1",
    "build_cgm_normalized_event_v1",
    "render_cgm_normalized_event_bridge_markdown_v1",
    "render_cgm_slice_bridge_markdown_v1",
    "summarize_cgm_normalized_event_bridge_v1",
    "summarize_cgm_slice_bridge_v1",
    "validate_cgm_normalized_event_v1",
    "write_cgm_normalized_event_bridge_report_v1",
    "write_cgm_slice_bridge_report_v1",
]
