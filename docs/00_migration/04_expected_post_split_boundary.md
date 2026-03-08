# expected post-split boundary

기준 문서: `wellnessbox-rnd/docs/context/master_context.md`

목표:
- `wellnessbox`는 서비스 런타임 전용 repo
- `wellnessbox-rnd`는 연구개발 SSOT repo

## 1. split 이후 각 repo의 역할

### `wellnessbox`에 남는 것

- 사용자 화면
  - `app/check-ai/`
  - `app/assess/`
  - `app/survey/`
  - `app/(features)/employee-report/`
  - `app/(features)/health-link/`
  - `app/(admin)/admin/b2b-reports/`
  - `app/(admin)/admin/b2b-employee-data/`
- 인증, 주문, 결제, 세션, 관리자 권한
- 운영 DB persistence
- 운영 export, sync, report assembly
- R&D API를 호출하는 thin client, adapter, proxy route
- 서비스 QA와 운영 런북

### `wellnessbox-rnd`가 가져야 하는 것

- TIPS / R&D 기준 문서와 구현 노트
- prompt, eval, dataset, KPI harness
- `lib/rnd` 계열 연구 코드
- agent/Codex 운영 문서와 생성 스크립트
- agent playground, RAG ingest/debug/reindex
- LLM prompt/guard/model orchestration
- B2B AI evaluation 본체
- NHIS AI summary 본체
- 웰니스 계산 엔진과 설문 규칙/텍스트 SSOT
- 지식 원문 문서와 frozen evaluation 자산

## 2. 금지할 경계

split 이후 아래 의존은 금지하는 것이 맞다.

1. `wellnessbox`가 `wellnessbox-rnd` 내부 파일을 상대 경로로 직접 읽는 것
2. `wellnessbox`가 R&D용 JSON/markdown 원본을 직접 import하는 것
3. `wellnessbox`가 OpenAI/LangChain/RAG 구현체를 직접 소유하는 것
4. `wellnessbox-rnd`가 서비스 DB 스키마와 운영 세션 로직을 직접 소유하는 것

## 3. 허용할 경계

split 이후 허용 가능한 연결 방식은 아래 셋 중 하나로 제한하는 것이 적절하다.

1. HTTP API
   - 예: `wellnessbox` -> `wellnessbox-rnd` chat, suggestion, evaluation, summary API 호출
2. versioned package
   - 예: `@wellnessbox-rnd/contracts`, `@wellnessbox-rnd/client`
3. frozen artifact import
   - 예: 빌드 시점에 고정된 schema snapshot만 서비스로 배포

## 4. 권장 책임 재배치

| 영역 | 최종 소유 repo | 서비스 쪽 잔존 형태 |
| --- | --- | --- |
| TIPS R&D 문서 | `wellnessbox-rnd` | 없음 |
| agent/Codex 문서와 tooling | `wellnessbox-rnd` | 없음 |
| agent playground | `wellnessbox-rnd` | 없음 |
| RAG ingest/debug/reindex | `wellnessbox-rnd` | 필요 시 관리자용 외부 링크만 |
| chat LLM orchestration | `wellnessbox-rnd` | `wellnessbox/lib/rnd-client/chat.ts` 같은 thin client |
| chat prompt / guard | `wellnessbox-rnd` | 없음 |
| B2B AI evaluation | `wellnessbox-rnd` | `analysis-service.ts`에서 remote call |
| NHIS AI summary | `wellnessbox-rnd` | `fetch-route-persist.ts`에서 remote enrich call |
| wellness scoring engine | `wellnessbox-rnd` | survey UI는 입력/표시만 유지, 계산은 remote call 또는 versioned package |
| survey rule/text datasets | `wellnessbox-rnd` | 서비스에는 projection 또는 snapshot만 |

## 5. 권장 폴더 구조 초안

```text
wellnessbox-rnd/
  docs/
    context/
    00_discovery/
    00_migration/
    imported/
      wellnessbox/
        legacy-rnd-docs/
        legacy-rnd-impl/
        agent-ops/
        wellness-engine/
    review/
      wellnessbox/
  packages/
    rnd-core/
    ai-runtime/
    prompt-registry/
    ai-guards/
    agent-playground/
    b2b-ai/
    nhis-ai-summary/
    wellness-engine/
  apps/
    rnd-api/
    rnd-console/
  tools/
    rnd/
    agent-ops/
    rag/
    nhis-ai-summary/
  data/
    knowledge/
      supplements/
    wellness-engine/
  quarantine/
    b2b-backups/
```

## 6. 권장 이주 파도

### Wave 1. 바로 이동 가능한 순수 R&D 자산

- `docs/rnd/`
- `docs/rnd_impl/`
- `lib/rnd/`
- `scripts/rnd/`
- `app/agent-playground/`
- `app/api/agent-playground/`
- `lib/agent-playground/`
- `app/api/rag/`
- `lib/server/rag-*`
- agent/Codex 문서
- `scripts/agent/`
- supplement knowledge docs

### Wave 2. thin interface가 먼저 필요한 자산

- `lib/ai/`
- `lib/chat/prompts.ts`
- `lib/chat/response-guard.ts`
- `lib/chat/actions/model.ts`
- `lib/b2b/ai-evaluation.ts`
- `lib/server/hyphen/fetch-ai-summary*`
- `lib/wellness/`
- `data/b2b/*.json`
- `lib/b2b/public-survey.ts`

### Wave 3. 회색지대 정리

- `docs/maintenance/`
- `scripts/lib/`
- `data/b2b/backups/`
- `PORTING_EDITOR_IMAGE_UPLOAD.md`
- 일부 scenarios/docs index

## 7. split 이후 wellnessbox에서 새로 생겨야 하는 얇은 계층

권장 경로:

```text
wellnessbox/lib/rnd-client/
  chat.ts
  chat-actions.ts
  chat-suggest.ts
  b2b-ai-evaluation.ts
  nhis-ai-summary.ts
  wellness-engine.ts
```

각 thin client의 책임:

- 요청 contract 직렬화
- 인증/timeout/retry
- fallback 정책
- 응답 schema 검증

각 thin client가 하면 안 되는 것:

- prompt 구성
- 모델 선택
- RAG indexing
- scoring formula 보유
- 원문 dataset import

## 8. split 완료 판단 기준

1. `wellnessbox`에서 `docs/rnd`, `lib/rnd`, `scripts/rnd`, agent playground, RAG debug tooling이 사라진다.
2. `wellnessbox`에서 AI 본체 import가 thin client 호출로 바뀐다.
3. `wellnessbox-rnd`가 prompt/eval/dataset/engine의 유일한 원본이 된다.
4. 서비스 화면과 운영 API는 그대로 동작한다.
