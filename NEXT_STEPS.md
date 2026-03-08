# NEXT_STEPS

## 다음 세션에서 가장 먼저 할 일

1. `master_context.md` 와 `original_plan.pdf` 를 다시 읽고 KPI/요구사항을 코드 측정 항목으로 재정리한다.
2. `src/wellnessbox_rnd/schemas/recommendation.py` 를 기준으로 R&D 전용 계약을 더 명확히 한다.
3. `data/frozen_eval/sample_cases.jsonl` 을 확장할 synthetic case 설계표를 만든다.
4. `safety_rules.json` 과 `ingredients.json` 의 확장 기준을 정한다.
5. deterministic baseline 의 ranking / missing info / explanation 약점을 보완한다.

## clean execution order

### 1. KPI / 요구사항 재정리

- 입력 기준:
  - `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
  - `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`
- 산출물:
  - KPI 목록
  - 측정 가능 metric
  - 가정 목록

### 2. R&D 데이터 계약 / 스키마 정교화

- 대상:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py`
- 목표:
  - 입력 용어 정제
  - explanation / evidence / missing info 구조 강화

### 3. frozen eval 확대

- 대상:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/evals/runner.py`
- 목표:
  - 정상 추천
  - 차단
  - 누락/모호성
  - 설명 품질
  - edge case

### 4. deterministic baseline 고도화

- 대상:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/`
- 목표:
  - intake normalization 품질 향상
  - recommendation 후보 선정 품질 향상

### 5. safety / efficacy / ranking 강화

- 대상:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/`
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/`
  - `C:/dev/wellnessbox-rnd/data/rules/`
  - `C:/dev/wellnessbox-rnd/data/catalog/`

### 6. synthetic data generation pipeline

- 목표:
  - eval 확대용 synthetic case 생성
  - follow-up / safety / policy synthetic pair 생성

### 7. optional LLM / agent layer

- 가장 마지막 단계다.
- deterministic baseline 과 eval 이 충분히 안정된 뒤에만 다룬다.

## KPI 달성 관점 다음 10개 작업

1. KPI 정의 재정리
2. metric 가정 재확인
3. schema refinement
4. frozen eval 확대
5. safety rules 확장
6. ranking 개선
7. explanation proxy 개선
8. evidence registry 초안
9. synthetic data builder 초안
10. optional LLM layer 성공/실패 기준 정의

## 현재 범위 밖

- 제품 repo 연동
- 특정 페이지/route 기반 adapter
- feature flag / rollout / timeout UX
- preview route / preview UI
- NHIS / chat / survey 제품 연결 계획

## 검증 순서

```bash
cd C:\dev\wellnessbox-rnd
python -m ruff check .
python -m pytest
python scripts/run_eval.py
```
