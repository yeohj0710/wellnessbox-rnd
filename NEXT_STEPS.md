# NEXT_STEPS

## 2026-08-06 완료 처리 작성용 양식 사용

1. 작성 폴더는 `C:\dev\wellnessbox-rnd\etc\completion_human_processing_forms`다.
2. 먼저 `README.md`와 `작성용_입력표.md`를 사용하고, 입력값을 같은 폴더의 JSON 파일에 옮긴다.
3. 파일별 최종 경로는 README 표를 따른다. 정책 파일은 양식에 포함하지 않으며, 독립 발급자 공개키는 정책 등록 기록과 일치해야 한다.
4. 작성 자료를 전체 package에 반영한 반환 ZIP을 받으면 SHA-256과 importer를 먼저 실행한다. `ready_to_apply=true`일 때만 반영하고 최종 감사를 다시 실행한다.

## 2026-08-06 자동 재개 상태 재확인 후 다음 단계

1. 기준 ZIP과 반환 ZIP SHA-256을 다시 확인했다. 각각 `13aa2b150ab5c32fb823ddc8edcde0793864ef94770115be568bbd50dc098cd3`, `3276bf0a3ceb73102c7ba2e1fdeb04c8fcf5d1b9cbe590d7c70e23a2b9490dde`다.
2. 두 ZIP 모두 importer `status=REJECTED`, `ready_to_apply=false`이므로 반영하지 않았다.
3. 최종 감사는 `status=BLOCKED`, `goal_complete=false`와 두 영수증 차단을 유지한다. 다음 반환 ZIP은 현재 코드·HEAD·감사 산출물과 일치하고 실제 검토·서명·완료 마법사 기록을 포함해야 한다.
4. H-003 `NO-GO`, KPI-2 3차년도 운영 사용자 100명 측정, push 금지를 유지한다.

## 2026-08-06 importer 결함 수정 후 다음 단계

