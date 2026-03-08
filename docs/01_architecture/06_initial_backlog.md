# 초기 백로그

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 백로그 원칙

- 구현 순서는 기능 화려함이 아니라 KPI 기여도와 재현성 기준으로 정한다.
- 웹 연동보다 먼저 contract, state machine, safety, eval을 만든다.
- LLM 의존 작업은 deterministic baseline 이후로 미룬다.

## Phase 0. 경계 확정

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P0 | `master_context.md` 기준 고정 유지 | 아키텍처/ADR 문서가 이를 명시 |
| P0 | web-rnd API contract 초안 작성 | 추천/안전/효과/정책 API 스키마 존재 |
| P0 | thin interface 대상 고정 | web에 남을 adapter 목록 확정 |

## Phase 1. 평가 하네스 우선 구축

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P0 | KPI별 eval case 형식 정의 | 추천/안전/상담/정책 공통 포맷 작성 |
| P0 | frozen eval loader 구현 | 파일 기반 eval 실행 가능 |
| P0 | 통합 리포트 포맷 구현 | Markdown/JSON 결과 생성 |
| P1 | 회귀 비교기 구현 | 이전 run 대비 pass/fail 표시 |

## Phase 2. deterministic baseline 엔진

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P0 | 입력 정규화 스키마 구현 | `UserSnapshot` 생성 가능 |
| P0 | 안전 규칙 엔진 v0 구현 | 금기/상호작용/과량 차단 가능 |
| P0 | 추천 점수화 v0 구현 | 상위 조합 3개 산출 가능 |
| P0 | 정책 상태기계 v0 구현 | 다음 행동 5종 분기 가능 |
| P1 | 효과 정량화 v0 구현 | 전후 점수 계산 가능 |

## Phase 3. 데이터 자산 구축

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P0 | 규칙/근거 레퍼런스 테이블 정리 | citation 가능한 구조화 파일 존재 |
| P0 | synthetic user case 생성기 구현 | 추천/안전 eval용 100+ case 생성 |
| P1 | follow-up synthetic pair 생성기 구현 | 효과 평가용 전후 쌍 100+ 생성 |
| P1 | 상담 QA 세트 구축 | 100+ 테스트 문항 존재 |

## Phase 4. API화

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P0 | `/v1/intake/normalize` 구현 | schema validation 통과 |
| P0 | `/v1/safety/check` 구현 | 안전 판정 JSON 반환 |
| P0 | `/v1/recommendations/plan` 구현 | 추천 조합 JSON 반환 |
| P0 | `/v1/followup/evaluate` 구현 | 개선도 JSON 반환 |
| P0 | `/v1/policy/next-action` 구현 | 상태기계 결과 반환 |
| P1 | `/v1/chat/answer` 구현 | optional layer로 동작 |

## Phase 5. 웹 연동

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P0 | `wellnessbox` thin client 추가 | 로컬 API 호출 가능 |
| P0 | `/survey` 결과 DTO 매핑 | web 화면 렌더링 유지 |
| P0 | `/chat` 어댑터 교체 설계 | 직접 모델 호출 제거 계획 확정 |
| P1 | NHIS AI summary contract 설계 | enrichment API contract 존재 |

## Phase 6. 운영 검증

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P0 | 배포 전 eval gate | KPI 회귀 실패 시 배포 중단 |
| P0 | run log/trace 저장 | run_id 기준 추적 가능 |
| P1 | adverse event 모니터링 | 월별 추이 대시보드 가능 |
| P1 | 센서/유전자 연동율 측정 | 성공률 집계 가능 |

## Phase 7. 선택적 LLM 강화

| 우선순위 | 작업 | 완료 기준 |
| --- | --- | --- |
| P2 | 상담 응답 품질 개선 | 91% 목표에 근접 |
| P2 | 설명 문장 생성 개선 | 구조화 근거 기반 설명 가능 |
| P2 | prompt registry 버전 관리 | 프롬프트 변경 이력 추적 |

## 이번 설계 기준의 실제 코드 시작 범위

1. `contracts`
2. `intake`
3. `safety_engine`
4. `recommendation_engine`
5. `policy_engine`
6. `eval_runner`

## 이번 단계에서 의도적으로 미루는 것

- 대규모 모델 학습
- 멀티 에이전트 그래프
- GPU 전용 파이프라인
- 복잡한 분산 배포
- web 내부 AI 로직 재구현
