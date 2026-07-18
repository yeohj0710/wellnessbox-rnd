# TIPS 원계획 완전 구현 마스터 로드맵

작성: 2026-07-15 (Claude). 근거: `docs/context/master_context.md`, `docs/plans/2026-07-15-original-plan-completion-program.md`(120-요구사항 원장), `docs/original_plan/COMPLETION_STATUS.md`, `docs/tips/CURRENT_REPO_AUDIT.md`, `docs/tips/interim/BLOCKERS.md`, 양 저장소 전수조사.

> 이 문서는 기존 120-요구사항 완료 프로그램을 **대체하지 않는다**. 원장(OP-001~120)과 증거 감사 체계를 그대로 유지하면서, 남은 96건을 어떤 순서·묶음·승인 체크포인트로 소진할지 정의하는 상위 실행 계획이다. 루프 실행 규칙은 `AGENTS.md`를 따른다.

---

## 1. 현재 상태 진단 (2026-07-15)

### 1.1 왜 "껍데기"로 보이는가 — 검증된 원인

1. **프로덕션 `/tips`는 연구 엔진이 아니라 시뮬레이션 랩이다.**
   - `/tips` → `InterimUserConsole` → `POST /api/tips/lab` → `wellnessbox` 저장소 내장 TypeScript 엔진(`lib/tips/proxy-model-engine.ts` 로지스틱회귀 + `lib/server/tips-lab/*`)이 **합성 proxy-gold 데이터**를 재채점한다.
   - 모든 응답에 `mode: PROXY_GOLD_SIMULATION`, `realResearchComplete: false`가 박혀 있다.
2. **진짜 연구 엔진(`wellnessbox-rnd` FastAPI)은 어디에도 배포되어 있지 않다.**
   - 배포 대상·프로덕션 URL 없음. Vercel에 `WB_RND_*` 환경변수 없음.
   - `/api/tips`, `/api/tips/profile`, `/api/tips/agent*`, `/api/tips/connector` 프록시 코드는 존재하나 `WB_RND_INTERIM_ENABLED` 미설정으로 전부 404. `/admin/tips`, `/pharm/tips`도 같은 이유로 죽어 있다.
3. **원장 기준 이행률 24/120.** A(증거 거버넌스) 10/10, B(입력·동의 계약) 10/10, C(Data Lake) 2/10, D(안전엔진) 2/10, **E~L(추천·PRO·최적화·Closed-loop·상담·기기연동·프로덕션 통합·배포감사) 전부 0/10.**
4. **실제 연구 장치가 없다.** 참여자 등록·적격성 심사·무작위배정 부재, 실사용자 PRO 수집 부재(PRO 코호트는 브라우저 localStorage 합성), `ingest_pro`/`ingest_device`/ADR 서버 핸들러는 `{accepted:true, simulation:true}` 고정 반환, follow-up work item은 DB에 쓰이지만 소비하는 스케줄러·알림(푸시/SMS/카카오톡)이 없다.
5. **KPI 7종 "통과"는 전부 합성 시뮬레이션 안에서의 통과다.** KPI-1 100%는 라벨을 생성한 동일 ontology를 모델이 재현한 결과로, 문서 스스로 "임상 정확도 아님"을 명시한다.

### 1.2 이미 잘 되어 있는 것 (버리면 안 되는 자산)

- **거버넌스 체계**: 요구사항 manifest + 증거 감사기 + CI 게이트 + 자동 완료 보고서. 완료 위장이 구조적으로 불가능한 체계가 이미 작동 중.
- **R&D 결정론 런타임**: `/v1/recommend` — intake 정규화, 구조화 안전엔진(알레르기/응급위험/용량), 후보 생성, 효능 점수, 최적화, 설명 생성. 입력 계약(B그룹)은 동의 스코프·정규화 해시까지 완성.
- **frozen eval 256케이스 + KPI 계산기 7종** (`src/wellnessbox_rnd/metrics/`), 재현 가능 baseline.
- **서비스 측 자산**: TipsLab 상태기계(10-state FSM, 전이·사후조건 검증), Prisma `TipsLabSession/Event/Artifact/WorkItem` 영속화, PSQI/ISI/PSS-10 채점, 프로필 어댑터 계약(양 저장소 byte-identical 스냅샷 + QA).
- **배포 준비물**: Dockerfile, `scripts/start_inference_api.py`, `docs/deployment/staging_api.md`, staging smoke 스크립트.