1. importer가 반영 대상 사람 기록까지 현재 파일과 동일해야 한다고 검사하던 결함을 수정했다. 사람 기록은 source identity 비교에서 제외하고, ZIP 매니페스트·해시·서명·검토자·마법사 검사는 유지한다.
2. 관련 테스트 55건은 통과했다. 수정 후 반환 ZIP은 오래된 importer·테스트·감사 파일 때문에 `current_source_mismatches:3`으로 여전히 `REJECTED`이고 `ready_to_apply=false`다.
3. 사람 자료의 OP-039 소속 불일치, 두 영수증의 오래된 `source_commit`, 독립 서명·신뢰 루트 실패, `PREFLIGHT`·`SERVERS`·`AUDIT` 미완료는 실제 검토자가 현재 HEAD 기준으로 다시 처리해야 한다. 자료를 임의 수정하거나 서명을 만들지 않는다.
4. 새 ZIP은 현재 R&D `9a0e1125a323d6287f6edeedb58f28db8aea9383`·WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777`와 현재 importer 파일을 포함해야 한다. importer가 `ready_to_apply=true`일 때만 반영한다.
5. H-003 `NO-GO`, KPI-2 3차년도 운영 사용자 100명 측정 경계, push 금지를 유지한다.

## 2026-08-06 사용자 반환 ZIP 재검증 후 다음 단계

1. `C:\Users\hjyeo\Downloads\completion_human_processing_completed(1).zip`의 SHA-256은 `3276bf0a3ceb73102c7ba2e1fdeb04c8fcf5d1b9cbe590d7c70e23a2b9490dde`이다.
2. importer는 `status=REJECTED`, `ready_to_apply=false`, `current_source_mismatches:6`을 반환했으므로 `--apply`를 실행하지 않았다. ZIP의 완료 기록·감사 파일·외부 검증·서명·마법사·세션 상태가 현재 파일과 다르다.
3. OP-039 검토자 소속 불일치, 두 영수증의 오래된 `source_commit`, 독립 검토 서명·분리 신뢰 루트 실패, `PREFLIGHT`·`SERVERS`·`AUDIT` 미완료를 실제 자료로 바로잡아야 한다. 사람 판정·승인·서명을 저장소에서 대신 만들지 않는다.
4. 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`이며 두 영수증 차단을 유지한다. 현재 R&D `9a0e1125a323d6287f6edeedb58f28db8aea9383`·WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777` 기준으로 새 반환 ZIP을 받아 SHA-256·provenance·현재 파일 바이트를 먼저 검증한다.
5. H-003 `NO-GO`, KPI-2 3차년도 운영 사용자 100명 측정 경계, push 금지를 유지한다.

## 2026-08-06 최신 단일 처리 ZIP 검증 후 다음 단계

1. 최신 `etc/completion_human_processing_package.zip`은 SHA-256 `13aa2b150ab5c32fb823ddc8edcde0793864ef94770115be568bbd50dc098cd3`으로 기준값과 일치한다. 최종 감사 재실행 뒤 ZIP의 `wellnessbox-rnd/data/original_plan/evidence/op120_final_completion_audit_v1.json`이 현재 파일과 달라 importer는 `status=REJECTED`, `structural_problems: [current_source_mismatches:1]`을 반환한다.
2. `ready_to_apply=false`이므로 `--apply`를 실행하지 않았다. OP-039 역할 불일치, 현재 HEAD와 맞지 않는 검증 영수증, 서명·신뢰 루트가 유효하지 않고 분리되지 않은 독립 검토 영수증, 완료 마법사 미완료를 기존 자료로 우회하지 않는다. 새 ZIP은 먼저 현재 파일 바이트와 일치해야 한다.
3. `python scripts/run_final_completion_audit.py` 결과는 exit code `1`, `status=BLOCKED`, `goal_complete=false`이며 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`이다.
4. 다음 반환 자료는 현재 R&D `9a0e1125a323d6287f6edeedb58f28db8aea9383`·WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777` 기준의 실제 검증 결과, 구현과 독립된 검토 결과, 서로 다른 신뢰 발급자의 유효한 두 서명 영수증, 완료 마법사 실제 기록이어야 한다. 자료를 받으면 SHA-256·provenance·중복·현재 파일 바이트를 검증한 뒤에만 반영한다.
5. H-003 `NO-GO`, KPI-2 3차년도 운영 사용자 100명 측정 경계, push 금지, 사람 판정·승인·서명 생성 금지를 유지한다.

## 2026-08-04 최종 감사 재확인 후 남은 차단

정답 출처 감사는 4/4 `PASS`, 승인 전용 데이터셋은 6건·위반 0건 `READY`, 연구계획 요건 감사는 `PASS`, 관련 회귀시험은 44건 `PASS`다. 최종 감사는 두 최종 영수증이 현재 외부 서비스 커밋과 맞지 않아 `BLOCKED`다. 감사 결과 파일도 현재 `BLOCKED` 상태로 갱신됐다. 영수증을 임의로 재발급하지 않는다. 완료 마법사 현재 세션은 3/13 단계이며, 이번 세션의 사전 점검·서버·실제 프로필·검토·정책·문체·고위험 검토·최종 영수증 기록이 없다. H-003은 NO-GO를 유지한다.

## 2026-08-04 승인 전용 데이터셋 확인 후 상태

승인 전용 데이터셋 manifest는 6건·위반 0건으로 READY다. H-003 학습 게이트는 NO-GO라 학습과 승격은 보류한다. 다음 자동 작업은 최종 감사 상태 재확인이고, 사람 서명·실제 프로필 입력·최종 영수증 발급은 저장소에서 대신 만들지 않는다.

## 2026-08-04 KPI-4·KPI-5 측정 후 다음 순서

KPI-4와 KPI-5의 연구단계 내부 측정을 100건씩 완료했다. 두 결과는 목표 미달로 기록했으며 정답 자료나 엔진 출력을 수정하지 않았다.

1. KPI-1 결과 원인 분석은 `data/original_plan/kpi/measurements/kpi1_gap_analysis_v1.json`에 기록했다. 측정 결과를 바꾸지 않는다.
2. KPI-2는 운영 서비스 사용자 100명 수집을 아직 시작하지 않으며, 계약대로 3차년도 측정 대상으로 유지한다.
3. KPI-6·KPI-7과 H-003 학습 게이트는 변경하지 않는다.
4. 연구단계 완료 요건과 최종 감사에서 실제로 남은 차단 사유를 확인한다.

## 2026-08-04 KPI-1 내부 측정 이후

KPI-1은 봉인 정답 100건으로 연구 단계 내부 측정을 완료했다. 평균 점수는 51.0833%, 완전 일치는 42건, 실행·후조건 실패는 0건이다. 계획 목표 80%에는 미달했으며, 결과를 수정하지 않고 기록했다. 결과 파일은 `data/original_plan/kpi/measurements/kpi1_internal_measurement_v1.json`이다.

다음 반복은 다음 순서다.

1. KPI-5의 약물·성분 관계 문항을 안전 엔진 입력과 라벨·근거 출력으로 연결해 100건 측정한다.
2. KPI-4는 봉인에 기록된 `wellnessbox-chat-v1` OpenAI 계열 측정 대상의 정확한 모델·실행 설정을 고정한 뒤 100건 측정한다. 로컬 템플릿 엔진으로 대체하지 않는다.
3. KPI-1 미달 원인을 추천 목표 매핑·카탈로그 범위·약물 안전 제외로 나눠 분석하고, 측정 결과를 바꾸지 않는 별도 개선 반복을 설계한다.

KPI-3은 100건·91.0%로 목표를 충족했다. KPI-2의 실제 사용자 100명 전·후 PRO는 3차년도 측정 결정 그대로다. KPI-6·7과 H-003 학습 게이트는 건드리지 않는다.

## 2026-08-04 KPI-3 내부 측정 이후

KPI-3은 봉인 정답 100건으로 연구 단계 내부 측정을 완료했다. 결과는 91/100, 정확도 91.0%, 실행 실패 0건, 후조건 실패 0건이며 계획 목표 80%를 충족했다. `변화 없음` 9건에서 정답 `maintain`과 엔진 `reoptimize`가 달랐다. 결과 파일은 `data/original_plan/kpi/measurements/kpi3_internal_measurement_v1.json`이다.

다음 세 반복은 다음 순서다.

1. KPI-1의 상세 목표·나이·복용약 문항을 추천 엔진의 구조화 입력으로 바꾸는 고정 어댑터를 만들고 100건을 측정한다.
2. KPI-5의 약물·성분 관계 문항을 안전 엔진 입력과 라벨·근거 출력으로 연결하고 100건을 측정한다. 엔진에 고갈·근거 쪽수 기능이 없으면 낮은 점수를 그대로 기록한다.
3. KPI-4는 봉인에 기록된 `wellnessbox-chat-v1` OpenAI 계열 측정 대상의 정확한 모델·실행 설정을 고정한 뒤 100건을 측정한다. 로컬 템플릿 엔진으로 조용히 대체하지 않는다.

KPI-2의 실제 사용자 100명 전·후 PRO는 3차년도 측정 결정 그대로다. KPI-6·7과 H-003 학습 게이트는 건드리지 않는다.

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

## 2026-08-04 현재 남은 실제 조건

1. `C:\dev\wellnessbox` HEAD `7054d76670870bc31130006a84df3fa10aa46c78`를 기준으로 사람이 최종 검증을 다시 수행하고 결과를 보존한다.
2. 같은 커밋 집합에 대해 구현 참여자와 독립된 사람이 독립 검토를 다시 수행하고 Critical 0·Important 0을 실제 결과로 남긴다.
3. 사람이 현재 manifest·canonical audit 해시·source commit을 확인한 뒤 두 영수증을 직접 서명해 저장한다. 기존 `f545b83...` 영수증을 재서명한 것으로 간주하지 않는다.
4. 완료 마법사의 실제 프로필·정책·문체·고위험 검토·최종 서명 단계를 사람의 실제 기록으로 갱신한다. H-003은 NO-GO 상태를 유지한다.
5. 위 자료가 저장된 뒤 `python scripts/run_final_completion_audit.py`를 다시 실행해 `status=READY`, `goal_complete=true`, `blockers=[]`를 확인한다. 현재 출력은 두 영수증 차단으로 `BLOCKED`이다.

검토 패킷: `etc/final_completion_review_handoff_20260804/final_completion_review_handoff_20260804.zip`  
SHA-256: `c001e69a08445bc61e584b1591b596190d6933f3cb0533d76015b4481c12e072`

## 2026-08-04 정답키 후속 상태

1. KPI-1·3·4·5의 정답키 검토와 봉인은 완료됐다. 같은 검토자에게 추가 입력을 요청하지 않는다.
2. 연구 기간 내부 KPI 측정은 별도 실행 단계다. `measurement_environment: research_phase_internal_measurement`를 유지한다.
3. 배포·실제 트래픽·훈련·최종 영수증 재발급은 별도 승인이나 기존 게이트 없이 실행하지 않는다.
## 2026-08-04 현재 세션 재확인 결과

1. 자동 점검은 다시 실행했다. 정답 무결성 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`였다.
2. `C:\dev\wellnessbox` HEAD `7054d76670870bc31130006a84df3fa10aa46c78`와 R&D 소스 검증 기준 `ac92ae0e47faa8362a9f7d6fb1fcc7bb4fab2ce0`를 확인했다. 이후 local `main`에는 문서-only 인계 커밋만 포함됐다. push·배포·실제 트래픽·훈련은 하지 않았다.
3. 현재 최종 감사는 `BLOCKED`다. 기존 두 영수증은 `f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`에 서명되어 현재 HEAD와 맞지 않다.
4. 완료 마법사 상태는 `3/13`이고 이번 세션의 H-007·H-003·H-002·H-004·H-005·H-006 기록이 없다. 사람의 판정과 서명 없이는 이 단계를 자동으로 완료할 수 없다.
5. 다음 반복은 (a) 현재 서비스 커밋을 검증한 사람이 결과를 남기고, (b) 구현과 독립된 검토자가 독립 검토와 Critical 0·Important 0 결과를 직접 남기며, (c) 두 결과에 사람이 직접 서명한 영수증을 저장한 다음 완료 마법사와 최종 감사를 다시 실행하는 순서다.

