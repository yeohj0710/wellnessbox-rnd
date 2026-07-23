# 연구계획서 정렬 재감사

## 결론

현재 구현은 closed-loop의 입력 수집, 후속 작업 예약, 일부 재평가 요청, 중대한 이상사례 중단까지 지원한다. 그러나 연구계획서가 요구하는 핵심 제어 루프는 아직 닫히지 않았다. `ClosedLoopState`는 `FOLLOWUP_ACTIVE`에서 후속 입력을 받은 뒤 같은 상태로 돌아가며, 개선·악화 결과에 따라 조합 유지·감량·교체를 결정하지 않는다. 유지·조정·교체는 별도 `PlanLifecycleState`가 외부 요청을 받아 기록할 뿐이다. 이 분리는 기존 `ClosedLoopState`와 `BoundedAgent`를 확장하라는 기준 프로그램의 확정 설계와 충돌하므로 중대 어긋남으로 판정한다.

연구계획서 원본은 59쪽이며 SHA-256 값은 `31291e6f93977fa2d5d083d0161743c49debef25caf12dccf6edc7fa1c2197d4`다. 이 값은 `data/original_plan/requirements_manifest_v1.json`의 `original_plan_sha256`과 일치한다. 16~24쪽은 이미지로 다시 렌더링해 표와 화살표를 직접 확인했다.

## 계획서가 요구하는 closed-loop와 현재 구현

| 계획서 구성 요소 | 원문 | 현재 구현 | 판정 |
|---|---|---|---|
| 개인 상태와 근거를 한 저장소에서 읽기 | 16쪽 | `src/wellnessbox_rnd/interim/store.py`, 사용자 프로필·근거·실행 이벤트 저장 구조가 있다. | 구현됨 |
| 개인별 안전 범위 산출 | 17쪽 | `src/wellnessbox_rnd/interim/safety.py`와 `BoundedAgent`의 안전 검사 경로가 있다. | 구현됨 |
| 복용 전후 효과 수치화 | 18~19쪽 | PRO와 기기 입력을 저장하고 재평가 작업을 예약한다. 효과 수치 연결은 OP-051~060과 OP-097에 분산돼 있다. | 부분 구현 |
| 안전·효과·비용을 반영한 조합 최적화 | 20쪽 | 후보 순위화와 조합 최적화 경로가 있으며 `BoundedAgent`가 계획 시작 전 순서를 강제한다. | 구현됨 |
| 상태를 주기적으로 수집하고 다음 행동 결정 | 21~22쪽 | `WorkflowJobQueue`가 7일 후속 일정, 입력 수신 재평가, 30일 만기 작업을 만든다. 그러나 입력 결과에 따른 유지·감량·교체 정책은 없다. | 부분 구현 |
| 개선·악화·이상사례에 따른 유지·조정·교체·중단 | 21쪽 | 중대한 이상사례는 계획 중단과 약사 검토로 이어진다. 일반 follow-up은 `FOLLOWUP_ACTIVE` 자기 전이만 한다. 별도 `PlanLifecycleState`는 호출자가 이미 정한 action을 기록하므로 다음 행동을 판단하지 않는다. | 미구현 |
| 센서·유전자 입력을 후속 판단에 반영 | 23~24쪽 | 기기 입력은 재평가 작업을 만든다. OP-097은 기기 수치의 후속평가 반영을 주장한다. 유전자 신규 입력에서 기존 상태기계의 재평가 전이로 이어지는 단일 정책은 확인되지 않았다. | 부분 구현 |
| 다음 수행 작업 정확도 측정 | 25~26쪽, master context 7.2 C | 일반 평가 코드에 `next_action_accuracy_pct`가 있지만, 상태·이벤트·정답 행동으로 구성된 100개 이상 전용 결정 평가셋과 Phase 2 자동 채점 증거는 없다. | 미구현 |

