# R&D core vs scope drift

## 분류 기준

- `KEEP_RND_CORE`: 현재 독립 R&D 실행에 직접 필요
- `REWRITE_AS_RND_ONLY`: 유지하지만 제품 연동 전제를 제거해야 함
- `ARCHIVE_AS_SCOPE_DRIFT`: 현재 범위 밖인 역사적 산출물
- `DELETE_IF_DUPLICATE`: 중복 생성물이지만 이번 단계에서는 삭제 대신 후보로만 기록

## 분류 표

| path | classification | 근거 |
| --- | --- | --- |
| `C:/dev/wellnessbox-rnd/docs/context/master_context.md` | `KEEP_RND_CORE` | 최상위 기준 문서 |
| `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf` | `KEEP_RND_CORE` | 원문 기준 문서 |
| `C:/dev/wellnessbox-rnd/apps/inference_api/` | `KEEP_RND_CORE` | 독립 inference API |
| `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/` | `KEEP_RND_CORE` | baseline / eval / schema 핵심 코드 |
| `C:/dev/wellnessbox-rnd/data/catalog/` | `KEEP_RND_CORE` | baseline catalog |
| `C:/dev/wellnessbox-rnd/data/rules/` | `KEEP_RND_CORE` | safety rules |
| `C:/dev/wellnessbox-rnd/data/frozen_eval/` | `KEEP_RND_CORE` | frozen eval seed |
| `C:/dev/wellnessbox-rnd/tests/` | `KEEP_RND_CORE` | 회귀 검증 |
| `C:/dev/wellnessbox-rnd/docs/02_eval/` | `KEEP_RND_CORE` | KPI / eval 문서 |
| `C:/dev/wellnessbox-rnd/README.md` | `REWRITE_AS_RND_ONLY` | 제품 연동 설명 제거 필요 |
| `C:/dev/wellnessbox-rnd/PROGRESS.md` | `REWRITE_AS_RND_ONLY` | preview / survey 연동 언급 제거 필요 |
| `C:/dev/wellnessbox-rnd/NEXT_STEPS.md` | `REWRITE_AS_RND_ONLY` | 제품 repo 기준 다음 작업 제거 필요 |
| `C:/dev/wellnessbox-rnd/SESSION_HANDOFF.md` | `REWRITE_AS_RND_ONLY` | integration 중심 handoff 제거 필요 |
| `C:/dev/wellnessbox-rnd/docs/01_architecture/` | `REWRITE_AS_RND_ONLY` | 특정 제품 repo 전제를 generic boundary 로 바꿔야 함 |
| `C:/dev/wellnessbox-rnd/docs/99_governance/` | `REWRITE_AS_RND_ONLY` | integration 다음 단계 전제 제거 필요 |
| `C:/dev/wellnessbox-rnd/docs/03_integration/` | `ARCHIVE_AS_SCOPE_DRIFT` | 제품 연동 문서 묶음 |
| `C:/dev/wellnessbox-rnd/docs/00_discovery/` | `ARCHIVE_AS_SCOPE_DRIFT` | `wellnessbox` 탐색 결과, 현재 실행 기준 아님 |
| `C:/dev/wellnessbox-rnd/docs/00_migration/` | `ARCHIVE_AS_SCOPE_DRIFT` | split/migration 역사 문서 |
| `C:/dev/wellnessbox-rnd/docs/legacy_from_wellnessbox/` | `ARCHIVE_AS_SCOPE_DRIFT` | `wellnessbox` 유래 legacy 문서 |
| `C:/dev/wellnessbox-rnd/docs/imported/wellnessbox/` | `ARCHIVE_AS_SCOPE_DRIFT` | imported legacy 문서 |
| `C:/dev/wellnessbox-rnd/docs/03_integration/openapi.inference_api.json` | `DELETE_IF_DUPLICATE` | FastAPI runtime schema에서 재생성 가능한 스냅샷. 이번 단계에서는 삭제하지 않음 |

## 추정 메모

- `docs/imported/wellnessbox/` 는 현재 tree 에 존재하므로 archive 범주로 본다.
- `docs/legacy_from_wellnessbox/` 와 `docs/imported/wellnessbox/` 는 참고 가치는 있지만 현재 source of truth 가 아니다.
- `C:/dev/wellnessbox-rnd/src/`, `C:/dev/wellnessbox-rnd/apps/`, `C:/dev/wellnessbox-rnd/tests/`, `C:/dev/wellnessbox-rnd/data/`, `C:/dev/wellnessbox-rnd/scripts/` 범위에서는 `wellnessbox` 특정 파일 경로를 직접 참조하는 런타임 코드는 찾지 못했다.
- 남아 있는 `survey`, `chat` 같은 용어는 현재 코드에서 generic self-report 입력 또는 optional explanation KPI proxy 수준으로 보이며, 특정 제품 파일 경로 의존성은 아니다.
