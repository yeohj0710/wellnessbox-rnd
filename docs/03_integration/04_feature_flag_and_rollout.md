# feature flag / rollout 계획

## 기본 방향

1차 rollout 은 `wellnessbox` 내부에서 flag 로 제어한다. `wellnessbox-rnd` 는 stateless API 로 동작하고, 배포 여부 판단은 호출자인 `wellnessbox` 가 가진다.

## 권장 flag 목록

| flag | 기본값 | 설명 |
| --- | --- | --- |
| `WB_RND_PREVIEW_ENABLED` | `false` | dev-only preview route/page 활성화 |
| `WB_RND_RECOMMEND_ENABLED` | `false` | `/survey` 에서 RND 추천 호출 활성화 |
| `WB_RND_RECOMMEND_SHADOW_MODE` | `true` | 사용자 결과는 legacy, 서버에서는 RND 동시 호출 |
| `WB_RND_RECOMMEND_TIMEOUT_MS` | `4000` | hard timeout |
| `WB_RND_RECOMMEND_ROLLOUT_PERCENT` | `0` | 샘플링 비율 |
| `WB_RND_CHAT_ENABLED` | `false` | `/api/chat` 계열 연동 |
| `WB_RND_CHAT_TIMEOUT_MS` | `8000` | chat helper timeout |
| `WB_RND_NHIS_SUMMARY_ENABLED` | `false` | NHIS AI summary 연동 |
| `WB_RND_SERVICE_BASE_URL` | 없음 | `wellnessbox-rnd` base URL |
| `WB_RND_SERVICE_TOKEN` | 없음 | 서버 간 인증 토큰 |

## rollout 단계

### Phase 0

- 계약 문서와 OpenAPI 고정
- `wellnessbox-rnd` health/recommend API 확인
- dev-only preview route 로 서버 연동 확인 가능

### Phase 1

- `wellnessbox` 서버에서 shadow call 만 수행
- 브라우저에는 기존 결과만 표시
- 로그로 latency, mismatch, blocked rate 측정

### Phase 2

- 내부 운영자 또는 admin/debug 세션만 RND 결과 표시
- fallback 은 계속 활성 상태 유지

### Phase 3

- 일반 `/survey` 세션 중 일부 비율만 RND 결과 사용
- 권장 시작값: 5%
- mismatch, fallback, timeout 수치 확인

### Phase 4

- `/survey` 기본값을 RND 결과로 전환
- legacy engine 은 fallback 전용으로 유지

### Phase 5

- NHIS summary enrichment 연동
- fetch 본문은 기존 로직 유지

### Phase 6

- `/api/chat` planner/helper 를 thin interface 로 전환

## rollout 판단 기준

| 항목 | 진행 기준 | 중단 기준 |
| --- | --- | --- |
| survey timeout rate | 1% 미만 | 5% 초과 |
| survey fallback rate | 3% 미만 | 10% 초과 |
| blocked decision rate | 도메인 기대 범위 내 | 급격한 증가 |
| p95 latency | 4초 이하 | 6초 초과 |
| 내부 QA mismatch | 허용 가능한 범위 | 핵심 시나리오 다수 불일치 |

## 샘플링 기준

- 사용자 ID 또는 device/session ID 해시 기반 고정 샘플링
- 같은 사용자는 같은 rollout bucket 에 남게 한다
- debug/admin override 는 별도 허용

## shadow mode 기록 원칙

- legacy result 와 RND result 를 별도 저장 또는 로그 비교
- 사용자 화면에는 legacy result 만 노출
- 차이는 QA 문서 또는 운영 대시보드에서만 확인

## 복구 전략

- 모든 RND 호출은 flag off 한 번으로 즉시 차단 가능해야 한다
- timeout 값은 재배포 없이 env 로 조정 가능해야 한다
- rollout percent 는 0 으로 즉시 되돌릴 수 있어야 한다
