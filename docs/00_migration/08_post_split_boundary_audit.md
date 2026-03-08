# post split boundary audit

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 기준 선언

- `master_context.md`를 다시 기준 문서로 확인했다.
- 앞으로 연구개발의 1차 기준 문서는 오직 `C:/dev/wellnessbox-rnd/docs/context/master_context.md` 하나다.
- `wellnessbox`에는 R&D 원본 문서, 평가 문서, agent 설계 문서, 실험 노트를 다시 두지 않는다.
- `wellnessbox`가 나중에 R&D 결과를 소비해야 하면 API contract, generated schema, snapshot artifact 같은 얇은 연결만 허용한다.

## 이번 단계에서 추가로 정리한 항목

### `wellnessbox` -> `wellnessbox-rnd` 실제 이동

- root agent 문서/산출물
  - `C:/dev/wellnessbox/AGENTS.md` 원본 -> `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/agents/AGENTS_wellnessbox_legacy.md`
  - `C:/dev/wellnessbox/AGENT_PRECHECK.md`
  - `C:/dev/wellnessbox/AGENT_SESSION_PRIMER.md`
  - `C:/dev/wellnessbox/AGENT_SKILLS_CATALOG.md`
  - `C:/dev/wellnessbox/API_GUARD_MAP.md`
  - `C:/dev/wellnessbox/FUNCTION_HOTSPOTS.md`
  - `C:/dev/wellnessbox/REFACTOR_HOTSPOTS.md`
  - `C:/dev/wellnessbox/REFACTOR_BACKLOG.md`
- agent 생성 스크립트
  - `C:/dev/wellnessbox/scripts/agent/` -> `C:/dev/wellnessbox-rnd/legacy_code/agent_ops/scripts/agent/`
- orphan helper
  - `C:/dev/wellnessbox/scripts/lib/skill-catalog.cts` -> `C:/dev/wellnessbox-rnd/legacy_code/agent_ops/scripts/lib/skill-catalog.cts`
- RAG 실험 스크립트
  - `C:/dev/wellnessbox/scripts/chat.mjs`
  - `C:/dev/wellnessbox/scripts/query.mjs`
  - `C:/dev/wellnessbox/scripts/reindex.mjs`
  - `C:/dev/wellnessbox/scripts/dump-rag-chunks.mjs`
  - 위 4건 -> `C:/dev/wellnessbox-rnd/legacy_code/rag_tools/scripts/`

### `wellnessbox` 내부 경계 정리

- `C:/dev/wellnessbox/AGENTS.md`를 서비스 전용 경계 문서로 재작성했다.
- `C:/dev/wellnessbox/package.json`에서 agent 전용 npm scripts를 제거했다.
- 비워진 `C:/dev/wellnessbox/docs/agent/` 폴더를 정리했다.

## split 이후 현재 상태 판단

### `wellnessbox` 쪽이 비교적 정리된 영역

- root의 agent 산출물/보고서가 제거됐다.
- `scripts/agent/`가 제거됐다.
- RAG 실험용 직접 호출 스크립트가 제거됐다.
- `data/*.md`, `data/b2b/*.md` 설명 문서가 제거됐다.
- `docs/agent/`가 제거됐다.

### 아직 `wellnessbox`에 남은 대표 R&D 잔재

| path | classification | why still here |
| --- | --- | --- |
| `C:/dev/wellnessbox/docs/rnd/` | `MOVE_TO_RND` 예정 | `scripts/rnd/*`가 경로를 직접 참조 |
| `C:/dev/wellnessbox/docs/rnd_impl/` | `MOVE_TO_RND` 예정 | `docs/rnd/*`와 강한 상호 참조 |
| `C:/dev/wellnessbox/lib/rnd/` | `MOVE_TO_RND` 예정 | 코드 경계가 크고 `scripts/rnd/*`와 결합 |
| `C:/dev/wellnessbox/scripts/rnd/` | `MOVE_TO_RND` 예정 | `package.json`의 `rnd:*` 명령 체계와 연결 |
| `C:/dev/wellnessbox/app/agent-playground/` | `MOVE_TO_RND` 예정 | runtime route 정리와 같이 가야 함 |
| `C:/dev/wellnessbox/app/api/rag/` | `MOVE_TO_RND` 예정 | 서비스 운영 API인지 실험 API인지 경계 정리가 더 필요 |
| `C:/dev/wellnessbox/lib/ai/` | `REPLACE_WITH_THIN_INTERFACE` | chat/NHIS/B2B가 직접 import |
| `C:/dev/wellnessbox/lib/wellness/` | `REPLACE_WITH_THIN_INTERFACE` | survey/admin/reporting이 직접 import |
| `C:/dev/wellnessbox/data/b2b/*.json` | `REPLACE_WITH_THIN_INTERFACE` | UI와 점수 계산이 직접 읽음 |

## 예외와 보수적 판단

- `app/agent-playground`, `app/api/rag`, `lib/agent-playground`, `lib/server/rag-*`는 R&D 쪽 성격이 강하지만, 이번 단계에서는 실제 route 제거까지 건드리지 않았다.
- `lib/ai`, `lib/wellness`, `lib/b2b/ai-evaluation`, `lib/server/hyphen/fetch-ai-summary*`는 서비스 코드가 직접 의존하므로 계약 없는 이동을 막았다.
- `docs/maintenance/`와 `scripts/lib/`는 service engineering 문서/helper와 R&D 흔적이 섞여 있어 전면 이동 대신 감사 문서에 예외로 남겼다.

## 결론

- `wellnessbox`는 이전 단계보다 훨씬 더 서비스 전용 저장소에 가까워졌다.
- 그러나 hard split 완료로 보려면 `docs/rnd + docs/rnd_impl + lib/rnd + scripts/rnd` 묶음과 `lib/ai/lib/wellness` thin interface 묶음을 다음 단계에서 정리해야 한다.