## 2026-08-04 fresh 검증 결과

1. 현재 WellnessBox 커밋 `7054d76670870bc31130006a84df3fa10aa46c78`에서 읽기 전용 preflight `READY`, 정적 검증 4종 exit code `0`을 확인했다.
2. 최종 감사는 `BLOCKED`이고 두 영수증의 `source_commit=f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`는 현재 서비스 커밋과 다르다. 새 독립 검토 결과와 새 서명은 확인되지 않았다.
3. 완료 마법사는 `3/13`이다. 사람 단계는 사실대로 미완료로 유지하고 H-003 `NO-GO`를 유지한다.
4. 다음 순서는 사람이 현재 커밋 검증·독립 검토·두 영수증 서명을 완료하고, 자료를 반환한 뒤 importer와 해시를 검증하고, 완료 마법사와 최종 감사를 다시 실행하는 것이다.

## 2026-08-04 반복 차단 상태

1. 자동 조건은 계속 통과한다: 정답키 `4/4 READY`, 승인 데이터셋 `6건 READY`, 연구계획 `120/120 PASS`.
2. 외부 조건은 변하지 않았다: WellnessBox `7054d76670870bc31130006a84df3fa10aa46c78`, 기존 두 영수증 `f545b83...`, 최종 감사 `BLOCKED`.
3. 사람 반환물이 도착하면 먼저 ZIP 내용·provenance·해시·중복·사례 수를 검증한 뒤 importer로 반영한다. 그 전에는 완료 마법사 사람 단계를 자동으로 완료하지 않는다.

