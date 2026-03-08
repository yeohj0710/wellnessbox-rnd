# wellnessbox-rnd

`wellnessbox-rnd` 는 TIPS 연구개발 전용 독립 저장소다.

현재 이 저장소의 연구개발 source of truth 는 아래 두 문서뿐이다.

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

`wellnessbox` 구조, 특정 설문 흐름, NHIS 연동, chat route, preview route, feature flag, 운영 화면은 현재 R&D 실행 범위의 입력값이 아니다.

## 현재 범위

현재 범위에 포함되는 것:

- KPI/요구사항 해석
- R&D 전용 데이터 계약/스키마
- frozen eval
- deterministic baseline 추천 엔진
- safety / efficacy / ranking 로직
- synthetic data generation 계획
- 독립 실행 가능한 inference API

현재 범위 밖(out of scope):

- 특정 제품 repo 와의 연동 설계/구현
- 특정 웹 페이지, route, server action 전제
- feature flag rollout
- preview page/helper
- NHIS/chat/survey 제품 흐름 연계

## 현재 구현 상태

- FastAPI 기반 최소 inference API
- `/health`
- `/v1/recommend`
- intake normalization
- personal safety validation
- candidate filtering
- efficacy / goal scoring
- optimization / ranking
- templated explanation generation
- frozen eval runner + metric calculators

## 유지하는 런타임 자산

- API:
  - `C:/dev/wellnessbox-rnd/apps/inference_api/main.py`
  - `C:/dev/wellnessbox-rnd/apps/inference_api/routes/health.py`
  - `C:/dev/wellnessbox-rnd/apps/inference_api/routes/recommend.py`
- 엔진:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/`
- 평가:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/metrics/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/evals/runner.py`
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/`

## 미구현 범위

- 실제 제품 catalog SSOT
- 대형 synthetic dataset 파이프라인
- real-world evidence ingestion
- optional LLM/agent layer
- 운영 통합 레이어

## 빠른 시작

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn apps.inference_api.main:app --reload
```

확인:

- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/v1/recommend`

검증:

```bash
python -m ruff check .
python -m pytest
python scripts/run_eval.py
```

## 문서 읽기 순서

1. `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
2. `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`
3. `C:/dev/wellnessbox-rnd/docs/00_scope_reset/00_scope_reset_summary.md`
4. `C:/dev/wellnessbox-rnd/docs/01_architecture/00_target_architecture.md`
5. `C:/dev/wellnessbox-rnd/docs/02_eval/01_metric_definitions.md`
6. `C:/dev/wellnessbox-rnd/PROGRESS.md`
7. `C:/dev/wellnessbox-rnd/NEXT_STEPS.md`

## 디렉터리 개요

```text
apps/inference_api/        FastAPI 추론 API
src/wellnessbox_rnd/       도메인, 스키마, safety/efficacy/optimizer/orchestration
data/catalog/              demo ingredient catalog
data/rules/                safety rules
data/frozen_eval/          frozen eval seed dataset
artifacts/reports/         eval 산출물
docs/context/              절대 기준 문서
docs/01_architecture/      독립 R&D 아키텍처
docs/02_eval/              평가 체계 문서
docs/00_scope_reset/       범위 재고정 감사 문서
docs/03_integration/       현재 out-of-scope archive
docs/legacy_from_wellnessbox/  과거 참고용 archive
docs/imported/wellnessbox/     과거 참고용 archive
```

## 주의점

- 신규 연구개발 문서와 코드는 `wellnessbox-rnd` 안에서만 추가한다.
- 과거 `wellnessbox` 기반 문서는 참고용 archive 일 뿐 현재 실행 기준이 아니다.
- `docs/03_integration/` 은 현재 범위 밖으로 보류된 상태다.
