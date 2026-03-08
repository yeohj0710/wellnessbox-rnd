from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    title_ko: str
    unit: str
    target: float
    comparison: str
    description: str
    assumption: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    "recommendation_coverage_pct": MetricDefinition(
        name="recommendation_coverage_pct",
        title_ko="건강기능식품 추천 정확도",
        unit="percent",
        target=80.0,
        comparison="min",
        description="정답 성분 세트 대비 추천 성분 커버리지",
    ),
    "efficacy_improvement_pp": MetricDefinition(
        name="efficacy_improvement_pp",
        title_ko="실제 효과 측정치 개선도",
        unit="percentage_points",
        target=0.0,
        comparison="positive",
        description="표준화 점수 전후 차이의 백분위 포인트 변화",
        assumption="현재는 synthetic follow-up z-score pair로만 계산한다.",
    ),
    "next_action_accuracy_pct": MetricDefinition(
        name="next_action_accuracy_pct",
        title_ko="다음 수행 작업 판단 및 수행 정확도",
        unit="percent",
        target=80.0,
        comparison="min",
        description="expected_next_action과 실제 next_action exact match",
    ),
    "explanation_quality_accuracy_pct": MetricDefinition(
        name="explanation_quality_accuracy_pct",
        title_ko="상담/설명 품질 정확도 proxy",
        unit="percent",
        target=91.0,
        comparison="min",
        description="required explanation term coverage",
        assumption="chat 모듈 미구현 상태이므로 설명 품질 proxy를 사용한다.",
    ),
    "safety_reference_accuracy_pct": MetricDefinition(
        name="safety_reference_accuracy_pct",
        title_ko="안전 검증/레퍼런스 정확도",
        unit="percent",
        target=95.0,
        comparison="min",
        description="status/rule_id/exclusion 기준 안전 판정 정확도",
        assumption="full citation graph 대신 구조화 subset match를 사용한다.",
    ),
    "adverse_event_count_yearly": MetricDefinition(
        name="adverse_event_count_yearly",
        title_ko="약물이상반응 보고 건수",
        unit="count_per_year",
        target=5.0,
        comparison="max",
        description="synthetic annual adverse event count proxy",
        assumption="현재 sample dataset의 adverse flag 합계를 연간 수치 proxy로 본다.",
    ),
    "sensor_genetic_integration_rate_pct": MetricDefinition(
        name="sensor_genetic_integration_rate_pct",
        title_ko="바이오센서·유전자 데이터 연동율",
        unit="percent",
        target=90.0,
        comparison="min",
        description="wearable/CGM/genetic modality의 통합 연동 성공률",
    ),
}