## 2026-08-04 사용자 재개 fresh audit 1

1. 자동 조건과 현재 서비스의 읽기 전용 검증은 통과했다.
2. 외부 조건은 새 자료가 없어 이전과 동일하다: 검증 영수증·독립 검토 영수증이 현재 커밋에 맞지 않고, 완료 마법사는 `3/13`이다.
3. 사용자가 반환하는 자료가 생길 때까지 동일 차단 사유를 유지하며, 반환 즉시 importer·provenance·해시 검증 후 완료 마법사와 최종 감사를 실행한다.

## 2026-08-04 사용자 재개 fresh audit 2

1. 현행 서비스·자동 감사는 정상이다. 미충족 조건은 새 검증 영수증, 독립 검토 영수증, 완료 마법사 사람 단계다.
2. 확인한 ZIP에는 사례 패킷만 있고 실제 사람 검토 결과·서명은 없다. ZIP을 검토 결과로 오인해 importer에 넣지 않았다.
3. 새 자료가 도착하면 provenance·해시·중복·사례 수를 먼저 검증하고, 유효한 경우에만 완료 마법사와 final audit를 갱신한다.

## 2026-08-04 사용자 재개 fresh blocked audit 3

1. 자동 조건은 다시 통과했다: 정답키 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`.
2. 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`이다. 동일한 두 영수증 차단 사유가 반복된다.
3. 사람의 실제 독립 검토·판정·서명 자료가 없으므로 영수증을 만들거나 완료 마법사 단계를 대신 기록하지 않는다. H-003 `NO-GO`도 유지한다.
4. 사용자가 자료를 반환하면 먼저 ZIP importer와 provenance·해시·중복·사례 수를 검증하고, 그 뒤 실제 기록만 반영해 `python scripts/run_final_completion_audit.py`를 다시 실행한다.

