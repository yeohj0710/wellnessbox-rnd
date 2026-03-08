# ADR-002: Eval First

상태: 채택

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 결정

구현보다 먼저 KPI 와 frozen eval 을 고정한다.

## 이유

1. 구현은 바뀔 수 있지만 평가 기준은 흔들리면 안 된다.
2. deterministic baseline 품질도 eval 없이는 개선 방향이 없다.
3. synthetic data 확장도 eval schema 가 먼저 있어야 한다.
