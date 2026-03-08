# PROGRESS

## 한 줄 상태

`wellnessbox-rnd` 는 기준 문서, 아키텍처, frozen eval, deterministic baseline 추천 API, `wellnessbox` dev preview 연동까지 완료된 상태다.

## Source Of Truth

- 연구개발 최상위 기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- 웹/R&D 경계 기준 문서: `C:/dev/wellnessbox-rnd/docs/01_architecture/01_service_boundary.md`
- 연동 기준 문서: `C:/dev/wellnessbox-rnd/docs/03_integration/00_integration_strategy.md`
- recommend 계약 기준: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py`
- OpenAPI 스냅샷: `C:/dev/wellnessbox-rnd/docs/03_integration/openapi.inference_api.json`

## 지금까지 구현된 것

### 문서/경계

- `wellnessbox` / `wellnessbox-rnd` hard split 방향 확정
- legacy R&D 문서와 agent 문서 이관
- 아키텍처 문서, ADR, eval 문서, integration 문서 작성 완료

### Python 서비스

- FastAPI 앱: `C:/dev/wellnessbox-rnd/apps/inference_api/main.py`
- health route: `C:/dev/wellnessbox-rnd/apps/inference_api/routes/health.py`
- recommend route: `C:/dev/wellnessbox-rnd/apps/inference_api/routes/recommend.py`
- 설정/로깅 기초: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/config.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/logging.py`

### baseline 추천 엔진

- intake normalization: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py`
- catalog loader: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/loaders.py`
- safety rules/service: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/rules.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/service.py`
- efficacy scoring: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/service.py`
- optimization/ranking: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/service.py`
- orchestration: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py`
- demo catalog/rules: `C:/dev/wellnessbox-rnd/data/catalog/ingredients.json`, `C:/dev/wellnessbox-rnd/data/rules/safety_rules.json`

### 평가 체계

- metric 정의: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/metrics/definitions.py`
- metric 계산기: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/metrics/calculators.py`
- eval runner: `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/evals/runner.py`
- 실행 스크립트: `C:/dev/wellnessbox-rnd/scripts/run_eval.py`
- frozen eval seed: `C:/dev/wellnessbox-rnd/data/frozen_eval/sample_cases.jsonl`
- 최신 산출물: `C:/dev/wellnessbox-rnd/artifacts/reports/eval_report.json`, `C:/dev/wellnessbox-rnd/artifacts/reports/eval_report.md`

### wellnessbox 최소 연동

- 서버 helper: `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts`
- preview route: `C:/dev/wellnessbox/app/api/internal/rnd/recommend-preview/route.ts`
- dev preview page: `C:/dev/wellnessbox/app/(dev)/rnd-preview/page.tsx`
- smoke check: `C:/dev/wellnessbox/scripts/qa/check-rnd-recommend-preview.cts`

## 아직 미구현인 것

- `/survey` 실제 런타임 서버 프록시 연동
- survey answer -> RND request adapter
- legacy survey engine fallback 실제 연결
- NHIS summary API 분리
- chat thin interface 분리
- 실제 제품 SSOT / product SKU 매핑
- 실제 citation graph / 근거 링크 구조
- larger frozen eval dataset
- 운영용 observability, structured persistence, rollout metrics
- LLM optional layer

## KPI 달성 관점에서 가장 중요한 다음 10개 작업

1. `/survey` 서버 프록시 연동 구현
2. survey payload -> `RecommendationRequest` adapter 구현
3. legacy fallback 과 RND 결과 shadow 비교 로깅 추가
4. frozen eval case 를 5건에서 100건 이상으로 확장
5. safety rule set 을 실제 금기/상호작용 기준으로 확장
6. efficacy scoring 을 demo catalog 에서 근거 기반 가중치 구조로 확장
7. recommendation ranking 과 missing info 질문 품질 개선
8. 실제 제품/성분 SSOT 연결 전략 고정
9. NHIS summary 를 별도 enrichment API 로 분리
10. rollout flag, timeout, fallback metric 을 `wellnessbox` 서버에 반영

## 현재 리스크 / 깨질 수 있는 부분

- `wellnessbox-rnd` baseline catalog 는 demo 데이터라 실제 제품 정확도를 보장하지 않는다.
- frozen eval 은 synthetic seed 5건이라 KPI gate 로 쓰기엔 아직 작다.
- `sensor_genetic_integration_rate_pct` 는 아직 목표 미달이다.
- `wellnessbox` preview 연동은 dev-only 이고 실제 `/survey` 흐름은 아직 붙지 않았다.
- `wellnessbox/docs`와 일부 기존 파일은 인코딩 흔적이 섞여 있어 후속 편집 시 주의가 필요하다.

## wellnessbox / wellnessbox-rnd 경계

- `wellnessbox`: UI, 인증, 주문, 세션, 운영 route, fallback runtime, feature flag, server proxy
- `wellnessbox-rnd`: 규칙, 점수화, safety, eval, 추론 API, prompt/실험/연구 문서
- 원본 중복 저장 금지
- 공통 계약은 API/OpenAPI/generated schema 로만 연결

## 레거시와 새 문서의 관계

- 과거 이관 문서: `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/`
- 현재 기준 문서:
  - context: `C:/dev/wellnessbox-rnd/docs/context/`
  - architecture: `C:/dev/wellnessbox-rnd/docs/01_architecture/`
  - eval: `C:/dev/wellnessbox-rnd/docs/02_eval/`
  - integration: `C:/dev/wellnessbox-rnd/docs/03_integration/`
  - governance: `C:/dev/wellnessbox-rnd/docs/99_governance/`
- legacy 문서는 참고 자료이고, 신규 설계 결정은 새 문서에만 기록한다.

## 다음 세션 첫 작업

- `wellnessbox` `/survey` 서버 프록시 구현을 시작하고, 기존 fallback 을 유지한 shadow mode 를 붙인다.
