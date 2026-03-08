# Metric 정의

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 공통 원칙

- 모든 metric은 가능한 한 deterministic하게 계산한다.
- case-level 계산식과 aggregate 계산식을 분리한다.
- metric의 이름, 단위, threshold 비교 방향은 코드에 고정한다.

## Metric 표

| metric | 단위 | 목표 | 비교 방향 | case-level 계산 |
| --- | --- | --- | --- | --- |
| `recommendation_coverage_pct` | % | 80 | 높을수록 좋음 | `100 * |required ∩ actual| / |required|` |
| `efficacy_improvement_pp` | pp | 0 초과 | 양수여야 함 | `100 * [Φ(z_post) - Φ(z_pre)]` |
| `next_action_accuracy_pct` | % | 80 | 높을수록 좋음 | exact match면 100, 아니면 0 |
| `explanation_quality_accuracy_pct` | % | 91 | 높을수록 좋음 | required explanation term coverage |
| `safety_reference_accuracy_pct` | % | 95 | 높을수록 좋음 | status/rule_id/exclusion 3항 평균 |
| `adverse_event_count_yearly` | 건/year | 5 이하 | 낮을수록 좋음 | case의 adverse flag 총합 |
| `sensor_genetic_integration_rate_pct` | % | 90 | 높을수록 좋음 | `100 * total_success / total_attempted` |

## Aggregate 규칙

### 평균형 metric

아래 항목은 case score 평균을 사용한다.

- `recommendation_coverage_pct`
- `efficacy_improvement_pp`
- `next_action_accuracy_pct`
- `explanation_quality_accuracy_pct`
- `safety_reference_accuracy_pct`

### 총합/비율형 metric

- `adverse_event_count_yearly`: dataset 전체 합계
- `sensor_genetic_integration_rate_pct`: dataset 전체 modality 합산 비율

## Pass/Fail 규칙

| metric | pass 규칙 |
| --- | --- |
| `recommendation_coverage_pct` | score >= 80 |
| `efficacy_improvement_pp` | score > 0 |
| `next_action_accuracy_pct` | score >= 80 |
| `explanation_quality_accuracy_pct` | score >= 91 |
| `safety_reference_accuracy_pct` | score >= 95 |
| `adverse_event_count_yearly` | score <= 5 |
| `sensor_genetic_integration_rate_pct` | score >= 90 |

## safety metric 세부 해석

`safety_reference_accuracy_pct`는 아래 3개 sub-score의 평균이다.

1. `expected_status == actual_status`
2. `required_rule_ids ⊆ actual_rule_ids`
3. `required_excluded_ingredients ⊆ actual_excluded_ingredients`

각 항목은 맞으면 100, 아니면 0으로 처리한다.

## explanation metric 세부 해석

- 현재는 chat 답변 정확도 원문 KPI를 그대로 구현하지 못한다.
- 따라서 `required_explanation_terms` 포함률을 proxy로 둔다.
- 비교 대상 텍스트는 `decision_summary + recommendation rationale + safety warning/block reason`을 합친 문자열이다.
- 계산식:
  `100 * (#present required terms / #required terms)`

## 모호점

1. 원문 상담 모듈 KPI는 실제 질문-정답 셋 기반인데, 현재 API에는 chat 모듈이 없다.
2. 원문 안전 KPI는 rule logic과 reference를 함께 본다. 현재는 rule id와 exclusion만 본다.
3. 원문 효과 KPI는 PRO 확보량까지 포함하지만, 현재 sample dataset은 소규모 synthetic pair만 갖는다.