`src/wellnessbox_rnd/interim/workflow_contract.py`의 `ClosedLoopState`는 11개다. `FOLLOWUP_ACTIVE + INGEST_FOLLOWUP`의 결과는 다시 `FOLLOWUP_ACTIVE`다. `ClosedLoopOperation`에는 유지, 감량, 교체, 재최적화, 에스컬레이션 작업이 없다. 따라서 “복용 후 상태를 다시 보고 다음 행동을 바꾸는 후속 제어”는 이 기준 상태기계 안에 존재하지 않는다.

`src/wellnessbox_rnd/interim/plan_lifecycle.py`에는 `MAINTAINED`, `ADJUSTED`, `MONITORING`, `REPLACED`, `STOPPED`가 있다. 하지만 `PlanLifecycleService.transition()`은 요청에 포함된 action을 검증·저장할 뿐, follow-up 점수와 이상사례를 읽어 action을 고르지 않는다. 또한 이 상태 집합은 `ClosedLoopState`와 별개여서 동일한 실행의 상태가 두 원장으로 갈라진다.

## 약사가 생성·검증하는 데이터의 역할과 의존 OP

연구계획서 18쪽은 초기 추천 모델이 전문가 추천 패턴과 전문가 라벨링 데이터를 사용한다고 정의한다. 25~26쪽의 추천 정확도는 사람의 정답 조합과 엔진 추천 조합의 일치율로 계산한다. 17쪽의 안전 규칙과 21~22쪽의 안전 검토·상담·후속 결정에도 의약학 판단이 필요하다. 따라서 약사 데이터는 다음 세 역할을 가진다.

1. 추천 정답: 개인 특성과 안전 조건에 맞는 성분·조합의 정답 집합을 제공한다. 관련 OP는 후보·추천·평가를 다루는 OP-041~050과 최종 KPI를 다루는 OP-120이다.
2. 안전 규칙과 고위험 판정: 금기, 상호작용, 용량 상한, 위험 신호의 허용·주의·차단 기준을 검증한다. 관련 OP는 OP-031~040이다. OP-039의 독립 외부 고위험 검증은 아직 비어 있다.
3. 건별 후속 결정 검토: AI가 만든 초안과 근거를 보고 승인·수정·반려하며, 승인 전 데이터가 추천·평가·학습에 들어가지 않도록 한다. 기존 검토 작업은 OP-077~078, 화면 왕복은 OP-105~106과 연결된다. Phase 3 provenance와 하류 차단은 아직 구현되지 않았다.

현재 `PharmacistReviewService`는 검토 작업 생성과 완료 기록을 지원하지만, `generation_source`, 모델 식별자, 프롬프트 버전, `pending | approved | approved_with_edits | rejected`, 수정 차이, 반려 이유를 갖춘 AI 초안 원장은 없다. 승인된 레코드만 하류에서 읽도록 강제하는 공통 경계도 확인되지 않았다. 이는 Phase 3에서 해결할 범위이며 Phase 1 중대 어긋남의 직접 원인은 아니다.

## 어긋남 목록

