# 서비스 경계

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 목적

이 문서는 `wellnessbox-rnd` 내부 경계와 외부 generic API boundary 를 정의한다. 특정 제품 repo 나 특정 UI 는 현재 범위 밖이다.

## 내부 경계

| 영역 | 책임 |
| --- | --- |
| intake | 입력 정규화, 기본 검증 |
| safety | 금기/상호작용/차단 판단 |
| recommendation | 후보 생성, 랭킹, 조합 선택 |
| efficacy | 기대 효과 점수화 |
| policy | 다음 행동 결정 |
| explanation | structured rationale / limitation |
| eval | frozen eval / metric 계산 |
| knowledge | rules / catalog / references |

## 외부 boundary

외부에 노출되는 것은 아래뿐이다.

- structured API
- generated schema 또는 OpenAPI
- eval / metric 보고서

외부에 노출하지 않는 것:

- 내부 규칙 원본 편집 구조
- 실험 메모
- synthetic generation 내부 grammar
- 미확정 prompt 실험물

## generic API surface 예시

| 범주 | 예시 endpoint | 응답 |
| --- | --- | --- |
| health | `GET /health` | runtime 상태 |
| recommendation | `POST /v1/recommend` | recommendation decision |
| safety | `POST /v1/safety/check` | safety decision |
| follow-up | `POST /v1/followup/evaluate` | efficacy / follow-up result |
| policy | `POST /v1/policy/next-action` | next action decision |

## 경계 규칙

1. runtime code 는 `src/wellnessbox_rnd/` 안에 둔다.
2. 평가 기준은 runtime 코드보다 먼저 고정한다.
3. 외부 소비자 요구로 내부 데이터 구조를 직접 노출하지 않는다.
4. 특정 제품 흐름을 기준으로 내부 모듈 책임을 나누지 않는다.

## out of scope

- 제품 파일 단위 변경 계획
- feature flag / rollout
- preview route / preview page
