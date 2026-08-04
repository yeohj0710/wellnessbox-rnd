# NEXT_STEPS

## 2026-08-04 KPI-1 마지막 2건 선택

다음 입력 파일은 `data/original_plan/kpi/review_handoff/replacement_round/second_replacement/kpi1_second_replacement_final_review_package.zip`이다. CSV 두 행에는 참조안 A, 독립 2차 의견 B, 권고안 B가 입력돼 있다. 각 행의 결정과 시각을 기록한 뒤 `MAKE_RETURN_ZIP.cmd`를 실행한다.

반환 ZIP을 가져온 뒤 기존 63건과 함께 워크벤치에 원자적으로 적용한다. 두 건이 확정되기 전에는 기존 63건만 부분 적용하거나 봉인하지 않는다. 스케줄러와 주기 확인은 사용하지 않는다.

## 2026-08-04 완료된 65건 최종 입력

65건 입력은 검증·보존을 마쳤다. 결과는 `ACCEPT` 51건, `EDIT` 12건, `REJECT` 2건이다. 원래 `kpi_replacement_final_review_package.zip`은 과거 입력이므로 다시 사용하지 않는다.

## 2026-08-04 완료된 Claude 재처리

`kpi_replacement_claude_retry_package.zip`의 Claude 응답 검증과 KPI-4 OpenAI 2차 의견 연결은 완료됐다. 기존 `kpi_replacement_input_package.zip`과 Claude 재처리 패키지는 과거 입력이므로 다시 사용하지 않는다.

1. KPI-1 추가 교체 2건의 최종 선택 자료를 가져온다.
2. 추가 2건과 기존 63건을 워크벤치에 원자적으로 적용한다.
3. 각 지표가 다시 100개 유효 사례가 되면 무결성 감사 후 봉인한다.
4. 새 봉인 뒤에만 `measurement_environment: research_phase_internal_measurement`로 연구 단계 내부 측정을 실행한다.

전체 pytest 기준선은 실제 실행 결과 90건 실패다. `.pytest_cache/v/cache/lastfailed` 항목 수를 기준선으로 사용하지 않는다.

## 현재 최우선 순서 (2026-08-01)

1. `data/original_plan/kpi/ai_review_requests/kpi3_claude_review_request_v1.json` 하나만 새 Claude 작업에 전달해 독립 2차 의견 100건을 받는다. Codex 1차 초안 100건은 이미 가져왔다.
2. `kpi4_claude_primary_request_v1.json` 하나만 새 Claude 작업에 전달해 독립 1차 초안 100건을 받은 뒤, 준비된 Codex 응답 100건을 독립 2차 의견으로 가져온다.
3. 사람은 불일치·위험 표시·결정론적 합의 표본만 상세 검토하고, 남은 AI 합의는 직접 일괄 승인한다. AI가 사람의 최종 선택을 대신하지 않는다.
4. KPI-1·5의 과거 봉인은 `discard-status`로 읽기 전용 확인한 뒤, 사람이 사유와 폐기자를 확인하여 정식 폐기한다.

## 2026-08-01 최소 사람 검토 경로의 다음 단계

1. **사람이 KPI-1·5 과속 봉인을 정식 폐기한다.** 먼저 `python scripts/run_answer_key_workbench.py discard-status --indicator KPI-1`과 KPI-5 명령으로 후보 해시와 `formal_disposal_count: 0`을 확인한다. 그다음 `discard-seal`을 지표별로 실행하고 폐기자·사유·확인 문구를 사람이 직접 입력한다. AI는 폐기 승인을 대신하지 않는다.
2. **KPI-1·5는 준비된 Claude 요청 파일로 2차 의견을 받는다.** `data/original_plan/kpi/ai_review_requests/`의 해당 JSON 하나만 Claude에 전달한다. 저장소나 워크벤치 원본은 전달하지 않는다. 응답은 `validate-ai-response`로 먼저 검사하고 `READY_TO_IMPORT`일 때만 `import-ai-review`로 가져온다.
3. **KPI-3은 Claude 2차 의견을 받고, KPI-4는 Claude 1차 초안을 받는다.** 지표별 Claude 요청 JSON은 이미 준비됐다. KPI-3 응답은 검증 뒤 `import-ai-review`, KPI-4 응답은 검증 뒤 `import-primary-ai-draft`로 가져온다. 그다음 보관 중인 KPI-4 Codex 응답을 2차 의견으로 가져온다.
4. **사람이 필요한 사례만 상세 검토한다.** 지표별로 `minimal-status`를 확인하고 `review-minimal --by <검토자>`를 실행한다. 모든 불일치·위험 플래그와 합의 표본 5건이 대상이다. 표본 수정에 따라 20건 또는 전수로 자동 확대된다. 2차년도 기록은 `pharmacist_candidate_preliminary_safety_review`이며 약사 검토라고 쓰지 않는다.
5. **같은 사람이 나머지 합의안을 최종 승인하거나 거부한다.** `approve-consensus --by <검토자>`에서 정확한 확인 문구를 직접 입력한다. 모두 합의했다면 네 지표의 상세 검토 하한은 합계 20건이고, 지표별 일괄 승인 1회가 추가된다.
6. **감사 PASS 뒤 봉인한다.** KPI-4는 `--system-under-test-id <상담_모듈_ID> --system-under-test-provider-family openai`를 함께 넣는다. 1차 초안 AI가 OpenAI 계열이면 봉인을 거부한다. 그 뒤에만 연구 단계 내부 측정을 실행하고 `measurement_environment: research_phase_internal_measurement`를 기록한다.

