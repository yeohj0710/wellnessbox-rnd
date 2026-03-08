# KPI 추출

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 목적

- `master_context.md`의 p.25~26 KPI를 코드로 측정 가능한 형태로 다시 고정한다.
- 구현은 바뀔 수 있지만 평가 항목과 pass/fail 기준은 쉽게 바뀌지 않게 만든다.
- 현재 데이터가 부족하므로 frozen eval은 synthetic case를 포함한다. 모든 synthetic case는 명시적으로 표시한다.

## 원문 KPI 추출

| 원문 KPI | 목표 | 가중치 | 코드 metric 이름 |
| --- | --- | --- | --- |
| 건강기능식품 추천 정확도 | 80% 이상 | 20 | `recommendation_coverage_pct` |
| 실제 효과 측정치 개선도 | 0pp 초과 | 20 | `efficacy_improvement_pp` |
| 다음 수행 작업 판단 및 수행 정확도 | 80% 이상 | 20 | `next_action_accuracy_pct` |
| 상담 모듈 답변 정확도 | 91% 이상 | 20 | `explanation_quality_accuracy_pct` |
| 안전 검증/레퍼런스 정확도 | 95% 이상 | 10 | `safety_reference_accuracy_pct` |
| 약물이상반응 보고 건수 | 연 5건 이하 | 5 | `adverse_event_count_yearly` |
| 바이오센서·유전자 데이터 연동율 | 90% 이상 | 5 | `sensor_genetic_integration_rate_pct` |

## KPI별 코드 해석

### 1. 추천 정확도

- 원문은 정답 성분 세트 `R_i`와 엔진 산출 성분 세트 `T_i`의 커버리지를 본다.
- 현재 frozen eval에서는 case마다 `required_ingredients`를 두고, 응답의 `recommendations[].ingredient_key`와 비교한다.
- 계산식:
  `100 * |required ∩ actual| / |required|`

### 2. 효과 개선도

- 원문은 표준화 점수 전후 차이를 백분위 포인트로 환산한다.
- 현재 frozen eval에서는 case별 `z_pre`, `z_post`를 두고 `100 * [Φ(z_post) - Φ(z_pre)]`를 계산한다.
- 이는 실제 모델 효능이 아니라 평가 하네스용 deterministic metric이다.

### 3. 다음 행동 정확도

- 원문은 다음 수행 작업 판단 및 수행 정확도를 본다.
- 현재는 `expected_next_action`과 API 응답 `next_action`의 exact match로 측정한다.
- 상태기계가 고도화되더라도 이 metric 계약은 유지한다.

### 4. 상담 정확도

- 아직 별도 chat 모듈이 없으므로 원문 KPI를 그대로 측정할 수 없다.
- 현재는 `explanation_quality_accuracy_pct`라는 proxy metric을 둔다.
- 평가 방식:
  응답 내 설명 텍스트가 `required_explanation_terms`를 얼마나 포함하는지 측정한다.
- 이 항목은 향후 chat 모듈이 생기면 `chat_answer_accuracy_pct`로 대체 또는 확장한다.

### 5. 안전 검증/레퍼런스 정확도

- 원문은 논리와 레퍼런스가 참조 규칙과 일치하는지 본다.
- 현재 frozen eval에서는 아래 세 하위 항목을 평균한다.
  - status exact match
  - required rule id subset match
  - required excluded ingredient subset match
- 이는 full citation graph가 없기 때문에 둔 1차 근사치다.

### 6. 약물이상반응 보고 건수

- 원문은 직전 12개월 누적 건수를 본다.
- 현재 sample dataset은 synthetic case이므로 `adverse_event_reported` 플래그 합계를 연간 건수 proxy로 사용한다.
- 이 값은 실제 운영 지표가 아니라 runner 인터페이스를 먼저 고정하기 위한 예비 지표다.

### 7. 바이오센서·유전자 연동율

- 현재 case별 `integration` 필드에 modality별 `attempted`, `success`를 둔다.
- 총합 기준으로 `100 * success / attempted`를 계산한다.

## 현재 가정

1. 상담 KPI는 아직 설명 품질 proxy로 측정한다.
2. 안전 KPI는 full rule logic AST가 아니라 status/rule_id/exclusion 일치로 측정한다.
3. adverse event KPI는 synthetic 연간 합계 proxy다.
4. sensor/genetic KPI는 현재 wearable/CGM/genetic modality만 다룬다.
5. frozen eval sample은 acceptance test가 아니라 metric contract를 고정하기 위한 seed dataset이다.

## 결론

- 지금 중요한 것은 모델보다 metric interface를 먼저 고정하는 것이다.
- 따라서 이 단계의 sample dataset과 calculator는 KPI 해석의 출발점이며, 구현 엔진이 바뀌어도 유지되어야 한다.
