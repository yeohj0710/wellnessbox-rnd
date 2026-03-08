# ADR-001: R&D 저장소는 독립 저장소로 유지한다

상태: 채택

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 결정

연구개발 source of truth 는 `wellnessbox-rnd` 안에만 둔다. 특정 제품 repo 구조나 운영 흐름은 현재 R&D 실행 기준이 아니다.

## 이유

1. KPI 달성은 제품 화면보다 규칙/평가/추천/효과 추정 품질에 달려 있다.
2. 제품 구조를 기준으로 R&D 를 설계하면 scope drift 가 반복된다.
3. 독립 저장소여야 평가, synthetic data, runtime, 문서 기준을 한곳에 고정할 수 있다.

## 결과

- 규칙, catalog, eval, runtime, 연구 문서는 이 저장소만 소유한다.
- 제품 연동 문서는 archive 또는 deferred 로 다룬다.
