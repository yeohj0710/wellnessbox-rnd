from __future__ import annotations

import json
import statistics
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime

from wellnessbox_rnd.interim.contracts import DataClass, ReplacementStatus
from wellnessbox_rnd.interim.manifest import canonical_json
from wellnessbox_rnd.interim.store import InterimStore
from wellnessbox_rnd.metrics.statistics import deterministic_bootstrap_mean_ci

KPI_NAMES = {
    "KPI-1": "추천 정확도",
    "KPI-2": "효과 개선 프록시",
    "KPI-3": "다음 행동 판단·실행",
    "KPI-4": "상담 답변",
    "KPI-5": "안전 라벨+근거",
    "KPI-6": "ADR 프록시",
    "KPI-7": "W/C/G 연동률 프록시",
}


@dataclass(frozen=True)
class LinkageResult:
    source_counts: dict[str, int]
    source_rates: dict[str, float]
    aggregate: float


@dataclass(frozen=True)
class KpiResult:
    kpi_id: str
    name: str
    sample_count: int
    proxy_value: float
    ci95: tuple[float, float] | None
    threshold: str
    internal_guardband: str
    proxy_pass: bool
    replacement_status: str
    hard_failures: int = 0
    details: dict[str, object] | None = None


@dataclass(frozen=True)
class KpiReport:
    mode: str
    generated_at: str
    proxy_kpis_passed: int
    proxy_kpis_total: int
    proxy_research_completion: bool
    real_research_completion: bool
    kpis: tuple[KpiResult, ...]

    def by_id(self, kpi_id: str) -> KpiResult:
        return next(item for item in self.kpis if item.kpi_id == kpi_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "generated_at": self.generated_at,
            "proxy_kpis_passed": self.proxy_kpis_passed,
            "proxy_kpis_total": self.proxy_kpis_total,
            "proxy_research_completion": self.proxy_research_completion,
            "real_research_completion": self.real_research_completion,
            "kpis": [asdict(item) for item in self.kpis],
        }


def recommendation_reference_coverage(
    *,
    reference: set[str],
    predicted: set[str],
) -> float:
    if not reference:
        return 100.0 if not predicted else 0.0
    return 100.0 * len(reference & predicted) / len(reference)


def linkage_macro_rate(rows: Iterable[dict[str, object]]) -> LinkageResult:
    grouped: dict[str, list[bool]] = {"W": [], "C": [], "G": []}
    for row in rows:
        source = str(row.get("source"))
        if source in grouped:
            grouped[source].append(bool(row.get("success")))
    if any(not grouped[source] for source in grouped):
        raise ValueError("linkage_requires_w_c_g")
    counts = {source: len(values) for source, values in grouped.items()}
    rates = {source: 100.0 * sum(values) / len(values) for source, values in grouped.items()}
    return LinkageResult(
        source_counts=counts,
        source_rates=rates,
        aggregate=statistics.mean(rates.values()),
    )


def device_linkage_metrics(
    store: InterimStore,
    *,
    data_class: DataClass | str,
) -> LinkageResult:
    try:
        effective_data_class = DataClass(data_class)
    except ValueError as error:
        raise ValueError("unsupported_device_linkage_data_class") from error
    if effective_data_class not in {
        DataClass.PRODUCTION_DEVICE_SESSION,
        DataClass.SIMULATED_DEVICE_SESSION,
        DataClass.SIMULATED_INTEGRATION_PROXY,
    }:
        raise ValueError("unsupported_device_linkage_data_class")
    table = (
        "connector_sessions"
        if effective_data_class == DataClass.SIMULATED_INTEGRATION_PROXY
        else "device_event_receipts"
    )
    rows = [
        {"source": str(row[0]), "success": bool(row[1])}
        for row in store.rows(
            f"""
            select source, success from {table}
            where data_class=?
            order by source, session_id
            """,
            (effective_data_class.value,),
        )
    ]
    return linkage_macro_rate(rows)


def _payloads(store: InterimStore, kind: str) -> list[dict[str, object]]:
    return [
        json.loads(row[0])
        for row in store.rows(
            "select payload_json from evaluation_cases where evaluation_kind = ? order by case_id",
            (kind,),
        )
    ]


