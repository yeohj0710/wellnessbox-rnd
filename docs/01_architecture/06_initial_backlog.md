# 초기 백로그

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 우선순위 원칙

- KPI / eval 우선
- deterministic baseline 우선
- safety 우선
- 특정 제품 통합은 현재 범위 밖

## P0

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P0 | KPI / 요구사항 재정리 | metric 과 가정 표 완성 |
| P0 | recommend schema refinement | request/response 안정화 |
| P0 | frozen eval 확대 | synthetic case 100+ |
| P0 | safety rules 확장 | 차단/경고 커버리지 상승 |
| P0 | efficacy / ranking 개선 | coverage / policy 품질 개선 |
| P0 | explanation / limitations 정교화 | structured output 일관성 확보 |

## P1

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P1 | synthetic data generation 초안 | reproducible case generation |
| P1 | evidence registry 초안 | rule / evidence 참조 구조 정리 |
| P1 | follow-up evaluation 강화 | efficacy 추적 기준 정리 |
| P1 | policy engine 강화 | next action 분기 정교화 |

## P2

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P2 | optional LLM layer 검토 | deterministic baseline 이후 |
| P2 | large-scale synthetic pipeline | baseline 안정화 이후 |

## out of scope

- 특정 웹 페이지 / route 연동
- 제품 repo file-by-file 변경 계획
- feature flag / preview / rollout
