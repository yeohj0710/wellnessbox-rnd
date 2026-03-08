# ADR-003: Deterministic Baseline First

상태: 채택

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 결정

핵심 의사결정은 먼저 규칙 기반 + 점수화 기반 deterministic baseline 으로 구현한다.

## 이유

1. safety 와 ranking 은 먼저 검증 가능한 형태가 필요하다.
2. KPI 추적과 디버깅이 쉽다.
3. optional LLM layer 를 붙이더라도 baseline 이 기준점이 된다.