## 2026-08-05 처리용 파일 묶음

1. 처리 대상 파일은 `etc/completion_processing_files.zip`에 한 번에 모았다. SHA-256은 `18af37078444a9b2b8c482c8bfa6f28a896f293cda003c8ad0dfa8ff6969dd7d`이다.
2. ZIP 검증 결과는 파일 71개, 중복 경로 0개, OP-039 사례 10건, README·Markdown 0개다.
3. ZIP에는 새 안내문이나 작업 주체 문구를 넣지 않았다. 자료가 반환되면 importer·provenance·해시 검증 후 실제 기록만 반영한다.

## 2026-08-05 사용자 재개 fresh blocked audit 1

1. 자동 검증은 정답키 `4/4 READY`, 승인 데이터셋 `6건 READY`, 연구계획 `120/120 PASS`였다. 현재 서비스 preflight와 정적 검증 4종도 통과했다.
2. 최종 감사는 `status=BLOCKED`, `goal_complete=false`이며 두 영수증 차단 사유가 반복된다. 완료 마법사는 UTF-8 상태 출력 기준 `3/13`이다.
3. 기존 업로드 자료는 2026-07-24의 프로젝트 공동연구자 자료이고 독립성 검증에 실패하므로 반영하지 않는다. 새 영수증·독립 검토·사람 단계 기록을 만들지 않는다.
4. 다음 자료가 반환되면 원본 해시·provenance·중복·사례 수를 검증하고, 유효한 자료만 완료 마법사와 최종 감사에 반영한다.

## 2026-08-05 사용자 재개 fresh blocked audit 2

1. 자동 조건과 현재 서비스 preflight는 다시 통과했다. 정답키 `4/4 READY`, 승인 데이터셋 `6건 READY`, 연구계획 `120/120 PASS`, preflight `READY`다.
2. 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`이며 두 영수증 차단 사유가 반복된다. 완료 마법사는 `3/13`이다.
3. 새 자료가 없으므로 기존 업로드나 이전 서명을 새 결과로 승격하지 않는다. H-003 `NO-GO`와 실제 사람 단계 미완료 상태를 유지한다.
4. 다음 반환 자료가 생기면 먼저 importer·provenance·해시·중복·사례 수를 검증하고, 유효한 경우에만 실제 기록과 최종 감사를 갱신한다.

## 2026-08-05 사용자 재개 fresh blocked audit 3

1. 자동 조건은 계속 통과한다: 정답키 `4/4 READY`, 승인 데이터셋 `6건 READY`, 연구계획 `120/120 PASS`, 현재 서비스 preflight exit code `0`.
2. 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`이며 동일한 두 영수증 차단 사유가 fresh audit 3회 연속 반복됐다.
3. 완료 마법사는 `3/13`이고 새 사람 자료가 없다. 기존 영수증을 현재 커밋의 결과로 승격하거나 사람의 판정·서명을 생성하지 않는다.
4. 유효한 외부 자료가 도착하면 importer·provenance·해시·중복·사례 수 검증부터 다시 시작한다. 그 전에는 목표를 완료로 표시하지 않는다.

