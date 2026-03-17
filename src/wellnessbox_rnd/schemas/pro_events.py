from __future__ import annotations

import json
from math import erf, sqrt
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from wellnessbox_rnd.schemas.recommendation import NextAction, RecommendationGoal

BASELINE_FOLLOWUP_PRO_EVENT_SCHEMA_VERSION_V1 = "baseline_followup_pro_event_v1"
PRO_EVENT_TIMEPOINTS_V1 = ("baseline", "follow_up")
PRO_EVENT_DELTA_TOLERANCE = 1e-6
PRO_EVENT_PERCENTILE_TOLERANCE = 1e-6


class PROTimepointSnapshotV1(BaseModel):
    timepoint: str
    aggregate_z: float
    domain_z: dict[str, float] = Field(default_factory=dict)
    aggregate_percentile: float | None = None
    domain_percentile: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def populate_percentiles(self) -> PROTimepointSnapshotV1:
        self.aggregate_percentile = _z_to_percentile(self.aggregate_z)
        self.domain_percentile = {
            domain_key: _z_to_percentile(z_value)
            for domain_key, z_value in self.domain_z.items()
        }
        return self


class BaselineFollowUpPROEventV1(BaseModel):
    schema_version: str = BASELINE_FOLLOWUP_PRO_EVENT_SCHEMA_VERSION_V1
    record_id: str
    user_id: str
    cohort_version: str
    trajectory_step: int = Field(ge=0)
    day_index: int = Field(ge=0)
    recommendation_goals: list[RecommendationGoal] = Field(default_factory=list)
    follow_up_next_action: NextAction
    adverse_event: bool = False
    baseline: PROTimepointSnapshotV1
    follow_up: PROTimepointSnapshotV1
    delta_z_by_domain: dict[str, float] = Field(default_factory=dict)


def build_baseline_followup_pro_event_v1(
    record: Any,
) -> BaselineFollowUpPROEventV1:
    request = _read_value(record, "request")
    labels = _read_value(record, "labels")
    baseline_pro = _read_value(record, "baseline_pro")
    follow_up_pro = _read_value(record, "follow_up_pro")
    return BaselineFollowUpPROEventV1(
        record_id=_read_value(record, "record_id"),
        user_id=_read_value(record, "user_id"),
        cohort_version=_read_value(record, "cohort_version"),
        trajectory_step=_read_value(record, "trajectory_step"),
        day_index=_read_value(record, "day_index"),
        recommendation_goals=list(_read_value(request, "goals")),
        follow_up_next_action=_read_value(labels, "next_action"),
        adverse_event=_read_value(labels, "adverse_event"),
        baseline=PROTimepointSnapshotV1(
            timepoint="baseline",
            aggregate_z=_read_value(baseline_pro, "aggregate_z"),
            domain_z=dict(_read_value(baseline_pro, "domain_z")),
        ),
        follow_up=PROTimepointSnapshotV1(
            timepoint="follow_up",
            aggregate_z=_read_value(follow_up_pro, "aggregate_z"),
            domain_z=dict(_read_value(follow_up_pro, "domain_z")),
        ),
        delta_z_by_domain=dict(_read_value(record, "delta_z_by_domain")),
    )


def validate_baseline_followup_pro_event_v1(
    event: BaselineFollowUpPROEventV1 | dict[str, object],
) -> list[str]:
    model = (
        event
        if isinstance(event, BaselineFollowUpPROEventV1)
        else BaselineFollowUpPROEventV1.model_validate(event)
    )
    issues: list[str] = []
    allowed_domains = {goal.value for goal in RecommendationGoal}
    baseline_domains = set(model.baseline.domain_z)
    follow_up_domains = set(model.follow_up.domain_z)
    delta_domains = set(model.delta_z_by_domain)
    baseline_percentile_domains = set(model.baseline.domain_percentile)
    follow_up_percentile_domains = set(model.follow_up.domain_percentile)

    if model.baseline.timepoint != "baseline":
        issues.append(f"unexpected_timepoint::{model.baseline.timepoint}")
    if model.follow_up.timepoint != "follow_up":
        issues.append(f"unexpected_timepoint::{model.follow_up.timepoint}")

    unknown_baseline_domains = sorted(baseline_domains - allowed_domains)
    unknown_follow_up_domains = sorted(follow_up_domains - allowed_domains)
    unknown_delta_domains = sorted(delta_domains - allowed_domains)
    issues.extend(f"unknown_domain::baseline::{domain}" for domain in unknown_baseline_domains)
    issues.extend(f"unknown_domain::follow_up::{domain}" for domain in unknown_follow_up_domains)
    issues.extend(f"unknown_domain::delta::{domain}" for domain in unknown_delta_domains)

    if baseline_domains != follow_up_domains:
        issues.append("domain_mismatch::baseline_vs_follow_up")
    if baseline_domains != delta_domains:
        issues.append("domain_mismatch::baseline_vs_delta")
    if baseline_domains != baseline_percentile_domains:
        issues.append("domain_mismatch::baseline_vs_baseline_percentile")
    if follow_up_domains != follow_up_percentile_domains:
        issues.append("domain_mismatch::follow_up_vs_follow_up_percentile")

    expected_baseline_percentile = _z_to_percentile(model.baseline.aggregate_z)
    if (
        abs(model.baseline.aggregate_percentile - expected_baseline_percentile)
        > PRO_EVENT_PERCENTILE_TOLERANCE
    ):
        issues.append(
            "aggregate_percentile_mismatch::baseline::"
            f"{expected_baseline_percentile}::{round(model.baseline.aggregate_percentile, 6)}"
        )
    expected_follow_up_percentile = _z_to_percentile(model.follow_up.aggregate_z)
    if (
        abs(model.follow_up.aggregate_percentile - expected_follow_up_percentile)
        > PRO_EVENT_PERCENTILE_TOLERANCE
    ):
        issues.append(
            "aggregate_percentile_mismatch::follow_up::"
            f"{expected_follow_up_percentile}::{round(model.follow_up.aggregate_percentile, 6)}"
        )

    for domain_key in sorted(baseline_domains & follow_up_domains & delta_domains):
        expected_delta = model.follow_up.domain_z[domain_key] - model.baseline.domain_z[domain_key]
        actual_delta = model.delta_z_by_domain[domain_key]
        if abs(expected_delta - actual_delta) > PRO_EVENT_DELTA_TOLERANCE:
            issues.append(
                "delta_mismatch::"
                f"{domain_key}::{round(expected_delta, 6)}::{round(actual_delta, 6)}"
            )
        expected_baseline_domain_percentile = _z_to_percentile(model.baseline.domain_z[domain_key])
        if (
            abs(
                model.baseline.domain_percentile[domain_key]
                - expected_baseline_domain_percentile
            )
            > PRO_EVENT_PERCENTILE_TOLERANCE
        ):
            issues.append(
                "domain_percentile_mismatch::baseline::"
                f"{domain_key}::{expected_baseline_domain_percentile}::"
                f"{round(model.baseline.domain_percentile[domain_key], 6)}"
            )
        expected_follow_up_domain_percentile = _z_to_percentile(
            model.follow_up.domain_z[domain_key]
        )
        if (
            abs(
                model.follow_up.domain_percentile[domain_key]
                - expected_follow_up_domain_percentile
            )
            > PRO_EVENT_PERCENTILE_TOLERANCE
        ):
            issues.append(
                "domain_percentile_mismatch::follow_up::"
                f"{domain_key}::{expected_follow_up_domain_percentile}::"
                f"{round(model.follow_up.domain_percentile[domain_key], 6)}"
            )

    return issues