현재 유효하게 가져온 AI 응답은 KPI-3 1차 초안 100건이다. 사람 상세 판단과 사람 일괄 승인은 0건이다. KPI-2의 실제 사용자 100명 경로와 3차년도 측정 결정은 그대로이며, KPI-6·7과 H-003 학습 게이트는 건드리지 않는다.

권장 다음 3개 bounded loop는 다음과 같다. (1) 사람이 KPI-1·5 오류 봉인을 정식 폐기하고 패킷만 사용한 외부 AI 응답을 확보한다. (2) 응답을 가져와 사람이 최소 상세 검토·일괄 승인·봉인을 끝낸다. (3) KPI-2 실제 사용자 100명의 전·후 PRO 수집 경로를 시작한다.

## 2026-07-31 KPI 정답지 무결성 게이트 이후 다음 네 단계

1. **사람이 KPI-1·5 오류 봉인을 정식 폐기한다.** 다음 명령을 지표별로 한 줄씩 실행하고 화면의 확인 문구를 직접 입력한다: `python scripts/run_answer_key_workbench.py discard-seal --indicator KPI-1 --by <폐기자> --reason "<폐기 사유>"`. KPI-5도 같은 절차를 따른다. 에이전트가 폐기자나 확인 문구를 대신 입력하지 않는다.
2. **사람이 KPI-1·3·4·5 각 100건을 검토한다.** `review` 명령을 한 줄씩 실행하며 에이전트가 수락·수정·반려를 대신 입력하지 않는다. KPI-3은 9개 행동 중 하나를 검토자가 직접 쓴다.
3. **사람 검토가 끝난 지표만 다시 감사하고 봉인한다.** 감사 PASS와 pending 0건을 확인한다. KPI-4 봉인 때는 `--system-under-test-agent <상담 모듈 계열>`을 입력하며 `drafting_agent=codex`와 다른 제공자 계열이어야 한다.
4. **KPI-2 전·후 PRO 수집 경로를 운영 서비스에 붙인다.** 실제 사용자 100명의 복용 전 PRO와 2주 후 PRO가 필요하다. 이 표본은 합성 자료나 내부 정답지로 대체할 수 없다.

남은 큰 병목은 KPI-1·5 사람 폐기 확인, 사람 판단 400건, 새 봉인 4종, KPI-4 에이전트 분리 증거, 카탈로그 밖 원문 성분 209종, KPI-2 실제 사용자 100명이다.

## 2026-07-31 KPI-3·4 초안 감사 이후 다음 세 반복

1. **KPI-3·4 초안의 독립 출처를 사람이 정한다.** 감사 결과 KPI-3은 엔진이 읽는 `closed_loop_next_action_policy_v1.json`이 그대로 정답이라 정확도가 구조적으로 100%가 되고, KPI-4는 고유 문항이 57개뿐이라 100문항 요건에 미달한다. 출처를 정하기 전에는 두 지표를 확정·봉인하지 않는다. 근거는 `docs/original_plan/KPI_COMPLIANCE_STRATEGY.md`의 "KPI-3·4 초안도 같은 감사에서 탈락했다" 절.
2. **KPI-1·5만 먼저 확정한다.** 이 둘은 독립 참조 코퍼스 기반이라 지금 상태로 유효하다. `python scripts/run_answer_key_workbench.py review --indicator KPI-1 --by <이름>` 을 사람이 직접 실행한다. 한 번에 한 명령씩 실행한다. 전부 Enter로 넘기면 수정률 0%가 기록에 남는다.
3. **KPI-2 전·후 PRO 수집을 운영 서비스에 붙인다.** 경로는 A로 확정됐고(계약 파일 `KPI-2.open_decision.chosen`), 아직 착수되지 않았다. 복용 전 PRO와 2주 후 후속 PRO 흐름을 지금 붙여야 3차년도 측정 시점에 표본이 있다.

KPI-1 67개 / KPI-5 27개인 고유 정답 수에 비해 KPI-3은 9개, KPI-4는 5개다. 이 수치가 유효 표본의 실질이며, 봉인 전에 봐야 할 신호다.

## 2026-07-31 독립 참조 코퍼스 이후 다음 세 반복

