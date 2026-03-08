# frozen_eval

이 디렉터리는 WellnessBox R&D 평가 하네스의 frozen eval seed dataset을 둔다.

## 현재 파일

- `sample_cases.jsonl`: synthetic sample case 5건

## 원칙

- 현재 샘플은 전부 synthetic이다.
- 목표는 실제 KPI 측정 인터페이스를 먼저 고정하는 것이다.
- 구현 엔진이 바뀌어도 동일한 JSONL 스키마로 다시 평가할 수 있어야 한다.

## 포함 범주

- 정상 추천
- 안전성 경고/차단
- 입력 누락/모호성
- 설명 품질 점검
- edge case

## 주의

- 이 데이터셋은 아직 공식 검증용 본세트가 아니다.
- acceptance set은 향후 `data/frozen_eval/` 아래에 별도 버전으로 확장한다.