### 1.3 지금 돌고 있는 작업 (충돌 주의)

- Codex가 OP-021/022(Data Lake 계보: `interim/data_lake.py`, `interim/store.py`, lineage smoke) 루프 진행 중 — 양 저장소에 uncommitted 변경 존재. **이 파일들을 건드리는 작업은 Codex 루프 종료·커밋 후 시작한다.**
- untracked `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` (평가자 UI 개편 계획, 미착수).

---

## 2. "완전 구현"의 정의 (Definition of Done)

원장 판정 규칙을 그대로 사용한다:

1. **비외부 요구사항 전건**이 요구 단계(IMPLEMENTED/INTEGRATED/OPERATED)를 증거와 함께 충족.
2. **EXTERNAL 항목**은 책임자·필요 입력·교체 계약·차단 사유가 기록되고, 동일 계약의 대체 증거가 존재 (OP-119).
3. **프로덕션에서** R&D FastAPI와 wellnessbox가 실제로 왕복하고(OP-105), `/tips`가 R&D 실행 결과와 로컬 스냅샷을 구분 표시하며(OP-104), 저장 사후조건을 재조회할 수 있다.
4. KPI 7종이 **실 파이프라인 위에서 측정 가능**하고, 합성/실데이터가 `data_class`로 구분된다 (OP-060, OP-098).
5. 독립 최종 감사가 100% 완료를 증명 (OP-120).

---

## 3. 실행 원칙

- **기존 루프 체계 유지**: 1 세션 = 1 bounded loop, 2-요구사항 슬라이스, 종료 시 PROGRESS/NEXT_STEPS/SESSION_HANDOFF 갱신, manifest 증거 등록 → 감사 → 보고서 재생성.
- **결정론 우선**: 안전은 구조화 규칙, closed-loop은 상태기계, 상담은 bounded RAG + verifier. 학습모델 트랙(training gate NO-GO)은 KPI 경로와 분리 유지 — 전체 구현의 전제조건이 아니다.
- **frozen-eval 비교가능성 보존**: 모든 루프에서 7지표 delta 보고 (원칙적으로 0, 의도된 변경만 예외).
- **UI보다 계약·증거 먼저**: 화면 개편(evaluator UI overhaul)은 K그룹 통합 시점에 함께 처리.
- **사람 개입 최소화**: 아래 §6의 승인 체크포인트에서만 사람이 결정. 나머지는 AI 루프가 자율 진행.

---

## 4. 단계별 로드맵 (Phase 0~9)

각 Phase는 원장 그룹과 1:1이며, 예상 루프 수는 현재 관측 속도(2-요구사항/루프) 기준이다.

### Phase 0 — 안정화 (사람 개입 불필요, 즉시)
- Codex의 OP-021/022 루프 완료 대기 → 양 저장소 커밋/푸시 확인.
- 이 로드맵 문서를 NEXT_STEPS.md 상단에서 참조하도록 갱신 (Codex 루프 종료 후).

### Phase 1 — C그룹 마무리: Data Lake와 근거 계보 (OP-023~030, 4루프)
- 이미 큐에 있음: OP-023/024(원문-규칙-추천 계보 + 지식 유효기간·라이선스), OP-025/026(로그 분리 + 실행 identity), OP-027/028(idempotency + 삭제·정정), OP-029/030(replay API + 서비스 화면 조회).
- C그룹의 OPERATED 판정은 K그룹 배포 이후에만 최종 성립 → 우선 IMPLEMENTED/INTEGRATED까지 올리고 OPERATED 증거는 Phase 8에서 일괄 회수.

