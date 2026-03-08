# remaining items

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 아직 `wellnessbox`에 남겨둔 주요 R&D 잔재

| path | current classification | why it remains now | next handling direction |
| --- | --- | --- | --- |
| `C:/dev/wellnessbox/docs/rnd/` | `MOVE_TO_RND`였으나 이번 단계 보류 | `scripts/rnd/train-all-ai.ts` 등이 직접 참조 | `scripts/rnd/`와 함께 분리 설계 후 이동 |
| `C:/dev/wellnessbox/docs/rnd_impl/` | `MOVE_TO_RND`였으나 이번 단계 보류 | `docs/rnd/*`와 강한 상호 참조 | `docs/rnd/`와 함께 이동 |
| `C:/dev/wellnessbox/lib/rnd/` | `MOVE_TO_RND` | 서비스 런타임과 직접 연결은 약하지만 코드 규모가 커서 별도 패키지 경계 설계가 필요 | `wellnessbox-rnd/legacy_code` 또는 패키지 구조로 이동 |
| `C:/dev/wellnessbox/scripts/rnd/` | `MOVE_TO_RND` | `package.json`의 `rnd:*` 명령과 직접 연결 | 명령 체계 이전과 함께 이동 |
| `C:/dev/wellnessbox/AGENTS.md` | 재평가 필요 | repo coding guard와 R&D 로딩 규칙이 섞여 있음 | 서비스용 guard만 남길지 분리 판단 필요 |
| `C:/dev/wellnessbox/AGENT_PRECHECK.md` | `MOVE_TO_RND` 후보 | 루트 agent 산출물과 함께 묶여 있음 | root agent bundle 단위로 재분류 |
| `C:/dev/wellnessbox/AGENT_SESSION_PRIMER.md` | `MOVE_TO_RND` 후보 | `scripts/agent/generate-session-primer.cts`가 재생성 | scripts/agent 처리와 함께 이동 또는 폐기 |
| `C:/dev/wellnessbox/AGENT_SKILLS_CATALOG.md` | `MOVE_TO_RND` 후보 | `scripts/agent/generate-skill-catalog.cts`가 재생성 | agent tooling과 함께 이동 |
| `C:/dev/wellnessbox/API_GUARD_MAP.md` | `MOVE_TO_RND` 후보 | generated artifact지만 서비스 repo에서 아직 생성 루틴 유지 | agent tooling 정리 후 이동 |
| `C:/dev/wellnessbox/FUNCTION_HOTSPOTS.md` | `MOVE_TO_RND` 후보 | generated artifact | agent tooling 정리 후 이동 |
| `C:/dev/wellnessbox/REFACTOR_HOTSPOTS.md` | `MOVE_TO_RND` 후보 | generated artifact | agent tooling 정리 후 이동 |
| `C:/dev/wellnessbox/REFACTOR_BACKLOG.md` | `MOVE_TO_RND` 후보 | generated artifact + 수기 backlog 혼합 | agent tooling 정리 후 이동 |
| `C:/dev/wellnessbox/scripts/agent/` | `MOVE_TO_RND` | package script 진입점과 연결 | `package.json` 재구성 후 이동 |
| `C:/dev/wellnessbox/app/agent-playground/` | `MOVE_TO_RND` | 서비스 runtime과 무관하지만 route 제거 시 동반 코드 정리가 필요 | rnd console로 이동 |
| `C:/dev/wellnessbox/app/api/agent-playground/run/route.ts` | `MOVE_TO_RND` | playground API | playground 앱과 같이 이동 |
| `C:/dev/wellnessbox/lib/agent-playground/` | `MOVE_TO_RND` | playground core | playground 앱과 같이 이동 |
| `C:/dev/wellnessbox/app/api/rag/` | `MOVE_TO_RND` | debug/ingest/reindex API | rnd API로 이동 |
| `C:/dev/wellnessbox/lib/server/rag-debug-route.ts` | `MOVE_TO_RND` | RAG 운영/디버그 core | RAG API와 같이 이동 |
| `C:/dev/wellnessbox/lib/server/rag-ingest-route.ts` | `MOVE_TO_RND` | RAG ingest core | RAG API와 같이 이동 |
| `C:/dev/wellnessbox/lib/server/rag-reindex-route.ts` | `MOVE_TO_RND` | RAG reindex core | RAG API와 같이 이동 |
| `C:/dev/wellnessbox/lib/ai/` | `REPLACE_WITH_THIN_INTERFACE` | 서비스 chat가 직접 import 중 | API contract 정의 후 thin interface로 대체 |
| `C:/dev/wellnessbox/lib/chat/prompts.ts` | `REPLACE_WITH_THIN_INTERFACE` | prompt SSOT이지만 chat route가 직접 사용 | prompt registry 외부화 |
| `C:/dev/wellnessbox/lib/chat/response-guard.ts` | `REPLACE_WITH_THIN_INTERFACE` | chat 응답 guard | ai-guard 패키지 분리 필요 |
| `C:/dev/wellnessbox/lib/chat/actions/model.ts` | `REPLACE_WITH_THIN_INTERFACE` | model 기반 planner | rnd API 경계 필요 |
| `C:/dev/wellnessbox/lib/wellness/` | `REPLACE_WITH_THIN_INTERFACE` | `/survey`, admin report, scoring이 직접 사용 | wellness engine 외부화 후 thin adapter만 유지 |
| `C:/dev/wellnessbox/data/b2b/survey.common.json` | `REPLACE_WITH_THIN_INTERFACE` | 현재 서비스 UI/계산 코드가 직접 읽음 | engine contract 정의 후 이관 |
| `C:/dev/wellnessbox/data/b2b/survey.sections.json` | `REPLACE_WITH_THIN_INTERFACE` | 현재 서비스 UI/계산 코드가 직접 읽음 | engine contract 정의 후 이관 |
| `C:/dev/wellnessbox/data/b2b/scoring.rules.json` | `REPLACE_WITH_THIN_INTERFACE` | 현재 서비스 계산이 직접 읽음 | engine contract 정의 후 이관 |
| `C:/dev/wellnessbox/data/b2b/report.texts.json` | `REPLACE_WITH_THIN_INTERFACE` | 결과 문구를 UI가 직접 사용 | snapshot 또는 API contract 설계 필요 |
| `C:/dev/wellnessbox/lib/b2b/public-survey.ts` | `REPLACE_WITH_THIN_INTERFACE` | 설문 구조/채점 adapter 중심 | engine thin interface로 축소 필요 |
| `C:/dev/wellnessbox/lib/b2b/ai-evaluation.ts` | `REPLACE_WITH_THIN_INTERFACE` | B2B narrative 생성 | ai report API 분리 필요 |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary.ts` | `REPLACE_WITH_THIN_INTERFACE` | NHIS fetch 흐름에 AI summary가 끼어 있음 | hyphen fetch와 AI enrichment 경계 분리 |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary-core.ts` | `REPLACE_WITH_THIN_INTERFACE` | AI summary orchestration | 패키지화 필요 |
| `C:/dev/wellnessbox/lib/server/hyphen/fetch-ai-summary-openai.ts` | `REPLACE_WITH_THIN_INTERFACE` | 직접 LLM 호출 | rnd API로 이관 |
| `C:/dev/wellnessbox/docs/maintenance/` | `NEEDS_REVIEW` | service engineering 문서와 agent refactor 메모가 섞여 있음 | service-only / rnd-only 재분류 필요 |
| `C:/dev/wellnessbox/scripts/lib/` | `NEEDS_REVIEW` | prebuild audit와 agent tooling이 공유 | helper dependency map 작성 후 분리 |
| `C:/dev/wellnessbox/data/b2b/backups/` | `NEEDS_REVIEW` | backup/PII 가능성 확인 전 이동 불가 | quarantine 판단 필요 |
| `C:/dev/wellnessbox/docs/scenarios/chat-client-scenarios.md` | `NEEDS_REVIEW` | 서비스 QA 문서 성격이 강함 | service repo 유지 여부 판단 |
| `C:/dev/wellnessbox/docs/scenarios/client-appuser-linking.md` | `NEEDS_REVIEW` | 인증/세션 정책 문서에 가까움 | service engineering docs로 재배치 여부 검토 |
| `C:/dev/wellnessbox/PORTING_EDITOR_IMAGE_UPLOAD.md` | `NEEDS_REVIEW` | legacy note인지 운영 문서인지 불명확 | 실제 참조 여부 확인 필요 |

## 당장 움직이지 않은 이유 요약

1. `scripts/rnd/*`, `scripts/agent/*`, `package.json` 명령 체계가 아직 `wellnessbox`에 남아 있다.
2. `lib/wellness/`, `data/b2b/*.json`, `lib/ai/`, `lib/chat/*`는 서비스 코드가 직접 import한다.
3. 일부 문서는 service engineering 문서와 R&D 문서가 섞여 있어 단순 이동보다 재분류가 먼저다.

## 다음 단계 우선순위

1. `docs/rnd/`, `docs/rnd_impl/`, `scripts/rnd/`, `lib/rnd/`를 하나의 묶음으로 옮길 수 있는지 검증
2. root agent bundle(`AGENT_*`, `API_GUARD_MAP.md`, `FUNCTION_HOTSPOTS.md`, `REFACTOR_*`, `scripts/agent/`)의 재생성 경로 정리
3. `lib/wellness/`와 `data/b2b/*.json`의 thin interface 계약서 작성
4. `lib/ai/`, `lib/chat/*`, `lib/server/hyphen/fetch-ai-summary*` 외부화 계약서 작성
5. `docs/maintenance/`, `scripts/lib/`, `data/b2b/backups/`의 보존/이관/격리 여부 판정
