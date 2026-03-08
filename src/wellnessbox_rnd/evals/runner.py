import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from wellnessbox_rnd.metrics.calculators import (
    average_metric,
    count_adverse_events,
    explanation_term_coverage_pct,
    integration_modality_breakdown,
    metric_passed,
    percentile_improvement_pp,
    recommendation_coverage_pct,
    safety_reference_accuracy_pct,
    sensor_genetic_integration_rate_pct,
)
from wellnessbox_rnd.metrics.definitions import METRIC_DEFINITIONS
from wellnessbox_rnd.orchestration.recommendation_service import recommend
from wellnessbox_rnd.schemas.recommendation import (
    NextAction,
    RecommendationRequest,
    RecommendationStatus,
)


class RecommendationReference(BaseModel):
    required_ingredients: list[str] = Field(default_factory=list)


class ExpectedEvalOutcome(BaseModel):
    recommendation_reference: RecommendationReference = Field(
        default_factory=RecommendationReference
    )
    expected_status: RecommendationStatus | None = None
    expected_next_action: NextAction | None = None
    required_rule_ids: list[str] = Field(default_factory=list)
    required_excluded_ingredients: list[str] = Field(default_factory=list)
    required_explanation_terms: list[str] = Field(default_factory=list)
    minimum_explanation_term_coverage: float = 100.0


class FollowUpObservation(BaseModel):
    z_pre: float
    z_post: float


class IntegrationObservation(BaseModel):
    attempted: int = 0
    success: int = 0


class EvalCase(BaseModel):
    case_id: str
    synthetic: bool = True
    category: str
    description: str
    request: RecommendationRequest
    expected: ExpectedEvalOutcome
    follow_up: FollowUpObservation | None = None
    integration: dict[str, IntegrationObservation] = Field(default_factory=dict)
    adverse_event_reported: bool = False


def load_eval_cases(dataset_path: str | Path) -> list[EvalCase]:
    path = Path(dataset_path)
    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cases.append(EvalCase.model_validate_json(line))
    return cases


def run_eval(dataset_path: str | Path) -> dict[str, object]:
    path = Path(dataset_path)
    cases = load_eval_cases(path)

    aggregates: dict[str, list[float]] = {
        "recommendation_coverage_pct": [],
        "efficacy_improvement_pp": [],
        "next_action_accuracy_pct": [],
        "explanation_quality_accuracy_pct": [],
        "safety_reference_accuracy_pct": [],
    }
    adverse_flags: list[bool] = []
    integration_records: list[dict[str, dict[str, int]]] = []
    case_results: list[dict[str, object]] = []

    for case in cases:
        response = recommend(case.request)
        actual_ingredients = [item.ingredient_key for item in response.recommendations]
        actual_rule_ids = [item.rule_id for item in response.safety_summary.rule_refs]
        actual_excluded = response.safety_summary.excluded_ingredients
        explanation_text = " ".join(
            [response.decision_summary.headline, response.decision_summary.summary]
            + [response.next_action_rationale.summary]
            + [item.rationale for item in response.recommendations]
            + [item.summary for item in response.safety_evidence]
            + response.safety_summary.warnings
            + response.safety_summary.blocked_reasons
            + [item.summary for item in response.limitation_details]
        )

        case_metrics: dict[str, float | None] = {}
        case_metrics["recommendation_coverage_pct"] = recommendation_coverage_pct(
            case.expected.recommendation_reference.required_ingredients,
            actual_ingredients,
        )
        case_metrics["next_action_accuracy_pct"] = (
            100.0 if response.next_action == case.expected.expected_next_action else 0.0
            if case.expected.expected_next_action is not None
            else None
        )
        case_metrics["explanation_quality_accuracy_pct"] = explanation_term_coverage_pct(
            case.expected.required_explanation_terms,
            explanation_text,
        )
        case_metrics["safety_reference_accuracy_pct"] = safety_reference_accuracy_pct(
            expected_status=(
                case.expected.expected_status.value
                if case.expected.expected_status is not None
                else None
            ),
            actual_status=response.status.value,
            required_rule_ids=case.expected.required_rule_ids,
            actual_rule_ids=actual_rule_ids,
            required_excluded_ingredients=case.expected.required_excluded_ingredients,
            actual_excluded_ingredients=actual_excluded,
        )

        if case.follow_up is not None:
            case_metrics["efficacy_improvement_pp"] = percentile_improvement_pp(
                case.follow_up.z_pre,
                case.follow_up.z_post,
            )
        else:
            case_metrics["efficacy_improvement_pp"] = None

        for metric_name, value in case_metrics.items():
            if value is not None and metric_name in aggregates:
                aggregates[metric_name].append(value)

        adverse_flags.append(case.adverse_event_reported)
        integration_records.append(
            {
                key: {"attempted": value.attempted, "success": value.success}
                for key, value in case.integration.items()
            }
        )

        case_results.append(
            {
                "case_id": case.case_id,
                "synthetic": case.synthetic,
                "category": case.category,
                "description": case.description,
                "case_metrics": case_metrics,
                "actual": {
                    "status": response.status.value,
                    "next_action": response.next_action.value,
                    "decision_summary": response.decision_summary.summary,
                    "recommendation_keys": actual_ingredients,
                    "rule_ids": actual_rule_ids,
                    "excluded_ingredients": actual_excluded,
                },
            }
        )

    summary: dict[str, object] = {}
    integration_breakdown = integration_modality_breakdown(integration_records)
    attempted_modalities = {
        name: item for name, item in integration_breakdown.items() if item["score"] is not None
    }
    bottleneck_modality = None
    bottleneck_rate = None
    if attempted_modalities:
        bottleneck_modality, bottleneck_item = min(
            attempted_modalities.items(),
            key=lambda item: item[1]["score"],
        )
        bottleneck_rate = bottleneck_item["score"]

    for metric_name, definition in METRIC_DEFINITIONS.items():
        if metric_name == "adverse_event_count_yearly":
            score = float(count_adverse_events(adverse_flags))
        elif metric_name == "sensor_genetic_integration_rate_pct":
            score = sensor_genetic_integration_rate_pct(integration_records)
        else:
            score = average_metric(aggregates.get(metric_name, []))

        summary[metric_name] = {
            "title_ko": definition.title_ko,
            "score": score,
            "unit": definition.unit,
            "target": definition.target,
            "comparison": definition.comparison,
            "passed": metric_passed(score, definition.comparison, definition.target),
            "assumption": definition.assumption,
        }
        if metric_name == "sensor_genetic_integration_rate_pct":
            summary[metric_name]["details"] = {
                "aggregation_method": "pooled_success_over_attempted",
                "modality_breakdown": integration_breakdown,
                "bottleneck_modality": bottleneck_modality,
                "bottleneck_rate_pct": bottleneck_rate,
            }

    return {
        "dataset_path": str(path),
        "generated_at": datetime.now(UTC).isoformat(),
        "case_count": len(cases),
        "summary": summary,
        "case_results": case_results,
    }