| 원문 | 현재 상태 | 영향 OP | 등급 | 판단 근거 |
|---|---|---|---|---|
| 21쪽: 상태를 주기적으로 수집·평가하고 유지·조정·교체·중단 결정 | `ClosedLoopState`는 `FOLLOWUP_ACTIVE`에서 자기 전이한다. `BoundedAgent`는 유지·감량·교체 action을 결정하지 않는다. | OP-071~080 | 중대 | 연구 핵심인 후속 제어 루프가 기준 상태기계 안에서 닫히지 않았다. |
| 21~22쪽: 상태에 맞는 다음 노드 자동 호출 | master context 19.3 형식의 선언적 상태×이벤트→action 데이터 파일이 없다. | OP-071~075, OP-079 | 중대 | 다음 행동이 데이터 정책으로 선언되지 않아 재현 가능한 결정 경로가 없다. |
| 21쪽: 조합·용량 자동 갱신 | 별도 `PlanLifecycleService`는 호출자가 고른 action을 기록한다. 감량을 독립 action으로 구분하지 않으며 `ClosedLoopState`와 상태가 분리돼 있다. | OP-075, OP-079~080 | 중대 | 확정 설계인 단일 명시적 상태기계와 충돌하며 실제 다음 행동 판단이 빠졌다. |
| 25~26쪽: 다음 수행 작업 판단 및 수행 정확도 80% | 전용 시나리오 100개 이상, 결정적 자동 채점기, Phase 2 정확도 증거 JSON이 없다. | OP-071~080, OP-120 | 중대 | KPI를 현재 closed-loop 정책에 대해 측정할 수 없다. |
| 23~24쪽: 새 센서·유전자 입력을 모델과 후속 판단에 재적용 | 기기 입력 재평가 작업은 있으나 유전자 입력을 동일 정책으로 처리하는 전이가 확인되지 않았다. | OP-091~100 | 경미 | Phase 2 정책 표에서 신규 입력 이벤트를 명시하면 해소할 수 있다. |
| 18쪽·25~26쪽: 전문가 정답과 안전 검증 데이터 | 외부 독립 고위험 검증 OP-039와 실제 약사 운영 데이터가 비어 있다. | OP-031~050, OP-078, OP-106, OP-120 | 경미/외부 차단 | 구현 결함과 별개인 외부 입력이다. 운영 전에는 `OPERATED`로 주장할 수 없다. |

중대 어긋남이 있으므로 기준 프로그램의 Phase 1 규칙에 따라 여기서 멈춘다. 다음 구현은 별도 `PlanLifecycleState`를 계속 확장하는 방식이 아니라, `ClosedLoopState`와 `BoundedAgent`에 follow-up 평가 이후 상태·작업을 통합하고 선언적 정책 파일이 그 전이를 선택하도록 고치는 Phase 2여야 한다.

## 감사 기준 숫자

2026-07-23 기준으로 다음 명령을 `PYTHONPATH=src`에서 실행했다.

- `python scripts/audit_original_plan_requirements.py`: PASS, 요구사항 120개, 주장 119개, 원본 해시 일치, 증거 파일 333개, 문제 0개.
- `python scripts/run_final_completion_audit.py`: BLOCKED, 유효 보고서 50/120, 보고서 누락 70개, 단계 미달 43개, 외부 검증 누락 1개(OP-039), 검증 영수증 미등록, 독립 검토 영수증 미등록.

이 메모만으로 유효 보고서 수나 차단 사유가 줄지는 않는다. 중대 어긋남을 해소하기 전에는 Phase 1을 완료로 세지 않는다.

## 남은 일

사용자 확인 후 Phase 2를 시작한다. 첫 작업은 master context 19.3 형식의 선언적 정책 파일을 만들고, 기존 `ClosedLoopState`/`BoundedAgent` 안에 유지·재최적화·감량·교체·중단·에스컬레이션 전이를 통합하는 것이다. 그 뒤 100개 이상 결정적 시나리오와 자동 채점기로 다음 수행 작업 정확도 80% 이상을 증명한다.

## Phase 2 처리 결과

사용자는 2026-07-23에 중대 어긋남 4건을 확정 설계대로 처리하는 방침을 승인했다. `ClosedLoopState`와 `BoundedAgent`에 후속 판단 전이를 통합했고, `data/original_plan/closed_loop_next_action_policy_v1.json`을 기준 정책으로 추가했다. 활성 에이전트 실행이 있으면 기존 `PlanLifecycleService`의 수동 전이를 거부해 이중 쓰기 경로도 막았다.

`data/original_plan/closed_loop_next_action_scenarios_v1.json`은 결정적 사례 130개를 담는다. 자동 채점 결과는 `data/original_plan/evidence/op071_op080_closed_loop_next_action_policy_v1.json`에 있으며 130개가 모두 정답 행동과 일치해 다음 수행 작업 정확도 100%를 기록했다. KPI 기준 80%를 넘었고, 유효 보고서 수도 50편에서 58편으로 늘었다. 따라서 감사에서 지적한 중대 어긋남 4건은 구현 기준으로 해소됐다.
