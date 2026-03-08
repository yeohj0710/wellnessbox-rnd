# ADR-001: web과 rnd를 하드 스플릿한다

- 상태: Accepted
- 날짜: 2026-03-08
- 기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 문맥

- `wellnessbox`에는 서비스 코드와 R&D 자산이 장기간 혼재되어 있었다.
- 이 상태는 중복 원본, 경계 붕괴, 런타임 리스크, 연구개발 자산 추적 실패를 만들었다.
- `master_context.md`는 평가 하네스, 재현성, KPI 달성을 웹 기능보다 우선하라고 명시한다.

## 결정

- `wellnessbox`는 Next.js 기반 웹서비스/UI 레이어로 한정한다.
- `wellnessbox-rnd`는 연구개발 전용 repo로 한정한다.
- 추천, 안전, 효과, 상태기계, 상담, 평가, 규칙, 프롬프트, 데이터셋 원본은 `wellnessbox-rnd`만 소유한다.
- `wellnessbox`는 API contract와 thin interface만 가진다.

## 이유

1. 연구개발 원본과 서비스 운영 로직을 분리해야 변경 위험을 제어할 수 있다.
2. KPI 우선 개발은 eval, rules, artifacts 중심인데 이것은 web repo 성격과 다르다.
3. 단일 개발자 기준으로도 repo 책임이 분리되어야 유지보수가 가능하다.

## 결과

- 장점: 경계 명확화, 원본 단일화, 실험 자산 추적 용이
- 비용: API contract 관리 필요, 초기 이관 비용 발생
- 후속 조치: thin interface 계약과 generated schema 체계 필요

## 기각한 대안

- 단일 repo 유지: 다시 혼합 상태가 된다.
- docs만 분리하고 코드는 유지: 추론 본체와 규칙 원본이 계속 web에 남는다.
