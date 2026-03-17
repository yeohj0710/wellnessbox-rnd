from __future__ import annotations

import json
from pathlib import Path

OFFICIAL_METRIC_ORDER = [
    "recommendation_coverage_pct",
    "efficacy_improvement_pp",
    "next_action_accuracy_pct",
    "explanation_quality_accuracy_pct",
    "safety_reference_accuracy_pct",
    "adverse_event_count_yearly",
    "sensor_genetic_integration_rate_pct",
]

FIT_METRIC_NAMES = [
    "aggregate_mae",
    "aggregate_r2",
    "policy_proxy_mae",
]


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_kpi_candidate_summary(
    *,
    baseline_eval_report: dict[str, object],
    baseline_eval_report_path: str | Path,
    candidate_compare_report: dict[str, object],
    candidate_compare_report_path: str | Path,
    weakest_slice_summary: dict[str, object],
    weakest_slice_summary_path: str | Path,
) -> dict[str, object]:
    baseline_metrics = _build_baseline_metrics(_as_dict(baseline_eval_report.get("summary")))
    candidate_comparison = _build_candidate_comparison(candidate_compare_report)
    weakest_slice_delta = _build_weakest_slice_delta(
        weakest_slice_summary=weakest_slice_summary,
        candidate_compare_report=candidate_compare_report,
    )
    adoption_summary = _build_adoption_summary(
        candidate_compare_report=candidate_compare_report,
        weakest_slice_delta=weakest_slice_delta,
    )

    return {
        "summary_name": "baseline_candidate_kpi_summary_v1",
        "source_artifacts": {
            "baseline_eval_report_path": str(baseline_eval_report_path),
            "candidate_compare_report_path": str(candidate_compare_report_path),
            "weakest_slice_summary_path": str(weakest_slice_summary_path),
        },
        "baseline_reference": {
            "dataset_path": baseline_eval_report.get("dataset_path"),
            "case_count": baseline_eval_report.get("case_count"),
            "metrics": baseline_metrics,
        },
        "candidate_comparison": candidate_comparison,
        "weakest_slice_delta": weakest_slice_delta,
        "adoption_summary": adoption_summary,
        "validation_issues": [],
    }


