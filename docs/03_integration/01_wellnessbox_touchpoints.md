# wellnessbox 연동 접점 맵

## 범위

`wellnessbox` 내부에서 `wellnessbox-rnd` 와 실제로 연결될 가능성이 높은 페이지, component, hook, API route, server util 을 정리한다.

## 핵심 접점 표

| 경로 | 현재 역할 | 타입 | 권장 연동 방식 | 우선순위 | 메모 |
| --- | --- | --- | --- | --- | --- |
| `C:/dev/wellnessbox/app/survey/page.tsx` | 설문 진입 페이지 | page | 유지 | 높음 | 실제 연동 로직은 client/server 하위 파일에서 처리 |
| `C:/dev/wellnessbox/app/survey/survey-page-client.tsx` | 설문 입력 수집, 현재 wellness 계산 호출 | client component | 서버 API 호출로 전환 | 매우 높음 | 1차 연동 핵심 |
| `C:/dev/wellnessbox/app/survey/_lib/survey-page-auto-compute.ts` | 설문 자동 계산 보조 | client util | shadow/fallback 제어 후보 | 높음 | 현재 자동 계산 UX 유지에 중요 |
| `C:/dev/wellnessbox/app/survey/_lib/use-survey-remote-sync.ts` | 설문 원격 저장/동기화 | client hook | 필요 시 request payload 재사용 | 중간 | 추천 호출과 저장 호출 분리 권장 |
| `C:/dev/wellnessbox/lib/b2b/public-survey.ts` | 설문 질문 구성, 검증, 입력 정규화 | shared util | 입력 adapter 의 핵심 입력원 | 매우 높음 | runtime 유지, 계산 원본은 점진 축소 |
| `C:/dev/wellnessbox/lib/wellness/analysis.ts` | 현재 추천/분석 계산 | shared runtime | fallback engine 로 유지 | 매우 높음 | 1차에는 제거하지 않음 |
| `C:/dev/wellnessbox/lib/wellness/data-loader.ts` | wellness 템플릿 로드 | shared util | fallback 유지 | 높음 | 추천 실패 시 계속 필요 |
| `C:/dev/wellnessbox/data/b2b/survey.common.json` | 공통 설문 정의 | runtime data | 계속 사용 | 높음 | 입력 수집 SSOT 는 당분간 wellnessbox 유지 |
| `C:/dev/wellnessbox/data/b2b/survey.sections.json` | 섹션 설문 정의 | runtime data | 계속 사용 | 높음 | 질문 구조 변경 시 contract 영향 큼 |
| `C:/dev/wellnessbox/data/b2b/scoring.rules.json` | 기존 점수 규칙 | runtime data | fallback 전용 유지 | 중간 | 장기적으로 R&D API 와 직접 공유하지 않음 |
| `C:/dev/wellnessbox/data/b2b/report.texts.json` | 리포트 문구 | runtime data | UI fallback 문구 유지 | 중간 | AI 응답 문구와 병행 가능 |
| `C:/dev/wellnessbox/app/api/chat/route.ts` | 채팅 API route entry | route | 후속 thin interface | 중간 | 1차 구현 대상 아님 |
| `C:/dev/wellnessbox/app/api/chat/route-service.ts` | 현재 채팅 스트림 orchestration | server route service | `wellnessbox-rnd` planner/chat proxy 후보 | 높음 | 서버 호출 제어점 |
| `C:/dev/wellnessbox/app/api/chat/actions/route-service.ts` | action suggest/execute 판단 | server route service | 후속 분리 후보 | 중간 | structured planner 로 이전 가능 |
| `C:/dev/wellnessbox/app/api/chat/title/route-service.ts` | 제목 생성 | server route service | 후순위 | 낮음 | KPI 핵심 아님 |
| `C:/dev/wellnessbox/app/api/chat/suggest/suggest-route-service.ts` | 추천 질문 생성 | server route service | 후순위 | 낮음 | thin interface 대상 |
| `C:/dev/wellnessbox/app/chat/hooks/useChat.api.ts` | 채팅 브라우저 fetch 집합 | client hook | endpoint 유지, 내부 구현만 교체 | 높음 | 클라이언트 변경 최소화 지점 |
| `C:/dev/wellnessbox/lib/ai/chain.ts` | 현재 LLM 체인 핵심 | server lib | 장기적으로 제거 또는 proxy wrapper | 높음 | R&D 원본 제거 대상 |
| `C:/dev/wellnessbox/lib/chat/prompts.ts` | 프롬프트 정의 | server lib | 장기적으로 R&D 소유 | 중간 | web 에는 thin prompt hints 만 남김 |
| `C:/dev/wellnessbox/lib/chat/response-guard.ts` | 채팅 응답 가드 | shared lib | 일부는 web 유지 가능 | 중간 | UI safe rendering guard 는 web 소유 |
| `C:/dev/wellnessbox/app/(features)/health-link/HealthLinkClient.tsx` | 건강연동 UI | client component | 현재 유지 | 중간 | AI summary 실패시 core UX 유지 필요 |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary.ts` | NHIS 요약 진입점 | server util | `wellnessbox-rnd` summary API 호출로 교체 후보 | 높음 | 가장 자연스러운 서버 접점 |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary-core.ts` | NHIS 요약 본체 | server util | 후속 thin interface | 높음 | R&D 이전 후보 |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary-openai.ts` | OpenAI 기반 요약 | server util | 후속 thin interface | 높음 | 직접 모델 호출 제거 후보 |
| `C:/dev/wellnessbox/app/(features)/employee-report/EmployeeReportClient.tsx` | 리포트 UI/동기화 | client component | 직접 연동 없음, 요약 결과만 소비 | 중간 | summary snapshot 표시 위치 |
| `C:/dev/wellnessbox/app/(features)/employee-report/_lib/api.ts` | 직원 리포트 fetch API | client util | AI 필드 추가 시 계약 반영 | 중간 | timeout budget 참고 대상 |
| `C:/dev/wellnessbox/components/b2b/report-summary/card-insights.ts` | B2B 인사이트 카드 텍스트 조합 | UI helper | AI 결과 소비 지점 후보 | 중간 | 직접 AI 호출 금지 |
| `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts` | `wellnessbox-rnd` recommend preview 서버 client/helper | server util | 서버 측 thin caller | 매우 높음 | 이번 단계 실제 구현 |
| `C:/dev/wellnessbox/lib/server/wb-rnd-recommend-preview-route.ts` | preview route orchestration | server route service | 내부 preview route 제어 | 매우 높음 | 이번 단계 실제 구현 |
| `C:/dev/wellnessbox/app/api/internal/rnd/recommend-preview/route.ts` | dev-only recommend proxy route | API route | web server -> rnd api | 매우 높음 | 이번 단계 실제 구현 |
| `C:/dev/wellnessbox/app/(dev)/rnd-preview/page.tsx` | dev preview entry page | page | raw JSON 확인용 UI | 높음 | 이번 단계 실제 구현 |
| `C:/dev/wellnessbox/app/(dev)/rnd-preview/rnd-preview-client.tsx` | preview payload 편집/실행/응답 표시 | client component | 내부 smoke/demo UI | 높음 | 이번 단계 실제 구현 |
| `C:/dev/wellnessbox/scripts/qa/check-rnd-recommend-preview.cts` | flag/fallback smoke check | QA script | helper 검증 | 높음 | 이번 단계 실제 구현 |

## 1차 연동 대상 상세

### A. 설문 추천

- 입력 수집: `app/survey/survey-page-client.tsx`
- 입력 정규화: `lib/b2b/public-survey.ts`
- 기존 계산 fallback: `lib/wellness/analysis.ts`
- 목표: 서버 경유 recommend API 호출

### A-0. dev preview

- route: `app/api/internal/rnd/recommend-preview/route.ts`
- helper: `lib/server/wb-rnd-client.ts`
- UI: `app/(dev)/rnd-preview/page.tsx`
- 목표: 실제 사용자 플로우를 건드리지 않고 `wellnessbox-rnd /v1/recommend` 연결, timeout, fallback, raw JSON 확인

### B. 건강 연동 AI 요약

- 결과 표시: `app/(features)/health-link/HealthLinkClient.tsx`
- 서버 호출 진입점: `lib/server/hyphen/fetch-ai-summary.ts`
- 목표: NHIS fetch 후 선택적 enrichment 로 분리

### C. 채팅

- 클라이언트 fetch 통로: `app/chat/hooks/useChat.api.ts`
- 서버 진입점: `app/api/chat/route-service.ts`
- 목표: 장기적으로 planner/recommend helper 를 `wellnessbox-rnd` 로 이관

## 연동 제외 원칙

- client component 가 직접 `wellnessbox-rnd` URL 을 알지 않게 한다.
- admin/report UI 가 `wellnessbox-rnd` 를 직접 호출하지 않게 한다.
- 기존 runtime JSON 과 fallback 계산 경로는 1차 rollout 동안 유지한다.
