# SESSION_HANDOFF

## 세션 종료 시점 요약

- `wellnessbox-rnd`는 pure R&D 저장소로만 유지 중이다.
- source of truth는 `master_context.md`와 `original_plan.pdf`다.
- 이번 루프에서는 `eval 데이터 생성 스크립트 개선`만 수행했다.
- frozen eval authoring을 위해 deterministic helper를 추가했다.
- 공식 KPI 점수는 바꾸지 않았고, eval workflow만 구조적으로 보강했다.

## 다음 세션에서 먼저 읽을 문서

1. `C:/dev/wellnessbox-rnd/PROGRESS.md`
2. `C:/dev/wellnessbox-rnd/NEXT_STEPS.md`
3. `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
4. `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`
5. `C:/dev/wellnessbox-rnd/docs/00_scope_reset/04_clean_rnd_execution_plan.md`
6. `C:/dev/wellnessbox-rnd/docs/02_eval/02_eval_dataset_schema.md`

## 이번 루프에서 직접 건드린 주요 파일

- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/evals/dataset_tools.py`
- `C:/dev/wellnessbox-rnd/scripts/manage_eval_dataset.py`
- `C:/dev/wellnessbox-rnd/tests/test_eval_dataset_tools.py`
- `C:/dev/wellnessbox-rnd/data/frozen_eval/README.md`
- `C:/dev/wellnessbox-rnd/docs/02_eval/02_eval_dataset_schema.md`
- `C:/dev/wellnessbox-rnd/PROGRESS.md`
- `C:/dev/wellnessbox-rnd/NEXT_STEPS.md`
- `C:/dev/wellnessbox-rnd/SESSION_HANDOFF.md`

## 현재 구현 상태

- FastAPI inference API
- recommend baseline
- frozen eval runner
- metric calculator
- alias-aware catalog normalization
- structured recommendation schema
- data-driven safety rules
- dataset authoring helper
  - `summary`
  - `validate`
  - `scaffold`

## 이번 루프에서 고정한 dataset invariant

- unique `case_id`
- sorted `case_id` order
- `request.request_id == case_id`
- `minimum_explanation_term_coverage` range check
- non-empty `required_explanation_terms` when coverage is above zero
- `integration.success <= attempted`

## 현재 검증 상태

- `python -m ruff check .`: 통과
- `python -m pytest`: `26 passed`
- `python scripts/run_eval.py`: 통과
- `python scripts/manage_eval_dataset.py validate`: issue 0건

## 현재 주요 metric

- `case_count = 16`
- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 13.070858781952536`
- `next_action_accuracy_pct = 100.0`
- `explanation_quality_accuracy_pct = 100.0`
- `safety_reference_accuracy_pct = 100.0`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 75.0`

## 아직 남은 큰 약점

- frozen eval이 아직 KPI gate로 쓰기에는 작다.
- integration KPI는 여전히 `75.0`이다.
- baseline failure 문서화가 아직 부족하다.
- scaffold는 minimal skeleton 중심이다.
- 자유 텍스트 product title parser는 아직 없다.

## 다음 루프 추천 작업

1. `baseline failure 분석 문서화`
2. `frozen eval 확대`
3. `efficacy scoring 개선`

## 주의사항

- `wellnessbox/`는 읽거나 참조하지 않는다.
- `docs/03_integration/`, `docs/00_discovery/`, `docs/00_migration/`, `docs/legacy_from_wellnessbox/`는 현재 범위 밖이다.
- KPI 해석이 불확실한 항목은 문서에 가정으로 남긴다.
- deterministic baseline 철학과 safety 우선 원칙을 유지한다.
