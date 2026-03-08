# PROGRESS

## 현재 상태

`wellnessbox-rnd`는 pure R&D 저장소로만 유지 중이다. 현재 source of truth는 아래 두 문서다.

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

이번 루프에서는 `eval 데이터 생성 스크립트 개선`만 수행했다. 목표는 frozen eval을 더 크게 만들기 전에, 케이스 생성과 검증을 deterministic helper로 고정하는 것이었다.

## 지금까지 구현된 것

- FastAPI inference API
- deterministic baseline recommendation engine
- intake normalization
- safety validation
- efficacy scoring
- ranking / optimizer
- structured recommendation schema
- frozen eval runner
- metric calculators
- alias-aware catalog normalization
- data-driven safety rules

## 이번 루프 변경 사항

- `src/wellnessbox_rnd/evals/dataset_tools.py` 추가
  - eval case skeleton 생성
  - dataset summary 계산
  - dataset invariant validation
  - sorted JSONL rewrite helper
- `scripts/manage_eval_dataset.py` 추가
  - `summary`
  - `validate`
  - `scaffold`
- dataset invariant를 코드로 고정
  - unique `case_id`
  - lexicographic `case_id` order
  - `request.request_id == case_id`
  - explanation coverage 범위 체크
  - `integration.success <= attempted`
- eval authoring 관련 문서 갱신

## 왜 이 작업을 우선했는가

- 현재 루프 원칙이 `eval first`인데, frozen eval authoring이 거의 수동 JSONL 편집에 의존하고 있었다.
- 현재 frozen eval은 여전히 작아서, 다음 단계의 `frozen eval 확대`를 하기 전에 생성/검증 helper를 먼저 두는 편이 안전하다.
- 이 작업은 공식 KPI를 인위적으로 바꾸지 않으면서도, future regression set expansion의 실패 비용을 낮춘다.
- deterministic baseline 철학과 safety 우선 원칙을 그대로 유지할 수 있다.

## 최신 검증 결과

- `python -m ruff check .`: 통과
- `python -m pytest`: `26 passed`
- `python scripts/run_eval.py`: 통과
- `python scripts/manage_eval_dataset.py validate`: validation issue 0건

### frozen eval 주요 metric

- `case_count`: `16 -> 16`
- `recommendation_coverage_pct`: `100.0 -> 100.0`
- `efficacy_improvement_pp`: `13.07 -> 13.07`
- `next_action_accuracy_pct`: `100.0 -> 100.0`
- `explanation_quality_accuracy_pct`: `100.0 -> 100.0`
- `safety_reference_accuracy_pct`: `100.0 -> 100.0`
- `adverse_event_count_yearly`: `0.0 -> 0.0`
- `sensor_genetic_integration_rate_pct`: `75.0 -> 75.0`

### 새 dataset summary 기준점

- `expected_next_action_counts`
  - `start_plan = 8`
  - `collect_more_input = 5`
  - `needs_human_review = 3`
- `integration_attempted_case_counts`
  - `wearable = 4`
  - `cgm = 2`
  - `genetic = 2`

## 가정

- 이번 루프의 개선은 공식 KPI 점수 상승이 아니라 eval authoring workflow의 구조 개선이다.
- `sensor_genetic_integration_rate_pct`는 여전히 dataset observation proxy다.
- frozen eval dataset은 여전히 synthetic regression set이다.

## 아직 부족한 점

- frozen eval은 아직 KPI gate로 쓰기에는 작다.
- integration KPI는 여전히 `75.0`이다.
- failure mode 문서화는 아직 얇다.
- scaffold는 minimal skeleton 수준이고, richer template library는 아직 없다.
- 자유 텍스트 product title parser는 아직 없다.

## 다음 루프 추천 작업

- `baseline failure 분석 문서화`
- `frozen eval 확대`
- `efficacy scoring 개선`
