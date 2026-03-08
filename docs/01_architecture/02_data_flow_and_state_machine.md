# 데이터 흐름과 상태기계

기준 문서:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## 상위 데이터 흐름

```mermaid
flowchart LR
    A[입력 데이터] --> B[Intake Normalize]
    B --> C[Safety Validation]
    C --> D[Candidate Filtering]
    D --> E[Goal / Efficacy Scoring]
    E --> F[Optimization / Ranking]
    F --> G[Decision Summary]
    G --> H[Follow-up Questions]
    G --> I[Policy Next Action]
    G --> J[Frozen Eval Logging]
```

## 입력 범주

- 자기기입 문진
- 증상
- 복용 약물
- 현재 복용 중인 건강기능식품
- 생활습관
- 센서 / 바이오마커 가용성 여부

## 상태기계

```mermaid
stateDiagram-v2
    [*] --> IntakeReady
    IntakeReady --> NeedsMoreInput: 필수 정보 부족
    IntakeReady --> SafetyBlocked: 금기/차단 규칙 충족
    IntakeReady --> CandidateReady: 안전 필터 통과
    CandidateReady --> NeedsReview: 점수 또는 정보 신뢰도 낮음
    CandidateReady --> PlanReady: 추천 조합 결정
    PlanReady --> FollowupScheduled: 추적 질문 / 관찰 포인트 생성
    NeedsMoreInput --> IntakeReady: 추가 정보 확보
    NeedsReview --> IntakeReady: 정보 정제
    FollowupScheduled --> [*]
    SafetyBlocked --> [*]
```

## 상태별 출력

| 상태 | 핵심 출력 |
| --- | --- |
| `NeedsMoreInput` | missing information, follow-up questions |
| `SafetyBlocked` | blocked reasons, excluded ingredients, rule refs |
| `NeedsReview` | low-confidence summary, 추가 확인 질문 |
| `PlanReady` | recommendations, rationale, follow-up window |

## 현재 코드 대응

- intake: `domain/intake.py`
- safety: `safety/service.py`
- scoring: `efficacy/service.py`
- ranking: `optimizer/service.py`
- orchestration: `orchestration/recommendation_service.py`

## 범위 밖

- 특정 제품 설문 흐름
- 특정 운영 DB 상태
- 특정 route lifecycle
