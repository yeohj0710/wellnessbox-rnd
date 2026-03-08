# Eval 데이터셋 스키마

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 포맷

- 파일 형식: JSONL
- 파일 위치: `data/frozen_eval/*.jsonl`
- 각 줄은 하나의 eval case다.
- 모든 sample case는 `synthetic: true`를 포함한다.

## 최상위 필드

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `case_id` | string | 고유 case 식별자 |
| `synthetic` | boolean | synthetic 여부 |
| `category` | string | case 범주 |
| `description` | string | 사람용 설명 |
| `request` | object | `/v1/recommend` 요청 payload |
| `expected` | object | 기대 결과 계약 |
| `follow_up` | object or null | 효과 metric용 전후 점수 |
| `integration` | object | modality별 연동 시도/성공 |
| `adverse_event_reported` | boolean | annual adverse count proxy |

## `expected` 구조

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `recommendation_reference.required_ingredients` | string[] | 추천 커버리지 기준 성분 |
| `expected_status` | string | `ok`, `needs_review`, `blocked` |
| `expected_next_action` | string | 상태기계 기대 결과 |
| `required_rule_ids` | string[] | safety rule ID 기준 |
| `required_excluded_ingredients` | string[] | safety exclusion 기준 |
| `required_explanation_terms` | string[] | 설명 품질 proxy 기준 |
| `minimum_explanation_term_coverage` | float | 설명 term coverage 최소값 |

## `follow_up` 구조

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `z_pre` | number | 복용 전 표준화 점수 |
| `z_post` | number | 복용 후 표준화 점수 |

## `integration` 구조

예시:

```json
{
  "wearable": { "attempted": 1, "success": 1 },
  "cgm": { "attempted": 1, "success": 0 },
  "genetic": { "attempted": 1, "success": 1 }
}
```

## 현재 sample case 범주

- 정상 추천
- 안전성 경고/차단
- 입력 누락/모호성
- 설명 품질 점검
- edge case

## 설계 이유

1. request는 실제 API 입력과 동일해야 한다.
2. expected는 구현이 바뀌어도 비교 가능한 최소 계약만 갖는다.
3. follow_up, integration, adverse는 운영 데이터가 없기 때문에 synthetic observation으로 시작한다.

## 주의

- 이 스키마는 현재 recommendation API 중심이다.
- chat 모듈, full citation graph, 실제 센서 인입 파이프라인이 생기면 필드가 확장될 수 있다.
- 하지만 기존 필드는 가급적 깨지지 않게 유지한다.
