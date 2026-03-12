# wellnessbox-rnd

`wellnessbox-rnd` 는 TIPS 연구개발 전용 독립 저장소다.

이 저장소는 **원문 구현 재현**이 아니라, **원문 p.25~26 KPI 달성**을 목표로 하는 R&D 작업 공간이다.

## 문서 역할

이 저장소에서 문서 역할은 아래처럼 구분한다.

- `AGENTS.md`
  - Codex/AI용 짧은 실행 계약서
  - 루틴 반복 작업 시 가장 먼저 따를 운영 규칙
- `docs/context/master_context.md`
  - KPI 중심 재설계까지 포함한 장문 기준 문서
  - 장기 맥락과 설계 철학의 기준
- `docs/context/original_plan.pdf`
  - 원문 기준 문서
  - KPI 해석/감사/audit 용 참고 원본
  - 루틴 반복 루프에서 전역 파싱 대상으로 쓰지 않음
- `PROGRESS.md`
  - 직전 루프의 실제 수행 결과 요약
- `NEXT_STEPS.md`
  - 다음 bounded loop의 우선순위
- `SESSION_HANDOFF.md`
  - 직전 작업자가 다음 루프에 넘기는 handoff 문서
- `README.md`
  - 사람용 저장소 개요 / 실행법 / 디렉터리 안내
  - planning authority 로 쓰지 않음

## 운영 원칙

- 절대 기준은 원문 p.25~26 KPI 달성이다.
- 구현 방식은 바꿔도 된다.
- 단일 창업자 + 단일 컴퓨터 기준으로 설계한다.
- 안전 판정은 deterministic structured rules 가 담당한다.
- learned artifact 는 필요하더라도 deterministic safety ceiling 아래에서 점진적으로 붙인다.
- 상담은 bounded RAG + verifier 중심으로 간다.
- synthetic / rule-generated / frozen-eval driven 방식이 기본이다.
- UI/운영 통합보다 평가 재현성과 실험 하네스가 우선이다.

## 현재 범위

현재 범위에 포함되는 것:

- KPI / 요구사항 해석
- R&D 전용 데이터 계약 / 스키마
- frozen eval
- deterministic baseline 추천 엔진
- safety / efficacy / ranking 로직
- synthetic data generation
- replay / simulation
- 독립 실행 가능한 inference API

현재 범위 밖(out of scope):

- 특정 제품 repo 와의 연동 설계 / 구현
- 특정 웹 페이지, route, server action 전제
- feature flag rollout
- preview page/helper
- NHIS/chat/survey 제품 흐름 연계
- 운영 화면 중심 개발

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
- structured next-action / safety evidence / limitation details in response schema
- frozen eval runner + metric calculators
- replay / simulation harness
- guarded learned effect / policy artifacts

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
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/simulation/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/synthetic/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/training/`
- 평가:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/metrics/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/evals/runner.py`
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/`

## 미구현 범위

- 실제 제품 catalog SSOT
- broad real-world evidence ingestion
- 운영 통합 레이어
- learned artifact 의 runtime 승격
- 대형 LLM/agent layer 의 본격 운용

## 문서 읽기 방식

### 1) 처음 맥락을 잡을 때

1. `AGENTS.md`
2. `docs/context/master_context.md`
3. `README.md`

### 2) routine loop 에서

1. `AGENTS.md`
2. `PROGRESS.md`
3. `NEXT_STEPS.md`
4. `SESSION_HANDOFF.md`
5. `README.md` (명령어 / 구조 확인이 필요할 때만)
6. `docs/context/master_context.md` (설계 해석이 더 필요할 때만)
7. `docs/context/original_plan.pdf` (KPI ambiguity / audit 시에만)

## 빠른 시작

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn apps.inference_api.main:app --reload
```
