# archive 또는 rewrite 대상 파일

## REWRITE_AS_RND_ONLY

| path | 조치 |
| --- | --- |
| `C:/dev/wellnessbox-rnd/README.md` | 독립 R&D repo 설명으로 재작성 |
| `C:/dev/wellnessbox-rnd/PROGRESS.md` | 제품 연동 다음 단계 제거 |
| `C:/dev/wellnessbox-rnd/NEXT_STEPS.md` | clean R&D plan 으로 재작성 |
| `C:/dev/wellnessbox-rnd/SESSION_HANDOFF.md` | 제품 통합 handoff 제거 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/00_target_architecture.md` | generic external boundary 로 수정 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/01_service_boundary.md` | 제품 repo 전제 제거 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/02_data_flow_and_state_machine.md` | generic intake/state machine 로 수정 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/03_deployment_topology.md` | 독립 단일 머신 R&D 기준으로 수정 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/05_initial_repo_structure.md` | 제품 연결점 제거 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/06_initial_backlog.md` | clean R&D backlog 로 수정 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/adr/adr-001-hard-split-web-vs-rnd.md` | standalone R&D repo 결정으로 재서술 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/adr/adr-005-no-training-inside-nextjs.md` | product repo coupling 금지 결정으로 재서술 |
| `C:/dev/wellnessbox-rnd/docs/99_governance/00_decisions_so_far.md` | R&D 단독 기준으로 수정 |
| `C:/dev/wellnessbox-rnd/docs/99_governance/01_open_questions.md` | integration 질문 제거 |
| `C:/dev/wellnessbox-rnd/docs/99_governance/02_priority_backlog.md` | 독립 R&D 우선순위로 수정 |

## ARCHIVE_AS_SCOPE_DRIFT

| path | 이유 |
| --- | --- |
| `C:/dev/wellnessbox-rnd/docs/03_integration/` | 제품 연동 문서 묶음 |
| `C:/dev/wellnessbox-rnd/docs/00_discovery/` | `wellnessbox` 현황 탐색 결과 |
| `C:/dev/wellnessbox-rnd/docs/00_migration/` | split / migration 역사 문서 |
| `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/` | legacy archive |
| `C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/` | imported legacy archive |

## DELETE_IF_DUPLICATE 후보

| path | 이유 | 이번 단계 처리 |
| --- | --- | --- |
| `C:/dev/wellnessbox-rnd/docs/03_integration/openapi.inference_api.json` | runtime schema 에서 재생성 가능한 generated snapshot | 삭제하지 않고 후보로만 기록 |

## 비고

- archive 는 삭제가 아니라 “현재 실행 기준 아님”을 뜻한다.
- legacy 문서는 참고용으로만 남긴다.