def evaluate_proxy_kpis(store: InterimStore) -> KpiReport:
    recommendation_rows = _payloads(store, "recommendation")
    recommendation_values = [
        recommendation_reference_coverage(
            reference=set(map(str, row.get("gold_proxy", []))),
            predicted=set(map(str, row.get("predicted", []))),
        )
        for row in recommendation_rows
    ]
    rec_value = statistics.mean(recommendation_values)
    rec_ci = deterministic_bootstrap_mean_ci(recommendation_values)

    effect_values = [
        float(row[0])
        for row in store.rows(
            """
            select percentile_point_change from pro_observations
            where data_class='SYNTHETIC_OUTCOME_PROXY' order by observation_id
            """
        )
    ]
    effect_value = statistics.mean(effect_values)
    effect_ci = deterministic_bootstrap_mean_ci(effect_values)

    action_rows = _payloads(store, "action")
    action_values = [
        100.0
        if row.get("expected_action") == row.get("actual_action")
        and bool(row.get("execution_success"))
        and bool(row.get("postcondition_success"))
        else 0.0
        for row in action_rows
    ]
    action_value = statistics.mean(action_values)
    action_ci = deterministic_bootstrap_mean_ci(action_values)
    high_risk_wrong = sum(
        1
        for row, value in zip(action_rows, action_values, strict=True)
        if int(row.get("risk_tier", 0)) >= 2 and value == 0.0
    )

    answer_rows = _payloads(store, "answer")
    answer_values = [
        100.0 if bool(row.get("acceptable")) and not bool(row.get("critical_safety_error")) else 0.0
        for row in answer_rows
    ]
    answer_value = statistics.mean(answer_values)
    answer_ci = deterministic_bootstrap_mean_ci(answer_values)
    answer_hard = sum(bool(row.get("critical_safety_error")) for row in answer_rows)

    safety_rows = _payloads(store, "safety")
    safety_values = [
        100.0
        if row.get("reference_label") == row.get("engine_label")
        and set(map(str, row.get("reference_evidence", [])))
        == set(map(str, row.get("engine_evidence", [])))
        else 0.0
        for row in safety_rows
    ]
    safety_value = statistics.mean(safety_values)
    safety_ci = deterministic_bootstrap_mean_ci(safety_values)
    hard_false_negatives = sum(
        1
        for row in safety_rows
        if row.get("reference_label") in {"BLOCK", "STOP_AND_ESCALATE"}
        and row.get("engine_label") not in {"BLOCK", "STOP_AND_ESCALATE"}
    )

    adr_count = int(
        store.scalar(
            """
            select count(*) from adverse_events
            where related_to_recommendation = 1 and data_class='SYNTHETIC_SAFETY_PROXY'
            """
        )
    )
    linkage = device_linkage_metrics(
        store,
        data_class=DataClass.SIMULATED_INTEGRATION_PROXY,
    )

    kpis = (
        KpiResult(
            "KPI-1",
            "추천 정확도",
            len(recommendation_values),
            rec_value,
            rec_ci,
            "N>=100, mean>=80%",
            ">=88%, CI lower>=84%",
            len(recommendation_values) >= 100 and rec_value >= 88.0 and rec_ci[0] >= 84.0,
            ReplacementStatus.PENDING_PHARMACIST_GOLD,
        ),
        KpiResult(
            "KPI-2",
            "효과 개선 proxy",
            len(effect_values),
            effect_value,
            effect_ci,
            "N>=100, mean>0pp, CI lower>0",
            "CI lower>0",
            len(effect_values) >= 100 and effect_value > 0 and effect_ci[0] > 0,
            ReplacementStatus.PENDING_REAL_WORLD_OUTCOME,
        ),
        KpiResult(
            "KPI-3",
            "다음 행동 판단·실행",
            len(action_values),
            action_value,
            action_ci,
            "N>=100, accuracy>=80%",
            ">=90%, high-risk wrong=0",
            len(action_values) >= 100 and action_value >= 90.0 and high_risk_wrong == 0,
            ReplacementStatus.PENDING_EXTERNAL_TEST,
            hard_failures=high_risk_wrong,
        ),
        KpiResult(
            "KPI-4",
            "상담 답변",
            len(answer_values),
            answer_value,
            answer_ci,
            "Q>=100, accuracy>=91%",
            ">=96%, critical safety errors=0",
            len(answer_values) >= 100 and answer_value >= 96.0 and answer_hard == 0,
            ReplacementStatus.PENDING_EXTERNAL_TEST,
            hard_failures=answer_hard,
        ),
        KpiResult(
            "KPI-5",
            "안전 label+근거",
            len(safety_values),
            safety_value,
            safety_ci,
            "R>=100, exact>=95%",
            ">=99%, hard FN=0",
            len(safety_values) >= 100 and safety_value >= 99.0 and hard_false_negatives == 0,
            ReplacementStatus.PENDING_PHARMACIST_GOLD,
            hard_failures=hard_false_negatives,
        ),
        KpiResult(
            "KPI-6",
            "ADR proxy",
            1_200,
            float(adr_count),
            None,
            "12 months <=5",
            "complete capture",
            adr_count <= 5,
            ReplacementStatus.PENDING_12_MONTH_REAL_OPERATION,
        ),
        KpiResult(
            "KPI-7",
            "W/C/G 연동률 proxy",
            sum(linkage.source_counts.values()),
            linkage.aggregate,
            None,
            "total>=100, each>=10, macro>=90%",
            "total>=150, each>=20, macro>=97%",
            sum(linkage.source_counts.values()) >= 150
            and all(value >= 20 for value in linkage.source_counts.values())
            and linkage.aggregate >= 97.0,
            ReplacementStatus.PENDING_PRODUCTION_DEVICE_SESSIONS,
            details={
                "source_counts": linkage.source_counts,
                "source_rates": linkage.source_rates,
                "aggregation": "equal_weight_macro_average",
            },
        ),
    )
    kpis = tuple(replace(item, name=KPI_NAMES[item.kpi_id]) for item in kpis)
    passed = sum(item.proxy_pass for item in kpis)
    report = KpiReport(
        mode="PROXY_GOLD_SIMULATION",
        generated_at=datetime.now(UTC).isoformat(),
        proxy_kpis_passed=passed,
        proxy_kpis_total=len(kpis),
        proxy_research_completion=passed == len(kpis),
        real_research_completion=False,
        kpis=kpis,
    )
    _persist_report(store, report)
    return report


def _persist_report(store: InterimStore, report: KpiReport) -> None:
    with store.transaction() as connection:
        for item in report.kpis:
            connection.execute(
                """
                INSERT OR REPLACE INTO kpi_results(
                  kpi_id, proxy_value, sample_count, ci95_lower, ci95_upper,
                  proxy_pass, replacement_status, hard_failures, details_json, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.kpi_id,
                    item.proxy_value,
                    item.sample_count,
                    item.ci95[0] if item.ci95 else None,
                    item.ci95[1] if item.ci95 else None,
                    int(item.proxy_pass),
                    item.replacement_status,
                    item.hard_failures,
                    canonical_json(item.details or {}),
                    report.generated_at,
                ),
            )
