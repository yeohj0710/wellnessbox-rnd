# migration execution report

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 이번 단계 원칙

- 실제 이동은 `MOVE_TO_RND` 중에서도 문서/지식 자산 위주로 제한했다.
- `REPLACE_WITH_THIN_INTERFACE`, `NEEDS_REVIEW` 항목은 건드리지 않았다.
- `wellnessbox`와 `wellnessbox-rnd`가 서로 다른 git 저장소라서 `git mv`는 사용할 수 없었다.
- 따라서 Windows 파일 이동(`Move-Item`)으로 이주했고, 이 문서에 실행 내역을 남긴다.

## 실제 이동 내역

| source path | action | destination path | reason | runtime impact |
| --- | --- | --- | --- | --- |
| `C:/dev/wellnessbox/docs/agent/b2b-survey-section-sync.md` | moved | `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/agents/b2b-survey-section-sync.md` | agent 운영 규칙 문서이며 서비스 런타임과 직접 결합되지 않음 | low |
| `C:/dev/wellnessbox/docs/engineering/agent-preflight.md` | moved | `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/engineering/agent-preflight.md` | agent/Codex 선행 점검 문서 | low |
| `C:/dev/wellnessbox/docs/scenarios/ai-chat-agent-handoff.md` | moved | `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/scenarios/ai-chat-agent-handoff.md` | agent handoff 시나리오 문서 | low |
| `C:/dev/wellnessbox/data/b2b/README.md` | moved | `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/wellness_engine/README.md` | 웰니스 설문 엔진 설명 문서 | low |
| `C:/dev/wellnessbox/data/b2b/B2B_SURVEY_SYSTEM_GUIDE.md` | moved | `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/wellness_engine/B2B_SURVEY_SYSTEM_GUIDE.md` | 설문/채점 구조 설명서 | low |
| `C:/dev/wellnessbox/data/b2b/B2B_SURVEY_TEST_MATRIX.md` | moved | `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/wellness_engine/B2B_SURVEY_TEST_MATRIX.md` | 설문 테스트 매트릭스 | low |
| `C:/dev/wellnessbox/data/mfds_supplement_functions.md` | moved | `C:/dev/wellnessbox-rnd/data/knowledge/supplements/mfds_supplement_functions.md` | 연구용 지식 문서 | low |
| `C:/dev/wellnessbox/data/supplement_categories.md` | moved | `C:/dev/wellnessbox-rnd/data/knowledge/supplements/supplement_categories.md` | 연구용 지식 문서 | low |
| `C:/dev/wellnessbox/data/supplement_overdose_and_drug_interactions_public.md` | moved | `C:/dev/wellnessbox-rnd/data/knowledge/supplements/supplement_overdose_and_drug_interactions_public.md` | 연구용 상호작용 지식 문서 | low |
| `C:/dev/wellnessbox/data/supplement_overdose_and_drug_interactions_expert.md` | moved | `C:/dev/wellnessbox-rnd/data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md` | 연구용 상호작용 지식 문서 | low |

## 삭제한 중복 문서

- `C:/dev/wellnessbox/CHAT_AGENT_HANDOFF.md`
  - canonical 문서는 `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/scenarios/ai-chat-agent-handoff.md`
  - 루트 파일 자체에 temporary/delete 안내가 있었고, 내용도 동일 세션 트랙의 핸드오프 요약이었다.

## 함께 갱신한 참조

- `C:/dev/wellnessbox/docs/DOCS_CATALOG.md`
  - 이동된 `agent-preflight.md`, `ai-chat-agent-handoff.md` 경로를 `wellnessbox-rnd` 기준으로 갱신했다.
- `C:/dev/wellnessbox/AGENT_SESSION_PRIMER.md`
  - `npm run agent:session-primer`를 다시 실행해 삭제된 `CHAT_AGENT_HANDOFF.md` 참조를 제거했다.
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/wellness_engine/README.md`
  - 함께 이동한 두 문서를 새 위치 기준의 상대 참조로 갱신했다.

## 이번 단계에서 보류한 대표 항목

- `C:/dev/wellnessbox/docs/rnd/`
- `C:/dev/wellnessbox/docs/rnd_impl/`
- `C:/dev/wellnessbox/lib/rnd/`
- `C:/dev/wellnessbox/scripts/rnd/`
- `C:/dev/wellnessbox/AGENTS.md` 및 루트 agent 산출물
- `C:/dev/wellnessbox/scripts/agent/`
- `C:/dev/wellnessbox/lib/ai/`
- `C:/dev/wellnessbox/lib/wellness/`
- `C:/dev/wellnessbox/data/b2b/*.json`

보류 사유는 공통적으로 다음 셋 중 하나였다.

- 현재 `wellnessbox` 스크립트나 서비스 코드가 직접 참조하고 있음
- 미래에는 `thin interface`로 바꿔야 하지만 아직 contract가 없음
- 서비스 운영 문서와 R&D 문서가 섞여 있어 경계 재분류가 더 필요함

## 최소 검증

- `rg -n`으로 이동/삭제한 문서 경로를 `wellnessbox` 전체에서 재검색했다.
- 남은 직접 참조는 아래 두 종류만 확인됐다.
  - `C:/dev/wellnessbox/docs/DOCS_CATALOG.md`의 이동 경로 표기
  - `C:/dev/wellnessbox/scripts/agent/generate-session-primer.cts` 내부의 optional filename 문자열
- `npm run agent:session-primer`를 실행해 실제 생성 산출물 `AGENT_SESSION_PRIMER.md`가 정상 갱신되는지 확인했다.

## 결론

- 이번 단계에서는 서비스 런타임과 분리 가능한 문서/지식 자산만 `wellnessbox-rnd`로 이주시켰다.
- `wellnessbox` 내부에는 더 큰 R&D 원본이 남아 있지만, 그것들은 다음 단계에서 경계 계약과 스크립트 결합을 먼저 해소해야 안전하게 옮길 수 있다.