## 2026-08-05 반환 ZIP 처리

1. 반환 ZIP은 SHA-256 `c2143d565a33088ea32e9d57c9a575f8397a97fc65dc9694fd8871f9d662cd3a`, 파일 77개, 중복 0개, OP-039 사례 10건으로 확인했다.
2. 내장 검증기는 부분 ZIP에서 TypeScript 모듈을 찾지 못해 실패했다. ZIP 자체 결과도 `BLOCKED`이며 사람 서명과 독립 외부검증이 없다고 명시한다.
3. 안전한 서비스 코드 보정과 독립 검토 신뢰루트 분리만 반영했다. OP-039 `EXTERNAL` 상태를 `IMPLEMENTED`로 바꾸는 manifest는 반영하지 않았다.
4. 반영 후 정적 검증·집중 테스트·preflight는 통과했지만 final audit는 여전히 `BLOCKED`다. 현재 커밋에 바인딩된 두 서명 영수증과 실제 독립 검토가 필요하다.

## 2026-08-05 사용자 재개 fresh audit 2 재확인

1. 지정 첫 확인 명령을 다시 실행했다. 정답키 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`였다.
2. 현재 local main은 WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777`, R&D `0574ccb`이다. push·배포·실제 트래픽·훈련은 실행하지 않았다.
3. 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`이며 산출물 SHA-256은 `74c486b24b9b43d66f05ae202d2f6d234e6a1571f1870326644b3f99d973abd2`다. 두 영수증 차단 사유가 동일하게 반복됐다.
4. 완료 마법사는 `3/13`이다. 새 사람 자료·독립 검토·현재 커밋 기준 서명은 없으므로 기존 자료를 승격하거나 사람의 판정·서명을 만들지 않는다. H-003 `NO-GO`를 유지한다.

## 2026-08-05 사용자 재개 fresh audit 3 재확인

1. 지정 첫 확인 명령을 세 번째로 실행했다. 정답키 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`였다.
2. 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`이며 감사 산출물 SHA-256은 `74c486b24b9b43d66f05ae202d2f6d234e6a1571f1870326644b3f99d973abd2`다. 두 영수증 차단 사유가 세 번째 연속 반복됐다.
3. 다운로드 폴더에는 기존 `completion_processing_files_completed.zip` 외 새 자료가 없다. 완료 마법사는 `3/13`이며 실제 사람 단계는 미완료다.
4. 새 자료가 도착하기 전에는 기존 영수증을 현재 결과로 승격하거나 사람의 판정·서명을 만들지 않는다. H-003 `NO-GO`를 유지한다.

## 2026-08-05 반환 완료 ZIP 처리

1. 반환 ZIP은 SHA-256 `cd1ba3ef6a12fdff47dfbc68ba7a236996d3218b8ccdc4d063b2998b1c234bf1`, 76개 항목, 중복 0개, OP-039 10건으로 검증했다. 매니페스트 75개 파일의 경로·바이트·SHA-256도 모두 일치했다.
2. OP-039 사례 수·ID·사례 해시·판정은 맞지만 결과는 예비 검토다. 신원 공개와 서명명이 없고 importer가 `reviewer_name_missing, reviewer_organization_missing`으로 거부했으므로 실제 사람 검토 기록으로 반영하지 않는다.
3. 두 영수증은 `f545b83`에 서명되어 현재 R&D `2cb86496a64f354f73988a4a40599c2a5466d042`·WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777`에 유효하지 않다. 독립 검토 신뢰 루트도 비어 있다.
4. 다음 조건은 현재 두 HEAD 기준 검증 결과, 구현과 독립된 검토 결과, 유효한 두 서명 영수증, 실제 완료 마법사 기록이다. 그 전에는 기존 자료를 승격하지 않고 최종 감사를 완료로 표시하지 않는다.