### Phase 2 — D그룹: 안전 검증 엔진 완성 (OP-033~038, OP-040, 4루프)
- 임신·수유 규칙 분리, 질환별 금기 확대, 약물-성분 상호작용 근거 ID 연결, 성분 중복·합산 용량, 단위 변환 후 상한 비교(불명확 시 보수적 차단), 규칙 버전·적용시각 응답 포함.
- OP-039(hard FN 0 외부 검증)는 EXTERNAL — §6 게이트로 이관.
- KPI-5(레퍼런스 정확도 95%) 및 KPI-6(ADR ≤5건/년)의 직접 담당 구간.

### Phase 3 — E그룹: 추천 후보와 효과 점수 (OP-041~050, 5루프)
- 핵심: **서비스 성분 식별자 ↔ R&D canonical ingredient 변환표 버전 관리(OP-041)** — 이것이 KPI-1 측정의 전제.
- 후보 prior+근거 등록, 증상·검사·생활습관의 점수 반영, 기기 관측값의 수치 반영, 차단 전/후 후보 보존, 추천 이유 분해(입력 신호·점수 항목·근거 ID), 불확실성 정량화, deterministic fallback, replay 비교, 실상품 후보 변환 계약 테스트.

### Phase 4 — F그룹: PRO 효과 수치화 (OP-051~060, 5루프)
- PSQI/ISI/PSS-10 채점 버전 고정(서비스 TS 구현과 R&D Python 구현의 **단일 소스 통일** 필요 — 현재 이중 구현), z-score/백분위 변환 고정, 복용 전/2주/4주/중단 PRO 이벤트 저장, 순응도·이상사례 반영, 개인/집단 개선도 분리, 신뢰구간, plan ID 계보, **`data_class`만 바꿔 실데이터 처리(OP-060)** — 실연구 전환의 관문.
- KPI-2(개선도 >0pp) 담당 구간.

### Phase 5 — G그룹: 다중제약 최적화와 실제 상품 (OP-061~070, 5루프)
- 실판매 상품(성분·함량·가격·재고·제형)을 읽는 서비스 계약 → 상품을 성분 조합 후보로 변환 → 예산·복용수 제약 → Top-k와 미선택 사유 → 재고 변경 시 재계산 → 장바구니 후보 변환(승인 전 주문 생성 금지, OP-070).
- wellnessbox의 실제 Product/재고 모델과 처음으로 결합되는 구간 — 서비스 저장소 변경 비중이 커진다.

### Phase 6 — H그룹: Closed-loop 상태기계와 후속 실행 (OP-071~080, 5루프)
- 서비스 TipsLab FSM과 R&D `next_action_state_machine`의 **단일 계약 통합(OP-071)**, 실행 순서 강제, **실제 업무 큐 + CronJob 재평가(OP-073/074)** — 현재 "쓰기만 하고 소비 안 되는" work item에 소비자를 붙이는 구간(Vercel cron 또는 R&D APScheduler, §6 결정 필요), 알림 채널(푸시/카카오톡) 연결, 이상사례 즉시 중단, fail-closed 처리, 약사 검토 사후조건, E2E 전이 검증, 주문 상태 변경과의 명시적 분리.
- KPI-3(다음 행동 정확도 80%) 담당 구간.

### Phase 7 — I그룹(상담)·J그룹(기기 연동) (OP-081~100, 8루프, 상호 독립 — 병렬 가능)
- I: passage 수집, 의도 추출, bounded RAG, 근거 ID·유효일·불확실성 포함 답변, verifier, 응급 우선, 세션 저장, 서비스 채팅 얇은 어댑터, provider 장애 fallback, frozen QA + E2E. KPI-4(상담 정확도 91%) 담당.
- J: Apple Health/범용 CSV·CGM·유전자 정규화, 동의 게이트, 부분 성공 응답, 파일 해시 계보, 점수 실반영, `data_class` 구분, 중복 수신 차단, W/C/G 성공률 재계산. KPI-7(연동율 90%) 담당.

