# Metric 정의

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 원칙

- 모든 metric은 deterministic하게 계산한다.
- case-level 계산과 aggregate 계산을 분리한다.
- 공식 KPI score와 diagnostic breakdown을 구분한다.
- 불확실한 KPI 해석은 문서에 가정으로 남긴다.

## 공식 metric 표

| metric | 단위 | 목표 | 비교 방향 | aggregate 계산 |
| --- | --- | --- | --- | --- |
| `recommendation_coverage_pct` | % | 80 | min | case 평균 |
| `efficacy_improvement_pp` | pp | 0 초과 | positive | case 평균 |
| `next_action_accuracy_pct` | % | 80 | min | case 평균 |
| `explanation_quality_accuracy_pct` | % | 91 | min | case 평균 |
| `safety_reference_accuracy_pct` | % | 95 | min | case 평균 |
| `adverse_event_count_yearly` | 건/year | 5 이하 | max | dataset 합계 |
| `sensor_genetic_integration_rate_pct` | % | 90 | min | pooled success / attempted |

## case-level 계산

### `recommendation_coverage_pct`

- 계산:
  - `100 * |required ∩ actual| / |required|`

### `efficacy_improvement_pp`

- 계산:
  - `100 * [Phi(z_post) - Phi(z_pre)]`

### `next_action_accuracy_pct`

- 계산:
  - exact match면 `100`
  - 아니면 `0`

### `explanation_quality_accuracy_pct`

- 계산:
  - `100 * (required explanation terms 중 실제 텍스트에 포함된 비율)`

### `safety_reference_accuracy_pct`

- 아래 3개 sub-score 평균:
  - status exact match
  - required rule id subset match
  - required excluded ingredient subset match

### `adverse_event_count_yearly`

- 계산:
  - dataset 내 `adverse_event_reported` 합계

### `sensor_genetic_integration_rate_pct`

- 공식 score 계산:
  - `100 * total_success / total_attempted`
- 현재 포함 modality:
  - `wearable`
  - `cgm`
  - `genetic`

## integration diagnostic breakdown

이번 루프부터 `sensor_genetic_integration_rate_pct`는 공식 pooled score 외에 아래 diagnostic 정보를 같이 남긴다.

- `aggregation_method`
- `modality_breakdown`
  - modality별 `attempted`
  - modality별 `success`
  - modality별 `score`
- `bottleneck_modality`
- `bottleneck_rate_pct`

이 diagnostic은 공식 KPI score를 대체하지 않는다. 목적은 어느 modality가 병목인지 즉시 보이게 만드는 것이다.

예시:

```json
{
  "aggregation_method": "pooled_success_over_attempted",
  "modality_breakdown": {
    "wearable": { "attempted": 4, "success": 4, "score": 100.0 },
    "cgm": { "attempted": 2, "success": 1, "score": 50.0 },
    "genetic": { "attempted": 2, "success": 1, "score": 50.0 }
  },
  "bottleneck_modality": "cgm",
  "bottleneck_rate_pct": 50.0
}
```

## pass/fail 규칙

| metric | pass 조건 |
| --- | --- |
| `recommendation_coverage_pct` | `score >= 80` |
| `efficacy_improvement_pp` | `score > 0` |
| `next_action_accuracy_pct` | `score >= 80` |
| `explanation_quality_accuracy_pct` | `score >= 91` |
| `safety_reference_accuracy_pct` | `score >= 95` |
| `adverse_event_count_yearly` | `score <= 5` |
| `sensor_genetic_integration_rate_pct` | `score >= 90` |

## 가정

- `explanation_quality_accuracy_pct`는 아직 chat module accuracy의 proxy다.
- `safety_reference_accuracy_pct`는 full citation graph가 아니라 status/rule/exclusion proxy다.
- `sensor_genetic_integration_rate_pct`는 아직 parser 실행 성공률이 아니라 dataset observation proxy다.
- integration diagnostic breakdown은 KPI를 좋게 보이게 만들기 위한 재정의가 아니라 병목 노출용 구조다.
