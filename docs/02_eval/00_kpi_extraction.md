# KPI 추출

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 목적

- 원문 p.25~26 KPI를 현재 deterministic baseline에서 측정 가능한 형태로 고정한다.
- 구현이 바뀌어도 KPI 이름, 목표값, pass/fail 기준이 흔들리지 않게 한다.
- 데이터가 아직 작거나 proxy인 항목은 가정으로 명시한다.

## KPI 매핑

| 원문 KPI | 목표 | metric |
| --- | --- | --- |
| 건강기능식품 추천 정확도 | 80% 이상 | `recommendation_coverage_pct` |
| 실제 효과 측정치 개선율 | 0pp 초과 | `efficacy_improvement_pp` |
| 다음 수행 작업 판단 및 수행 정확도 | 80% 이상 | `next_action_accuracy_pct` |
| 상담 모듈 답변 정확도 | 91% 이상 | `explanation_quality_accuracy_pct` |
| 안전 검증/레퍼런스 정확도 | 95% 이상 | `safety_reference_accuracy_pct` |
| 이상반응 보고 건수 | 연 5건 이하 | `adverse_event_count_yearly` |
| 바이오센서·유전자 데이터 연동율 | 90% 이상 | `sensor_genetic_integration_rate_pct` |

## 현재 해석

### 추천 정확도

- frozen eval의 `required_ingredients` 대비 실제 추천 ingredient coverage를 본다.

### 효과 개선율

- synthetic `z_pre`, `z_post` 쌍으로 percentile improvement proxy를 계산한다.

### 다음 행동 정확도

- `expected_next_action`과 실제 `next_action` exact match를 본다.

### 상담 정확도

- 아직 별도 chat module이 없으므로 `required_explanation_terms` coverage proxy를 쓴다.

### 안전 검증/레퍼런스 정확도

- status, rule ids, excluded ingredients의 일치 여부를 본다.

### 이상반응 건수

- synthetic annual adverse-event flag 합계를 본다.

### 바이오센서·유전자 데이터 연동율

- 공식 score는 계속 `100 * total_success / total_attempted`를 쓴다.
- 이번 루프부터는 아래 diagnostic breakdown도 함께 남긴다.
  - modality별 `attempted`
  - modality별 `success`
  - modality별 `score`
  - bottleneck modality

## 이번 루프에서 추가된 구조

- `sensor_genetic_integration_rate_pct`에 diagnostic breakdown이 추가됐다.
- 공식 KPI score는 바꾸지 않았다.
- report만 봐도 `wearable`, `cgm`, `genetic` 중 어디가 병목인지 바로 확인할 수 있다.

## 현재 가정

1. `explanation_quality_accuracy_pct`는 chat accuracy proxy다.
2. `safety_reference_accuracy_pct`는 citation graph 완성 전의 proxy다.
3. `adverse_event_count_yearly`는 synthetic annual proxy다.
4. `sensor_genetic_integration_rate_pct`는 parser runtime KPI가 아니라 dataset observation proxy다.
5. integration diagnostic breakdown은 score 재정의가 아니라 병목 분석용 구조다.
