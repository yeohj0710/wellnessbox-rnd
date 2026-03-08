# ADR-005: 제품 저장소와 결합된 학습/추론 본체를 두지 않는다

상태: 채택

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 결정

학습 코드, 데이터 생성, 평가 하네스, 추론 본체는 `wellnessbox-rnd` 에만 둔다. 특정 제품 저장소는 현재 R&D 설계 기준이 아니다.

## 이유

1. 연구 실험과 운영 변경을 강하게 결합하면 재현성이 무너진다.
2. KPI / eval / runtime 을 한 저장소 안에서 통제해야 한다.
3. scope drift 를 막으려면 제품 구조 의존을 줄여야 한다.

## 결과

- 제품 repo 연동 문서는 archive 처리한다.
- generic external API boundary 만 남긴다.