def write_report_files(
    report: dict[str, object],
    output_json_path: str | Path,
    output_md_path: str | Path,
) -> None:
    json_path = Path(output_json_path)
    md_path = Path(output_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown_report(report), encoding="utf-8")


def render_markdown_report(report: dict[str, object]) -> str:
    summary = report["summary"]
    case_results = report["case_results"]

    lines = [
        "# eval report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- dataset_path: {report['dataset_path']}",
        f"- case_count: {report['case_count']}",
        "",
        "## metric summary",
        "",
        "| metric | score | target | comparison | passed |",
        "| --- | --- | --- | --- | --- |",
    ]

    for metric_name, item in summary.items():
        lines.append(
            "| "
            f"{metric_name} | {item['score']} | {item['target']} | "
            f"{item['comparison']} | {item['passed']} |"
        )

    integration_metric = summary.get("sensor_genetic_integration_rate_pct")
    integration_details = (
        integration_metric.get("details") if isinstance(integration_metric, dict) else None
    )
    if integration_details:
        lines.extend(["", "## integration diagnostics", ""])
        lines.append(
            f"- aggregation_method: {integration_details['aggregation_method']}"
        )
        lines.append(
            f"- bottleneck_modality: {integration_details['bottleneck_modality']}"
        )
        lines.append(
            f"- bottleneck_rate_pct: {integration_details['bottleneck_rate_pct']}"
        )
        lines.append("")
        lines.append("| modality | attempted | success | score |")
        lines.append("| --- | --- | --- | --- |")
        for modality_name, item in integration_details["modality_breakdown"].items():
            lines.append(
                "| "
                f"{modality_name} | {item['attempted']} | {item['success']} | "
                f"{item['score']} |"
            )

    lines.extend(["", "## case results", ""])
    for case in case_results:
        lines.append(f"### {case['case_id']} ({case['category']})")
        lines.append(f"- description: {case['description']}")
        lines.append(f"- actual_status: {case['actual']['status']}")
        lines.append(f"- actual_next_action: {case['actual']['next_action']}")
        lines.append(f"- decision_summary: {case['actual']['decision_summary']}")
        lines.append(f"- recommendation_keys: {case['actual']['recommendation_keys']}")
        lines.append(f"- case_metrics: {case['case_metrics']}")
        lines.append("")

    return "\n".join(lines)
