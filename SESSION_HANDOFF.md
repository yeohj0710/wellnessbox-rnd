# SESSION_HANDOFF

## 세션 종료 시점 요약

- `wellnessbox-rnd` 는 독립 R&D 저장소로 범위가 다시 고정되었다.
- 기준 문서는 `master_context.md` 와 `original_plan.pdf` 뿐이다.
- runtime code 는 FastAPI + deterministic baseline + frozen eval 중심으로 유지된다.
- 제품 repo 연동 문서는 현재 out-of-scope archive 로 격리되었다.

## 다음 세션이 먼저 읽어야 할 문서

1. `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
2. `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`
3. `C:/dev/wellnessbox-rnd/docs/00_scope_reset/00_scope_reset_summary.md`
4. `C:/dev/wellnessbox-rnd/docs/01_architecture/00_target_architecture.md`
5. `C:/dev/wellnessbox-rnd/docs/02_eval/01_metric_definitions.md`
6. `C:/dev/wellnessbox-rnd/docs/99_governance/02_priority_backlog.md`

## 유지되는 핵심 코드

- `C:/dev/wellnessbox-rnd/apps/inference_api/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/metrics/`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/evals/runner.py`

## archive / scope drift 로 취급할 것

- `C:/dev/wellnessbox-rnd/docs/03_integration/`
- `C:/dev/wellnessbox-rnd/docs/00_discovery/`
- `C:/dev/wellnessbox-rnd/docs/00_migration/`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/`
- `C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/`

## 지금까지 구현된 것

- FastAPI inference API
- recommend baseline
- frozen eval runner
- metric calculator
- demo catalog / safety rules
- R&D 단독 기준 아키텍처 / governance / scope reset 문서

## 아직 미구현인 것

- 대규모 eval set
- 고도화된 safety citations
- synthetic data pipeline
- optional LLM layer

## 주의점

- `wellnessbox` 의 특정 파일/흐름을 다음 작업 입력으로 다시 끌어오지 않는다.
- `docs/03_integration/` 내용은 현재 실행 기준이 아니다.
- runtime schema 변경 시 eval 과 문서를 같이 갱신한다.

## 다음 세션의 첫 작업

1. KPI / 요구사항 재정리
2. recommend schema refinement
3. frozen eval 확대 계획 작성
4. baseline safety / efficacy 강화 우선순위 결정
