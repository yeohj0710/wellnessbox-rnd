# NEXT_STEPS

## 직전 루프 결과 반영

- 완료 작업: `eval 데이터 생성 스크립트 개선`
- 핵심 산출물:
  - `dataset_tools.py`
  - `manage_eval_dataset.py`
  - dataset summary / validate / scaffold workflow
  - eval dataset invariant 고정
- 검증 결과:
  - `python -m ruff check .`: 통과
  - `python -m pytest`: `26 passed`
  - `python scripts/run_eval.py`: 통과
  - `python scripts/manage_eval_dataset.py validate`: issue 0건

## 다음 루프 우선순위 후보

1. `baseline failure 분석 문서화`
2. `frozen eval 확대`
3. `efficacy scoring 개선`
4. `safety_rules 강화`
5. `recommendation schema 정교화`

## 우선순위 기준

- 원문 p.25~26 KPI에 직접 기여하는가
- 현재 frozen eval 실패 또는 coverage gap과 직접 연결되는가
- safety를 약화하지 않는가
- deterministic baseline 철학을 유지하는가
- 구현 복잡도 대비 측정 가능한 개선 폭이 큰가

## 추천 작업 상세

### 1. `baseline failure 분석 문서화`

- 목표:
  - 지금까지 고정된 regression과 아직 풀지 못한 failure mode를 문서로 정리
- 이유:
  - eval이 커질수록 어떤 failure를 이미 커버했고 무엇이 비어 있는지 먼저 보여줄 필요가 있다.
- 주요 대상:
  - `C:/dev/wellnessbox-rnd/docs/02_eval/`

### 2. `frozen eval 확대`

- 목표:
  - 새 helper를 이용해 integration bottleneck, schema rationale, richer alias 케이스를 추가
- 이유:
  - 이번 루프에서 authoring helper를 만들었으므로, 다음에는 실제 regression set 확장이 자연스럽다.
- 주요 대상:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/`
  - `C:/dev/wellnessbox-rnd/tests/`

### 3. `efficacy scoring 개선`

- 목표:
  - goal/symptom/lifestyle signal 연결을 더 분명하게 보강
- 이유:
  - 현재 공식 metric 중 점수는 유지되고 있지만, efficacy breakdown은 아직 단순하다.
- 주요 대상:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/`

### 4. `safety_rules 강화`

- 목표:
  - exclusion coverage와 citation-ready rule metadata를 더 넓힘
- 주요 대상:
  - `C:/dev/wellnessbox-rnd/data/rules/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/`

### 5. `recommendation schema 정교화`

- 목표:
  - response contract 전용 문서와 downstream eval 연결을 보강
- 주요 대상:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/`
  - `C:/dev/wellnessbox-rnd/docs/`

## 현재 남은 핵심 리스크

- frozen eval이 아직 작다.
- `sensor_genetic_integration_rate_pct = 75.0`이다.
- failure mode 문서가 부족하다.
- scaffold는 minimal case 생성까지만 제공한다.
- free-text parser는 없다.

## 범위 밖

- `wellnessbox/`
- `docs/03_integration/`
- `docs/00_discovery/`
- `docs/00_migration/`
- `docs/legacy_from_wellnessbox/`
- LLM / agent layer / fine-tuning / 외부 API
