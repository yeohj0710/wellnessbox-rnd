# ADR-005: Next.js 내부에서 학습과 추론 본체를 운영하지 않는다

- 상태: Accepted
- 날짜: 2026-03-08
- 기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 문맥

- 기존 `wellnessbox`에는 AI 관련 코드와 실험 자산이 섞여 있었다.
- Next.js repo 안에 학습 코드, 모델 아티팩트, 평가 하네스를 두면 런타임과 연구개발 변경이 서로를 깨뜨린다.
- 무거운 파이프라인은 별도 프로세스와 별도 repo가 있어야 재현성과 배포가 단순해진다.

## 결정

- 학습 코드, 데이터 생성, 평가 하네스, 추론 본체, 모델 가중치는 `wellnessbox-rnd`에만 둔다.
- `wellnessbox`는 HTTP API 호출, 결과 렌더링, 세션 저장만 수행한다.
- web repo 안에는 thin client와 generated contract 외의 AI 원본을 두지 않는다.

## 이유

1. 웹서비스 가용성과 R&D 실험 속도를 동시에 지키려면 프로세스 분리가 필요하다.
2. 단일 개발자 환경에서도 프로세스 분리가 디버깅과 배포를 단순화한다.
3. Next.js는 UI/운영 서버이고, 연구 파이프라인 런타임과 역할이 다르다.

## 결과

- 장점: 런타임 안정성, repo 책임 명확화, artifact 관리 용이
- 비용: API 계약 관리와 배포 파이프라인이 추가된다
- 후속 조치: `wellnessbox-rnd` API, eval runner, contract package 우선 구현

## 기각한 대안

- Next.js API route 안에 추론 본체 유지: 배포와 실험이 강하게 결합된다.
- 모델/프롬프트를 web repo에 보관: 원본 단일화 원칙을 깨뜨린다.
