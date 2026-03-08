# SESSION_HANDOFF

## 이번 세션 종료 시점 요약

- `wellnessbox-rnd` 는 Python/FastAPI 기반 독립 R&D repo 로 초기화되어 있다.
- deterministic baseline recommend API 와 frozen eval 이 동작한다.
- `wellnessbox` 와의 hard split 문서화가 완료되어 있다.
- `wellnessbox` 쪽에는 dev-only preview 연동만 최소 범위로 추가되어 있다.
- 실제 `/survey` 운영 흐름은 아직 바꾸지 않았다.

## 다음 세션이 읽어야 할 순서

1. `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
2. `C:/dev/wellnessbox-rnd/docs/01_architecture/00_target_architecture.md`
3. `C:/dev/wellnessbox-rnd/docs/02_eval/01_metric_definitions.md`
4. `C:/dev/wellnessbox-rnd/docs/03_integration/00_integration_strategy.md`
5. `C:/dev/wellnessbox-rnd/docs/03_integration/05_file_by_file_change_plan.md`
6. 이 문서

## 지금까지 완료된 구현

### R&D repo

- project scaffold: `pyproject.toml`, `.env.example`, `README.md`
- FastAPI app:
  - `C:/dev/wellnessbox-rnd/apps/inference_api/main.py`
  - `C:/dev/wellnessbox-rnd/apps/inference_api/routes/health.py`
  - `C:/dev/wellnessbox-rnd/apps/inference_api/routes/recommend.py`
- domain / schemas / engines:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/`
- eval:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/evals/runner.py`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/metrics/`
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/sample_cases.jsonl`

### wellnessbox 최소 연동

- helper: `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts`
- route: `C:/dev/wellnessbox/app/api/internal/rnd/recommend-preview/route.ts`
- page: `C:/dev/wellnessbox/app/(dev)/rnd-preview/page.tsx`
- smoke: `C:/dev/wellnessbox/scripts/qa/check-rnd-recommend-preview.cts`

## 아직 미구현인 것

- `/survey` 서버 프록시 실연동
- survey answer adapter
- legacy fallback result UI 병행
- NHIS summary 분리
- chat thin interface
- larger eval dataset
- product/catalog SSOT 연계
- production logging/metrics

## 현재 기준 커맨드

### wellnessbox-rnd

```bash
cd C:\dev\wellnessbox-rnd
python -m ruff check .
python -m pytest
python scripts/run_eval.py
uvicorn apps.inference_api.main:app --reload
```

### wellnessbox

```bash
cd C:\dev\wellnessbox
npm run qa:rnd:preview-route
npm run dev
```

preview env 예시:

```bash
WB_RND_PREVIEW_ENABLED=1
WB_RND_SERVICE_BASE_URL=http://127.0.0.1:8000
WB_RND_RECOMMEND_TIMEOUT_MS=4000
```

## 깨질 수 있는 부분 / 주의점

- `wellnessbox` 쪽에는 이미 크고 복잡한 survey runtime 이 있다. 직접 계산 로직을 한 번에 지우면 안 된다.
- preview 연동 helper 는 dev-only 전제다. production 경로로 바로 재사용하지 말고 `/survey` 전용 adapter 를 따로 두는 편이 안전하다.
- `wellnessbox-rnd` recommend 스키마 변경 시 OpenAPI 스냅샷과 integration 문서를 같이 갱신해야 한다.
- 일부 구 문서는 인코딩이 섞여 있으므로 편집 시 diff 를 주의해서 봐야 한다.

## 경계 재확인

- `wellnessbox`:
  - UI
  - 세션/인증
  - 운영 route
  - feature flag
  - server proxy
  - fallback UX
- `wellnessbox-rnd`:
  - safety rule
  - scoring
  - eval
  - recommendation contract
  - API
  - 연구 문서

## legacy 문서와 새 문서의 관계

- legacy 참고:
  - `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/`
- 현재 의사결정 기준:
  - `C:/dev/wellnessbox-rnd/docs/context/`
  - `C:/dev/wellnessbox-rnd/docs/01_architecture/`
  - `C:/dev/wellnessbox-rnd/docs/02_eval/`
  - `C:/dev/wellnessbox-rnd/docs/03_integration/`
  - `C:/dev/wellnessbox-rnd/docs/99_governance/`

## 다음 세션에서 가장 먼저 할 일

1. `wellnessbox` `/survey`에 붙일 서버 프록시 route 또는 server action 경로를 결정한다.
2. `public-survey.ts` 기준으로 survey answer -> `RecommendationRequest` 매핑표를 만든다.
3. RND 결과를 shadow mode 로만 호출하고 기존 `analysis.ts` 결과와 나란히 비교한다.
