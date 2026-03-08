# 지금까지의 결정

## 최상위 결정

1. 현재 연구개발 source of truth 는 아래 두 문서뿐이다.
   - `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
   - `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`
2. `wellnessbox-rnd` 는 완전히 독립적인 R&D 저장소다.
3. 특정 제품 repo 의 구조, 화면, route, survey, NHIS, chat, preview route 는 현재 실행 범위의 입력값이 아니다.

## 기술 결정

- FastAPI + Pydantic + pytest + ruff
- deterministic baseline first
- eval first
- LLM is optional layer
- synthetic data generation 은 baseline/eval 뒤에 온다

## 문서 결정

- 실행 기준 문서:
  - `docs/context/`
  - `docs/01_architecture/`
  - `docs/02_eval/`
  - `docs/99_governance/`
- archive 문서:
  - `docs/03_integration/`
  - `docs/00_discovery/`
  - `docs/00_migration/`
  - `docs/legacy_from_wellnessbox/`
  - `docs/imported/wellnessbox/`

## 런타임 결정

- 현재 유지하는 API:
  - `/health`
  - `/v1/recommend`
- 현재 유지하는 핵심 코드:
  - domain
  - schemas
  - safety
  - efficacy
  - optimizer
  - orchestration
  - metrics
  - eval runner

## 범위 밖 결정

- 제품 연동 설계/구현은 현재 하지 않는다.
- feature flag, rollout, preview route 계획은 현재 하지 않는다.
- 제품 repo 기준 file-by-file adapter 설계는 현재 하지 않는다.

## KPI 관점 우선순위

1. safety
2. recommendation quality
3. measurable eval
4. efficacy / policy
5. optional LLM layer
