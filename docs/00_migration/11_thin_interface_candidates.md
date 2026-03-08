# thin interface candidates

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 원칙

- 아래 항목은 현재 `wellnessbox`에 남아 있지만, 장기적으로는 `wellnessbox-rnd`의 API 또는 generated contract를 호출하는 얇은 인터페이스로 바뀌어야 한다.
- 원본 로직과 원본 데이터는 장기적으로 `wellnessbox-rnd`에만 남긴다.

## 우선 후보

| source path | current role in wellnessbox | future boundary | thin interface left in wellnessbox | risk |
| --- | --- | --- | --- | --- |
| `C:/dev/wellnessbox/lib/ai/` | chat/RAG/model wrapper core | `wellnessbox-rnd` AI runtime API | request/response client + auth wrapper | high |
| `C:/dev/wellnessbox/app/api/chat/route-service.ts` | chat streaming orchestration | external chat runtime endpoint | route adapter only | high |
| `C:/dev/wellnessbox/app/api/chat/suggest/` | LLM 기반 제안 생성 | suggestion API | route adapter only | medium |
| `C:/dev/wellnessbox/app/api/chat/title/` | LLM 기반 title 생성 | title API | route adapter only | medium |
| `C:/dev/wellnessbox/app/api/chat/actions/route-service.ts` | action planner orchestration | action-planning API | route adapter only | medium |
| `C:/dev/wellnessbox/lib/chat/prompts.ts` | prompt SSOT | prompt registry in `wellnessbox-rnd` | generated prompt snapshot or API-selected template id | medium |
| `C:/dev/wellnessbox/lib/chat/response-guard.ts` | AI response validation | AI guard package/API | validation adapter only | medium |
| `C:/dev/wellnessbox/lib/chat/actions/model.ts` | model 기반 UI action planner | action model service | adapter only | medium |
| `C:/dev/wellnessbox/lib/wellness/` | survey scoring/report engine | wellness engine API/package owned by `wellnessbox-rnd` | client adapter + DTO mapper | very high |
| `C:/dev/wellnessbox/data/b2b/survey.common.json` | survey source data | generated contract/schema or frozen snapshot | generated artifact only | very high |
| `C:/dev/wellnessbox/data/b2b/survey.sections.json` | survey source data | generated contract/schema or frozen snapshot | generated artifact only | very high |
| `C:/dev/wellnessbox/data/b2b/scoring.rules.json` | scoring source data | generated rules artifact | generated artifact only | very high |
| `C:/dev/wellnessbox/data/b2b/report.texts.json` | report copy source data | generated texts snapshot | generated artifact only | high |
| `C:/dev/wellnessbox/lib/b2b/public-survey.ts` | survey render/selection adapter | wellness engine contract client | adapter only | high |
| `C:/dev/wellnessbox/lib/b2b/ai-evaluation.ts` | B2B narrative AI generation | report narrative API | adapter only | medium |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary.ts` | NHIS fetch 후 AI summary enrichment | NHIS summary API | enrichment client only | high |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary-core.ts` | AI summary orchestration | summary runtime service | adapter only | high |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary-openai.ts` | direct OpenAI call | R&D-owned provider layer | none | high |

## 계약 우선순위

### 1. wellness engine 계약

필요 경계:

- survey template contract
- scoring input/output contract
- report text contract
- versioned snapshot artifact format

우선 관련 경로:

- `C:/dev/wellnessbox/lib/wellness/`
- `C:/dev/wellnessbox/lib/b2b/public-survey.ts`
- `C:/dev/wellnessbox/data/b2b/*.json`
- `C:/dev/wellnessbox/components/b2b/report-summary/card-insights.ts`

### 2. chat / AI runtime 계약

필요 경계:

- chat completion request/response schema
- suggest/title/actions schema
- prompt id/version contract
- response guard result contract

우선 관련 경로:

- `C:/dev/wellnessbox/lib/ai/`
- `C:/dev/wellnessbox/app/api/chat/`
- `C:/dev/wellnessbox/lib/chat/`

### 3. NHIS AI enrichment 계약

필요 경계:

- NHIS normalized payload schema
- AI summary request/response schema
- fallback/timeout policy

우선 관련 경로:

- `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary.ts`
- `C:/dev/wellnessbox/lib/server/hyphen/fetch-route-persist.ts`

## 지금은 thin interface로 분류만 하고 실제 이동하지 않은 이유

1. 현재 서비스 코드가 직접 import하고 있다.
2. DTO, error contract, timeout policy, auth policy가 아직 정해지지 않았다.
3. 계약 없이 이동하면 `/survey`, `/chat`, `/employee-report`, `/health-link`, admin flows가 바로 깨질 수 있다.