1. KPI-1·5 초안 각 100건을 사람이 확정한다. `python scripts/run_answer_key_workbench.py review --indicator KPI-1 --by <이름>` 이며 KPI-5도 같다. 확정이 끝나야 `seal` 로 넘어간다. 봉인 전에는 엔진을 돌리지 않는다.
2. `out_of_catalog_nutrients` 목록을 카탈로그 확장 우선순위로 삼는다. 지금 카탈로그는 12종이라 원문 권장 성분 대부분이 채점에서 빠진다. 여기를 넓히지 않으면 KPI-1 상한이 카탈로그 크기에 묶인다.
3. KPI-3·4 초안도 같은 기준으로 출처 독립성을 감사한다. 두 지표의 초안은 저장소 안의 정책·시나리오 파일에서 나오므로, 그 파일이 엔진의 실행 입력이기도 한지 확인해야 한다.

이번 감사에서 KPI-1 초안의 유효 표본이 100이 아니라 7이었고, KPI-5 초안은 엔진 자신의 규칙 파일이 정답이었다. 두 건 모두 교체했으나 KPI-3·4는 아직 같은 점검을 받지 않았다.

## 2026-07-30 원스텝 실행기 이후 다음 세 반복

1. `research-complete.cmd` 를 실행해 2차년도 세션을 끝까지 수행한다. 12단계를 순서대로 안내하며, 과거 기록은 세지 않으므로 H-002~H-007을 이번 세션에서 다시 해야 한다. 실제 참여자 5명의 자료와 동의 근거만 준비되면 된다.
2. 학습 게이트를 여는 CGM 최종 단계 기하 blocker를 해소한다. 그전까지 6·7단계는 실행 계획만 남기고 건너뛴다. 게이트가 열려야 후보 학습과 교체 판정을 실제 값으로 돌릴 수 있다.
3. 3차년도(2027-01 면허 취득 이후)에 `op039_reviewer_identity_registry_v1.json` 의 `qualification_stage` 를 `licensed_pharmacist` 로 바꾸고 같은 10개 사례를 약사 자격으로 다시 검토한다. 최종 마감은 2027-10이다.

현재 사전 점검은 `READY`, OP-120 감사는 120/120 `READY`다. 다만 두 신호 모두 이번 세션의 사람 판정을 입증하지 않는다. 실행기 기준 현재 진행은 12단계 중 2단계(학습 게이트로 건너뛴 두 단계)뿐이다. OP-039 외부 기관 평가는 연구 종료 후 단계이며 두 신뢰 원장이 0건이라 경로가 닫혀 있다. Ruff 28건은 main 조상 커밋의 기존 부채다.

> 아래 항목은 과거 시점의 기록이다. 과거 항목의 보고서 수와 완료 수치를 현재 우선순위로 사용하지 않는다.

## OP-027/028 이후 다음 bounded loop

1. OP-029/030의 deterministic session replay와 WellnessBox 서비스·UI 조회 연결을 기존 구현, smoke, 커밋과 대조해 두 장문 보고서로 작성한다.
2. OP-031/032의 안전 규칙 우선순위와 구조화 입력 정규화를 검토하고 현재 증거보다 높은 stage를 주장하지 않는다.
3. OP-033/034의 특수집단·질환 안전 규칙과 fail-closed 동작을 같은 기준으로 backfill한다.

2026-07-23 당시 물리 연구보고서는 70개, 유효 연구보고서는 48/120이며 누락·부적합 72개가 남았다. 전체 글자 수는 327,598자였다. completion은 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, OP-120 evidence SHA-256은 `e9d00582015a0ea0581d107eb212601ded346468030004641304c486ddba281d`였다. GitHub Actions `29970576517`이 성공했다. 이 수치는 과거 기록이며 현재 상태가 아니다.

## OP-025/026 이후 다음 bounded loop

1. OP-027/028의 event idempotency와 사용자 데이터 정정·삭제 mutation 이력을 조사해 두 장문 보고서를 작성한다.
2. OP-029/030의 deterministic session replay와 서비스 UI 조회 연결을 같은 기준으로 backfill한다.
3. OP-031/032의 안전 규칙 우선순위와 구조화 입력 정규화를 검토해 현재 단계보다 높이지 않고 보고서를 작성한다.

현재 물리 연구보고서는 68개, 유효 연구보고서는 46/120이며 누락·부적합 74개가 남는다. 전체 글자 수는 316,581자다. completion은 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, OP-120 evidence SHA-256은 `68aaa12d6c0541324fe27f888b9392d30ddff03dcbbf8a432b0ff11a2bca426b`이다. GitHub Actions `29969740776`이 성공했다. 현재 병목은 보고서 74개, required-stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt다.

## OP-023/024 이후 다음 bounded loop

1. OP-025/026의 사용자 행동 로그 분리와 model·engine·code·dataset·config 실행 identity 고정을 조사해 두 장문 보고서를 작성한다.
2. OP-027/028의 이벤트 멱등성과 사용자 데이터 정정·삭제 이력을 같은 기준으로 backfill한다.
3. OP-029/030의 session replay와 서비스 UI 조회 연결을 검토해 현재 단계보다 높이지 않고 보고서를 작성한다.

