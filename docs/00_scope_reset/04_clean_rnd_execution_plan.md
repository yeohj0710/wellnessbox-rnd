# clean R&D execution plan

## 원칙

- 입력 기준은 `master_context.md` 와 `original_plan.pdf` 뿐이다.
- 특정 제품 repo, 페이지, route, 파일명, 운영 플로우를 실행 계획에 넣지 않는다.
- 평가 기준을 먼저 고정하고 구현은 그 뒤에 바꾼다.

## 작업 순서

### 1. KPI / 요구사항 재정리

- 목표:
  - 원문 요구사항을 코드 측정 단위로 재분해
  - 가정과 불명확성을 명시
- 산출물:
  - KPI 표
  - metric 정의
  - pass/fail 기준

### 2. R&D 데이터 계약 / 스키마 정교화

- 목표:
  - 입력/출력 schema 안정화
  - evidence / limitation / missing info 구조 명확화
- 대상:
  - `src/wellnessbox_rnd/schemas/`

### 3. frozen eval 확대

- 목표:
  - synthetic case 를 충분히 늘려 회귀 검증 기반 확보
- 대상:
  - `data/frozen_eval/`
  - `src/wellnessbox_rnd/evals/`

### 4. deterministic baseline 고도화

- 목표:
  - intake normalization 정확도 향상
  - ranking 품질 향상
  - blocked / needs_review / ok 기준 명확화

### 5. safety / efficacy / ranking 강화

- 목표:
  - safety rule coverage 확대
  - efficacy scoring 근거 강화
  - ranking penalty / diversity / conservatism 조정

### 6. synthetic data generation pipeline

- 목표:
  - eval 확대 자동화
  - follow-up / policy / safety synthetic pair 생성

### 7. optional LLM / agent layer

- 목표:
  - deterministic baseline 과 eval 이 충분히 안정된 뒤에만 보조 계층으로 검토
- 조건:
  - core decision 은 계속 deterministic / structured / testable 이어야 함

## 현재 범위 밖

미래에는 외부 애플리케이션이 이 저장소의 generic API boundary 를 소비할 수 있다. 그러나 그 통합 방식, adapter, feature flag, rollout, 제품 화면 연결은 현재 범위 밖이다.