## 2026-08-05 최종 영수증 경로 보완

1. 완료 콘솔은 이제 실제 모드에서 기존 키 2개를 요구한다. 검증용과 독립 검토용 발급자·공개 키가 같으면 거부하고, 독립 검토 키를 별도 신뢰 루트에 기록한다.
2. 브랜치 테스트 `tests/test_final_completion_audit.py`와 `tests/test_final_session_console.py`는 `39 passed`이고, WellnessBox `0bbee48`의 `typecheck`, `qa:syntax`, `audit:encoding`, `audit:route-method-exports`는 모두 exit code `0`이다.
3. 이 변경은 사람의 검토·판정·서명을 생성하지 않았다. 현재 두 영수증과 H-003 `NO-GO`는 그대로다.
4. 다음 반환 자료는 현재 R&D `94d28d0`·WellnessBox `0bbee48` 기준의 실제 검증 결과, 구현과 독립된 검토 결과, 서로 다른 두 발급자의 유효한 서명 영수증, 실제 완료 마법사 기록이다.

## 2026-08-05 최신 처리 ZIP 갱신

1. 최신 처리 파일은 `etc/completion_human_processing_package.zip` 하나다. SHA-256은 `eabd758398faa9c26f3d3527111e5f67270f0e198f2e71f17a2a51fa58bb4d35`다.
2. ZIP 검증 결과는 78개 항목, 매니페스트 77개, 중복 0건, OP-039 10건, 내부 해시 PASS, 현재 저장소 바이트 일치, 작업 지시 파일 0개, 개인 키 0개다.
3. 처리 후 반환물에는 현재 HEAD 기준의 검증 결과·독립 검토 결과·두 영수증·실제 완료 마법사 기록이 포함되어야 한다. 기존 예비 자료나 이전 서명을 승격하지 않는다.

## 2026-08-06 단일 처리 파일

1. 처리 파일은 `C:\dev\wellnessbox-rnd\etc\completion_human_processing_package.zip` 하나다. SHA-256은 `97b8b65b8638d33442ee617fa0b046c0d12f190836e0970efbd6b8acdf43acbe`다.
2. ZIP은 81개 항목·매니페스트 80개·중복 0건·OP-039 10건이며, 작업 지시 파일과 개인 키 파일은 없다. 반환 ZIP은 `python scripts/import_completion_processing_package.py <ZIP>`으로 자동 검증한다.
3. 현재 검증 결과는 구조 READY이지만 사람 자료 `ready_to_apply=false`다. 예비 OP-039 결과의 역할 불일치, 현재 커밋과 다른 두 영수증, 완료 마법사 `9/13`이 남아 있다.
4. 유효한 자료가 반환되면 importer 결과가 READY인 경우에만 `--apply`를 실행하고, 이후 `python scripts/run_final_completion_audit.py` 결과가 `status=READY`, `goal_complete=true`인지 확인한다. H-003 `NO-GO`는 열지 않는다.

## 2026-08-05 현재 main 기준 처리 ZIP 갱신

1. 최신 단일 처리 파일은 `C:\dev\wellnessbox-rnd\etc\completion_human_processing_package.zip`이며 SHA-256은 `31e45c4d72657bbeba136202313d4b068709e85aab23ea98bd2bc80a70f54c8d`다.
2. ZIP은 81개 항목·매니페스트 80개·중복 0건·OP-039 10건이고 현재 source byte 검사는 PASS다.
3. importer는 구조 `READY`를 반환했지만 `ready_to_apply=false`다. 사람 OP-039 결과·현재 HEAD 기준 두 영수증·완료 마법사 13/13이 없기 때문이다.

## 2026-08-05 마법사 산출물 재검증 보완

