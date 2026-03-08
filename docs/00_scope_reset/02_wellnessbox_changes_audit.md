# wellnessbox 변경분 감사

## 원칙

- 아래 파일들은 현재 목표 기준으로 out-of-scope 이다.
- 이번 단계에서는 실제 revert 하지 않는다.
- 참조 관계가 좁고 고립되어 있어도 실제 revert 는 다음 승인 단계에서만 검토한다.

## 감사 표

| path | why it was added | why it is now out-of-scope | safe to revert? | recommended action |
| --- | --- | --- | --- | --- |
| `C:/dev/wellnessbox/app/(dev)/rnd-preview/page.tsx` | dev-only preview 진입점 추가 | 제품 repo 연동 자체가 현재 범위 밖 | yes | `REVERT_CANDIDATE`, 실제 revert 는 보류 |
| `C:/dev/wellnessbox/app/(dev)/rnd-preview/rnd-preview-client.tsx` | raw JSON preview UI 추가 | preview UI 는 R&D 단독 트랙에 불필요 | yes | `REVERT_CANDIDATE`, 실제 revert 는 보류 |
| `C:/dev/wellnessbox/app/api/internal/rnd/recommend-preview/route.ts` | preview proxy route 추가 | 제품 내부 proxy route 는 현재 범위 밖 | yes | `REVERT_CANDIDATE`, 실제 revert 는 보류 |
| `C:/dev/wellnessbox/lib/server/wb-rnd-recommend-preview-route.ts` | preview route orchestration helper 추가 | 제품 repo 전용 glue code | yes | `REVERT_CANDIDATE`, 실제 revert 는 보류 |
| `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts` | `wellnessbox-rnd` 호출 helper 추가 | 제품 연동 helper 자체가 현재 범위 밖 | yes | `REVERT_CANDIDATE`, 실제 revert 는 보류 |
| `C:/dev/wellnessbox/scripts/qa/check-rnd-recommend-preview.cts` | preview smoke check 추가 | 제품 연동 smoke check 는 현재 범위 밖 | yes | `REVERT_CANDIDATE`, 실제 revert 는 보류 |
| `C:/dev/wellnessbox/package.json` 의 `qa:rnd:preview-route` script | preview smoke script 실행용 | 제품 repo 연동 실행 entry 는 현재 범위 밖 | yes | script 제거 후보로만 기록 |

## 근거

참조 검색 기준:

- `C:/dev/wellnessbox/package.json`
- `C:/dev/wellnessbox/app/(dev)/rnd-preview/page.tsx`
- `C:/dev/wellnessbox/app/(dev)/rnd-preview/rnd-preview-client.tsx`
- `C:/dev/wellnessbox/app/api/internal/rnd/recommend-preview/route.ts`
- `C:/dev/wellnessbox/lib/server/wb-rnd-recommend-preview-route.ts`
- `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts`
- `C:/dev/wellnessbox/scripts/qa/check-rnd-recommend-preview.cts`

## 판단 메모

- 위 파일들은 `rg` 기준 서로만 좁게 참조하고 있어 고립도는 높다.
- 다만 이번 단계에서는 실제 revert 를 하지 않는다.