### Phase 8 — K그룹: 프로덕션 통합 (OP-101~110, 6루프 + 사람 승인 2회)
1. **OP-101 [사람 결정 필요]** R&D FastAPI 배포 대상·영속 DB·내부 인증 확정 (§6-D1).
2. OP-102 배포(health/추천/상태기계/기기/상담) → OP-103 Vercel `WB_RND_*` 등록 **[사람 승인: 프로덕션 환경변수]**.
3. OP-104 `/tips`가 R&D 실행 결과와 로컬 스냅샷 결과를 구분 표시 — 여기서 `/tips`가 "껍데기"에서 "진짜 연구 화면"으로 바뀐다. evaluator UI overhaul 계획도 이 시점에 흡수.
4. OP-105 프로필 저장·추천 왕복 검증 → OP-106 약사 검토 화면 실연결 → OP-107 관리자 화면 실API → OP-108 실상품 연결 → OP-109 승인 후 createOrder만 주문 변경 → OP-110 소분·배송 상태 읽기 전용 환류.

### Phase 9 — L그룹: 배포·보안·최종 감사 (OP-111~120, 5루프)
- 권한 회귀, 개인정보 최소수집·가명처리·마스킹, 장애 주입(timeout/retry/circuit breaker), OpenAPI↔TS 계약 CI 차단, 양 저장소 전체 검사, 배포 후 health/alias 확인, 실브라우저 3역할 경로 재현, 전 비외부 항목 운영 증거 연결, 외부 항목 기록(OP-119), 독립 최종 감사(OP-120).

**총 예상: 약 47~52 bounded loop.** 2026-07-15 하루에 8루프가 소화된 관측 속도 기준, 외부 게이트를 제외한 AI 실행분은 **연속 실행 시 약 1~2주** 분량.

---

## 5. 실연구 전환 트랙 (원장 외 — 시뮬레이션을 실데이터로 교체)

원장은 시스템 완성을 다루고, 아래는 **연구 자체의 실화(實化)**다. `docs/tips/interim/BLOCKERS.md`의 외부 게이트와 1:1 대응:

| 게이트 | 대응 KPI | AI가 준비하는 것 | 사람이 하는 것 |
|---|---|---|---|
| 약사 독립 라벨 | KPI-1, 5 | 라벨링 매뉴얼·케이스 패키지·수집 UI(약사 콘솔) | 약사 섭외·계약 |
| 실사용자 PRO/outcome | KPI-2 | OP-053/057/060 완성, 동의·설문 플로우, `data_class=production` 전환 스위치 | 파일럿 사용자 모집 승인 |
| 외부 블라인드 행동/답변 테스트 | KPI-3, 4 | 테스트 프로토콜·채점 하네스 export | 외부 평가자 확보 |
| 12개월 실ADR 운영 | KPI-6 | ADR 신고 UI·집계·보고 자동화 | 운영 개시 승인 |
| 실기기 세션 | KPI-7 | 업로드 포맷·파서·연동율 집계 (J그룹) | 기기/데이터 제공 사용자 확보 |
| 보안·법률·인증 검토 | 전체 | 증거 패키지 자동 생성 (L그룹) | 외부 기관 의뢰 |

각 게이트는 Phase 4~9 완료 시 "AI 준비물"이 자동으로 갖춰지도록 원장 항목에 이미 반영되어 있다. `real_research_completion=true`와 시뮬레이션 배지 제거는 전 게이트 통과 전 금지 (기존 규칙 유지).

---

## 6. 사람 승인 체크포인트 (이것만 결정하면 나머지는 자동)

