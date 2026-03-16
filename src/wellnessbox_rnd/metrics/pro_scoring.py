from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from wellnessbox_rnd.schemas.recommendation import RecommendationGoal
from wellnessbox_rnd.synthetic.rich_longitudinal_v2 import RichSyntheticCohortRecord

PRO_FORM_SCHEMA_VERSION_V1 = "pro_form_schema_v1"
PRO_SCORE_ORIENTATION_V1 = "lower_is_better_for_problem_score"


class PROItemSchemaV1(BaseModel):
    item_key: str
    prompt_label: str
    response_min: int = Field(default=0, ge=0)
    response_max: int = Field(default=4, ge=0)


class PRODomainFormSchemaV1(BaseModel):
    domain_key: RecommendationGoal
    display_name: str
    baseline_form_key: str
    follow_up_form_key: str
    score_orientation: Literal["lower_is_better_for_problem_score"] = (
        PRO_SCORE_ORIENTATION_V1
    )
    items: list[PROItemSchemaV1] = Field(min_length=1)


class PROFormSchemaV1(BaseModel):
    schema_version: str = PRO_FORM_SCHEMA_VERSION_V1
    timepoints: tuple[Literal["baseline"], Literal["follow_up"]] = ("baseline", "follow_up")
    domains: list[PRODomainFormSchemaV1] = Field(min_length=1)


class PROFormResponseV1(BaseModel):
    schema_version: str = PRO_FORM_SCHEMA_VERSION_V1
    timepoint: Literal["baseline", "follow_up"]
    domain_item_scores: dict[str, dict[str, int]] = Field(default_factory=dict)


