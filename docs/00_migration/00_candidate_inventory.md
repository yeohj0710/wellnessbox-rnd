# wellnessbox 내부 R&D 후보 인벤토리

기준 문서: `wellnessbox-rnd/docs/context/master_context.md`

작성 목적:
- `wellnessbox/` 안에 섞여 있는 R&D 관련 자산과 경계성 자산을 다시 훑고
- 실제 이동 전 단계에서 후보군을 빠짐없이 묶어 보고
- 어떤 묶음이 `MOVE_TO_RND`, `REPLACE_WITH_THIN_INTERFACE`, `KEEP_IN_WELLNESSBOX`, `NEEDS_REVIEW`, `DELETE_AS_DUPLICATE` 후보인지 1차 판단하기 위함

경로 표기 규칙:
- 모든 경로는 `C:\dev\` 기준 상대 경로로 적는다.
- 예: `wellnessbox/lib/rnd/...`, `wellnessbox-rnd/docs/...`

## 1. 순수 R&D / 에이전트 / 실험 자산 클러스터

| 클러스터 | 대표 경로 | R&D 신호 | 현재 런타임 결합도 | 1차 분류 후보 |
| --- | --- | --- | --- | --- |
| TIPS R&D 문서 본체 | `wellnessbox/docs/rnd/` | KPI, 평가, 데이터레이크, closed-loop, 바이오센서, 학습 파이프라인 명시 | 낮음 | `MOVE_TO_RND` |
| TIPS R&D 구현 메모 | `wellnessbox/docs/rnd_impl/` | 구현 노트, 모듈별 impl notes | 낮음 | `MOVE_TO_RND` |
| R&D 코드 본체 | `wellnessbox/lib/rnd/` | `module02~07`, `ai-training/pipeline.ts` | 낮음 | `MOVE_TO_RND` |
| R&D 실행 스크립트 | `wellnessbox/scripts/rnd/` | `rnd:module02~07`, `rnd:train:all` | 낮음 | `MOVE_TO_RND` |
| Agent playground UI | `wellnessbox/app/agent-playground/` | 비교 실행, trace, evaluation PASS/FAIL UI | 낮음 | `MOVE_TO_RND` |
| Agent playground API | `wellnessbox/app/api/agent-playground/run/route.ts` | 실험용 agent 실행 엔드포인트 | 낮음 | `MOVE_TO_RND` |
| Agent playground 런타임 | `wellnessbox/lib/agent-playground/` | pattern, tools, trace, OpenAI 실행 | 낮음 | `MOVE_TO_RND` |
| RAG 디버그/인덱싱 API | `wellnessbox/app/api/rag/`, `wellnessbox/lib/server/rag-*.ts` | ingest/debug/reindex | 낮음 | `MOVE_TO_RND` |
| Agent 운영 문서 | `wellnessbox/AGENTS.md`, `wellnessbox/AGENT_PRECHECK.md`, `wellnessbox/AGENT_SESSION_PRIMER.md`, `wellnessbox/AGENT_SKILLS_CATALOG.md`, `wellnessbox/API_GUARD_MAP.md`, `wellnessbox/FUNCTION_HOTSPOTS.md`, `wellnessbox/REFACTOR_HOTSPOTS.md`, `wellnessbox/REFACTOR_BACKLOG.md` | Codex/agent 운영, 생성 문서, 핫스팟, 백로그 | 낮음 | `MOVE_TO_RND` |
| Agent 스크립트 | `wellnessbox/scripts/agent/` | 세션 프라이머/가드맵/스킬카탈로그 생성 | 낮음 | `MOVE_TO_RND` |
| Agent/RAG 실험용 CLI | `wellnessbox/scripts/chat.mjs`, `wellnessbox/scripts/query.mjs`, `wellnessbox/scripts/reindex.mjs`, `wellnessbox/scripts/dump-rag-chunks.mjs` | RAG query/reindex/debug smoke | 낮음 | `MOVE_TO_RND` |
| 원천 지식 문서 | `wellnessbox/data/mfds_supplement_functions.md`, `wellnessbox/data/supplement_categories.md`, `wellnessbox/data/supplement_overdose_and_drug_interactions_public.md`, `wellnessbox/data/supplement_overdose_and_drug_interactions_expert.md` | 지식 베이스, 상호작용, 기능 카탈로그 | 낮음 | `MOVE_TO_RND` |

## 2. 서비스가 직접 물고 있는 AI / 웰니스 엔진 클러스터

| 클러스터 | 대표 경로 | 현재 사용처 | 결합 형태 | 1차 분류 후보 |
| --- | --- | --- | --- | --- |
| Chat/LLM 체인 | `wellnessbox/lib/ai/` | `/api/chat`, `/api/chat/suggest`, `/api/chat/title`, `/api/rag`, `b2b ai-evaluation`, `nhis ai-summary` | 서비스 API가 직접 import | `REPLACE_WITH_THIN_INTERFACE` |
| Chat prompt / 응답 가드 | `wellnessbox/lib/chat/prompts.ts`, `wellnessbox/lib/chat/response-guard.ts`, `wellnessbox/lib/chat/actions/model.ts` | 채팅 응답, 액션 추천/실행 | 서비스 API가 직접 import | `REPLACE_WITH_THIN_INTERFACE` |
| B2B AI narrative | `wellnessbox/lib/b2b/ai-evaluation.ts` | `lib/b2b/analysis-service.ts` | 분석 저장 흐름 내부에서 직접 호출 | `REPLACE_WITH_THIN_INTERFACE` |
| NHIS AI summary | `wellnessbox/lib/server/hyphen/fetch-ai-summary.ts`, `wellnessbox/lib/server/hyphen/fetch-ai-summary-core.ts`, `wellnessbox/lib/server/hyphen/fetch-ai-summary-openai.ts` | NHIS fetch 결과 enrich | NHIS 런타임 내부 후처리 | `REPLACE_WITH_THIN_INTERFACE` |
| 웰니스 계산 엔진 | `wellnessbox/lib/wellness/` | `/survey`, B2B report payload, survey template bootstrap | 런타임이 직접 import | `REPLACE_WITH_THIN_INTERFACE` |
| B2B 설문 규칙/문안 데이터 | `wellnessbox/data/b2b/survey.common.json`, `wellnessbox/data/b2b/survey.sections.json`, `wellnessbox/data/b2b/scoring.rules.json`, `wellnessbox/data/b2b/report.texts.json` | 설문 렌더링, 채점, 리포트 텍스트 | 정적 import | `REPLACE_WITH_THIN_INTERFACE` |
| 공용 설문 adapter | `wellnessbox/lib/b2b/public-survey.ts` | `/survey`, 관리자 설문 편집, 결과 계산 | 런타임 직접 import | `REPLACE_WITH_THIN_INTERFACE` |
| 웰니스 리포트 재생성 스크립트 | `wellnessbox/scripts/b2b/regenerate-reports-with-wellness.cts`, `wellnessbox/scripts/b2b/regenerate-reports-with-wellness-runner.cjs` | 운영용 재계산 | 엔진 내부 구현과 직접 결합 | `REPLACE_WITH_THIN_INTERFACE` |
| AI 모델 설정 API | `wellnessbox/lib/server/admin-model-route.ts`, `wellnessbox/app/api/admin/model/route.ts` | 관리자 모델 선택 | 서비스 DB에 모델 설정 저장 | `REPLACE_WITH_THIN_INTERFACE` |

## 3. 서비스 런타임에 남겨야 하는 경계 클러스터

| 클러스터 | 대표 경로 | 남겨야 하는 이유 | 1차 분류 후보 |
| --- | --- | --- | --- |
| 빠른 진단 UI | `wellnessbox/app/check-ai/`, `wellnessbox/lib/checkai.ts`, `wellnessbox/lib/checkai-client.ts`, `wellnessbox/app/api/check-ai/save/route.ts`, `wellnessbox/lib/server/check-ai-save-route.ts` | 실제 서비스 화면, 저장 API, 내 데이터 연계 | `KEEP_IN_WELLNESSBOX` |
| 심화 진단 UI | `wellnessbox/app/assess/`, `wellnessbox/app/api/assess/save/route.ts`, `wellnessbox/lib/server/assess-save-route.ts` | 실제 서비스 화면과 저장 API | `KEEP_IN_WELLNESSBOX` |
| 현재 운영 설문 화면 | `wellnessbox/app/survey/` | 공용 설문 렌더링과 사용자 입력 플로우 | `KEEP_IN_WELLNESSBOX` |
| NHIS 연동 본체 | `wellnessbox/app/(features)/health-link/`, `wellnessbox/app/api/health/nhis/`, `wellnessbox/lib/server/hyphen/client*.ts`, `wellnessbox/lib/server/hyphen/fetch-route*.ts`, `wellnessbox/lib/server/hyphen/init-route*.ts`, `wellnessbox/lib/server/hyphen/sign-route*.ts`, `wellnessbox/lib/server/hyphen/status-route*.ts`, `wellnessbox/lib/server/hyphen/unlink-route.ts` | 인증/조회/캐시/세션은 웹서비스 운영 기능 자체 | `KEEP_IN_WELLNESSBOX` |
| 직원 결과 조회 | `wellnessbox/app/(features)/employee-report/` | 실제 사용자 조회 화면 | `KEEP_IN_WELLNESSBOX` |
| B2B 관리자 리포트 | `wellnessbox/app/(admin)/admin/b2b-reports/`, `wellnessbox/lib/b2b/report-*.ts`, `wellnessbox/lib/b2b/export/`, `wellnessbox/lib/b2b/admin-report-*.ts` | 관리자 운영, PDF/PPTX export, 리포트 편집 | `KEEP_IN_WELLNESSBOX` |
| B2B 직원 데이터 운영 | `wellnessbox/app/(admin)/admin/b2b-employee-data/`, `wellnessbox/lib/b2b/admin-employee-*.ts`, `wellnessbox/lib/b2b/employee-*.ts` | 관리자 운영과 데이터 동기화 | `KEEP_IN_WELLNESSBOX` |
| B2B 분석 저장 orchestration | `wellnessbox/lib/b2b/analysis-service.ts`, `wellnessbox/lib/b2b/report-service.ts`, `wellnessbox/lib/b2b/report-payload.ts` | DB, 주기, 이력, 리포트 조합은 서비스 운영 로직 | `KEEP_IN_WELLNESSBOX` |
| 서비스 문서/클라이언트 맵 | `wellnessbox/docs/survey_client_map.md`, `wellnessbox/docs/employee_report_client_map.md`, `wellnessbox/docs/b2b_admin_report_client_map.md`, `wellnessbox/docs/b2b_admin_employee_data_client_map.md`, `wellnessbox/docs/b2b_employee_report_spec.md`, `wellnessbox/docs/b2b_employee_report_manual_test.md`, `wellnessbox/docs/b2b_employee_report_dev_runbook.md`, `wellnessbox/docs/b2b_report_*.md`, `wellnessbox/docs/engineering/hyphen-nhis-integration.md`, `wellnessbox/docs/engineering/check-ai-maintenance-map.md`, `wellnessbox/docs/engineering/b2b-survey-selection-policy.md`, `wellnessbox/docs/engineering/b2b-report-maintenance.md` | 운영/유지보수 문서이며 실제 화면과 API를 설명 | `KEEP_IN_WELLNESSBOX` |
| 서비스 테스트/QA | `wellnessbox/scripts/qa/`, `wellnessbox/data/hyphen/nhis-mock.json`, `wellnessbox/app/assess/docs/` | 운영 기능 회귀 검증과 런북 | `KEEP_IN_WELLNESSBOX` |

## 4. 회색지대 / 검토 필요 클러스터

| 클러스터 | 대표 경로 | 검토가 필요한 이유 | 1차 분류 후보 |
| --- | --- | --- | --- |
| 서비스 리팩터 문서 묶음 | `wellnessbox/docs/maintenance/` | 런타임 코드를 설명하지만 비실행 문서이며 agent 산출물이 섞여 있음 | `NEEDS_REVIEW` |
| 문서 인덱스 묶음 | `wellnessbox/docs/README.md`, `wellnessbox/docs/DOCS_CATALOG.md`, `wellnessbox/docs/DOC_TYPES_AND_FORMAT.md` | split 이후 카탈로그 재작성 필요 | `NEEDS_REVIEW` |
| 시나리오 문서 일부 | `wellnessbox/docs/scenarios/chat-client-scenarios.md`, `wellnessbox/docs/scenarios/client-appuser-linking.md` | R&D라기보다 서비스 QA/세션 설계 문서에 가까움 | `NEEDS_REVIEW` |
| 공용 스크립트 라이브러리 | `wellnessbox/scripts/lib/` | agent 스크립트와 build/prebuild audit가 함께 의존 | `NEEDS_REVIEW` |
| B2B 백업 JSON | `wellnessbox/data/b2b/backups/` | 실제 운영 스냅샷인지, 샘플인지, PII 포함 여부 불명확 | `NEEDS_REVIEW` |
| 설문 템플릿 DB bootstrap | `wellnessbox/lib/b2b/survey-template.ts` | DB bootstrap과 wellness template SSOT가 섞여 있음 | `NEEDS_REVIEW` |
| 결과 카드 UI의 직접 JSON 의존 | `wellnessbox/components/b2b/report-summary/card-insights.ts` | UI가 `data/b2b/*.json`를 직접 import | `NEEDS_REVIEW` |
| 포팅 메모 | `wellnessbox/PORTING_EDITOR_IMAGE_UPLOAD.md` | 서비스 운영 문서인지 일회성 구현 메모인지 불명확 | `NEEDS_REVIEW` |

## 5. 중복 삭제 후보

| 경로 | 근거 | 1차 분류 후보 |
| --- | --- | --- |
| `wellnessbox/CHAT_AGENT_HANDOFF.md` | `wellnessbox/docs/scenarios/ai-chat-agent-handoff.md`와 같은 트랙의 임시 handoff 문서이며, 루트 문서 본문에 “Temporary”, “Delete this file after the next session”가 명시되어 있음 | `DELETE_AS_DUPLICATE` |

## 6. 이번 인벤토리에서 읽은 핵심 결론

1. `lib/rnd`와 `scripts/rnd`는 현재 서비스 런타임이 직접 import하지 않아서 바로 `wellnessbox-rnd`로 옮기기 쉬운 축이다.
2. `lib/ai`, `lib/wellness`, `lib/b2b/public-survey`, `lib/server/hyphen/fetch-ai-summary*`는 서비스가 직접 물고 있어 바로 이동하면 런타임이 깨진다.
3. `wellnessbox` 루트의 agent/Codex 문서와 `scripts/agent`는 웹서비스 운영 필수 자산이 아니라 생성/분석용 자산이다.
4. `data/b2b/*.json`는 현재 설문 렌더링과 리포트 UI까지 이어지는 실사용 데이터이므로 이동보다 인터페이스화가 먼저다.
5. `docs/maintenance/`와 `scripts/lib/`는 R&D와 서비스 엔지니어링이 뒤섞인 영역이라 별도 검토가 필요하다.