- **D1. R&D FastAPI 배포 대상** (Phase 8 진입 전, 가장 긴 리드타임): 후보 — 컨테이너 호스트(Fly.io/Cloud Run/경량 VM) 또는 기존 사용 이력이 있는 Kakao/NAVER 클라우드. Dockerfile·시작 스크립트·smoke는 준비 완료. 월 비용 승인 포함.
- **D2. R&D 영속 DB**: 현재 SQLite `InterimStore` → 프로덕션은 관리형 Postgres 권장(서비스와 동일 벤더 또는 동일 인스턴스 별도 스키마). OP-101과 함께 결정.
- **D3. Vercel `WB_RND_*` 프로덕션 환경변수 등록** (OP-103): 값 자체는 AI가 준비, 등록 클릭만 사람.
- **D4. 스케줄러 방식** (Phase 6): Vercel cron(서비스 측) vs R&D 프로세스 내 APScheduler. 권장: R&D 측 소유(연구 이벤트 주권) + 서비스는 알림 발송만.
- **D5. 알림 채널**: 기존 SolAPI(SMS)/web-push 재사용 vs 카카오톡 알림톡 신규 계약.
- **D6. 실사용자 파일럿 개시** (§5): 모집 규모·시점.
- **D7. 외부 기관 의뢰** (§5): 약사·평가자·법률/인증.

---

## 7. 리스크와 완화

1. **77건 상시 red 테스트가 신규 회귀를 가린다** → Phase 0 직후 luoop 하나를 할애해 known-failure를 skip 마커/별도 마커로 격리하고 "green 기준선"을 만든다 (기대값 조작 금지, 마커 분리만).
2. **PRO 채점 이중 구현** (서비스 TS vs R&D Python) → Phase 4에서 R&D를 단일 소스로 정하고 서비스는 API 소비 또는 생성 스냅샷만 사용 (ADR-005 정신 유지).
3. **성분 식별자 불일치** (KPI-1 측정 실패 위험) → OP-041 변환표를 E그룹 최우선으로.
4. **학습모델 트랙 혼입** → training gate NO-GO 유지, replay-only 경계 감사 지속. 전체 구현은 deterministic 경로만으로 성립.
5. **Codex 병행 작업 충돌** → 루프 시작 전 `git status` 확인, uncommitted 파일과 겹치는 OP는 뒤로 미룬다.
6. **원계획 PDF 이중 해시 혼동** (PDF 해시 `31291e6f…` vs 전달 패키지 manifest 해시 `2a430ac5…`) → 감사 문서에 두 객체가 별개임을 명시하는 각주 추가 (1회성).

---

## 8. 다음 세션 킥오프 프롬프트 (복붙용)

```text
C:\dev\wellnessbox-rnd 에서 작업한다. AGENTS.md 실행 계약을 따른다.
상위 실행 계획은 docs/plans/2026-07-15-tips-full-implementation-roadmap.md 이고,
과제 원장은 docs/plans/2026-07-15-original-plan-completion-program.md 다.
git status로 다른 에이전트의 uncommitted 작업과 겹치지 않는지 먼저 확인하라.
NEXT_STEPS.md의 최우선 미완 OP 두 개(현재 기준 OP-023, OP-024)를 한 개의 bounded loop로 구현하고,
manifest 증거 등록 → 감사 → 완료 보고서 재생성 → frozen eval 델타 0 확인까지 마친 뒤
PROGRESS.md / NEXT_STEPS.md / SESSION_HANDOFF.md를 갱신하라.
```

---

## 9. 이 문서의 유지 규칙

- Phase 완료 시 §4 해당 항목에 완료 표시와 완료 일자를 기록한다.
- 원장(`…original-plan-completion-program.md`)과 상태가 어긋나면 **원장이 우선**이며 이 문서를 원장에 맞춘다.
- §6 결정이 내려지면 결정 내용과 일자를 해당 항목에 인라인 기록한다.
