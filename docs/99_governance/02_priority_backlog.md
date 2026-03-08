# 우선순위 백로그

## P0

| 우선순위 | 작업 | 이유 | 주요 파일 |
| --- | --- | --- | --- |
| P0-1 | `/survey` 서버 프록시 route/server action 구현 | 실제 사용자 가치와 KPI 측정 시작점 | `C:/dev/wellnessbox/app/survey/*`, `C:/dev/wellnessbox/app/api/*`, `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts` |
| P0-2 | survey -> recommend adapter 구현 | live integration 의 필수 선행조건 | `C:/dev/wellnessbox/lib/b2b/public-survey.ts`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py` |
| P0-3 | legacy fallback 연결 | 기존 서비스 안정성 유지 | `C:/dev/wellnessbox/lib/wellness/analysis.ts` |
| P0-4 | shadow logging 추가 | rollout-safe 비교와 KPI 관측 필요 | `C:/dev/wellnessbox/lib/server/*` |
| P0-5 | frozen eval 100+ case 확대 | KPI gate 의 최소 데이터 확보 | `C:/dev/wellnessbox-rnd/data/frozen_eval/*` |
| P0-6 | safety rule set 확장 | 잘못된 추천을 줄이는 최우선 작업 | `C:/dev/wellnessbox-rnd/data/rules/safety_rules.json` |
| P0-7 | ranking/scoring 개선 | recommendation coverage 개선 | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/service.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/service.py` |
| P0-8 | missing info 질문 개선 | `collect_more_input` 정확도 개선 | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py` |
| P0-9 | OpenAPI/TS contract sync 프로세스 고정 | web-rnd 계약 drift 방지 | `C:/dev/wellnessbox-rnd/docs/03_integration/*` |
| P0-10 | README/PROGRESS/SESSION_HANDOFF 유지 | 다음 세션 연속성 확보 | repo 루트 및 governance 문서 |

## P1

| 우선순위 | 작업 | 이유 | 주요 파일 |
| --- | --- | --- | --- |
| P1-1 | NHIS summary enrichment API 설계 | 건강 연동 가치 증가 | `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary.ts` |
| P1-2 | product/catalog SSOT 전략 수립 | 실제 추천 품질 향상 | `C:/dev/wellnessbox-rnd/data/catalog/ingredients.json` |
| P1-3 | citation/근거 구조화 | safety_reference KPI 향상 | rules/catalog/future knowledge schema |
| P1-4 | rollout bucket/flag 운영 설계 구현 | 안전한 배포 | `wellnessbox` env + server config |
| P1-5 | response normalization/view model 정리 | UI 연동 비용 절감 | `wellnessbox` survey result layer |

## P2

| 우선순위 | 작업 | 이유 | 주요 파일 |
| --- | --- | --- | --- |
| P2-1 | chat helper thin interface | optional layer | `C:/dev/wellnessbox/app/api/chat/*` |
| P2-2 | LLM explanation layer | deterministic baseline 이후 품질 개선 | future RND module |
| P2-3 | sensor/genetic ingest 구조 | KPI 확장 | future integration module |

## 지금까지 구현된 것

- baseline engine
- frozen eval runner
- integration docs
- dev preview route

## 아직 미구현인 것

- live survey integration
- NHIS summary API
- chat thin interface
- production observability

## 우선순위 판단 기준

- KPI 직접 기여 여부
- 운영 리스크 감소 여부
- `wellnessbox` 변경 범위 최소화 여부
- source of truth 분리 유지 여부