def render_kpi_candidate_summary_markdown(summary: dict[str, object]) -> str:
    baseline_reference = _as_dict(summary.get("baseline_reference"))
    candidate_comparison = _as_dict(summary.get("candidate_comparison"))
    candidate_delta = _as_dict(candidate_comparison.get("delta_summary"))
    weakest_slice_delta = _as_dict(summary.get("weakest_slice_delta"))
    frozen_anchor = _as_dict(weakest_slice_delta.get("frozen_eval_anchor"))
    adoption = _as_dict(summary.get("adoption_summary"))

    lines = [
        "# baseline candidate kpi summary v1",
        "",
        f"- baseline_case_count: `{baseline_reference.get('case_count')}`",
        f"- candidate_label: `{candidate_comparison.get('candidate_label')}`",
        f"- decision: `{adoption.get('decision')}`",
        f"- conclusion: `{adoption.get('one_line_conclusion')}`",
        "",
        "## Baseline Reference",
        "",
        "| metric | score | target | passed |",
        "| --- | --- | --- | --- |",
    ]
    for metric_name, metric in _as_dict(baseline_reference.get("metrics")).items():
        lines.append(
            "| "
            f"{metric_name} | {metric.get('score')} | {metric.get('target')} | "
            f"{metric.get('passed')} |"
        )

    lines.extend(
        [
            "",
            "## Candidate Delta",
            "",
            f"- aggregate_mae_delta: `{candidate_delta.get('test_aggregate_mae_delta')}`",
            f"- aggregate_r2_delta: `{candidate_delta.get('test_aggregate_r2_delta')}`",
            f"- policy_proxy_mae_delta: `{candidate_delta.get('test_policy_proxy_mae_delta')}`",
            (
                "- fit_gate_status: "
                f"`{candidate_comparison.get('fit_gate_status')}`"
            ),
            "",
            "## Weakest Slice Delta",
            "",
            (
                "- frozen_eval_overall_weakest: "
                f"`{frozen_anchor.get('overall_category')}` "
                f"(cases={frozen_anchor.get('overall_case_count')}, "
                f"metrics={frozen_anchor.get('overall_metric_names')})`"
            ),
            (
                "- frozen_eval_sensor_genetic_weakest: "
                f"`{frozen_anchor.get('sensor_genetic_category')}` "
                f"(score={frozen_anchor.get('sensor_genetic_score')}, "
                f"target={frozen_anchor.get('sensor_genetic_target')})`"
            ),
            (
                "- dominant_candidate_regression_slice: "
                f"`{weakest_slice_delta.get('dominant_candidate_regression_slice')}`"
            ),
            (
                "- low_risk_vs_cgm_regression_score: "
                f"`{weakest_slice_delta.get('candidate_regression_balance')}`"
            ),
            (
                "- still_empty_weakest_families: "
                f"`{weakest_slice_delta.get('still_empty_weakest_families')}`"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_kpi_candidate_summary_files(
    summary: dict[str, object],
    *,
    report_json_path: str | Path,
    report_md_path: str | Path,
) -> None:
    json_path = Path(report_json_path)
    md_path = Path(report_md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_kpi_candidate_summary_markdown(summary), encoding="utf-8")


def _build_baseline_metrics(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    metrics = {}
    for metric_name in OFFICIAL_METRIC_ORDER:
        metric = _as_dict(summary.get(metric_name))
        metrics[metric_name] = {
            "score": metric.get("score"),
            "target": metric.get("target"),
            "comparison": metric.get("comparison"),
            "passed": metric.get("passed"),
            "unit": metric.get("unit"),
        }
    return metrics


def _build_candidate_comparison(candidate_compare_report: dict[str, object]) -> dict[str, object]:
    reference = _as_dict(candidate_compare_report.get("reference"))
    candidate = _as_dict(candidate_compare_report.get("candidate"))
    deltas = _as_dict(candidate_compare_report.get("deltas"))
    fit_gate = _build_fit_gate_status(deltas)
    return {
        "reference_label": candidate_compare_report.get("reference_label"),
        "candidate_label": candidate_compare_report.get("candidate_label"),
        "reference_effect_artifact_path": reference.get("effect_artifact_path"),
        "candidate_effect_artifact_path": candidate.get("effect_artifact_path"),
        "reference_fit_metrics": _extract_fit_metrics(_as_dict(reference.get("test_metrics"))),
        "candidate_fit_metrics": _extract_fit_metrics(_as_dict(candidate.get("test_metrics"))),
        "delta_summary": {
            "test_aggregate_mae_delta": deltas.get("test_aggregate_mae_delta"),
            "test_aggregate_r2_delta": deltas.get("test_aggregate_r2_delta"),
            "test_policy_proxy_mae_delta": deltas.get("test_policy_proxy_mae_delta"),
            "effect_only_low_risk_disagreement_delta": deltas.get(
                "effect_only_low_risk_disagreement_delta"
            ),
            "combined_low_risk_disagreement_delta": deltas.get(
                "combined_low_risk_disagreement_delta"
            ),
            "effect_only_cgm_disagreement_delta": deltas.get(
                "effect_only_cgm_disagreement_delta"
            ),
            "combined_cgm_disagreement_delta": deltas.get("combined_cgm_disagreement_delta"),
        },
        "fit_gate_status": fit_gate["status"],
        "fit_gate_reason_codes": fit_gate["reason_codes"],
    }


def _build_weakest_slice_delta(
    *,
    weakest_slice_summary: dict[str, object],
    candidate_compare_report: dict[str, object],
) -> dict[str, object]:
    frozen_anchor = _as_dict(weakest_slice_summary.get("frozen_eval_anchor"))
    weakest_by_metric = _as_dict(frozen_anchor.get("weakest_category_by_metric"))
    sensor_genetic_anchor = _as_dict(weakest_by_metric.get("sensor_genetic_integration_rate_pct"))
    overall_anchor = _as_dict(frozen_anchor.get("weakest_category_overall"))

    slice_deltas = _as_dict(candidate_compare_report.get("slice_deltas"))
    effect_only = _as_dict(slice_deltas.get("learned_effect_guarded"))
    combined = _as_dict(slice_deltas.get("learned_effect_and_policy_guarded"))
    low_risk_regression_score = _slice_regression_score(
        effect_only_distribution=_as_dict(effect_only.get("low_risk_final_action_delta")),
        combined_distribution=_as_dict(combined.get("low_risk_final_action_delta")),
        effect_only_disagreement=effect_only.get("low_risk_disagreement_delta"),
        combined_disagreement=combined.get("low_risk_disagreement_delta"),
    )
    cgm_regression_score = _slice_regression_score(
        effect_only_distribution=_as_dict(effect_only.get("cgm_final_action_delta")),
        combined_distribution=_as_dict(combined.get("cgm_final_action_delta")),
        effect_only_disagreement=effect_only.get("cgm_disagreement_delta"),
        combined_disagreement=combined.get("cgm_disagreement_delta"),
    )
    dominant_slice = "low_risk" if low_risk_regression_score >= cgm_regression_score else "cgm"

    return {
        "frozen_eval_anchor": {
            "overall_category": overall_anchor.get("category"),
            "overall_case_count": overall_anchor.get("case_count"),
            "overall_metric_names": overall_anchor.get("metrics"),
            "sensor_genetic_category": sensor_genetic_anchor.get("category"),
            "sensor_genetic_score": sensor_genetic_anchor.get("score"),
            "sensor_genetic_target": sensor_genetic_anchor.get("target"),
            "sensor_genetic_passed": sensor_genetic_anchor.get("passed"),
        },
        "candidate_regression_balance": {
            "low_risk_regression_score": low_risk_regression_score,
            "cgm_regression_score": cgm_regression_score,
        },
        "dominant_candidate_regression_slice": dominant_slice,
        "candidate_slice_delta": {
            "learned_effect_guarded": {
                "low_risk_final_action_delta": effect_only.get("low_risk_final_action_delta"),
                "cgm_final_action_delta": effect_only.get("cgm_final_action_delta"),
                "low_risk_disagreement_delta": effect_only.get("low_risk_disagreement_delta"),
                "cgm_disagreement_delta": effect_only.get("cgm_disagreement_delta"),
            },
            "learned_effect_and_policy_guarded": {
                "low_risk_final_action_delta": combined.get("low_risk_final_action_delta"),
                "cgm_final_action_delta": combined.get("cgm_final_action_delta"),
                "low_risk_disagreement_delta": combined.get("low_risk_disagreement_delta"),
                "cgm_disagreement_delta": combined.get("cgm_disagreement_delta"),
            },
        },
        "still_empty_weakest_families": weakest_slice_summary.get("still_empty_weakest_families"),
        "audit_layer_gap_count": weakest_slice_summary.get("audit_layer_gap_count"),
    }


def _build_adoption_summary(
    *,
    candidate_compare_report: dict[str, object],
    weakest_slice_delta: dict[str, object],
) -> dict[str, object]:
    deltas = _as_dict(candidate_compare_report.get("deltas"))
    fit_gate = _build_fit_gate_status(deltas)
    candidate_label = str(candidate_compare_report.get("candidate_label"))
    dominant_slice = weakest_slice_delta.get("dominant_candidate_regression_slice")
    balance = _as_dict(weakest_slice_delta.get("candidate_regression_balance"))
    low_risk_score = balance.get("low_risk_regression_score")
    cgm_score = balance.get("cgm_regression_score")

    if fit_gate["status"] == "worse_on_all_fit_gates":
        decision = "hold_baseline_candidate_not_ready"
        conclusion = (
            f"Hold baseline: {candidate_label} is worse on all overall fit gates and the "
            f"larger replay regression is concentrated in {dominant_slice}, "
            "not a compensating gain."
        )
    elif fit_gate["status"] == "better_on_all_fit_gates":
        decision = "candidate_improved_but_replay_review_needed"
        conclusion = (
            "Candidate improved overall fit, but keep adoption pending until "
            "replay slices stay stable across low-risk and cgm."
        )
    else:
        decision = "hold_baseline_mixed_evidence"
        conclusion = (
            f"Hold baseline: overall evidence is mixed and replay drift still favors "
            f"{dominant_slice} regression over adoption."
        )

    return {
        "decision": decision,
        "reason_codes": fit_gate["reason_codes"],
        "one_line_conclusion": conclusion,
        "decision_context": {
            "fit_gate_status": fit_gate["status"],
            "dominant_candidate_regression_slice": dominant_slice,
            "low_risk_regression_score": low_risk_score,
            "cgm_regression_score": cgm_score,
        },
    }


def _build_fit_gate_status(deltas: dict[str, object]) -> dict[str, object]:
    mae_delta = _to_float(deltas.get("test_aggregate_mae_delta"))
    r2_delta = _to_float(deltas.get("test_aggregate_r2_delta"))
    proxy_delta = _to_float(deltas.get("test_policy_proxy_mae_delta"))
    better_mae = mae_delta is not None and mae_delta <= 0.0
    better_r2 = r2_delta is not None and r2_delta >= 0.0
    better_proxy = proxy_delta is not None and proxy_delta <= 0.0
    worse_mae = mae_delta is not None and mae_delta > 0.0
    worse_r2 = r2_delta is not None and r2_delta < 0.0
    worse_proxy = proxy_delta is not None and proxy_delta > 0.0

    if worse_mae and worse_r2 and worse_proxy:
        return {
            "status": "worse_on_all_fit_gates",
            "reason_codes": [
                "aggregate_mae_worse",
                "aggregate_r2_worse",
                "policy_proxy_mae_worse",
            ],
        }
    if better_mae and better_r2 and better_proxy:
        return {
            "status": "better_on_all_fit_gates",
            "reason_codes": [
                "aggregate_mae_better_or_equal",
                "aggregate_r2_better_or_equal",
                "policy_proxy_mae_better_or_equal",
            ],
        }

    reason_codes = []
    if worse_mae:
        reason_codes.append("aggregate_mae_worse")
    if worse_r2:
        reason_codes.append("aggregate_r2_worse")
    if worse_proxy:
        reason_codes.append("policy_proxy_mae_worse")
    if better_mae:
        reason_codes.append("aggregate_mae_better_or_equal")
    if better_r2:
        reason_codes.append("aggregate_r2_better_or_equal")
    if better_proxy:
        reason_codes.append("policy_proxy_mae_better_or_equal")
    return {
        "status": "mixed_fit_gates",
        "reason_codes": reason_codes,
    }


def _extract_fit_metrics(metrics: dict[str, object]) -> dict[str, object]:
    return {metric_name: metrics.get(metric_name) for metric_name in FIT_METRIC_NAMES}


def _slice_regression_score(
    *,
    effect_only_distribution: dict[str, object],
    combined_distribution: dict[str, object],
    effect_only_disagreement: object,
    combined_disagreement: object,
) -> int:
    return (
        _sum_absolute_ints(effect_only_distribution)
        + _sum_absolute_ints(combined_distribution)
        + abs(_to_int(effect_only_disagreement))
        + abs(_to_int(combined_disagreement))
    )


def _sum_absolute_ints(values: dict[str, object]) -> int:
    return sum(abs(_to_int(value)) for value in values.values())


def _to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _to_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


__all__ = [
    "build_kpi_candidate_summary",
    "load_json",
    "render_kpi_candidate_summary_markdown",
    "write_kpi_candidate_summary_files",
]
