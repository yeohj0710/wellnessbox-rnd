# rnd owned by wellnessbox rnd

기준 문서: `C:/dev/wellnessbox-rnd/docs/context/master_context.md`

## 기준 선언

- 연구개발의 1차 기준 문서는 오직 `C:/dev/wellnessbox-rnd/docs/context/master_context.md`다.
- 앞으로 R&D 관점의 신규 설계/문서/평가/실험 기록은 모두 `wellnessbox-rnd`에만 작성한다.
- `wellnessbox`에는 R&D 원본을 복제하지 않는다.

## `wellnessbox-rnd` 소유 영역

### 기준 문서와 탐색/이관 문서

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`
- `C:/dev/wellnessbox-rnd/docs/00_discovery/`
- `C:/dev/wellnessbox-rnd/docs/00_migration/`

### `wellnessbox`에서 이주된 legacy 문서

- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/agents/`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/engineering/`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/scenarios/`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/wellness_engine/`

포함 예시:

- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/agents/AGENTS_wellnessbox_legacy.md`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/agents/AGENT_PRECHECK.md`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/agents/API_GUARD_MAP.md`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/scenarios/ai-chat-agent-handoff.md`
- `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/engineering/agent-preflight.md`

### 연구용 지식 자산

- `C:/dev/wellnessbox-rnd/data/knowledge/supplements/`

포함 파일:

- `mfds_supplement_functions.md`
- `supplement_categories.md`
- `supplement_overdose_and_drug_interactions_public.md`
- `supplement_overdose_and_drug_interactions_expert.md`

### legacy code / tooling 보관소

- `C:/dev/wellnessbox-rnd/legacy_code/agent_ops/scripts/agent/`
- `C:/dev/wellnessbox-rnd/legacy_code/agent_ops/scripts/lib/skill-catalog.cts`
- `C:/dev/wellnessbox-rnd/legacy_code/rag_tools/scripts/`

### 앞으로 `wellnessbox-rnd`에만 추가되어야 할 것

- R&D 설계 문서
- KPI/평가 기준 문서
- prompt SSOT
- dataset 정의, synthetic data 생성 규칙, frozen eval
- agent 설계/운영 문서
- 실험 메모, 구현 메모, 회고, handoff
- R&D용 스크립트와 실행 결과 리포트

## 아직 `wellnessbox-rnd`로 완전히 안 넘어온 큰 묶음

- `C:/dev/wellnessbox/docs/rnd/`
- `C:/dev/wellnessbox/docs/rnd_impl/`
- `C:/dev/wellnessbox/lib/rnd/`
- `C:/dev/wellnessbox/scripts/rnd/`
- `C:/dev/wellnessbox/app/agent-playground/`
- `C:/dev/wellnessbox/app/api/rag/`

이 묶음들은 ownership 기준으로는 장기적으로 `wellnessbox-rnd` 소유가 맞다. 다만 현재는 경계 계약과 런타임 영향 때문에 단계적으로 이관해야 한다.