현재 물리 연구보고서는 66개, 유효 연구보고서는 44/120이며 누락·부적합 76개가 남는다. 전체 글자 수는 304,015자다. completion은 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, OP-120 evidence SHA-256은 `17189085bee1c02a4a350d8bbf333a1d5da082938d6f15704ec8566d1f138c16`이다. GitHub Actions `29968699617`이 성공했다. 현재 병목은 보고서 76개, required-stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt다.

## OP-021/022 이후 다음 bounded loop

1. OP-023/024의 지식 근거 lineage와 결과별 claim·rule 연결을 조사해 장문 보고서를 작성한다.
2. OP-025/026의 행동 로그 분리와 실행 identity 고정을 같은 기준으로 backfill한다.
3. OP-027/028의 이벤트 멱등성과 사용자 데이터 수정 이력을 검토해 두 보고서를 작성한다.

현재 물리 연구보고서는 64개, 유효 연구보고서는 42/120이며 누락·부적합 78개가 남는다. 전체 글자 수는 292,110자다. completion은 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, OP-120 evidence SHA-256은 `d8059938b8487452b68c3c4a26ffa8f24429f6119750286d725cf2d6941dccb6`이다. GitHub Actions `29940069699`이 성공했다. 현재 병목은 보고서 78개, required-stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt다.

## OP-019/020 이후 다음 bounded loop

1. OP-021/022의 구현·증거 경계를 조사하고 장문 보고서를 작성한다.
2. OP-023/024의 구현·증거 경계를 조사하고 장문 보고서를 작성한다.
3. OP-025/026의 구현·증거 경계를 조사하고 장문 보고서를 작성한다.

현재 물리 연구보고서는 62개, 유효 연구보고서는 40/120이며 누락·부적합 80개가 남는다. 전체 글자 수는 282,078자다. completion은 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, OP-120 evidence SHA-256은 `6318bd672f8202dfe5513641f4edad694c47123a082e0fc0390f45a79752a6b7`이다. GitHub Actions `29937570061`은 최초 일시적 build 실패 후 동일 failed-job 재실행에서 성공했다.

## OP-017/018 이후 다음 bounded loop

1. OP-019/020의 service profile adapter와 추천 가능성 계약을 같은 기준으로 backfill한다.
2. OP-021/022의 구현·증거 경계를 조사하고 장문 보고서를 작성한다.
3. OP-023/024의 구현·증거 경계를 조사하고 장문 보고서를 작성한다.

현재 물리 연구보고서는 60개, 유효 연구보고서는 38/120이며 누락·부적합 82개가 남는다. 전체 글자 수는 274,237자다. completion은 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, OP-120 evidence SHA-256은 `ca11bc8843c4f7a92a3336f16e09f1e0d268b16e2879d8d5f0e8d56074b98bb0`, 성공 CI는 `29935977162`다.

## OP-015/016 이후 다음 bounded loop

1. OP-017/018의 동의·안정된 입력 hash와 지원하지 않는 입력 차단 계약을 같은 기준으로 backfill한다.
2. OP-019/020의 service profile adapter와 추천 가능성 계약을 backfill한다.
3. OP-021/022의 다음 구현·증거 경계를 조사하고 장문 보고서를 작성한다.

현재 물리 연구보고서는 58개, 유효 연구보고서는 36/120이며 누락·부적합 84개가 남는다. 전체 글자 수는 267,068자다. completion은 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, OP-120 evidence SHA-256은 `ad43403b9105a3bdd49ddf23d616d35e47da559db7b11e692ed4832ed8bd2c8e`, 성공 CI는 `29934330927`이다.

## OP-013/014 이후 다음 bounded loop

1. OP-015/016의 식사·생활·검사 입력과 동의·입력 hash 계약을 backfill한다.
2. OP-017/018의 지원하지 않는 입력 차단과 service profile adapter 계약을 backfill한다.
3. OP-019/020의 실행 계보와 원천 가용성 계약을 backfill한다.

## OP-011/012 이후 다음 bounded loop

1. OP-013/014의 약물·질환·알레르기 입력과 목표 우선순위 계약을 같은 기준으로 backfill한다.
2. OP-015/016의 식사·생활·검사 입력과 동의·입력 hash 계약을 같은 기준으로 backfill한다.
3. OP-017/018의 지원하지 않는 입력 차단과 service profile adapter 계약을 같은 기준으로 backfill한다.