def build_default_pro_form_schema_v1() -> PROFormSchemaV1:
    return PROFormSchemaV1(
        domains=[
            _domain_schema(
                RecommendationGoal.STRESS_SUPPORT,
                "Stress support",
                [
                    ("perceived_stress_load", "How heavy did your stress feel?"),
                    ("tension_burden", "How tense did your body feel?"),
                    ("calm_recovery_delay", "How hard was it to settle down?"),
                    ("stress_resilience_drop", "How much did stress affect your function?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.SLEEP_SUPPORT,
                "Sleep support",
                [
                    ("sleep_latency_burden", "How hard was it to fall asleep?"),
                    ("nighttime_awakenings", "How disruptive were nighttime awakenings?"),
                    ("sleep_duration_shortfall", "How short did your sleep feel?"),
                    ("wake_refreshment_deficit", "How unrefreshed did you feel on waking?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.IMMUNITY_SUPPORT,
                "Immunity support",
                [
                    ("infection_susceptibility", "How vulnerable did you feel to illness?"),
                    ("recovery_delay", "How slow was recovery from minor illness?"),
                    (
                        "sore_throat_nasal_burden",
                        "How much upper-respiratory discomfort was present?",
                    ),
                    ("immune_fatigue_burden", "How much fatigue followed immune stress?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.ENERGY_SUPPORT,
                "Energy support",
                [
                    ("morning_fatigue", "How fatigued did you feel in the morning?"),
                    ("afternoon_energy_crash", "How strong was your afternoon energy crash?"),
                    ("activity_tolerance_drop", "How limited was your activity tolerance?"),
                    ("daylong_fatigue_burden", "How heavy did daily fatigue feel?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.GUT_HEALTH,
                "Gut health",
                [
                    ("bloating_burden", "How much bloating bothered you?"),
                    ("abdominal_discomfort", "How much abdominal discomfort was present?"),
                    ("bowel_irregularity", "How irregular was your digestion?"),
                    ("meal_tolerance_drop", "How difficult was it to tolerate meals?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.BONE_JOINT,
                "Bone and joint",
                [
                    ("joint_stiffness", "How much joint stiffness was present?"),
                    ("pain_burden", "How much pain limited you?"),
                    ("mobility_drop", "How reduced did your mobility feel?"),
                    ("load_tolerance_drop", "How hard was it to tolerate physical load?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.HEART_HEALTH,
                "Heart health",
                [
                    ("exertion_intolerance", "How limited were you during exertion?"),
                    ("resting_recovery_delay", "How slow was your recovery after effort?"),
                    ("palpitation_burden", "How much did palpitations bother you?"),
                    ("chest_discomfort_burden", "How much chest discomfort was present?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.BLOOD_GLUCOSE,
                "Blood glucose",
                [
                    ("post_meal_crash", "How strong was your post-meal crash?"),
                    (
                        "carb_tolerance_drop",
                        "How poorly did you tolerate carbohydrate-heavy meals?",
                    ),
                    ("hunger_instability", "How unstable did your hunger feel?"),
                    ("glucose_symptom_burden", "How much did glucose swings affect you?"),
                ],
            ),
            _domain_schema(
                RecommendationGoal.GENERAL_WELLNESS,
                "General wellness",
                [
                    ("overall_wellbeing_drop", "How reduced did overall wellbeing feel?"),
                    ("daily_function_drop", "How limited was daily function?"),
                    ("recovery_quality_drop", "How poor was your recovery quality?"),
                    ("resilience_drop", "How reduced did your general resilience feel?"),
                ],
            ),
        ]
    )


def validate_pro_form_response_v1(
    response: PROFormResponseV1 | dict[str, object],
    schema: PROFormSchemaV1,
) -> list[str]:
    issues: list[str] = []
    response_model = (
        response
        if isinstance(response, PROFormResponseV1)
        else PROFormResponseV1.model_validate(response)
    )
    domain_map = {domain.domain_key.value: domain for domain in schema.domains}

    for domain_key, item_scores in response_model.domain_item_scores.items():
        if domain_key not in domain_map:
            issues.append(f"unknown_domain::{domain_key}")
            continue
        item_map = {item.item_key: item for item in domain_map[domain_key].items}
        for item_key, score in item_scores.items():
            if item_key not in item_map:
                issues.append(f"unknown_item::{domain_key}::{item_key}")
                continue
            item_schema = item_map[item_key]
            if not item_schema.response_min <= score <= item_schema.response_max:
                issues.append(f"score_out_of_range::{domain_key}::{item_key}::{score}")
        missing_items = sorted(set(item_map) - set(item_scores))
        for item_key in missing_items:
            issues.append(f"missing_item::{domain_key}::{item_key}")

    missing_domains = sorted(set(domain_map) - set(response_model.domain_item_scores))
    for domain_key in missing_domains:
        issues.append(f"missing_domain::{domain_key}")

    return issues


def summarize_pro_form_contract_v1(
    records: list[RichSyntheticCohortRecord],
    *,
    dataset_path: str | Path,
) -> dict[str, object]:
    schema = build_default_pro_form_schema_v1()
    domain_keys = [domain.domain_key.value for domain in schema.domains]
    baseline_domain_coverage_pct = {
        domain_key: _domain_coverage_pct(records, domain_key, timepoint="baseline")
        for domain_key in domain_keys
    }
    follow_up_domain_coverage_pct = {
        domain_key: _domain_coverage_pct(records, domain_key, timepoint="follow_up")
        for domain_key in domain_keys
    }
    all_baseline_present = sum(
        1
        for record in records
        if all(domain_key in record.baseline_pro.domain_z for domain_key in domain_keys)
    )
    all_follow_up_present = sum(
        1
        for record in records
        if all(domain_key in record.follow_up_pro.domain_z for domain_key in domain_keys)
    )
    return {
        "contract_id": "pro_scoring_contract_v1",
        "schema_version": schema.schema_version,
        "dataset_path": str(dataset_path),
        "case_count": len(records),
        "user_count": len({record.user_id for record in records}),
        "timepoints": list(schema.timepoints),
        "domain_count": len(schema.domains),
        "domain_item_counts": {
            domain.domain_key.value: len(domain.items) for domain in schema.domains
        },
        "score_orientation": PRO_SCORE_ORIENTATION_V1,
        "synthetic_alignment": {
            "baseline_domain_coverage_pct": baseline_domain_coverage_pct,
            "follow_up_domain_coverage_pct": follow_up_domain_coverage_pct,
            "all_schema_domains_present_baseline_case_count": all_baseline_present,
            "all_schema_domains_present_follow_up_case_count": all_follow_up_present,
        },
        "sample_form_stub": {
            "baseline": _build_empty_form_stub(schema, timepoint="baseline"),
            "follow_up": _build_empty_form_stub(schema, timepoint="follow_up"),
        },
    }


def write_pro_form_contract_report_v1(
    report: dict[str, object],
    *,
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_pro_form_contract_markdown_v1(report), encoding="utf-8")


def render_pro_form_contract_markdown_v1(report: dict[str, object]) -> str:
    lines = [
        "# pro scoring contract v1",
        "",
        f"- dataset_path: {report['dataset_path']}",
        f"- case_count: {report['case_count']}",
        f"- user_count: {report['user_count']}",
        f"- schema_version: {report['schema_version']}",
        f"- domain_count: {report['domain_count']}",
        f"- timepoints: {report['timepoints']}",
        f"- score_orientation: {report['score_orientation']}",
        "",
        "## domain item counts",
        "",
        "| domain | item_count |",
        "| --- | --- |",
    ]
    for domain_key, item_count in report["domain_item_counts"].items():
        lines.append(f"| {domain_key} | {item_count} |")

    lines.extend(["", "## synthetic alignment", ""])
    lines.append(
        "- all_schema_domains_present_baseline_case_count: "
        f"{report['synthetic_alignment']['all_schema_domains_present_baseline_case_count']}"
    )
    lines.append(
        "- all_schema_domains_present_follow_up_case_count: "
        f"{report['synthetic_alignment']['all_schema_domains_present_follow_up_case_count']}"
    )
    lines.extend(["", "| domain | baseline_pct | follow_up_pct |", "| --- | --- | --- |"])
    for domain_key in report["domain_item_counts"]:
        lines.append(
            "| "
            f"{domain_key} | "
            f"{report['synthetic_alignment']['baseline_domain_coverage_pct'][domain_key]} | "
            f"{report['synthetic_alignment']['follow_up_domain_coverage_pct'][domain_key]} |"
        )

    lines.extend(
        [
            "",
            "## sample form stub",
            "",
            "- baseline domains: "
            f"{sorted(report['sample_form_stub']['baseline']['domain_item_scores'])}",
            "- follow_up domains: "
            f"{sorted(report['sample_form_stub']['follow_up']['domain_item_scores'])}",
        ]
    )
    return "\n".join(lines) + "\n"


def _domain_schema(
    domain_key: RecommendationGoal,
    display_name: str,
    items: list[tuple[str, str]],
) -> PRODomainFormSchemaV1:
    return PRODomainFormSchemaV1(
        domain_key=domain_key,
        display_name=display_name,
        baseline_form_key=f"pro::{domain_key.value}::baseline_v1",
        follow_up_form_key=f"pro::{domain_key.value}::follow_up_v1",
        items=[
            PROItemSchemaV1(item_key=item_key, prompt_label=prompt_label)
            for item_key, prompt_label in items
        ],
    )


def _build_empty_form_stub(
    schema: PROFormSchemaV1,
    *,
    timepoint: Literal["baseline", "follow_up"],
) -> dict[str, object]:
    return PROFormResponseV1(
        timepoint=timepoint,
        domain_item_scores={
            domain.domain_key.value: {item.item_key: 0 for item in domain.items}
            for domain in schema.domains
        },
    ).model_dump(mode="json")


def _domain_coverage_pct(
    records: list[RichSyntheticCohortRecord],
    domain_key: str,
    *,
    timepoint: Literal["baseline", "follow_up"],
) -> float:
    if not records:
        return 0.0
    present_count = sum(
        1
        for record in records
        if domain_key
        in (
            record.baseline_pro.domain_z
            if timepoint == "baseline"
            else record.follow_up_pro.domain_z
        )
    )
    return round(100.0 * present_count / len(records), 3)


__all__ = [
    "PRODomainFormSchemaV1",
    "PROFormResponseV1",
    "PROFormSchemaV1",
    "PROItemSchemaV1",
    "PRO_FORM_SCHEMA_VERSION_V1",
    "PRO_SCORE_ORIENTATION_V1",
    "build_default_pro_form_schema_v1",
    "render_pro_form_contract_markdown_v1",
    "summarize_pro_form_contract_v1",
    "validate_pro_form_response_v1",
    "write_pro_form_contract_report_v1",
]
