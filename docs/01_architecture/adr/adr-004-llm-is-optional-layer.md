# ADR-004: LLM 은 선택적 레이어다

상태: 채택

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 결정

LLM 은 core decision engine 이 아니라 선택적 설명/보조 레이어로만 취급한다.

## 이유

1. safety / ranking / policy 는 deterministic 검증이 우선이다.
2. eval 과 재현성 확보가 먼저다.
3. LLM 은 baseline 이 충분히 안정된 뒤에만 붙인다.