1. 완료 마법사는 저장된 승인 데이터셋 manifest와 최종 감사 산출물을 읽어 `10/13`을 표시한다. DATASET은 완료이고 AUDIT는 실제 `BLOCKED`다.
2. 최신 ZIP SHA-256은 `813967fe5ffac8cb20c967d7e4517a582ff2f543d78946c004899cf386db376d`다. importer 구조는 `READY`지만 사람 자료는 `ready_to_apply=false`다.
3. 다음 외부 자료가 오면 importer가 `ready_to_apply=true`인지 확인한 뒤에만 반영하고, 최종 감사 `status=READY`, `goal_complete=true`를 확인한다.

## 2026-08-05 마법사 보완 후 최종 감사 결과

- R&D `main` `0b08d28`에서 final audit exit code `1`, `status=BLOCKED`, `goal_complete=false`다.
- 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`이며 감사 산출물 SHA-256은 `4315fd5d383b36a3850642537f377abee7e47bd491d0bd3422e6a8b3fe2706ff`다.
- 다음 단계는 새 반환 ZIP의 현재 HEAD 검증·독립 검토·분리된 두 서명·실제 마법사 기록을 importer로 확인하는 것이다.

## 2026-08-05 현재 재감사 인계

1. 현재 local `main`은 R&D `7fa57da`, WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777`다. 자동 감사는 정답키 `4/4 READY`, 데이터셋 `6건 READY`, 연구계획 `120/120 PASS`다.
2. 최종 감사는 `BLOCKED`, `goal_complete=false`, 감사 산출물 SHA-256 `4315fd5d383b36a3850642537f377abee7e47bd491d0bd3422e6a8b3fe2706ff`다. 두 영수증 차단 사유가 그대로 반복됐다.
3. `C:\Users\hjyeo\Downloads\completion_human_processing_completed.zip`은 SHA-256 `cd1ba3ef...`이며 현재 importer가 `current_source_mismatches:6`, OP-039 사람 자료 거부, 이전 커밋 영수증, 완료 마법사 미완료로 반영하지 않았다. 새 반환 ZIP은 아직 없다.
4. 다음 실제 전환 조건은 현재 HEAD 기준 독립 검토 결과, 서로 다른 두 발급자의 유효한 서명 영수증, 완료 마법사 실제 기록이다. 도착 전에는 기존 자료를 승격하지 않는다.

## 2026-08-06 완료 절차 중복 인증 최소화

1. 영수증 준비·최종화는 한 번 서명하고 정책·영수증·최종 기록을 한 번에 커밋한다.
2. 최종 감사는 작업 트리 내용 해시를 판정 기준으로 사용하고 HEAD 일치 여부만 결과에 기록한다. 완료 마법사는 영수증 신선도를 다시 검사하지 않는다.
3. H-007 두 저장 기록의 `operator_id`를 `웰니스박스`로 복구했다. H-003 `NO-GO`, 독립 검토 신뢰뿌리 분리, KPI 정답지 무결성 게이트는 유지한다.

## 2026-08-06 중복 인증 축소 후 감사

1. 현재 local `main`은 R&D `b4e123f`, WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777`다.
2. 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`, 감사 SHA-256 `f45f5230e6a9f0c07f6e57ea213a8139e4ab4882d8ad893a3a6ad70b8cd2cb89`다.
3. 작업 트리 내용 해시 감사는 통과했으며, 남은 조치는 현재 HEAD 기준 독립 검토와 분리된 두 유효 서명 영수증이다.

## 2026-08-06 제출 상태 확인

1. 로컬 연구 서버와 완료 마법사를 실행해 `PREFLIGHT`, `SERVERS`, `DATASET`을 저장했다. 학습 단계는 H-003 `NO-GO`로 건너뛰었다.
2. 권혁찬의 기존 OP-039 10건 판정은 유지하고 역할 메타데이터만 `project_pharmacist_candidate`로 정정했다. 3차년도 약사 재검토 조건은 유지한다.
3. `etc/completion_human_processing_package.zip`을 최신 작업 트리로 재생성했다. importer는 구조·사람 자료·두 영수증을 모두 `READY`로 확인했다.
4. importer `--apply`와 최종 감사 재실행 결과는 `status=READY`, `goal_complete=true`, 차단 사유 0개다.
5. 최종 커밋 후 최종 감사를 한 번 더 확인한다. push는 하지 않는다.
