# 파일 단위 변경 계획

## 원칙

- 이번 문서는 실제 코드 수정이 아니라, 다음 구현 단계에서 어떤 파일을 어떻게 건드릴지 고정하는 계획서다.
- `wellnessbox` 는 웹서비스 전용 repo 로 유지한다.
- AI 원본 로직은 `wellnessbox-rnd` 에만 둔다.

## 1차 구현 대상

| 파일 | 현재 역할 | 예정 변경 | 연동 방향 | 위험도 | rollout phase |
| --- | --- | --- | --- | --- | --- |
| `C:/dev/wellnessbox/app/survey/survey-page-client.tsx` | 설문 답변 수집과 결과 생성 | 클라이언트가 직접 계산하지 않고 `wellnessbox` 서버 endpoint 호출 | web -> web server | 중간 | 1 |
| `C:/dev/wellnessbox/lib/b2b/public-survey.ts` | 질문/답변 정규화 | RND request adapter 가 재사용할 매핑 함수 선별 | shared util 유지 | 중간 | 1 |
| `C:/dev/wellnessbox/lib/wellness/analysis.ts` | 기존 추천 엔진 | fallback engine 로 한정 | legacy fallback | 높음 | 1 |
| `C:/dev/wellnessbox/app/survey/_lib/survey-page-auto-compute.ts` | 자동 계산 트리거 | feature flag 와 debounce/shadow 호출 연결 | client -> web server | 중간 | 1 |
| `C:/dev/wellnessbox/app/survey/_lib/use-survey-remote-sync.ts` | 원격 동기화 | 추천 요청과 분리 여부 조정 | none or helper reuse | 낮음 | 1 |
| `C:/dev/wellnessbox/app/api/...` 신규 route 또는 server action | 아직 없음 또는 추후 추가 | `wellnessbox-rnd /v1/recommend` 프록시 추가 | web server -> rnd api | 중간 | 1 |

## 이번 단계 실제 구현

| 파일 | 현재 상태 | 구현 내용 | 비고 |
| --- | --- | --- | --- |
| `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts` | 신규 | `wellnessbox-rnd /v1/recommend` 호출 helper, env 해석, timeout, fallback 구현 | 실제 thin caller |
| `C:/dev/wellnessbox/lib/server/wb-rnd-recommend-preview-route.ts` | 신규 | preview route orchestration 추가 | server-only 진입점 |
| `C:/dev/wellnessbox/app/api/internal/rnd/recommend-preview/route.ts` | 신규 | dev-only preview proxy route 추가 | 기존 사용자 플로우와 분리 |
| `C:/dev/wellnessbox/app/(dev)/rnd-preview/page.tsx` | 신규 | preview page 진입점 추가 | flag off 시 404 |
| `C:/dev/wellnessbox/app/(dev)/rnd-preview/rnd-preview-client.tsx` | 신규 | payload 편집, 실행, raw JSON 결과 표시 | smoke/demo UI |
| `C:/dev/wellnessbox/scripts/qa/check-rnd-recommend-preview.cts` | 신규 | preview flag/fallback smoke check 추가 | 네트워크 없이 실행 가능 |
| `C:/dev/wellnessbox/package.json` | 수정 | `qa:rnd:preview-route` script 추가 | 최소 검증 진입점 |

## 이번 단계에서 일부러 하지 않은 것

- `/survey` 실제 런타임 경로 교체
- 기존 `lib/wellness/analysis.ts` fallback 연동
- `/chat` 또는 NHIS summary 연동
- rollout sampling, shadow persistence, server metrics 저장

## 2차 구현 대상

| 파일 | 현재 역할 | 예정 변경 | 연동 방향 | 위험도 | rollout phase |
| --- | --- | --- | --- | --- | --- |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary.ts` | NHIS AI summary 진입점 | `wellnessbox-rnd` summary endpoint 호출 wrapper 로 변경 | web server -> rnd api | 중간 | 5 |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary-core.ts` | summary 핵심 로직 | thin interface 또는 제거 | web server -> rnd api | 높음 | 5 |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary-openai.ts` | 직접 모델 호출 | 제거 또는 RND 서비스 호출 wrapper | web server -> rnd api | 높음 | 5 |
| `C:/dev/wellnessbox/app/(features)/health-link/HealthLinkClient.tsx` | 건강연동 UI | summary 준비/실패 UX 조정 | UI consumes snapshot | 낮음 | 5 |
| `C:/dev/wellnessbox/app/(features)/employee-report/_lib/api.ts` | 직원 리포트 API helper | AI summary 필드 소비 추가 | web client -> web api | 낮음 | 5 |

## 3차 구현 대상

| 파일 | 현재 역할 | 예정 변경 | 연동 방향 | 위험도 | rollout phase |
| --- | --- | --- | --- | --- | --- |
| `C:/dev/wellnessbox/app/api/chat/route-service.ts` | 채팅 스트리밍 orchestration | planner/helper 를 RND 로 위임 | web server -> rnd api | 높음 | 6 |
| `C:/dev/wellnessbox/app/chat/hooks/useChat.api.ts` | 브라우저 fetch helper | endpoint 는 유지, payload 확장 | client -> web api | 중간 | 6 |
| `C:/dev/wellnessbox/lib/ai/chain.ts` | 현재 AI 본체 | thin interface 또는 제거 | web server -> rnd api | 높음 | 6 |
| `C:/dev/wellnessbox/lib/chat/prompts.ts` | 프롬프트 원본 | RND 로 이전 후 web 에는 최소 UI context 만 유지 | rnd owns prompt | 높음 | 6 |
| `C:/dev/wellnessbox/lib/chat/response-guard.ts` | 응답 렌더링 가드 | UI 안전 가드만 유지 | shared/UI safe guard | 낮음 | 6 |

## wellnessbox-rnd 쪽 예정 추가

| 파일 또는 경로 | 현재 상태 | 예정 변경 |
| --- | --- | --- |
| `C:/dev/wellnessbox-rnd/apps/inference_api/routes/recommend.py` | recommend baseline 존재 | 안정 버전 유지, contract 기준점 |
| `C:/dev/wellnessbox-rnd/apps/inference_api/routes/` | health/recommend 만 존재 | health summary, chat helper 는 후속 추가 |
| `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py` | Pydantic 스키마 존재 | contract SSOT 유지 |
| `C:/dev/wellnessbox-rnd/docs/03_integration/openapi.inference_api.json` | 이번 단계 생성 | web 계약 검토 기준 |

## 구현 순서 제안

1. `wellnessbox` 서버 프록시용 env/flag 설계 추가
2. `/survey` 서버 프록시 endpoint 추가
3. survey payload -> RND contract adapter 구현
4. fallback to `lib/wellness/analysis.ts`
5. shadow logging 추가
6. health-link summary 분리
7. chat thin interface 설계/구현

## 변경 금지 원칙

- 브라우저에서 직접 `wellnessbox-rnd` URL 호출 금지
- 1차 단계에서 `data/b2b/*.json` 구조 파괴 금지
- fallback engine 제거 금지