def summarize_baseline_followup_pro_event_contract_v1(
    records: list[Any],
    *,
    dataset_path: str | Path,
) -> dict[str, object]:
    events = [build_baseline_followup_pro_event_v1(record) for record in records]
    invalid_records: dict[str, list[str]] = {}
    for event in events:
        issues = validate_baseline_followup_pro_event_v1(event)
        if issues:
            invalid_records[event.record_id] = issues

    sample_event = events[0] if events else None
    return {
        "contract_id": BASELINE_FOLLOWUP_PRO_EVENT_SCHEMA_VERSION_V1,
        "dataset_path": str(dataset_path),
        "case_count": len(records),
        "user_count": len({_read_value(record, "user_id") for record in records}),
        "schema_version": BASELINE_FOLLOWUP_PRO_EVENT_SCHEMA_VERSION_V1,
        "timepoints": list(PRO_EVENT_TIMEPOINTS_V1),
        "domain_count": len(sample_event.baseline.domain_z) if sample_event else 0,
        "valid_case_count": len(records) - len(invalid_records),
        "invalid_case_count": len(invalid_records),
        "invalid_record_ids": sorted(invalid_records),
        "connected_flows": {
            "recommendation": [
                "recommendation_goals",
                "follow_up_next_action",
            ],
            "pro_scoring": [
                "baseline.aggregate_z",
                "baseline.aggregate_percentile",
                "follow_up.aggregate_z",
                "follow_up.aggregate_percentile",
                "delta_z_by_domain",
            ],
            "effect_training_and_eval": [
                "record_id",
                "user_id",
                "delta_z_by_domain",
            ],
            "closed_loop_follow_up": [
                "trajectory_step",
                "day_index",
                "follow_up_next_action",
                "adverse_event",
            ],
        },
        "not_directly_connected_in_this_contract": [
            "safety_evidence_linkage",
            "wearable_cgm_gene_normalized_event",
        ],
        "example_record_id": sample_event.record_id if sample_event else None,
        "example_event": sample_event.model_dump(mode="json") if sample_event else None,
    }


def write_baseline_followup_pro_event_contract_report_v1(
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
        render_baseline_followup_pro_event_contract_markdown_v1(report),
        encoding="utf-8",
    )
    example_path.write_text(
        json.dumps(report["example_event"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_baseline_followup_pro_event_contract_markdown_v1(report: dict[str, object]) -> str:
    lines = [
        "# baseline follow-up pro event contract v1",
        "",
        f"- dataset_path: {report['dataset_path']}",
        f"- case_count: {report['case_count']}",
        f"- user_count: {report['user_count']}",
        f"- schema_version: {report['schema_version']}",
        f"- timepoints: {report['timepoints']}",
        f"- domain_count: {report['domain_count']}",
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
            f"- follow_up_next_action: {report['example_event']['follow_up_next_action']}",
            f"- recommendation_goals: {report['example_event']['recommendation_goals']}",
            f"- adverse_event: {report['example_event']['adverse_event']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_value(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        return payload[key]
    return getattr(payload, key)


def _z_to_percentile(z_value: float) -> float:
    return round(100.0 * (0.5 * (1.0 + erf(z_value / sqrt(2.0)))), 6)


__all__ = [
    "BASELINE_FOLLOWUP_PRO_EVENT_SCHEMA_VERSION_V1",
    "BaselineFollowUpPROEventV1",
    "PROTimepointSnapshotV1",
    "build_baseline_followup_pro_event_v1",
    "render_baseline_followup_pro_event_contract_markdown_v1",
    "summarize_baseline_followup_pro_event_contract_v1",
    "validate_baseline_followup_pro_event_v1",
    "write_baseline_followup_pro_event_contract_report_v1",
]