현재 물리 연구보고서는 54개, 유효 연구보고서는 32/120이며 누락·부적합 88개가 남았다. 전체 글자 수는 254,619자다. completion 상태는 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`다. OP-120 evidence SHA-256은 `5a8c90de500aa12ff871df36a8bdd2758f6637a730399b803701521e9f8c9873`, 성공 CI는 `29922469760`이다.

## Next after OP-120

1. 누락·부적합 연구보고서 88개를 기존 manifest·증거·커밋과 대조해 작성하거나 보강하고 보고서 감사를 통과시킨다.
2. 비외부 요구사항 43개의 required stage 부족을 운영 증거별로 나눠 해소한다. production 변경은 사용자 승인을 받은 뒤에만 수행한다.
3. OP-039 외부 입력·승인·독립 평가가 실제로 제공되면 trust root 계약에 등록하고 외부 검증을 실행한다.

## 2026-07-15 original plan completion program

The authoritative execution ledger is `docs/plans/2026-07-15-original-plan-completion-program.md`, the machine-readable source is `data/original_plan/requirements_manifest_v1.json`, and the generated status report is `docs/original_plan/COMPLETION_STATUS.md`. OP-101/102 now enforce a deployment contract and required endpoint inventory across two local processes, but remain below required `OPERATED` because no provider deployment occurred. Generated status is complete `70`, partial `31`, pending `18`, external `1`, contradicted `0`. Long-form research-report coverage is only `24/120`; the remaining `96` reports still require separate evidence-grounded prose. The current reports total `168,510` characters, so manifest completion must never be presented as 120 finished reports.

Every OP requires one independent research report. Write the report as full, connected prose for a human reader rather than as an abbreviated log or a list of results. Explain the original requirement, existing system, sources inspected, decisions and reasons, implementation sequence, failures and corrections, reproducible tests, limitations, and the exact evidence stage. Expand unfamiliar abbreviations on first use. Machine-readable evidence, test output, manifest entries, and handoff bullets are supporting material only and never replace the report. Backfill OP-001 through OP-078 from source commits and canonical evidence; do not invent missing history from short summaries.

Next three loops:

1. Continue with OP-103 and OP-104 for service environment variables and result-origin contracts without provider mutation.
2. Continue with OP-105 and OP-106 for profile roundtrip and review-queue integration.
3. Continue evidence-grounded report backfill for OP-001 through OP-078 without reconstructing facts from summaries alone.

Continue through the closed-loop execution group, then the RAG group, in two-requirement slices. Reuse the current `agent_runs`, `agent_steps`, follow-up tables, knowledge tables, and service paths; do not add a parallel scheduler, event store, or knowledge store. Production has no deployed R&D endpoint or `WB_RND_*` settings, so OP-071 through OP-080 remain below `OPERATED`, and OP-101 through OP-105 remain separate deployment and production-integration requirements.

Keep OP-101 through OP-110 open until an independently deployed R&D FastAPI process, internal authentication, persistent storage, service environment variables, and real two-process E2E evidence exist. Current proxy code alone is not integration evidence.

The legacy full-test baseline remains red for two independent reasons: historical report artifacts are absent and four CGM geometry assertions do not match current execution. The current environment collected `1,138` tests and reports `1,061 passed, 77 failed`; none of the failures exercises the OP-101/102 implementation. Restore report evidence only from a trusted hash-verified source; investigate the CGM drift separately instead of changing expected values to force PASS.

## 2026-07-14 verified restoration path

The human approval sequence was completed, and a fail-closed restoration command now exists. The next
action is to supply the original trusted archive plus its SHA-256 manifest, run
`scripts/restore_large_drop_replay_prerequisites.py`, rerun the prerequisite audit, and only then run the
three-case `large_drop` attribution. Hash mismatch, missing input, or path escape must keep restoration
blocked. Do not retrain or reconstruct the held evidence from narrative summaries.

## 2026-07-13 large-drop prerequisite outcome

The highest-priority replay loop is correctly selected but cannot be reproduced from the current checkout.
Its held candidate artifact and four prior replay reports are ignored local artifacts and are absent.

Next action:

1. restore the exact held candidate and prior replay evidence from their original trusted archive;
2. verify restored SHA-256 values and rerun the prerequisite audit until status is `ready`;
3. then run the three-case `threshold_duration_sensitive / mid_margin / large_drop` attribution.

Do not regenerate the missing held candidate through training while the strict gate remains `NO-GO`.
Do not infer the three-case result from narrative docs alone.

## 2026-07-13 Cloud GPU loop outcome

The reusable Cloud GPU inference path is operational. Infrastructure is no longer the immediate blocker.
Keep GPU use limited to sufficiently large offline batches because the measured first-transfer cost was
`0.323738 s`, while CUDA compute itself took `0.030180 s` for the benchmark batch.

The evidence priorities after prerequisite restoration remain unchanged:

1. replay-only attribution for `threshold_duration_sensitive / mid_margin / large_drop`;
2. replay-only attribution for the single `mid_margin / medium_drop` case;
3. one narrow synthetic-validity follow-up on `generator_contamination`.

Do not run effect training or promote `effect_model_v3`. The strict training gate remains `NO-GO`.

## TIPS interim external replacement gates

The automated `PROXY_GOLD_SIMULATION` package is complete. Remaining work requires external inputs:

1. independent pharmacist labels for KPI-1 and KPI-5;
2. consented real PRO/outcomes for KPI-2;
3. external blind action/answer testing for KPI-3 and KPI-4;
4. 1,200-person, 12-month real ADR operation for KPI-6;
5. production wearable/CGM/genetic sessions for KPI-7;
6. external security, privacy, legal, test-lab and certification review.

Do not remove the simulation badge or set `real_research_completion=true` before these gates close.
The legacy narrow-loop priorities below remain valid for the separate learned effect-model track.

## Current priority

The current repo state is:

- deterministic baseline remains the runtime reference
- latest held decision remains:
  - `effect_model_v3_training_view_enforced_slice_balanced_candidate`
  - `decision = hold_baseline_candidate_not_ready`
  - `principal_blocker = synthetic_data_circularity_and_generator_contamination`
  - `dominant_replay_regression_family = non_cgm_continue_to_monitor_threshold_cross`
- the strict training-readiness gate still fixes:
  - `authorized_now = false`
  - `decision = no_go_keep_training_blocked`
  - `first_blocking_criterion = dominant_replay_residual_explained_tightly_enough`
- one synthetic-validity minimum-change item is now bounded explicitly:
  - `chosen_item = calibration_target_coupling`
  - `resolution_state = still_risky`
  - `actionable_for_future_gate_work = true`
- the replay-only residual family is now narrowed further:
  - `threshold_duration_sensitive = 10`
  - `mid_margin = 9`
  - prior explained `small_drop = 5`
  - current residual `large_drop + medium_drop = 4`
- requested effect-training rerun is blocked by gate precondition:
  - no `effect_model_v4_authorized_candidate` artifact should be created yet

So the next session should stay in replay-only / audit mode, not reopen training.

## Closed-enough loops

These are closed enough for the current KPI path and should stay closed unless new evidence appears:

1. replay compare and baseline-vs-candidate judgement
   - status: `complete_candidate_held`
   - decision: `hold_baseline_candidate_not_ready`

2. PRO baseline/follow-up shared normalized contract
   - status: `direct_shared_event_summary_connected`
   - proof:
     - `shared_event_schema_version = baseline_followup_pro_event_v1`
     - `event_to_summary_valid_case_count = 480`
     - `event_to_summary_invalid_case_count = 0`
     - `delta_pp_matches_percentile_diff_all_valid_cases = true`

3. learned artifact replay-only runtime boundary
   - status: `replay_only_boundary_preserved`
   - `promoted_core_path_count = 0`
   - `all_core_paths_preserved = true`
   - `chat_optional_only = true`

4. replay-only explanation of the current smallest `non_cgm` drift surface
   - status: `current_smallest_surface_explained`
   - bounded surface:
     - `threshold_duration_sensitive`
     - `mid_margin`
     - `small_drop`
     - `trajectory_step`
     - `fixed_uniform_offset`
     - `0.5` half-offset
     - local contract `uniform_score_gap_offset`

5. replay-only residual attribution for the remaining `mid_margin` residual surface
   - status: `residual_surface_narrowed_but_not_closed`
   - bounded residual surface:
     - `threshold_duration_sensitive`
     - `mid_margin`
     - `large_drop = 3`
     - `medium_drop = 1`
   - current finding:
     - `primary_residual_family = mixed_residual_overlap`
     - `score_geometry_share_pct = 74.52`
     - `trajectory_step_behavior_share_pct = 25.48`
     - `threshold_duration_interaction_direct_share_pct = 0.0`
     - `explained_well_enough_for_future_gate_work = false`

6. narrow synthetic-validity single-item calibration follow-up
   - status: `bounded_single_item_written`
   - proof:
     - `chosen_item = calibration_target_coupling`
     - `resolution_state = still_risky`
     - `candidate_supported_share_of_net_gain_pct = 106.75`
     - `baseline_supported_share_of_net_gain_pct = 111.17`

7. strict training-readiness gate
   - status: `current_no_go_gate_written_v2`
   - proof:
     - `authorized_now = false`
     - `decision = no_go_keep_training_blocked`
     - `first_blocking_criterion = dominant_replay_residual_explained_tightly_enough`
     - next required non-training loop is `large_drop` only

8. requested effect-training rerun
   - status: `blocked_by_gate_precondition`
   - proof:
     - `training_readiness_gate_v2 = NO-GO`
     - no new candidate artifact should be created yet

## Open bottlenecks 5

Order these by current evidence:

1. the dominant replay regression family is still unresolved above the already-explained `small_drop` slice
   - family: `non_cgm_continue_to_monitor_threshold_cross`
   - residual surface is now only `4` cases, but still lacks one bucket-agnostic local contract

2. synthetic validity remains the principal project blocker
   - supported effect-enriched rows still remain:
     - `exact_reconstruction_rate_pct = 100.0`
     - `assignment_top2_match_rate_pct = 100.0`
     - materially calibration-coupled to `expected_effect_proxy`
   - one item is now better bounded, but not closed:
     - `calibration_target_coupling = still_risky`

3. weakest-slice lineage is still bridge-connected rather than fully closed
   - requested `weakest_slice_lineage_proof_v1.json` is absent
   - current closest lineage anchor still has:
     - `audit_layer_gap_count = 4`
     - sample-fixture based parser/CGM joins
     - partial structured-safety overlap

4. `cgm` final-step geometry still has unresolved structural overlap
   - status: `structural_continue_plan_overlap_persists`
   - outside-band unresolved cases still dominate over the single threshold-edge win
   - but this is still not the next blocker right now

5. further training reruns remain blocked by evidence quality, not infrastructure
   - current gate is strict `NO-GO`
   - first blocker remains replay `large_drop`
   - reopened `cgm` blocker is not yet closed or proven non-blocking

## Next 3 bounded loops

1. `P3/P4`: replay-only attribution for `threshold_duration_sensitive / mid_margin / large_drop` only
   - this is now the densest remaining residual bucket
   - success output:
     - one artifact showing whether `large_drop` reduces to one reusable local contract or still needs a mixed two-feature explanation

2. `P3/P4`: replay-only attribution for the single `threshold_duration_sensitive / mid_margin / medium_drop` case only
   - only after loop 1 completes or stalls cleanly
   - success output:
     - one artifact proving whether the lone medium case is already fully explained by the current mixed story or needs a separate local contract

3. `P3/P4`: one narrow synthetic-validity follow-up on `generator_contamination` only
   - stay single-item and minimum-change
   - success output:
     - one artifact separating acceptable shared assignment assumptions from unacceptable generator-coupled supported-slice efficacy evidence

Do not run training or a new `cgm` loop yet.
- Why:
  - latest gate `v2` is strict `NO-GO`
  - first blocker remains replay `large_drop`
  - `cgm` still fails the gate's non-blocking check because `cgm_outside_band_final_step_geometry_v2` is absent

## Priority rule

- runtime/core KPI path outranks everything else
- replay-only evidence still outranks every other training-adjacent task because the current gate names it as the required precondition
- synthetic-validity follow-up stays above weakest-slice cleanup, `cgm`, and any training churn
- training rerun stays blocked until the current gate materially changes from `no_go_keep_training_blocked`
- optional chat/OpenAI stays below replay, synthetic validity, weakest-slice cleanup, `cgm`, and training-boundary work

## Manual backlog priority

- must-do: none
- optional:
  - rerun the latest OpenAI live smoke only if deeper provider-failure diagnosis is still needed later

## Guardrails

- Keep work inside `C:/dev/wellnessbox-rnd`
- Preserve deterministic baseline, frozen-eval comparability, safety precedence, bounded chat, and replay-only learned artifacts
- Do not widen `dataset_f_effect_training_view_v1`
- Do not reintroduce forbidden outcome-side features into effect training
- Prefer evidence-chain tightening over architecture churn
# Next after OP-103/104

1. Complete OP-105/106 with a committed profile-to-R&D roundtrip and review-queue integration, without public deployment.
2. Backfill evidence-grounded Korean reports for OP-001 through OP-078; `94/120` reports remain.
3. Register WB_RND values and verify browser labels only after explicit approval for Vercel and deployment changes.
# Next after OP-105/106

1. Complete OP-107/108 for real admin API state and selling-product candidate integration.
2. Backfill OP-001~078 reports; `92/120` reports remain.
3. Keep OP-101~106 below OPERATED until approved provider and real user/pharmacist evidence exists.
# Next after OP-107/108

1. Complete OP-109/110 order mutation and plan-only state integration.
2. Backfill `90/120` missing reports.
3. Add an isolated real Prisma catalog plus real localhost R&D recommendation roundtrip before promoting OP-108 beyond `IMPLEMENTED`; keep production operation gated on approval.
# Next after OP-109/110

1. Complete OP-111/112 internal authorization, data minimization, pseudonymization, and log-masking integration evidence.
2. Backfill the remaining `88/120` Korean research reports.
3. Use isolated PostgreSQL and payment sandbox evidence before promoting OP-109/110; keep production changes approval-gated.

# Next after OP-111/112

1. 다음 bounded loop에서만 OP-113/114의 요청 제한·비용 상한과 장애 복구 계약을 구현하고 검증한다.
2. 누락된 한국어 연구 보고서 `86/120`개를 근거 파일에 연결해 보강한다.
3. 승인을 받은 뒤에만 production identity provider와 production log sink를 관찰해 OP-111/112의 `OPERATED` 후보 증거를 수집한다.

# Next after OP-113/114

1. 다음 bounded loop에서만 OP-115/116의 전체 테스트 계층과 배포 후 health·alias 검증 계약을 구현한다.
2. 누락된 한국어 연구 보고서 `84/120`개를 canonical evidence와 연결해 보강한다.
3. 승인을 받은 뒤에만 production 장애 훈련과 배포 artifact hash를 관찰해 OP-113/114의 `OPERATED` 후보 증거를 수집한다.
# Next after OP-115/116

1. 다음 bounded loop에서만 OP-117의 브라우저 사용자·약사·관리자 핵심 경로 재현을 구현하고 증거화한다.
2. 별도 보고서 loop에서 OP-001~OP-078 누락 연구보고서를 기존 구현·manifest·증거와 대조해 작성한다. 현재 38/120이며 82개가 남았다.
3. 사용자 승인을 받은 뒤에만 production R&D와 WellnessBox를 배포하고 배포 ID·커밋·관측 시각이 연결된 health/alias 기록을 수집해 OP-116 OPERATED 후보를 검토한다.

# Next after OP-117/118

1. 다음 bounded loop에서만 OP-119의 외부 책임자·입력·교체 계약·차단 사유 원장을 구현하고 검증한다.
2. 별도 보고서 loop에서 누락된 한국어 연구보고서 80개를 기존 canonical evidence와 대조해 작성한다.
3. 사용자 승인을 받은 뒤에만 production 배포·traffic과 실제 약사 계정 세션을 관찰해 OP-116~118의 OPERATED 후보를 검토한다.

# Next after OP-119

1. 다음 bounded loop에서만 OP-120 최종 requirement-by-requirement 감사 계약을 구현하되, 미완료 요구사항이 있으면 전체 완료를 거부한다.
2. 별도 보고서 loop에서 누락된 한국어 연구보고서 79개를 기존 canonical evidence와 대조해 작성한다.
3. 외부 독립 조직이 실제 OP-039 입력 4종과 승인 기록을 제공한 뒤에만 trust root를 변경하고 외부 평가를 실행한다.
# 2026-07-22 OP-001/002 이후 다음 세 bounded loop

1. OP-003/004의 manifest 요구, 구현 파일, 테스트, Git 이력을 확인하고 두 한국어 장문 연구보고서를 작성한다. OP-120 유효 보고서를 24개로 높이는 범위만 다룬다.
2. OP-005/006의 원문 지표와 감사 계약을 같은 방식으로 검증해 두 연구보고서를 보강한다. 구현·통합·운영 단계를 현재 증거보다 높이지 않는다.
3. OP-007/008의 요구사항 추출과 증거 연결을 검토해 두 연구보고서를 보강한다. 각 반복 뒤 OP-120 고정 사례와 canonical evidence를 다시 생성한다.

현재 우선 병목은 누락·부적합 연구보고서 98개다. 비외부 단계 미달 43개, OP-039 외부 검증, 최종 검증·독립 검토 영수증은 별도 승격 반복에서 다룬다. 승인 없이 production 배포, 실제 traffic, 외부 서명 증거를 만들지 않는다.
# 2026-07-22 OP-003/004 이후 다음 세 bounded loop

1. OP-005/006의 p.25~26 KPI 수식·분모와 기계 판독형 manifest 계약을 확인하고 두 한국어 장문 보고서를 작성한다. OP-120 유효 보고서를 26개로 높이는 범위만 다룬다.
2. OP-007/008의 단계 판정 Pydantic 모델과 증거 없는 완료 거부 감사를 검토해 두 연구보고서를 보강한다. 현재 증거보다 높은 단계를 주장하지 않는다.
3. OP-009/010의 pytest·CI 연결과 manifest 기반 100% 감사 보고서 생성을 검토해 두 연구보고서를 보강한다. 각 반복 뒤 OP-120 고정 사례와 canonical evidence를 다시 생성한다.

현재 우선 병목은 누락·부적합 연구보고서 96개다. 비외부 단계 미달 43개, OP-039 외부 검증, 최종 검증·독립 검토 영수증은 별도 승격 반복에서 다룬다. 승인 없이 production 배포, 실제 traffic, 외부 서명 증거를 만들지 않는다.

# 2026-07-24 다음 실제 사람 작업

1. 사람이 연령·목표·복용약물이 다른 실제 프로필 4개 이상을 추가로 실행해 서로 다른 실제 프로필을 5개 이상으로 만든다.
2. 운영 세션에서 실제 추천 초안이 생기면 권혁찬이 본인 이름으로 승인·수정 승인·반려한다. 대기 건수를 늘리려고 데이터를 자동 생성하지 않는다.
3. 권혁찬이 OP-039 사례 10개를 각각 직접 판정하고 자격 확인 방법을 입력한 뒤 서명한다. 완료 후 감사를 다시 실행해 READY 복귀를 확인한다.
-
## 2026-08-04 다음 단계

1. 기존 `kpi_completed_review.zip`의 `비식별 검토자`와 등록 검토자 신원을 연결하는 일괄 확인 기록 1건을 받는다. 335건을 다시 판정하지 않는다.
2. 확인 기록을 검증한 뒤 기존 335개 결정에 동일한 신원 참조를 연결하고 `scripts/audit_answer_key_integrity.py`를 다시 실행한다.
3. 감사 PASS 전에는 봉인과 KPI 측정을 실행하지 않는다. 최종 영수증도 재발급하지 않는다.

## 2026-08-04 단일 반환 자료

1. `data/original_plan/kpi/review_handoff/identity_linkage/kpi_original_review_identity_linkage_input.zip` 하나를 사용한다.
2. 반환 ZIP 하나를 받은 뒤 335건의 신원 연결, 무결성 감사, 봉인을 순서대로 처리한다.
3. 같은 검토자에게 사례별 추가 입력을 다시 요청하지 않는다.
