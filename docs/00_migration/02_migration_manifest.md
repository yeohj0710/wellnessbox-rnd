# migration manifest

기준 문서: `wellnessbox-rnd/docs/context/master_context.md`

설명:
- 이번 문서는 실제 이동 지시서가 아니라, 다음 단계에서 그대로 실행 가능한 수준의 분류/도착지 초안이다.
- 경로는 `C:\dev\` 기준 상대 경로다.
- `target destination path`는 최종 제안안이며, 후속 단계에서 구조를 확정하면서 미세 조정 가능하다.

| source path | current purpose | classification | target destination path | why | runtime impact risk | move now or later |
| --- | --- | --- | --- | --- | --- | --- |
| `wellnessbox/docs/rnd/` | TIPS 연구개발 요구사항, KPI, 모듈 설명 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-docs/` | R&D 명세의 직접 원본 | 낮음 | 지금 |
| `wellnessbox/docs/rnd_impl/` | 모듈별 구현 메모 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/legacy-rnd-impl/` | R&D 구현 노트 SSOT를 R&D repo로 통합해야 함 | 낮음 | 지금 |
| `wellnessbox/lib/rnd/` | R&D 모듈 02~07 및 학습 파이프라인 | `MOVE_TO_RND` | `wellnessbox-rnd/packages/rnd-core/` | 현재 서비스 런타임에서 직접 참조되지 않는 순수 R&D 코드 | 낮음 | 지금 |
| `wellnessbox/scripts/rnd/` | R&D scaffold/MVP/evaluation 실행 스크립트 | `MOVE_TO_RND` | `wellnessbox-rnd/tools/rnd/` | 연구 실행 도구이며 서비스 운영 필수 아님 | 낮음 | 지금 |
| `wellnessbox/app/agent-playground/` | agent vs llm 비교 UI | `MOVE_TO_RND` | `wellnessbox-rnd/apps/rnd-console/app/agent-playground/` | 실험/평가용 콘솔 | 낮음 | 지금 |
| `wellnessbox/app/api/agent-playground/run/route.ts` | playground 실행 API | `MOVE_TO_RND` | `wellnessbox-rnd/apps/rnd-console/app/api/agent-playground/run/route.ts` | 실험 API이고 사용자 서비스 필수 아님 | 낮음 | 지금 |
| `wellnessbox/lib/agent-playground/` | playground engine/tools/trace | `MOVE_TO_RND` | `wellnessbox-rnd/packages/agent-playground/` | 연구/실험 본체 | 낮음 | 지금 |
| `wellnessbox/lib/server/agent-playground-route.ts` | playground route adapter | `MOVE_TO_RND` | `wellnessbox-rnd/apps/rnd-console/lib/agent-playground-route.ts` | 실험용 API adapter | 낮음 | 지금 |
| `wellnessbox/app/api/rag/` | RAG debug/ingest/reindex API | `MOVE_TO_RND` | `wellnessbox-rnd/apps/rnd-console/app/api/rag/` | 서비스 운영 API가 아니라 실험/운영자용 인덱싱 도구 | 낮음 | 지금 |
| `wellnessbox/lib/server/rag-debug-route.ts` | RAG debug route core | `MOVE_TO_RND` | `wellnessbox-rnd/apps/rnd-api/lib/rag/debug-route.ts` | RAG 실험용 내부 API | 낮음 | 지금 |
| `wellnessbox/lib/server/rag-ingest-route.ts` | RAG ingest route core | `MOVE_TO_RND` | `wellnessbox-rnd/apps/rnd-api/lib/rag/ingest-route.ts` | 문서 인덱싱은 R&D 쪽 책임이 맞음 | 낮음 | 지금 |
| `wellnessbox/lib/server/rag-reindex-route.ts` | RAG reindex route core | `MOVE_TO_RND` | `wellnessbox-rnd/apps/rnd-api/lib/rag/reindex-route.ts` | 인덱스 재생성은 R&D/지식베이스 운영 기능 | 낮음 | 지금 |
| `wellnessbox/lib/ai/` | Chat chain, RAG, embeddings, model wrapper | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/ai-runtime/` | 서비스가 직접 import 중인 AI 본체라 경계 계층이 먼저 필요 | 높음 | 나중 |
| `wellnessbox/app/api/chat/route-service.ts` | 채팅 streaming route core | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/apps/rnd-api/src/chat/stream.ts` | 장기적으로는 wellnessbox가 R&D API를 호출해야 함 | 높음 | 나중 |
| `wellnessbox/app/api/chat/suggest/` | suggested question/topic 생성 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/apps/rnd-api/src/chat/suggest/` | LLM 호출 기반 추천 계층 | 중간 | 나중 |
| `wellnessbox/app/api/chat/title/` | 채팅 제목 생성 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/apps/rnd-api/src/chat/title/` | LLM 호출 기반 후처리 | 중간 | 나중 |
| `wellnessbox/app/api/chat/actions/route-service.ts` | 채팅 액션 추천/실행 route core | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/apps/rnd-api/src/chat/actions.ts` | 모델 기반 action planner 본체는 R&D 쪽으로 옮기는 편이 맞음 | 중간 | 나중 |
| `wellnessbox/lib/chat/prompts.ts` | chat prompt SSOT | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/prompt-registry/chat/prompts.ts` | prompt SSOT는 R&D repo에 있어야 함 | 중간 | 나중 |
| `wellnessbox/lib/chat/response-guard.ts` | 채팅 응답 가드 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/ai-guards/chat/response-guard.ts` | 모델 응답 품질/가드 기준은 R&D 자산 | 중간 | 나중 |
| `wellnessbox/lib/chat/actions/model.ts` | model 기반 UI action planner | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/apps/rnd-api/src/chat/action-model.ts` | OpenAI 호출 기반 planner 본체 | 중간 | 나중 |
| `wellnessbox/lib/b2b/ai-evaluation.ts` | B2B 리포트용 AI narrative 생성 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/b2b-ai/evaluation.ts` | 리포트 AI 문안 생성은 R&D 본체로 분리 가능 | 중간 | 나중 |
| `wellnessbox/lib/server/hyphen/fetch-ai-summary.ts` | NHIS fetch 결과 AI summary 진입점 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/nhis-ai-summary/fetch-ai-summary.ts` | NHIS fetch는 서비스에 남기되 AI 후처리는 R&D 본체로 빼는 구조가 적합 | 중간 | 나중 |
| `wellnessbox/lib/server/hyphen/fetch-ai-summary-core.ts` | NHIS AI summary orchestration | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/nhis-ai-summary/fetch-ai-summary-core.ts` | AI 후처리 코어 | 중간 | 나중 |
| `wellnessbox/lib/server/hyphen/fetch-ai-summary-openai.ts` | NHIS AI summary OpenAI 호출 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/nhis-ai-summary/fetch-ai-summary-openai.ts` | 직접 LLM 호출 코드 | 중간 | 나중 |
| `wellnessbox/scripts/maintenance/smoke-hyphen-ai-summary.cts` | NHIS AI summary smoke | `MOVE_TO_RND` | `wellnessbox-rnd/tools/nhis-ai-summary/smoke-hyphen-ai-summary.cts` | AI summary 본체와 함께 이동하는 편이 자연스러움 | 낮음 | 지금 |
| `wellnessbox/scripts/maintenance/run-smoke-hyphen-ai-summary.cjs` | smoke launcher | `MOVE_TO_RND` | `wellnessbox-rnd/tools/nhis-ai-summary/run-smoke-hyphen-ai-summary.cjs` | 위 smoke script의 런처 | 낮음 | 지금 |
| `wellnessbox/lib/wellness/` | 웰니스 설문 계산, 채점, 리포트 조언 생성 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/wellness-engine/` | 장기적으로 R&D가 소유해야 할 계산 엔진이지만 현재 서비스가 직접 사용 중 | 매우 높음 | 나중 |
| `wellnessbox/data/b2b/survey.common.json` | 공통 설문 원본 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/data/wellness-engine/survey.common.json` | 설문 엔진 SSOT 후보 | 매우 높음 | 나중 |
| `wellnessbox/data/b2b/survey.sections.json` | 섹션 설문 원본 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/data/wellness-engine/survey.sections.json` | 설문 엔진 SSOT 후보 | 매우 높음 | 나중 |
| `wellnessbox/data/b2b/scoring.rules.json` | 채점 규칙 원본 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/data/wellness-engine/scoring.rules.json` | 계산식 SSOT 후보 | 매우 높음 | 나중 |
| `wellnessbox/data/b2b/report.texts.json` | 리포트 문구 원본 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/data/wellness-engine/report.texts.json` | 웰니스 리포트 텍스트 SSOT 후보 | 높음 | 나중 |
| `wellnessbox/lib/b2b/public-survey.ts` | 설문 질문 리스트/응답 해석 adapter | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/packages/wellness-engine/public-survey.ts` | 현재 서비스 렌더링이 직접 의존하지만 엔진 측 adapter 성격이 강함 | 높음 | 나중 |
| `wellnessbox/lib/b2b/survey-template.ts` | DB survey template bootstrap + file template 연결 | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/lib-b2b-survey-template.md` | DB bootstrap과 엔진 SSOT가 섞여 있어 바로 분리하면 위험 | 높음 | 나중 |
| `wellnessbox/data/b2b/README.md` | 설문 시스템 인덱스 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/wellness-engine/README.md` | 설문 엔진 문서이므로 엔진 SSOT와 같이 이동하는 편이 맞음 | 낮음 | 지금 |
| `wellnessbox/data/b2b/B2B_SURVEY_SYSTEM_GUIDE.md` | 설문/채점 시스템 설명서 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/wellness-engine/B2B_SURVEY_SYSTEM_GUIDE.md` | 엔진 구조 문서 | 낮음 | 지금 |
| `wellnessbox/data/b2b/B2B_SURVEY_TEST_MATRIX.md` | 설문 테스트 매트릭스 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/wellness-engine/B2B_SURVEY_TEST_MATRIX.md` | 엔진 정합성 테스트 문서 | 낮음 | 지금 |
| `wellnessbox/components/b2b/report-summary/card-insights.ts` | 결과 카드에서 설문 JSON 직접 읽음 | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/components-b2b-card-insights.md` | UI가 미래 이동 대상 데이터 파일을 직접 import하고 있음 | 높음 | 나중 |
| `wellnessbox/scripts/b2b/regenerate-reports-with-wellness.cts` | 웰니스 엔진으로 기존 리포트 재계산 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/tools/wellness-engine/regenerate-reports-with-wellness.cts` | 운영 스크립트지만 계산 엔진 본체와 강하게 결합 | 높음 | 나중 |
| `wellnessbox/scripts/b2b/regenerate-reports-with-wellness-runner.cjs` | 위 스크립트 런처 | `REPLACE_WITH_THIN_INTERFACE` | `wellnessbox-rnd/tools/wellness-engine/regenerate-reports-with-wellness-runner.cjs` | 엔진 이주 후 호출 경계 재설계 필요 | 중간 | 나중 |
| `wellnessbox/app/check-ai/` | 현재 운영 중인 빠른 진단 UI | `KEEP_IN_WELLNESSBOX` | `-` | 서비스 화면 본체 | 낮음 | 유지 |
| `wellnessbox/lib/checkai.ts` | check-ai 질문/옵션 정의 | `KEEP_IN_WELLNESSBOX` | `-` | 현재 서비스 quick-check 도메인 데이터 | 낮음 | 유지 |
| `wellnessbox/lib/checkai-client.ts` | check-ai 클라이언트 계산/저장 helper | `KEEP_IN_WELLNESSBOX` | `-` | 현재 서비스 기능 구현체 | 낮음 | 유지 |
| `wellnessbox/app/assess/` | 심화 진단 UI와 흐름 | `KEEP_IN_WELLNESSBOX` | `-` | 실제 서비스 진단 화면 | 낮음 | 유지 |
| `wellnessbox/app/survey/` | 현재 운영 설문 렌더링 | `KEEP_IN_WELLNESSBOX` | `-` | 사용자 입력 UI는 서비스에 남아야 함 | 낮음 | 유지 |
| `wellnessbox/app/(features)/health-link/` | NHIS 연동 UI | `KEEP_IN_WELLNESSBOX` | `-` | 운영 기능 본체 | 낮음 | 유지 |
| `wellnessbox/app/api/health/nhis/` | NHIS sign/init/fetch/status/unlink API | `KEEP_IN_WELLNESSBOX` | `-` | 인증/조회/세션은 서비스 운영 기능 | 낮음 | 유지 |
| `wellnessbox/app/(features)/employee-report/` | 직원 보고서 UI | `KEEP_IN_WELLNESSBOX` | `-` | 실사용 화면 | 낮음 | 유지 |
| `wellnessbox/app/(admin)/admin/b2b-reports/` | 관리자 B2B 리포트 운영 UI | `KEEP_IN_WELLNESSBOX` | `-` | 운영 백오피스 | 낮음 | 유지 |
| `wellnessbox/app/(admin)/admin/b2b-employee-data/` | 관리자 직원 데이터 운영 UI | `KEEP_IN_WELLNESSBOX` | `-` | 운영 백오피스 | 낮음 | 유지 |
| `wellnessbox/lib/b2b/analysis-service.ts` | B2B 분석 저장 orchestration | `KEEP_IN_WELLNESSBOX` | `-` | DB, 기간, 저장, 리포트 조립이 중심이며 AI 호출만 분리하면 됨 | 중간 | 유지 |
| `wellnessbox/lib/b2b/report-payload.ts` | 리포트 payload 조립 | `KEEP_IN_WELLNESSBOX` | `-` | 서비스 report assembly 역할이 큼 | 중간 | 유지 |
| `wellnessbox/AGENTS.md` | repo agent 지침 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/AGENTS.md` | agent 운영 문서 | 낮음 | 지금 |
| `wellnessbox/AGENT_PRECHECK.md` | agent precheck 문서 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/AGENT_PRECHECK.md` | agent 운영 문서 | 낮음 | 지금 |
| `wellnessbox/AGENT_SESSION_PRIMER.md` | agent session primer | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/AGENT_SESSION_PRIMER.md` | agent 운영 문서 | 낮음 | 지금 |
| `wellnessbox/AGENT_SKILLS_CATALOG.md` | agent skills catalog | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/AGENT_SKILLS_CATALOG.md` | agent 운영 문서 | 낮음 | 지금 |
| `wellnessbox/API_GUARD_MAP.md` | API guard 산출물 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/API_GUARD_MAP.md` | agent/maintenance generated document | 낮음 | 지금 |
| `wellnessbox/FUNCTION_HOTSPOTS.md` | 함수 hotspot 산출물 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/FUNCTION_HOTSPOTS.md` | generated analysis output | 낮음 | 지금 |
| `wellnessbox/REFACTOR_HOTSPOTS.md` | 리팩터 hotspot 보고서 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/REFACTOR_HOTSPOTS.md` | generated analysis output | 낮음 | 지금 |
| `wellnessbox/REFACTOR_BACKLOG.md` | 리팩터 backlog | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/REFACTOR_BACKLOG.md` | 코드베이스 분석/작업 메모 | 낮음 | 지금 |
| `wellnessbox/CHAT_AGENT_HANDOFF.md` | 임시 AI chat handoff | `DELETE_AS_DUPLICATE` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/CHAT_AGENT_HANDOFF.md` | `docs/scenarios/ai-chat-agent-handoff.md`와 중복 트랙이고 임시 삭제 안내가 명시됨 | 낮음 | 나중 |
| `wellnessbox/docs/agent/` | agent 관련 docs | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/docs-agent/` | agent 운영 문서 | 낮음 | 지금 |
| `wellnessbox/docs/scenarios/ai-chat-agent-handoff.md` | AI chat agent handoff 시나리오 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/ai-chat-agent-handoff.md` | agent 운영 시나리오 | 낮음 | 지금 |
| `wellnessbox/docs/engineering/agent-preflight.md` | agent preflight 문서 | `MOVE_TO_RND` | `wellnessbox-rnd/docs/imported/wellnessbox/agent-ops/agent-preflight.md` | agent/Codex 운용 문서 | 낮음 | 지금 |
| `wellnessbox/scripts/agent/` | agent 산출물 생성 스크립트 | `MOVE_TO_RND` | `wellnessbox-rnd/tools/agent-ops/` | agent tooling은 서비스 runtime과 분리하는 편이 맞음 | 낮음 | 지금 |
| `wellnessbox/scripts/chat.mjs` | chat+rag smoke script | `MOVE_TO_RND` | `wellnessbox-rnd/tools/rag/chat.mjs` | RAG/AI 디버그 스크립트 | 낮음 | 지금 |
| `wellnessbox/scripts/query.mjs` | RAG query smoke script | `MOVE_TO_RND` | `wellnessbox-rnd/tools/rag/query.mjs` | RAG 디버그 스크립트 | 낮음 | 지금 |
| `wellnessbox/scripts/reindex.mjs` | RAG reindex trigger | `MOVE_TO_RND` | `wellnessbox-rnd/tools/rag/reindex.mjs` | RAG 운영 스크립트 | 낮음 | 지금 |
| `wellnessbox/scripts/dump-rag-chunks.mjs` | rag_chunks DB dump | `MOVE_TO_RND` | `wellnessbox-rnd/tools/rag/dump-rag-chunks.mjs` | RAG 내부 데이터 디버그 도구 | 낮음 | 지금 |
| `wellnessbox/data/mfds_supplement_functions.md` | 건강기능식품 기능 지식 원문 | `MOVE_TO_RND` | `wellnessbox-rnd/data/knowledge/supplements/mfds_supplement_functions.md` | 지식 베이스 원문 | 낮음 | 지금 |
| `wellnessbox/data/supplement_categories.md` | 카테고리 지식 원문 | `MOVE_TO_RND` | `wellnessbox-rnd/data/knowledge/supplements/supplement_categories.md` | 지식 베이스 원문 | 낮음 | 지금 |
| `wellnessbox/data/supplement_overdose_and_drug_interactions_public.md` | 공개 상호작용 지식 원문 | `MOVE_TO_RND` | `wellnessbox-rnd/data/knowledge/supplements/supplement_overdose_and_drug_interactions_public.md` | 지식 베이스 원문 | 낮음 | 지금 |
| `wellnessbox/data/supplement_overdose_and_drug_interactions_expert.md` | 전문가용 상호작용 지식 원문 | `MOVE_TO_RND` | `wellnessbox-rnd/data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md` | 지식 베이스 원문 | 낮음 | 지금 |
| `wellnessbox/docs/maintenance/` | 서비스 refactor/maintenance 메모 묶음 | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/maintenance/` | R&D라기보다 service engineering 문서에 가까우나, 서비스 repo에서 줄일 후보이기도 함 | 중간 | 나중 |
| `wellnessbox/docs/README.md` | docs index | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/docs-index/README.md` | split 이후 다시 써야 함 | 낮음 | 나중 |
| `wellnessbox/docs/DOCS_CATALOG.md` | docs catalog | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/docs-index/DOCS_CATALOG.md` | split 이후 다시 써야 함 | 낮음 | 나중 |
| `wellnessbox/docs/DOC_TYPES_AND_FORMAT.md` | docs 작성 규칙 | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/docs-index/DOC_TYPES_AND_FORMAT.md` | 서비스용인지 전체 개발용인지 경계가 불명확 | 낮음 | 나중 |
| `wellnessbox/docs/scenarios/chat-client-scenarios.md` | `/chat` 세션/클라이언트 시나리오 | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/scenarios/chat-client-scenarios.md` | 서비스 QA 문서에 가까워 R&D repo로 바로 보내기 애매함 | 낮음 | 나중 |
| `wellnessbox/docs/scenarios/client-appuser-linking.md` | client-appUser linking 정책 | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/scenarios/client-appuser-linking.md` | 인증/세션 설계 문서이며 R&D와 직접 관련이 약함 | 낮음 | 나중 |
| `wellnessbox/scripts/lib/` | shared script helper 라이브러리 | `NEEDS_REVIEW` | `wellnessbox-rnd/tools/review/shared-script-lib/` | agent tooling과 prebuild audit가 함께 의존 | 중간 | 나중 |
| `wellnessbox/data/b2b/backups/` | B2B 백업 JSON | `NEEDS_REVIEW` | `wellnessbox-rnd/quarantine/b2b-backups/` | 샘플/실운영/PII 여부를 먼저 확인해야 함 | 높음 | 나중 |
| `wellnessbox/PORTING_EDITOR_IMAGE_UPLOAD.md` | editor image upload 포팅 메모 | `NEEDS_REVIEW` | `wellnessbox-rnd/docs/review/wellnessbox/porting/PORTING_EDITOR_IMAGE_UPLOAD.md` | 서비스 운영 문서인지 일회성 메모인지 불명확 | 낮음 | 나중 |
| `wellnessbox/docs/survey_client_map.md` | 설문 화면 구조 문서 | `KEEP_IN_WELLNESSBOX` | `-` | 운영 설문 화면 유지보수 문서 | 낮음 | 유지 |
| `wellnessbox/docs/employee_report_client_map.md` | 직원 결과 화면 구조 문서 | `KEEP_IN_WELLNESSBOX` | `-` | 서비스 유지보수 문서 | 낮음 | 유지 |
| `wellnessbox/docs/b2b_admin_report_client_map.md` | B2B 관리자 리포트 클라이언트 맵 | `KEEP_IN_WELLNESSBOX` | `-` | 운영 백오피스 문서 | 낮음 | 유지 |
| `wellnessbox/docs/b2b_admin_employee_data_client_map.md` | B2B 직원 데이터 클라이언트 맵 | `KEEP_IN_WELLNESSBOX` | `-` | 운영 백오피스 문서 | 낮음 | 유지 |
| `wellnessbox/docs/b2b_employee_report_spec.md` | 직원 리포트 spec | `KEEP_IN_WELLNESSBOX` | `-` | 운영 기능 스펙 문서 | 낮음 | 유지 |
| `wellnessbox/docs/b2b_employee_report_manual_test.md` | 직원 리포트 수동 테스트 | `KEEP_IN_WELLNESSBOX` | `-` | 운영 QA 문서 | 낮음 | 유지 |
| `wellnessbox/docs/b2b_employee_report_dev_runbook.md` | 직원 리포트 개발 런북 | `KEEP_IN_WELLNESSBOX` | `-` | 운영/개발 런북 | 낮음 | 유지 |
| `wellnessbox/docs/b2b_report_summary_map.md`, `wellnessbox/docs/b2b_report_score_engine.md`, `wellnessbox/docs/b2b_report_redesign_worklog.md`, `wellnessbox/docs/b2b_report_payload_map.md`, `wellnessbox/docs/b2b_report_design_system.md` | B2B 리포트 운영 문서 | `KEEP_IN_WELLNESSBOX` | `-` | 현재 운영 백오피스와 export 흐름 유지보수에 직접 필요 | 낮음 | 유지 |

## 실행 우선순위 메모

1. 바로 옮겨도 되는 1차 묶음:
   `docs/rnd`, `docs/rnd_impl`, `lib/rnd`, `scripts/rnd`, `app/agent-playground`, `app/api/agent-playground`, `lib/agent-playground`, `app/api/rag`, `lib/server/rag-*`, agent/Codex 문서, `scripts/agent`, supplement knowledge docs
2. contract가 먼저 필요한 2차 묶음:
   `lib/ai`, `lib/chat/prompts.ts`, `lib/chat/response-guard.ts`, `lib/chat/actions/model.ts`, `lib/wellness`, `data/b2b/*.json`, `lib/b2b/public-survey.ts`, `lib/b2b/ai-evaluation.ts`, `lib/server/hyphen/fetch-ai-summary*`
3. 마지막에 다시 결정해야 하는 3차 묶음:
   `docs/maintenance`, `scripts/lib`, `data/b2b/backups`, `PORTING_EDITOR_IMAGE_UPLOAD.md`, `docs/scenarios/chat-client-scenarios.md`, `docs/scenarios/client-appuser-linking.md`
