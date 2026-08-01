# SESSION_HANDOFF

## 2026-08-01 Claude 로그인 blocker handoff

- **선택 단계와 과제:** 준비된 KPI-3 Claude 요청을 실제 외부 AI에 전달할 실행 경로를 점검했다.
- **주 데이터셋과 사례 수:** `data/original_plan/kpi/ai_review_requests/kpi3_claude_review_request_v1.json` 100건이다. 파일은 외부에 전송하지 않았다.
- **변경 파일:** `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`만 갱신했다.
- **점검 결과:** Claude CLI 없음, Anthropic API 키 없음, Anthropic 패키지 없음, Chrome 연결 없음, 인앱 Claude 세션 로그인 안 됨이다. Claude 로그인 페이지는 사용자가 이어갈 수 있도록 남겼다.
- **검증:** 외부 전송 0건, 응답 생성 0건, 워크벤치 변경 0건이다. 로그인·가입·요금제·결제를 실행하지 않았다.
- **공식 delta:** 엔진·데이터·채점식·frozen eval·replay·slice를 변경하거나 실행하지 않아 모두 0이다.
- **가장 큰 병목 5개:** Claude 로그인과 응답 400건, KPI-1·5 사람 폐기 확인, 사람 상세 판단 최소 20건·최대 400건, 새 봉인 4종, KPI-2 실제 사용자 100명 전·후 PRO다.
- **권장 다음 반복 3개:** (1) 사용자가 Claude에 로그인한 뒤 KPI-3 요청을 단독 전달, (2) 응답을 사전검증·가져오기, (3) KPI-4 Claude primary와 Codex review를 연결한다.
- **재개 조건:** 사용자가 Claude 로그인 완료를 알려야 한다. 그전에는 같은 제공자 계열 Codex로 Claude 응답을 대체하지 않는다.

## 2026-08-01 Claude 블라인드 요청 번들 handoff

- **선택 단계와 과제:** 외부 Claude 응답을 저장소 노출 없이 바로 받을 수 있도록 역할별 요청 파일과 비변경 사전검증을 만들었다.
- **주 데이터셋과 사례 수:** `data/original_plan/kpi/ai_review_requests/`의 KPI-1·3·4·5 요청 각 100건, 총 400건이다.
- **변경 파일:** `adaptive_answer_key_review.py`, `run_answer_key_workbench.py`, 적응형 검토 테스트, Claude 요청 JSON 4개와 README, `KPI_COMPLIANCE_STRATEGY.md`, 인계 문서 3종이다.
- **핵심 변경:** `export-external-ai-request`는 사례와 허용 어휘만 든 단독 전달 파일을 만든다. `validate-ai-response`는 실제 등록 함수와 deepcopy를 사용해 응답을 검사하고 원본 워크벤치를 바꾸지 않는다. KPI-1·3·5는 Anthropic review, KPI-4는 Anthropic primary 요청이다.
- **검증:** 관련 시험 124건 PASS, 변경 파일 Ruff PASS. 전체 pytest 실제 실행은 기준선과 같은 90건 실패·실패 파일 73개다. 네 실제 요청은 request SHA-256 일치, 고유 사례 100건, 사례 필드 `case_id`·`prompt` 제한, `only_input_allowed: this_request_file`을 모두 통과했다.
- **공식 delta:** 엔진 입력·안전 규칙·채점식·frozen eval을 바꾸거나 실행하지 않아 delta 0이다. replay·slice도 변경하지 않아 delta 0이다.
- **가장 큰 병목 5개:** Claude 응답 400건, KPI-1·5 사람 폐기 확인, 사람 상세 판단 최소 20건·최대 400건, 새 봉인 4종, KPI-2 실제 사용자 100명 전·후 PRO다.
- **권장 다음 반복 3개:** (1) KPI-3 요청 파일로 Claude 응답을 받아 검증·가져오기, (2) KPI-4 Claude primary 뒤 Codex review 가져오기, (3) KPI-1·5 Claude 응답과 사람 폐기 확인이다.
- **한계:** 요청 파일은 Claude가 실제로 다른 자료를 보지 않았음을 기술적으로 증명하지 못한다. 별도 작업 경계와 응답 자기 진술에 의존한다. 1초 하한·합의 표본 5건은 임의 기준이고 원문 234종 중 209종은 카탈로그 밖이다.

## 2026-08-01 pytest 기준선 오진 정정 handoff

- **선택 단계와 과제:** KPI 정답지 변경 뒤 전체 pytest 실패 수가 90→114로 늘었다는 보고의 원인을 체계적으로 진단했다.
- **주 데이터셋과 사례 수:** 제품 데이터셋 변경은 없다. 전체 pytest 실행 결과의 실패 90건, 실패 파일 73개와 `.pytest_cache`의 stale node ID 24개를 비교했다.
- **변경 파일:** `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`만 갱신했다. 진단용 임시 worktree는 제거했다.
- **핵심 결과:** 실제 회귀 증가는 없었다. `.pytest_cache/v/cache/lastfailed`가 삭제·이름 변경된 테스트 24개를 보존한 상태에서 캐시 길이를 실제 실패 수로 잘못 셌다. 캐시가 아닌 전체 pytest 실행 출력은 기준선과 같은 90건 실패다.
- **검증:** `python -m pytest -q --tb=no` 실제 결과를 별도 프로세스에서 캡처해 `ACTUAL_FAILED 90`, `FAILED_FILES 73`을 확인했다. 관련 KPI 회귀 121건 PASS, 지정 Ruff 범위의 기존 오류 2건은 그대로다.
- **공식 delta:** 코드·데이터·엔진 입력·채점식·frozen eval을 바꾸거나 재실행하지 않아 delta 0이다. replay·slice도 변경하지 않아 delta 0이다.
- **가장 큰 병목 5개:** KPI-1·5 사람 폐기 확인, KPI-1·3·5 Claude 2차 응답 300건, KPI-4 Claude 1차 응답 100건, 사람 상세 판단 최소 20건·최대 400건과 봉인 4종, KPI-2 실제 사용자 100명 전·후 PRO다.
- **권장 다음 반복 3개:** (1) KPI-3 Claude 2차 응답 확보·가져오기, (2) KPI-4 Claude 1차 초안 뒤 Codex 2차 의견 가져오기, (3) KPI-1·5 Claude 응답과 사람 폐기 확인이다.
- **주의:** 전체 실패 수를 `.pytest_cache` 항목 수로 보고하지 않는다. 실제 pytest 출력의 `FAILED` 항목이나 최종 요약을 사용한다.

## 2026-08-01 KPI-3 블라인드 Codex 1차 초안 handoff

- **선택 단계와 과제:** 교차 AI 정답지 작성 중 KPI-3의 placeholder를 별도 블라인드 Codex 응답으로 교체했다. 사람 판정·승인·봉인은 실행하지 않았다.
- **주 데이터셋과 사례 수:** `data/original_plan/kpi/ai_review_responses/kpi3_codex_blind_response_v1.json` 100건과 `data/original_plan/kpi/workbench/kpi3_workbench_v1.json` 100건이다.
- **변경 파일:** 원본 KPI-3 응답, KPI-3 워크벤치, `adaptive_answer_key_review.py`, 워크벤치 CLI, 적응형 검토 테스트, `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`다. KPI-4 응답은 아직 1차 Claude 응답이 없어 가져오지 않았다.
- **핵심 변경:** `--promote-review-response`를 명시한 경우에만 `reviewing_agent` 형식의 블라인드 응답을 1차 초안으로 전환한다. 원래 역할과 원본 파일 SHA-256을 provenance에 남긴다. 단일 답 문자열은 가져오기 경계에서 배열로 정규화하고 저장·감사 형식은 배열로 고정한다.
- **현재 상태:** KPI-3 1차 Codex 응답 100건은 등록됐다. 2차 AI 응답 0건, 사람 상세 판단 0건, 일괄 승인 0건, 봉인 0건이다. 다음 단계는 다른 제공자 계열 Claude 응답 100건이다.
- **검증:** 관련 회귀 시험 121건 PASS. KPI-3 가져오기 `READY_FOR_INDEPENDENT_AI_REVIEW`; `minimal-status`는 예상대로 `complete_independent_ai_review_required`; 무결성 감사는 출처 4/4 PASS이고 완료만 `BLOCKED`다. 전체 pytest 실제 실행은 기준선과 같은 90건 실패다. 직전 114건 보고는 stale `lastfailed` 캐시 집계 오류였다. 지정 Ruff 범위는 기존 파일 오류 2건이다.
- **공식 delta:** 엔진 입력·안전 규칙·채점식·frozen eval을 바꾸거나 실행하지 않았다. delta 0이다. replay·slice도 변경·재실행하지 않아 delta 0이다.
- **가장 큰 병목 5개:** KPI-1·5 사람 폐기 확인, KPI-1·3·5 Claude 2차 응답 300건, KPI-4 Claude 1차 응답 100건과 Codex 2차 가져오기, 사람 상세 판단 최소 20건·최대 400건과 봉인 4종, KPI-2 실제 사용자 100명 전·후 PRO다.
- **권장 다음 반복 3개:** (1) KPI-3 Claude 2차 응답을 받아 교차 비교를 연다. (2) KPI-4 Claude 1차 초안 뒤 보관 중인 Codex 응답을 붙인다. (3) KPI-1·5 Claude 응답과 사람 폐기 확인을 마친다.
- **한계:** 외부 Codex의 실제 블라인딩은 응답 자기 진술과 별도 작업 경계에 의존한다. 응답 역할 전환은 생성 당시 판단 내용을 바꾸지 않지만, 원래 파일이 2차 의견 형식이었다는 사실을 provenance로만 증명한다. 1초 하한·합의 표본 5건은 임의 기준이고 원문 234종 중 209종은 카탈로그 밖이다.

## 2026-08-01 Codex 블라인드 독립 의견 handoff

- `data/original_plan/kpi/ai_review_responses/kpi3_codex_blind_response_v1.json`: KPI-3 Codex 독립 의견 100건. 원래 응답 역할을 provenance에 남기고 1차 초안으로 가져왔다.
- `data/original_plan/kpi/ai_review_responses/kpi4_codex_blind_response_v1.json`: KPI-4 Codex 독립 2차 의견 100건.
- 두 Codex 작업은 각 KPI의 블라인드 패킷 하나만 읽었다. 패킷 SHA-256 일치, 고유 문항 100건, 누락·추가 0건, 허용 답변 밖 선택 0건, 엔진 출력 열람 없음이 확인됐다.
- KPI-4 Codex 파일은 아직 가져오지 않았다. KPI-3에는 비 OpenAI 2차 의견, KPI-4에는 비 OpenAI 1차 초안이 필요하다. Claude 응답은 아직 0건이다.
- AI 응답과 KPI-3 가져오기는 정답·사람 승인·봉인이 아니다. 다음 작업자는 필요한 비 OpenAI 응답을 확보·검증·가져온 뒤 사람의 최소 상세 검토와 명시적 일괄 승인을 받는다.
- `python scripts/run_answer_key_workbench.py discard-status --indicator KPI-1`과 KPI-5 명령은 과거 봉인 후보를 변경하지 않고 보여준다. 실제 폐기는 사람 확인이 있어야 한다.

## 2026-08-01 미확인 오류 봉인 상태 확인 handoff

- **선택 단계와 과제:** KPI-1·5 무효 봉인을 AI가 폐기 처리하지 않으면서 사람이 확인할 근거를 읽기 전용으로 표시했다. `discard-status`는 어떤 파일도 바꾸지 않는다.
- **주 데이터셋과 사례 수:** KPI-1·5 과거 봉인 각 100건, 합계 200건이다. 두 봉인은 건당 약 0.038초·수정률 0%인 자동수락 오류의 산물이므로 유효한 연구 정답지가 아니다.
- **변경 파일:** `scripts/run_answer_key_workbench.py`, `tests/test_answer_key_workbench.py`, `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`다. 사람 확인 전 증거인 `data/original_plan/kpi/seals/` 파일은 미추적 상태로 그대로 뒀다.
- **현재 상태:** KPI-1·5 모두 `AWAITING_HUMAN_CONFIRMATION`, 정식 폐기 이력 0건이다. 상태 명령이 출력한 파일 SHA-256은 KPI-1 `8918fd6fea2e839251cad4a47d3f3a1169bc37537c864d35d94b40cacdd7cf26`, KPI-5 `8822b96d2de196a39bf424f1e6d7255603f319cd442ea17bfae9f82d90b5eb61`이다.
- **검증:** `tests/test_answer_key_workbench.py` 50건 PASS, 변경 파일 Ruff PASS, `git diff --check` PASS다. KPI-1·5 실제 `discard-status`도 `mutated: false`를 반환했다.
- **공식 delta:** 엔진 입력·안전 규칙·채점식·frozen eval·replay·slice를 바꾸거나 실행하지 않았다. delta 0이다.
- **가장 큰 병목 5개:** KPI-1·5 사람 폐기 확인, 외부 AI 응답 600건, 사람 상세 판단 최소 20건·최대 400건, 새 봉인 4종, KPI-2 실제 사용자 100명의 전·후 PRO다.
- **권장 다음 반복 3개:** (1) 사람이 상태 해시를 확인하고 KPI-1·5를 정식 폐기한다. (2) 패킷 전용 외부 AI 응답을 확보해 가져온다. (3) 사람이 최소 상세 검토·일괄 승인·봉인을 수행한다.
- **한계:** 상태 명령은 파일 존재와 해시, 기록 수만 확인한다. 과거 검토의 임상적 적절성이나 폐기 사유를 대신 판단하지 않는다. 1초 검토 하한과 합의 표본 5건은 임의의 운영 기준이며, 원문 성분 234종 중 209종은 카탈로그 밖이다.

## 2026-08-01 교차 AI 기반 최소 사람 검토 handoff

- **선택 단계와 과제:** KPI-1·3·4·5의 100건 측정 표본은 유지하면서 사람의 상세 검토를 최소화했다. 브랜치는 `feat/adaptive-answer-key-review`다. push·배포·훈련·실제 트래픽·사람 판정·서명·봉인은 실행하지 않았다.
- **최소 검토 규칙:** 다른 제공자 계열 AI 두 개가 모든 사례를 독립 판단한다. 사람은 불일치, 위험 플래그, 결정적 합의 표본 5건을 상세 검토한다. 표본 1건 수정 시 20건, 2건 수정 시 모든 합의 사례로 확대한다. 나머지는 같은 사람이 정확한 확인 문구로 일괄 승인한다. 합의만으로는 자동 확정되지 않는다.
- **최소·최대 건수:** 네 지표가 모두 완전 합의하고 위험 플래그가 없으면 상세 검토는 지표별 5건, 합계 20건이다. 지표별 일괄 승인 1회도 사람이 직접 한다. 불일치나 오류가 많으면 최대 400건까지 늘어난다. 5건은 통계적·임상적 검증 표본이 아니다.
- **KPI-3·4 특수 경로:** KPI-3의 `미정_검토자가_판단`은 답이 아니므로 Claude 같은 첫 블라인드 AI 응답을 `import-primary-ai-draft`로 가져온다. KPI-4 측정 대상은 OpenAI 상담 모듈이므로 비-OpenAI 1차 초안을 같은 명령으로 넣는다. 두 지표의 2차 의견은 새 블라인드 Codex 작업처럼 1차와 다른 계열이어야 한다. 현재 Codex 작업은 엔진 정책을 이미 읽어 검수자를 대신하지 않았다.
- **감사·봉인:** 블라인드 패킷과 AI 응답은 SHA-256으로 묶는다. 같은 계열 AI, 알 수 없는 제공자 계열, 금지 출처, 누락 사례, 어휘 밖 답, 엔진 출력 열람, 빠진 블라인딩 경로, 변조된 일괄 승인, 잘못된 시간 순서, 상세 검토로 위장한 일괄 결정을 차단한다. `reference_standard_seal_v2`는 정답과 provenance 전체를 해시하고 현재 워크벤치와 다시 대조한다. KPI-4 봉인은 상담 모델 제공자 계열을 필수로 받고 1차 AI와 같으면 거부한다.
- **현재 데이터 상태:** KPI-1·3·4·5 각 100건, 총 400건은 그대로다. 실제 독립 AI 응답, 사람 상세 판단, 일괄 승인, 새 봉인은 모두 0건이다. 네 블라인드 패킷만 준비됐다. KPI-1·5의 과속 봉인은 `seals/discarded/`에 보존됐지만 사람 확인이 있는 정식 폐기 기록은 아직 없다.
- **주요 파일:** `adaptive_answer_key_review.py`, `answer_key_workbench.py`, `answer_key_integrity.py`, `reference_standard.py`, 두 봉인 CLI, `data/original_plan/kpi/ai_review_packets/`, 계약·KPI 전략·관련 테스트다. 엔진·안전 규칙·채점 로직·frozen eval·replay·slice는 바꾸지 않았다.
- **검증:** 관련 기능·봉인·완료 게이트 테스트 190건 PASS. 전체 pytest는 기존과 같은 90건 실패, 전체 Ruff는 기존과 같은 28건으로 신규 실패·오류 0건이다. 엔진 입력 레지스트리 재생성 diff가 없고 정답지 출처 감사는 4/4 PASS이며, 사람 결정·봉인이 없어서 완료 상태는 `BLOCKED`다.
- **공식 delta:** 엔진 입력·채점식·frozen eval을 바꾸거나 다시 실행하지 않아 공식 frozen metric delta는 0이다. replay·slice 데이터와 산출물도 바꾸지 않아 delta 0이다.
- **감사 한계:** 외부 AI 블라인딩은 응답의 자기 진술과 별도 실행 증빙에 의존한다. AST는 파일 단위이고, 제공자 계열 판별은 알려진 이름에 대한 휴리스틱이다. 1초 검토 하한과 합의 표본 5건은 과학적 충분성 기준이 아닌 임의의 운영 하한이다. 원문 성분 234종 중 209종은 카탈로그 밖이라 채점에서 빠진다.
- **가장 큰 병목 5개:** KPI-1·5 과속 봉인의 사람 폐기 확인, KPI-1·5의 Claude 2차 응답 200건, KPI-3·4의 Claude 1차·블라인드 Codex 2차 응답 400건, 최소 20건부터 최대 400건인 사람 상세 판단과 지표별 승인·봉인, KPI-2 실제 사용자 100명의 전·후 PRO다.
- **권장 다음 반복 3개:** (1) 사람이 KPI-1·5 봉인을 정식 폐기하고 패킷 전용 외부 AI 응답을 확보한다. (2) 응답을 가져와 사람이 `review-minimal`·`approve-consensus`·`seal`을 수행한다. (3) KPI-2 실제 사용자 100명의 전·후 PRO 수집 경로를 시작한다.

## 2026-07-31 KPI 정답지 무결성 게이트 handoff

- **선택 단계:** TIPS KPI-1·3·4·5 reference-standard integrity.
- **선택 과제:** 실제 파일 읽기 기반 출처 감사, 감사 가능한 봉인 폐기 명령, 과속 판단 저장 차단, 두 봉인 CLI·완료 마법사·최종 감사의 fail-closed 게이트, 초안 에이전트 provenance를 구현했다.
- **주 데이터셋과 사례 수:** `data/original_plan/kpi/workbench/`의 KPI-1·3·4·5 각 100건, 총 400건. 현재 판단 기록은 0건이며 사람이 검토해야 한다. `engine_input_registry_v1.json`은 입력 10개를 `engine_logic` 9개와 `vocabulary` 1개로 분류한다.
- **변경 파일:** 무결성·워크벤치 모듈, 두 봉인 CLI, 두 draft builder, 완료 마법사와 최종 감사 실행기, 계약, workbench 4종, CI workflow, 관련 시험, KPI 전략 문서와 인계 문서 3종이다.
- **핵심 변경:** AST가 실제 읽기 호출로 이어지는 경로만 찾고 선언 전용 `BLINDED_FROM`을 제외한다. 선언 목록을 반복문이나 컴프리헨션이 실제 읽으면 위반으로 잡는다. 출처 인덱스는 지표와 모듈이 붙은 출처를 함께 사용한다. 1.0초 미만 검토 입력은 저장하지 않는다. 봉인은 현재 감사 PASS·전 건 판단·검토 시간 PASS를 요구한다. 새 봉인은 폐기 이력, `drafting_agent`, `blinded_from`, 감사 스냅샷을 보존한다. KPI-4는 OpenAI 계열처럼 초안 에이전트와 상담 모듈 제공자 계열이 같으면 봉인하지 않는다.
- **폐기 상태:** KPI-1·5 오류 봉인 파일은 `seals/discarded/`에 남아 있지만 폐기자·시각·사유가 있는 사람 확인 기록은 없다. 이 이동은 정식 폐기가 아니다. `discard-seal`은 활성 봉인과 이 사전 이동 파일을 모두 찾으며, 사람이 정확한 확인 문구를 입력해야 append-only 이력을 만든다. 파일과 판단을 임의로 복원하거나 폐기 승인을 대신 만들지 않았다.
- **검증 명령과 결과:** `python scripts/audit_answer_key_integrity.py --json`은 출처 감사 4/4 PASS, 실패 0건, 완료 상태 `BLOCKED`를 반환했다. 전체 `python -m pytest -q --tb=no`는 기준선과 같은 90건 실패로 신규 실패 0건이다. 전체 `python -m ruff check .`은 기준선과 같은 28건으로 신규 오류 0건이다. 변경 파일 Ruff, YAML 파싱, 엔진 입력 레지스트리 재생성과 diff 확인도 통과했다.
- **커밋과 브랜치:** `1700616`, `e9bf924`, `f8a272d`; 최종 브랜치는 `fix/kpi-answer-key-integrity-clean`이다. 사람 확인 없는 봉인 파일을 포함한 다른 작업 브랜치 커밋은 main에 병합하지 않는다.
- **공식 frozen eval metric delta:** 엔진 입력·frozen eval·채점 로직을 바꾸거나 다시 평가하지 않았다. delta 0이다.
- **replay·slice delta:** replay와 slice 데이터·산출물을 바꾸지 않았다. delta 0이다.
- **가장 큰 병목 5개:** KPI-1·5 사람 폐기 확인, 사람 판단 400건, 새 봉인 4종, KPI-4 에이전트 분리 증거, KPI-2 실제 사용자 100명 전·후 PRO다.
- **권장 다음 반복 3개:** 사람이 KPI-1·5 폐기를 확인, 사람이 400건 검토, 감사 PASS를 확인한 지표부터 봉인하는 순서다.
- **감사 한계:** 파일을 읽고 정답에 쓰지 않은 경우를 구분하지 못한다. 1.0초 하한은 임의 기준이다. 이 두 한계를 조용한 예외로 숨기지 않는다.

## 2026-07-31 KPI-3·4 초안 감사 + KPI-2 경로 확정 handoff

- **선택 단계와 과제:** 정답 400건 확정을 요청받았으나 확정은 사람의 행위여서 수행하지 않았다. 대신 `NEXT_STEPS.md` 3번(KPI-3·4 출처 독립성 감사)을 수행하고 KPI-2 경로를 기록했다. 브랜치 `kpi2-decision-record`; push·배포·훈련·사람 판정·서명·봉인 없음.
- **주 데이터셋과 사례 수:** 워크벤치 4종 각 100건(총 400건, 전부 pending 유지). 감사 대상은 `kpi3_workbench_v1.json`, `kpi4_workbench_v1.json`.
- **변경 파일:** `data/original_plan/contracts/kpi_measurement_contract_v1.json`, `docs/original_plan/KPI_COMPLIANCE_STRATEGY.md`, `NEXT_STEPS.md`, `PROGRESS.md`, `SESSION_HANDOFF.md`. 코드·초안·봉인 파일은 건드리지 않았다.
- **핵심 변경:** 두 가지다. (1) **KPI-3·4 초안이 봉인 부적합임을 확인했다.** KPI-3의 정답은 엔진이 `interim/next_action.py:79`에서 읽는 바로 그 정책 파일의 `action` 값이고 문항은 그 규칙 자신의 `when` 절로 생성돼, 정확도가 구조적으로 100%가 된다(고유 정답 9개). KPI-4는 고유 문항이 57개뿐이라 100문항 요건에 미달하고 고유 정답은 5개다. 두 워크벤치의 `draft_source` 라벨도 실제 출처와 다르다. (2) KPI-2 경로를 A(운영 사용자 확보) + 측정 3차년도로 기록했다.
- **코드·데이터·학습·시뮬레이션:** 코드 변경 0건. 엔진·안전 규칙·채점 로직·학습·시뮬레이션·초안 데이터 모두 그대로다. 워크벤치 400건은 전부 pending이고 `reviewers`는 비어 있다.
- **검증 명령과 결과:** 전체 `pytest -q --tb=no` **90 failed**(기준선 89 + 옆 저장소 이동으로 깨진 영수증 1건), 신규 실패 0건. `ruff check .` 28건으로 신규 0건. 계약 JSON 파싱과 `chosen` 필드 확인 통과.
- **공식 frozen eval delta:** frozen eval 데이터와 지표를 바꾸지 않았다. delta는 0이다.
- **replay·slice delta:** 엔진 입력·산출물을 바꾸지 않았다. delta는 0이다.
- **병목 5개:** KPI-3·4 초안 교체용 독립 출처 미정, KPI-1·5 사람 확정 미실행, KPI-2 전·후 PRO 수집 미착수, 학습 게이트 NO-GO, 최종 영수증이 옆 저장소 커밋에 묶여 깨진 상태다.
- **다음 세 반복:** KPI-3·4 독립 출처 결정, KPI-1·5 사람 확정과 봉인, KPI-2 수집 흐름 부착 순서다.
- **아침에 사람이 확인할 세 가지:** KPI-3·4를 어떤 출처로 다시 만들지, KPI-2 경로 A 기록에 이의가 없는지(계약 파일 `chosen_detail` 한 필드만 바꾸면 됨), KPI-1·5 확정을 누가 언제 앉아서 할지다.

## 2026-07-31 독립 참조 코퍼스 handoff

- **선택 단계와 과제:** KPI-1·5 정답 초안이 측정 대상 엔진과 출처를 공유하는지 감사하고, 겹치지 않는 출판 저작물로 교체했다. 브랜치 `book-corpus-answer-keys`; push·배포·훈련·사람 판정·봉인 없음.
- **주 데이터셋과 사례 수:** `data/knowledge/external/health_checker_reference_extract_v1.json` — 판정 사례 138건, 약물 맥락 7종, 성분 매핑 25종. 초안은 KPI-1 100건, KPI-5 100건.
- **변경 파일:** 새 `scripts/build_health_checker_reference_extract.py`, `scripts/build_reference_corpus_answer_key_drafts.py`, `src/wellnessbox_rnd/evals/reference_corpus_drafters.py`, `tests/test_reference_corpus_drafters.py`, 추출물·초안 데이터, `docs/original_plan/KPI_COMPLIANCE_STRATEGY.md` 갱신, 인계 문서 3종.
- **핵심 변경:** 정답 초안 출처를 엔진 밖으로 옮겼다. 판정 상태의 원문 권장 성분에 그 사례가 명시한 약물의 고갈 성분을 더하므로 정답이 맥락을 따라 움직인다. 서로 다른 정답 조합 7 → 67.
- **코드·데이터·학습·시뮬레이션:** 엔진 지식베이스, 안전 규칙, 채점 로직, 학습·시뮬레이션 코드는 건드리지 않았다. 기존 `answer_key_drafters.py` 와 작업대 CLI도 그대로 두고 `--cases` 경로로만 연결했다.
- **검증 명령과 결과:** `pytest tests/test_reference_corpus_drafters.py` 12 passed; `pytest tests/test_answer_key_workbench.py` 32 passed; `pytest -k "answer_key or reference_standard or reference_corpus"` 66 passed; 신규 파일 `ruff check` 0건.
- **공식 frozen eval delta:** frozen eval 데이터와 지표를 바꾸지 않았다. delta는 0이다.
- **replay·slice delta:** 엔진 입력·산출물을 바꾸지 않았다. delta는 0이다.
- **병목 5개:** KPI-1·5 사람 확정 미실행, 카탈로그 12종 한계로 원문 성분 209종 채점 제외, KPI-3·4 초안 출처 미감사, KPI-2 실사용자 100명, 학습 게이트 NO-GO다.
- **다음 세 반복:** KPI-1·5 확정과 봉인, 카탈로그 확장, KPI-3·4 출처 감사 순서다.
- **아침에 사람이 확인할 세 가지:** KPI-1 초안 한 건의 근거 문구가 원문 쪽수와 맞는지, 소아·임신 교차 사례를 남길지 반려할지, 카탈로그 확장을 어디까지 할지다.

## 2026-07-30 원스텝 실행기 handoff

- **선택 단계와 과제:** 남은 연구 과정을 사람이 켜서 다음다음만 눌러 끝낼 수 있게 안내 실행기를 만들었다. 브랜치 `one-step-completion-wizard`; push·배포·훈련·사람 판정·서명 없음.
- **주 데이터셋과 사례 수:** OP-039 고위험 검토 10건, OP-120 감사 8건. 새 데이터셋은 만들지 않았다.
- **변경 파일:** 새 `src/wellnessbox_rnd/governance/completion_wizard.py`, `scripts/run_research_completion_wizard.py`, `research-complete.cmd`, `docs/original_plan/ONE_STEP_COMPLETION_GUIDE.md`, `tests/test_completion_wizard.py`와 이 세 인계 문서다.
- **핵심 변경:** 12단계를 하나의 흐름으로 묶었다. 자동 단계는 스스로 실행하고 사람 단계는 화면을 띄운 뒤 기다린다. Enter를 눌러도 저장이 확인되지 않으면 넘어가지 않고 무엇이 빠졌는지 알려 준다. 세션 시작 시각 이전 기록은 이번 세션 근거로 세지 않는다.
- **코드·데이터·학습·시뮬레이션:** 새 코드는 마법사 모듈과 실행기, 런처뿐이다. 추천·안전·학습·시뮬레이션 코드와 모델, 원천·frozen 데이터는 그대로다. 운영 DB에도 쓰지 않는다.
- **검증 명령과 결과:** `pytest tests/test_completion_wizard.py` 34 passed; `research-complete.cmd --status` 실행 결과 2/12 단계 완료로 과거 기록을 정확히 제외; 전체 pytest `1,235 passed / 89 failed`, 새 실패 0건; 전체 Ruff 28건으로 신규 0건.
- **공식 frozen eval delta:** 데이터와 지표를 바꾸거나 다시 평가하지 않았다. delta는 0이다.
- **replay·slice delta:** 입력·산출물을 바꾸지 않았다. delta는 0이다.
- **병목 5개:** 학습 게이트 NO-GO, 실제 프로필 5건 미실행, 3차년도 약사 자격 재검토, 기존 pytest 실패 89건, 기존 Ruff 28건이다.
- **다음 세 반복:** `research-complete.cmd` 로 2차년도 세션을 끝까지 수행, CGM 기하 blocker 해소, 3차년도 자격 단계 전환 순서다.
- **아침에 사람이 확인할 세 가지:** `research-complete.cmd --status` 를 한 번 실행해 12단계 목록이 이해되는지, 과거 기록이 제외된 이유가 납득되는지, 실제 참여자 5명의 자료가 준비됐는지다.

## 2026-07-30 예비 약사 자격 구조 handoff

- **선택 단계와 과제:** 안전 검토자의 자격 표현을 사실에 맞게 재설정했다. 과제 참여자 두 사람은 2026-07 현재 약사 면허가 없고 2027-01 취득 예정이므로, 2차년도 검토를 예비 약사 사전 검토로 기록하도록 코드·데이터·문서를 모두 바꿨다. 브랜치 `pre-licensure-reviewer-model`; push·배포·훈련·사람 판정·서명 없음.
- **주 데이터셋과 사례 수:** OP-039 고위험 검토 `data/original_plan/op039_external_review_cases_v1.json` 10건, OP-120 감사 `data/original_plan/op120_final_completion_audit_cases_v1.json` 8건.
- **변경 파일:** `src/wellnessbox_rnd/governance/reviewer_credentials.py`, `final_session_console.py`, `data/original_plan/contracts/op039_reviewer_identity_registry_v1.json`, `scripts/build_op039_external_review_package.py`와 생성된 검토 화면·패키지, 새 `docs/original_plan/REVIEWER_QUALIFICATION_POLICY.md`, `FINAL_SESSION_RUNBOOK.md`, `human_signoff_checklist.md`, `OPERATIONAL_AND_PHARMACIST_SESSION_PROCEDURE.md`, `OPERATIONAL_SESSION_QUICK_GUIDE.md`, `PROJECT_SUMMARY_PLAIN.md`, `research_reports/OP-039.md`, `_OPEN_QUESTIONS.md`, 연구 활동 원장, OP-120 감사 JSON, 시험 3종과 이 세 인계 문서다.
- **핵심 변경:** 검토 화면 입력을 성명·소속·서명 세 개로 줄였다. 면허 번호와 자격 확인 방법은 2차년도에 받지 않는다. 존재하지 않는 값이기 때문이다. 백엔드는 오너·시스템 계정 차단, 등록 참여자 확인, 소속 일치, H-003 원장 교차확인, `licensed_pharmacist` 허위 주장 차단을 수행한다. 예비 약사 검토는 OP-039를 `EXTERNAL`로 올리지 않고 `requires_licensed_reconfirmation=true`를 남긴다.
- **코드·데이터·학습·시뮬레이션:** 자격 검증 모듈과 신원 원장, 검토 화면 생성기만 바꿨다. 추천·안전·학습·시뮬레이션 코드와 모델, 원천·frozen 데이터는 그대로다. 훈련과 고정 평가를 실행하지 않았다.
- **검증 명령과 결과:** `pytest tests/test_reviewer_credentials.py` 30 passed; `tests/test_op039_reviewer_form_neutrality.py` 7 passed; `tests/test_final_session_console.py` 27 passed; 실제 preflight `READY`·종료 코드 0·차단 0건, 저장 경계 5개 불변; `run_final_completion_audit.py` 120/120 `READY`; 전체 pytest는 아래 최종 수치를 따른다.
- **공식 frozen eval delta:** 256건 데이터와 7개 지표를 바꾸거나 다시 평가하지 않았다. delta는 0이다.
- **replay·slice delta:** 입력·산출물을 바꾸지 않았다. delta는 0이다.
- **병목 5개:** 학습 게이트가 NO-GO라 후보 모델을 못 만드는 점, 서로 다른 실제 프로필 5건의 전체 경로가 아직 실행되지 않은 점, 3차년도 약사 자격 재검토가 남은 점, 기존 pytest 실패 89건, 기존 Ruff 28건이다.
- **다음 세 반복:** CGM 기하 blocker 해소, 실제 프로필 5건 실행, 2차년도 최종 세션을 예비 약사 검토로 완료 순서다.
- **3차년도 전환 방법:** `op039_reviewer_identity_registry_v1.json`의 `qualification_stage`를 `licensed_pharmacist`로 바꾸고 각 참여자 항목의 자격 단계도 함께 올린다. 코드 수정은 필요 없다. 그 뒤 같은 10개 사례를 다시 검토하면 증거 성격이 `licensed_pharmacist_expert_safety_review`로 바뀐다.
- **아침에 사람이 확인할 세 가지:** `data/original_plan/final_session/op039_external_reviewer_form.html`을 열어 입력란이 성명·소속·서명 셋뿐인지, `REVIEWER_QUALIFICATION_POLICY.md`의 면허 취득 시기(2027-01)와 마감(2027-10)이 실제 일정과 맞는지, 두 참여자의 소속 표기가 과제 등록 정보와 같은지다.

## 2026-07-27 H-005 중립화·H-003 학습 계보 handoff

- **선택 단계와 과제:** 사람 최종 세션을 막던 두 결함을 실제로 고쳤다. H-005 검토 화면 중립화와 H-003 승인 초안 학습·평가 계보 구현이다. 브랜치 `h005-neutral-h003-lineage`; push·배포·훈련·사람 판정·서명 없음.
- **주 데이터셋과 사례 수:** OP-039 고위험 검토 `data/original_plan/op039_external_review_cases_v1.json` 10건, OP-120 감사 `data/original_plan/op120_final_completion_audit_cases_v1.json` 8건, 고정 평가 256건(실행하지 않음).
- **변경 파일:** `scripts/build_op039_external_review_package.py`, `data/original_plan/final_session/op039_external_reviewer_form.html`과 검토 패키지 zip, `tests/test_final_session_console.py`, 새 `tests/test_op039_reviewer_form_neutrality.py`, 새 `src/wellnessbox_rnd/training/approved_draft_dataset.py`·`candidate_promotion.py`, 새 `scripts/build_approved_draft_dataset.py`·`train_approved_draft_candidate.py`·`decide_candidate_promotion.py`, `src/wellnessbox_rnd/evals/runner.py`, `scripts/run_eval.py`, 새 `tests/test_approved_draft_training_lineage.py`, OP-120 감사 JSON, `FINAL_SESSION_RUNBOOK.md`, `_OPEN_QUESTIONS.md`, 연구 활동 원장과 이 세 인계 문서다. 추적되지 않은 과거 영수증·uploads는 건드리지 않았다.
- **핵심 변경:** H-005 화면이 어떤 판정도 미리 고르지 않는다. 라디오 20개 미선택, 의견란 10개 공백, 면허·자격 확인 방법·서명이 빈 입력란이며 서명은 성명과 일치해야 한다. H-003은 승인 전용 manifest → 게이트로 잠긴 학습 → 후보 artifact 주입 평가 → 안전 회귀 gate → 교체·유지와 rollback 영수증으로 이어지는 여섯 구간을 모두 채웠다.
- **코드·데이터·학습·시뮬레이션:** 새 코드는 검토 화면 생성기 재작성, 학습 계보 모듈 2개, CLI 3개, 시험 2개다. 추천·안전·시뮬레이션 로직은 바꾸지 않았다. `run_eval`에 후보 artifact 인자를 더했으나 기본 동작은 그대로다. 훈련·frozen eval을 실행하지 않았고 모델과 원천 데이터도 바꾸지 않았다.
- **검증 명령과 결과:** 실제 preflight → `READY`, 종료 코드 0, 차단 0건, H-005 0/0 선입력, 다섯 저장 경계 모두 `true`, 잔류 listener 없음; `pytest tests/test_op039_reviewer_form_neutrality.py` → 6 passed; `pytest tests/test_approved_draft_training_lineage.py` → 20 passed; `pytest tests/test_final_session_console.py` → 27 passed; `python scripts/run_final_completion_audit.py` → 120/120 `READY`, `goal_complete=true`, 차단 0건; 실제 원장 manifest → `READY`, 승인 6건 전부 권혁찬, 오너 계정 1건 제외, DB 해시 불변; 전체 pytest `1,170 passed / 89 failed / 5 warnings`, 167초, 새 실패 0건; 전체 Ruff 29건(기존 32건에서 3건 감소, 신규 0건).
- **공식 frozen eval delta:** 256건 데이터와 7개 공식 지표를 바꾸거나 다시 평가하지 않았다. delta는 0이다.
- **replay·slice delta:** 입력·산출물을 바꾸지 않았다. delta는 0이다.
- **병목 5개:** 면허 번호의 실제 발급 여부를 조회하지 못해 현장 확인에 의존하는 점, 학습 게이트가 NO-GO라 후보 모델을 아직 만들 수 없는 점, 서로 다른 실제 프로필 5건의 전체 경로가 아직 실행되지 않은 점, 기존 pytest 실패 89건, 기존 Ruff 29건이다.
- **다음 세 반복:** 학습 게이트를 여는 CGM 기하 blocker 해소, 실제 후속 자료로 통제된 사람 최종 세션 수행, 그 뒤 연구 종료 단계에서 외부 기관 평가 접수 순서다.
- **병합 판정:** preflight `READY`, 감사 120/120 `READY`, pytest 새 실패 0건, Ruff 신규 0건을 모두 충족했다. 이 handoff 커밋 뒤 `main`에 fast-forward 병합하며 push는 하지 않는다.
- **아침에 사람이 확인할 세 가지:** `data/original_plan/final_session/op039_external_reviewer_form.html`을 직접 열어 10건이 정말 비어 있는지, 권혁찬 약사의 실제 면허 번호와 자격 확인 방법을 현장에서 받을 준비가 됐는지, 학습 게이트를 여는 CGM 기하 blocker를 언제 다룰지다. OP-039 외부 기관 평가는 연구 종료 후 단계이므로 지금 준비할 항목이 아니다.

## 2026-07-27 근거 심화·감사 정본·사전 점검 최종 handoff

- **선택 단계와 과제:** 목표의 단계 0~5 전체다. 보고서 53편의 등록 근거를 끝까지 다시 읽고, 내용과 증거 단계를 바로잡은 뒤 OP-120 감사, Ruff 출처, 런북, H-005, H-003과 전체 회귀를 확인했다.
- **주 데이터셋과 사례 수:** `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `5a2fc3d6549062ba919567d89273bd953391f324091538f8f621ab1eccbf7c29`.
- **변경 파일:** 대상 OP 보고서 53편, `docs/original_plan/EVIDENCE_VERIFICATION_REPORT.md`, 연구보고서의 `_REWRITE_TARGETS.md`·`_REWRITE_PROGRESS.md`·`_OPEN_QUESTIONS.md`, OP-120 감사 JSON, `scripts/run_final_session_preflight.py`, 전용 테스트, 새 `data/original_plan/evidence/evidence_verification_ledger_v1.json`과 `scripts/verify_evidence_verification_ledger.py`, `FINAL_SESSION_RUNBOOK.md`, 연구 활동 원장·요약과 이 세 인계 문서다. `COMPLETION_STATUS.md`와 추적되지 않은 과거 영수증·uploads는 건드리지 않았다.
- **핵심 변경:** 보고서 32편의 단계·버전·해시·함수·입력 또는 증거 해석을 고쳤다. manifest 파일 경로 492건은 모두 존재하고 최종 내용 불일치는 0건이다. 447개 OP-경로 판정을 행 단위 원장(SHA-256 `21d1388ed3912174126ae435a85aa80baa991ebd65d1b6aeb3ad0b9816319257`)과 전용 검증기로 재현할 수 있게 했다. 무영수증 preflight는 임시 DB·상태만 사용하고, DB 세 파일·제어 파일·최종 세션 직접 파일·운영 영수증의 다섯 저장 경계를 각각 비교한다. H-005 검사는 Chromium이 렌더링한 DOM을 읽어 동적으로 주입된 선택·의견도 잡는다.
- **코드·데이터·학습·시뮬레이션:** 새 코드는 사전 점검 스크립트, 근거 원장 검증기와 전용 테스트뿐이다. 추천·안전·학습·시뮬레이션 코드는 바꾸지 않았다. 원천·frozen·학습 데이터와 모델도 바꾸지 않았고 훈련·배포·사람 판정·서명을 실행하지 않았다.
- **검증 명령과 결과:** `python scripts/run_final_completion_audit.py` → 120/120, 누락·단계·외부 격차 0, `READY`, `goal_complete=true`, `blockers []`; `python scripts/verify_evidence_verification_ledger.py` → `READY`, 447/447, 누락·불일치 0; `python -m pytest tests/test_final_session_preflight.py -q` → 10 passed; 전용 Ruff와 `python -m py_compile` 통과; 실제 preflight는 서버·화면 정상에 다섯 저장 경계 모두 `true`, H-005 선입력 때문에 예상된 `BLOCKED`(종료 코드 2, 차단 1건); 전체 pytest `1,144 passed / 89 failed / 5 warnings`, 실측 177초, 새 실패 0건; 전체 Ruff는 기존 32건이다.
- **공식 frozen eval delta:** 256건 데이터와 7개 공식 지표를 바꾸거나 다시 평가하지 않았다. 입력·산출물 delta는 0이다.
- **replay·slice delta:** replay와 weakest slice 입력·산출물을 바꾸지 않았다. delta는 0이다.
- **병목 5개:** H-005 판정·의견 선입력, 면허·자격 확인·별도 서명 검증 부재, H-003 승인 초안→학습→후보 평가 계보 부재, DB 5/5를 유효한 사람 세션 5건으로 볼 수 없는 점, 기존 Ruff 32건과 전체 pytest 89건의 장기 부채다.
- **다음 세 반복:** H-005 중립성과 자격 gate 구현, H-003 approved-only 학습·후보 평가·안전 회귀 gate 구현, 실제 후속 자료를 사용한 통제된 사람 최종 세션 순서다.
- **병합 판정:** OP-120 120/120 `READY`, 보고서 내용 불일치 0건, pytest 새 실패 0건을 모두 충족했다. 이 handoff 커밋 뒤 `report-quality-pass`를 `main`에 fast-forward 병합하며 push는 하지 않는다.
- **아침에 사람이 확인할 세 가지:** H-005 화면의 모든 선택과 의견이 비어 있는지, 검토자의 실제 면허·자격 확인 방법·별도 서명을 받을 수 있는지, 서로 다른 실제 프로필 5건에 실제 후속 자료와 동의 근거가 준비됐는지 확인한다.

## 2026-07-23 OP-027/028 최종 handoff

- 단계/과제: 이벤트 중복 방지와 사용자 데이터 정정·삭제 계보 연구보고서 backfill. OP-027/028은 `IMPLEMENTED / COMPLETE`다.
- dataset: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `d32cfd1b8830f5c727696556bc6ecc247abc01ca54e3c2f5d461ea76cdf077da`; mutation smoke 3건 SHA-256 `980e5677adcb54db684679a3111b0a6927b4e5fc47d6ddc7c9cc8bf6ab19dfb8`; OP-120 evidence `e9d00582015a0ea0581d107eb212601ded346468030004641304c486ddba281d`.
- 변경: OP-027/028 장문 보고서, schema 14 canonical smoke, 증거 현재성 회귀 테스트, OP-120 보고서 재고와 evidence를 갱신했다.
- 결과: 물리 70개, 유효 48/120, 누락·부적합 72개, 327,598자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- 검증: focused pytest 106건, tracked Ruff, manifest audit, completion check PASS. 독립 검토 `Critical 0 / Important 0 / Minor 0`; CI `29970576517` 성공.
- R&D 증거 HEAD `e7e0d3918035a24a4a7cd40da6f24b68ba1b94f6`은 `origin/main`에 있다. 서비스는 `8b9e2df62c998147ef045390909f7244501ef6e8`을 유지했고 기존 사용자 변경을 보존했다.
- 코드 변경은 증거 현재성 테스트뿐이다. production·서비스·원천/frozen/학습 데이터·모델·simulation 변경 없음; frozen/replay/slice delta 0. 다음: OP-029/030, OP-031/032, OP-033/034.

## 2026-07-23 OP-025/026 최종 handoff

- 단계/과제: 사용자 행동·연구평가 로그 분리와 model·engine·code·dataset·config 실행 identity 보고서 backfill. OP-025/026 `IMPLEMENTED / COMPLETE`.
- dataset 8건 SHA-256 `99245ed22d1401e07898138da4efd1b8853edf085e1e6c4fec443dd2ee2198a1`; log identity smoke 2건 SHA-256 `4bda8974a6eba797d9d585a2eff8fd15611cdffdf169dee27be95540041ac221`; OP-120 evidence `68aaa12d6c0541324fe27f888b9392d30ddff03dcbbf8a432b0ff11a2bca426b`.
- 결과: 물리 68개, 유효 46/120, 누락·부적합 74개, 316,581자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- 결함 수정: smoke schema 8을 14로 재생하고 dataset ID 목록을 현재 코드 상수에서 계산하게 했다. evidence 현재성 테스트도 추가했다.
- 독립 검토 Minor 1건은 OP-025의 공통·behavior 전용 열 설명을 수정한 뒤 `Critical 0 / Important 0 / Minor 0`으로 종료했다.
- 검증: focused pytest 92, tracked Ruff, manifest audit, completion check PASS. CI `29969740776` 성공.
- R&D 증거 HEAD `bddfb09da5dab94d41abdafc9bf30cb11b58f170`은 `origin/main`에 있다. 서비스는 `8b9e2df62c998147ef045390909f7244501ef6e8`에 유지했고 기존 사용자 변경을 보존했다.
- production·서비스·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen/replay/slice delta 0. 다음: OP-027/028, OP-029/030, OP-031/032.

## 2026-07-23 OP-023/024 최종 handoff

- 단계/과제: 원문·파싱 구간·주장·규칙·추천 결과 계보와 지식 source lifecycle·type·license 저장 보고서 backfill. OP-023/024 `IMPLEMENTED / COMPLETE`.
- dataset 8건 SHA-256 `39e363ecae5f1f7187e0edd25a01cc553cc77bdf816252491f85f64007749970`; knowledge smoke 1건 SHA-256 `b13b97b0ccb20ba4cda96bc8f4b32acc398f49a683adda20ab09d06685d504fd`; OP-120 evidence `17189085bee1c02a4a350d8bbf333a1d5da082938d6f15704ec8566d1f138c16`.
- 결과: 물리 66개, 유효 44/120, 누락·부적합 76개, 304,015자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- 결함 수정: smoke가 schema 8과 초기 artifact count를 고정했다. schema 14·정본 artifact count를 동적으로 비교하고 evidence 현재성 테스트를 추가했다.
- 독립 검토 `0/1/1`은 runtime quarantine 과장과 claim-rule 검증 방향 문구를 바로잡은 뒤 `Critical 0 / Important 0 / Minor 0`으로 종료했다.
- 검증: focused pytest 87, tracked Ruff, manifest audit, completion check PASS. CI `29968699617` 성공.
- R&D 증거 HEAD `186ee41f891477e35b30ea3fbb2a48fb48f92c6a`은 `origin/main`에 있다. 서비스는 `8b9e2df62c998147ef045390909f7244501ef6e8`에 유지했고 기존 사용자 변경을 보존했다.
- production·서비스·원천 지식·frozen/학습 데이터·모델·simulation 변경 없음. frozen/replay/slice delta 0. 다음: OP-025/026, OP-027/028, OP-029/030.

## 2026-07-23 OP-021/022 최종 handoff

- 단계/과제: 프로필·동의 snapshot 영속화와 추천·안전·최적화·대화·후속평가 공통 실행 ID 보고서 backfill. OP-021/022 `IMPLEMENTED / COMPLETE`.
- dataset 8건 SHA-256 `eb6fa5b6bdfdadf0f81d28aec9d941847f951b0cbfda08408dc38313936ecd02`; lineage smoke 3건 SHA-256 `4ed927ba7a081b74b5fd1a7dff62a67ac797ba7450dd90fcb489b7e210e0da97`; OP-120 evidence `d8059938b8487452b68c3c4a26ffa8f24429f6119750286d725cf2d6941dccb6`.
- 결과: 물리 64개, 유효 42/120, 누락·부적합 78개, 292,110자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- 독립 검토 Important 1건은 stale schema 8 smoke였다. schema 14 재생과 `SCHEMA_VERSION` 직접 비교 회귀 테스트로 수정했고 최종 재검토는 `Critical 0 / Important 0 / Minor 0`이다.
- 검증: 수정 후 R&D focused pytest 109, 서비스 QA 17 checks, tracked Ruff, manifest audit, completion check PASS. CI `29940069699` 성공.
- R&D HEAD `e8e5e133a5d9c2a4be5ca1c2802ca8bf4c6bd4ac`은 `origin/main`에 있다. 서비스는 `8b9e2df62c998147ef045390909f7244501ef6e8`에 유지했고 기존 사용자 변경을 보존했다.
- 서비스 보호 변경·production·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen/replay/slice delta 0. 다음: OP-023/024, OP-025/026, OP-027/028.

## 2026-07-23 OP-019/020 최종 handoff

- 단계/과제: WellnessBox profile adapter와 미지원 입력·지원 결측 계약 보고서 backfill. OP-019/020 `INTEGRATED / COMPLETE`.
- dataset 8건 SHA-256 `a0c4255339a2945dce61bd330d427693ef4f797799c246db603028447206a545`; OP-120 evidence `6318bd672f8202dfe5513641f4edad694c47123a082e0fc0390f45a79752a6b7`.
- 결과: 물리 62개, 유효 40/120, 누락·부적합 80개, 282,078자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- 검증: R&D focused pytest 72, 서비스 QA 17 checks, tracked Ruff, manifest audit, completion check PASS. 독립 검토 `0/0/0`.
- CI `29937570061`: 최초 OP-115/116 과거 build 재생이 일시 실패했으나 동일 source failed-job 재실행은 전체 성공했다.
- 서비스 보호 변경·production·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen/replay/slice delta 0. 다음: OP-021/022, OP-023/024, OP-025/026.

## 2026-07-23 OP-017/018 최종 handoff

- 단계/과제: 출처별 동의와 안정된 정규화 입력 hash 보고서 backfill. OP-017/018 `IMPLEMENTED / COMPLETE`.
- dataset 8건 SHA-256 `b5991cc307f5fa6cea20fb3165d57798a9389d50338adb89da51c807debbcf6d`; OP-120 evidence `ca11bc8843c4f7a92a3336f16e09f1e0d268b16e2879d8d5f0e8d56074b98bb0`.
- 결과: 물리 60개, 유효 38/120, 누락·부적합 82개, 274,237자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- 검증: focused pytest 62, tracked Ruff, manifest audit, completion check PASS. 독립 검토 `0/0/0`; CI `29935977162` 성공.
- 서비스·production·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen/replay/slice delta 0. 다음: OP-019/020, OP-021/022, OP-023/024.

## 2026-07-23 OP-015/016 최종 handoff

- 단계/과제: 식사·생활 습관과 검사 관측값 구조화 입력 보고서 backfill. OP-015/016 `IMPLEMENTED / COMPLETE`.
- dataset 8건 SHA-256 `9911c8b9344d82478bfa5aad41524f7507c9dbc9185df0501bd3b7372be7e1eb`; OP-120 evidence `ad43403b9105a3bdd49ddf23d616d35e47da559db7b11e692ed4832ed8bd2c8e`.
- 결과: 물리 58개, 유효 36/120, 누락·부적합 84개, 267,068자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- 검증: focused pytest 57, tracked Ruff, manifest audit, completion check PASS. 전체 pytest는 기존 artifact 부재·CGM 실패군만 남았다. 독립 검토 `0/0/0`; CI `29934330927` 성공.
- 서비스·production·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen/replay/slice delta 0. 다음: OP-017/018, OP-019/020, OP-021/022.

## 2026-07-22 OP-013/014 최종 handoff

- 단계/과제: 약물과 건강기능식품 구조화 입력. OP-013/014 `IMPLEMENTED / COMPLETE`.
- dataset 8건 SHA-256 `183b3b8e61134046df7dc8245d9ce40da9b1b0aec01c1c381b89ea98af448dbe`; OP-120 evidence `103014005b229e778fde4e71e018743643305baa2eebf7efd69a96f72fa6b7c8`.
- 결과: 물리 56개, 유효 34/120, 누락·부적합 86개, 259,631자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- 수정: boolean dose 거부, audited input commit/blob 재현, service shallow-history 독립 provenance, CI evidence-root portable test. schema-dependent canonical evidence도 workflow 환경에서 갱신했다.
- 검증: focused pytest 87, tracked Ruff, audit, completion check PASS; 독립 검토 `0/0/0`; CI `29931855632` 성공.
- production·학습·simulation 변경 없음. frozen/replay/slice delta 0. 다음: OP-015/016, OP-017/018, OP-019/020.

## 2026-07-22 OP-013/014 중간 handoff

- 보고서·OP-120 evidence와 공용 dose boolean 거부 수정은 HEAD `9a02008`까지 push됐다.
- 현재 보고서: 물리 56, 유효 34/120, 누락·부적합 86. evidence SHA-256 `1d8653bf098fa8dd57ebca445497e56e1bda8e07a13d3010683cfe837aa8018f`.
- 최초 독립 검토 `0/1/0`; Important 수정 후 재검토 진행 중. CI `29924086385`도 진행 중이다.
- 두 gate를 확인하기 전 OP-013/014 loop 완료를 주장하지 않는다. 코드 외 서비스·production·학습·simulation 변경은 없다.

## 2026-07-22 OP-011/012 handoff

- 단계/과제: 구조화 건강 입력 보고서 backfill. OP-011/012 `IMPLEMENTED / COMPLETE`.
- 데이터셋 8건 SHA-256 `6faeb8fc5d5a61ccd5c02e068c7be2df166176b2e888671c740769778ababb84`; evidence SHA-256 `5a8c90de500aa12ff871df36a8bdd2758f6637a730399b803701521e9f8c9873`.
- 물리 54개, 유효 32/120, 누락·부적합 88개, 254,619자. completion `76/43/0/1/0`, OP-120 `BLOCKED`.
- pytest 49건, tracked Ruff, audit, completion check 통과. 독립 검토 `Critical 0 / Important 0 / Minor 0`; CI `29922469760` 성공.
- 코드·서비스·데이터·학습·모델·simulation 변경 없음. frozen/replay/slice delta 0 유지.
- 병목 5개: 보고서 88개, stage gap 43개, OP-039, validation receipt, independent-review receipt. 다음: OP-013/014, OP-015/016, OP-017/018.

## 2026-07-22 OP-009/010 handoff

- 단계/과제: 원본 요구사항 감사 자동화; OP-009 감사 CLI·CI와 OP-010 generated completion report 연구보고서 backfill. 둘 다 `IMPLEMENTED / COMPLETE`다.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `345006573b8cbdd16765c16dc6b2dd125154413f664d3012bd8a25af3752e791`.
- 변경: OP-009·010 장문 보고서와 OP-120 보고서·사례·evidence만 갱신했다. 코드, 서비스, 데이터, 학습, 모델, simulation은 바꾸지 않았다.
- 결과: 물리 52개, 유효 30/120, 누락·부적합 90개, 246,876자. completion `76/43/0/1/0`; OP-120은 `BLOCKED`다.
- 검증: 계약 pytest 31건, manifest audit, completion check, tracked Ruff 통과. evidence 2회 동일 SHA-256 `0b649dd9d14bc13f511a1a369533103838ca083ff68a064988a4552e8246a574`. 독립 검토 최종 `0/0/0`. CI `29921069084` 성공.
- frozen/replay/slice delta: 변경 대상이 아니며 256건의 7개 지표와 weakest slice, replay delta는 0 유지. 학습·simulation 미실행.
- 병목 5개: 보고서 90개, stage gap 43개, OP-039, validation receipt, independent-review receipt.
- 다음 세 loop: OP-011/012, OP-013/014, OP-015/016.

## 2026-07-22 OP-007/008 handoff

- 선택 단계와 작업: original plan / evidence governance. OP-007의 단계 schema와 OP-008의 manifest 파일 감사를 코드·테스트·Git 이력·PDF KPI 기준에 대조하고 두 장문 보고서를 작성했다.
- 주 데이터셋과 case 수: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `0b5e2cb31533798c6281574761723c2fbc71f156e17652f099814e1e2f5c6b5b`.
- 변경 파일: `docs/original_plan/research_reports/OP-007.md`, `OP-008.md`, `OP-120.md`, `data/original_plan/op120_final_completion_audit_cases_v1.json`, `data/original_plan/evidence/op120_final_completion_audit_v1.json`, 그리고 세 인계 문서.
- 핵심 결과: OP-007은 네 단계 어휘와 단계별 최소 evidence를 고정한다. OP-008은 `external_dependencies`를 제외한 파일형 evidence 5종의 저장소 접두사, owner, path escape, 존재와 Git 추적을 검사하고 원본 PDF hash를 검증한다. 파일 내용의 진실성, 실제 운영, 외부 receipt 자체는 자동으로 증명하지 않는다.
- 코드·데이터·학습·시뮬레이션: 구현 코드, manifest stage, 서비스 저장소, 원천·frozen·학습 데이터, 모델, 시뮬레이션은 변경하지 않았다. 공식 frozen eval 256건 일곱 지표 delta 0, replay delta 0, weakest slice 변화 없음.
- 보고서·상태: OP-007 6,523자, OP-008 7,507자. 물리 파일 50개, 유효 28개, 미작성·부적합 92개, 전체 233,130자. completion은 `76/43/0/1/0`이며 Goal은 active다.
- 검증: 관련 선택 31개 통과, Ruff·manifest audit·completion check PASS. 독립 검토는 Minor 1을 고친 뒤 Critical 0 / Important 0 / Minor 0. OP-120 evidence는 두 번 byte-identical, SHA-256 `1be4ea55dcca71849aaed7332ee6859fdb419061561177ddf8eb2e7120a4ce01`. GitHub Actions run `29919479757` 성공.
- 커밋: `031c913`, `75a8538`, `6edb1c0`, `5419fb3`; 다음 handoff 문서 커밋이 이 항목을 포함한다.
- 병목 5개: 보고서 92개, stage 미달 43건, OP-039 외부 검증, validation receipt, 전체 독립 감사 receipt.
- 다음 loop 3개: OP-009/010, OP-011/012, OP-013/014 보고서 backfill.

## 2026-07-22 OP-005/006 handoff

- 선택 단계와 작업: OP-005/006 `IMPLEMENTED` 근거 재조사, 두 장문 연구보고서 backfill, OP-120 보고서 감사 갱신, 검토에서 발견한 KPI-1 빈 분모 결함 수정.
- 데이터셋과 case 수: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `a552b4418c8c523c5ae8c6ef370a1b521be9fe59363d8625f35563c3a3bbfbce`.
- 핵심 파일: `docs/original_plan/research_reports/OP-005.md`, `OP-006.md`, `OP-120.md`; `src/wellnessbox_rnd/interim/kpi.py`; `src/wellnessbox_rnd/interim/reports.py`; 관련 테스트; OP-055/056·OP-099/100·OP-120 canonical evidence.
- 코드·데이터·학습·시뮬레이션: 빈 recommendation reference를 직접 계산에서 거부하고 집계에서 제외한다. KPI-1은 valid 3,544 / invalid 1,456 / total 5,000을 보고한다. 프록시 점수는 유효 표본에서 100%다. 원천·학습 데이터, 모델, 시뮬레이션, 서비스 저장소는 변경하지 않았다.
- 검증: 관련 선택 테스트 38개, 연쇄 evidence 관련 테스트 24개·15개·9개 통과; Ruff, manifest audit, completion check, diff 검사 통과. 독립 재검토 Critical 0 / Important 0 / Minor 0. GitHub Actions `29917930551` 성공.
- frozen eval·replay·slice: 256건 frozen evaluation의 7개 지표 delta 0, replay delta 0, weakest slice 변화 없음. KPI-1 표본 계약만 5,000에서 유효 3,544로 수정됐다.
- 결과: 연구보고서 유효 26, 미작성 94, 물리 파일 48. 상태는 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`. 최종 OP-120 evidence SHA-256 `6d761eba95504e84b5de02fe1efdca62604cdad2235d4fecfff9db1c7e3e6b71`.
- 커밋: `468f2ca`, `06031be`, `47980fc`, `336f851`, `6bc3d0e`, `32f3eb1`, `8e67412`. 다음 handoff 문서 커밋은 이 항목을 포함한다.
- 병목 5개: 보고서 94개, stage 미달 43건, OP-039 외부 검증, 운영 validation receipt, 최종 120개 독립 감사 receipt.
- 다음 loop 3개: OP-007/008, OP-009/010, OP-011/012 보고서 backfill. Goal은 아직 active다.

## 2026-07-22 OP-120 handoff

- 단계/과제: 최종 완료 감사 계약. OP-120은 `IMPLEMENTED / PARTIAL`이며 required stage `OPERATED`에는 도달하지 않았다.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `e6506727ab9a01a65e53f4de27ed4383e0a6419e29832e081ae1bb0dd2ff3883`.
- 결과: 감사 `BLOCKED`, `goal_complete=false`; 전체 상태 `76/43/0/1/0`, 주장 119건이다. 보고서 파일 42개 중 강화된 검증을 통과한 보고서는 `20/120`이다.
- 차단 조건: required stage 부족 43건, OP-039 외부 검증, 누락·부적합 보고서 100건, 최종 검증 영수증, Critical 0·Important 0 독립 검토 영수증이다.
- 경계: public deployment, production 설정, 인증정보와 서비스 저장소 사용자 변경을 건드리지 않았다. frozen·학습·모델·safety·replay·slice delta는 모두 0이다.
- 다음 세 loop: OP-001~078 보고서 backfill, 승인된 production 운영 증거 수집, OP-039 외부 검증 입력 등록이다.
- 검증된 구현·증거 HEAD `914c4572e23e385fe34f0b1f9362137fa6118f7b`은 `origin/main`에 있고 GitHub Actions `Original plan evidence` 실행 `29911825838`이 성공했다. 독립 검토는 Critical 0, Important 0, Minor 1이다.

## 2026-07-22 OP-101/102 handoff

- Chosen stage/tasks: `original plan / production service integration`; OP-101 defines the R&D deployment target, persistent DB, and internal authentication contract, while OP-102 verifies the five required API families in the mounted FastAPI app.
- Primary dataset/cases: `data/original_plan/op101_op102_deployment_contract_endpoint_cases_v1.json`, `8` Git-blob cases. Canonical evidence is `data/original_plan/evidence/op101_op102_deployment_contract_endpoint_smoke_v1.json`, SHA-256 `5F5DB9FF4157BD183F96A647ABC4866DF57F159CF54473DA89A282D95091F108`; source identity is `98345fce92b1f6b94e8a203c1b8f6b77290365b5`.
- Main files: `deployment.py`, FastAPI lifespan and health route, Docker build identity, `.env.example`, staging deployment contract, endpoint tests, two-process runner/evidence, workflow, manifest/status, and `OP-101.md` plus `OP-102.md`.
- Code/data/training/simulation: staging/production cannot bypass contract validation; code SHA must match the immutable installed-image file; DB path/durability, actual worker alias, token complexity, provider secret reference, and internal auth fail closed. Health removes internal paths and secret-derived values. Five endpoint families come from final mounted routes. No training, frozen-data change, simulation-policy change, provider deployment, service edit, or production operation occurred.
- Stage/result: OP-101 and OP-102 are both PARTIAL at claimed `INTEGRATED` versus required `OPERATED`. Completion counts are `70/31/18/1/0`.
- Reports: coverage is `24/120`, not 120/120; `96` remain. Total text is `168,510` characters. OP-101 is `4,523` characters and OP-102 is `4,660` characters.
- Independent review: initial Critical `0`, Important `5`, Minor `0`; enforcement, worker alias, secret exposure, image identity, and Git-blob dataset issues were fixed. Packaging-path and working-tree checks were also corrected. Final result is Critical `0`, Important `0`, Minor `0`.
- Validation: focused selection `127 passed`; final CI exact selection `696 passed, 2 skipped`; canonical smoke, tracked-Python Ruff, audit, completion check PASS. Audit has `101` claims and `279` evidence files. Full regression collected `1,138`: `1,061 passed`, `77 failed`, all in known absent-artifact/CGM groups. Frozen evaluation has `256` cases and seven zero deltas.
- Publication: R&D HEAD `8eab198cbb76ff0ca643e396e238840e0ce464ff` is on `origin/main`; final CI run `29888020924` passed. The service stays at `a24b6c3308cc76627c3ca29807db1705e32c2178`; its pre-existing user changes were preserved.
- Five current bottlenecks: `96/120` reports remain; OP-101/102 lack provider operation; OP-103/104 lack approved environment/result-origin integration; OP-105/106 lack full service roundtrip/review-queue evidence; legacy full suite retains `77` absent-artifact and CGM failures.
- Next three loops: OP-103/104 environment-variable and result-origin contracts without provider mutation; OP-105/106 profile roundtrip and review-queue integration; OP-001 through OP-078 evidence-grounded report backfill.

## 2026-07-22 OP-099/100 handoff

- Chosen stage/tasks: `original plan / wearable·CGM·genetic integration`; OP-099 blocks duplicate device events independently of retry session IDs, and OP-100 recomputes W/C/G rates plus equal-weight macro average.
- Primary dataset/cases: `data/original_plan/op099_op100_device_dedup_linkage_cases_v1.json`, `7` cases. Canonical evidence is `data/original_plan/evidence/op099_op100_device_dedup_linkage_smoke_v1.json`, SHA-256 `7C11B895B37BF42CACCAAAC05B8B492A20015A2DBACBF02678785DC585ABFE4C`; source identity is `029f606ed5191d34132fe78e3b21fef8d88cd75f`.
- Main files: schema-v14 `InterimStore`, `connectors.py`, `kpi.py`, authenticated interim route/agent queue bridge, focused tests, frozen dataset, canonical runner/evidence, workflow, manifest/status, and `OP-099.md` plus `OP-100.md`.
- Code/data/training/simulation: canonical tuple identity, immediate transaction, immutable receipts, conflict 409s, timezone-aware observation validation, concurrent replay coverage, class-scoped immutable KPI input, and W/C/G macro calculation were added. No model training, frozen-data change, simulation-policy change, service edit, deployment, provider integration, or production operation occurred.
- Stage/result: OP-099 is PARTIAL at claimed `IMPLEMENTED` versus required `OPERATED`; OP-100 is COMPLETE at required `IMPLEMENTED`. Counts are `70/29/20/1/0` for complete/partial/pending/external/contradicted.
- Reports: coverage is `22/120`, not 120/120; `98` remain. Total text is `159,327` characters. OP-099 is `4,141` characters and OP-100 is `4,079` characters. Toss easy-finance references guided only the explanatory structure.
- Independent review: initial Critical `0`, Important `4`, Minor `2`; date validation, immutable KPI input, missing-ID replay, tuple collision, error contract, and concurrency coverage were fixed. Final result is Critical `0`, Important `0`, Minor `0`.
- Validation: focused selection `49 passed`; final CI exact selection `681 passed, 2 skipped`; canonical smoke, tracked-Python Ruff, audit, and completion check PASS. Audit has `99` claims and `272` evidence files. Full regression collected `1,124`: `1,029 passed`, `95 failed`, all in known absent-artifact/CGM groups. Frozen evaluation has `256` cases and seven zero deltas.
- Publication: R&D source/evidence through `cb75d92410f2e95c0076476dcd70e4c7cb385838` is on `origin/main`; final CI run `29886594091` passed. The service stays at `a24b6c3308cc76627c3ca29807db1705e32c2178`; its pre-existing user changes were preserved.
- Five current bottlenecks: `98/120` reports remain; OP-099 lacks provider operation; no authenticated production device feed exists; OP-101 through OP-105 lack deployment evidence; legacy full suite retains `95` absent-artifact and CGM failures.
- Next three loops: OP-101/102 deployment contracts without public deployment; OP-103/104 service environment and two-process contracts without production mutation; OP-001 through OP-078 evidence-grounded report backfill.

## 2026-07-22 OP-097/098 handoff

- Chosen stage/tasks: `original plan / wearable·CGM·genetic integration`; OP-097 connects device values to real recommendation score snapshots and follow-up deltas, while OP-098 separates production-device and simulation-fixture data classes.
- Primary dataset and cases: `data/original_plan/op097_op098_device_followup_data_class_cases_v1.json`, `7` frozen cases. Canonical evidence is `data/original_plan/evidence/op097_op098_device_followup_data_class_smoke_v1.json`, SHA-256 `20C3B6FEE428E2AFB12E97ED6A51532EA3ED624374695177A14E2BACD10DC635`; source identity is `7dde4d66b6f56ac60eac4914d7e4251a54e001bb`.
- Main files: authenticated interim route, `device_evaluation.py`, `DataClass`, schema-v13 `InterimStore`, canonical profile/storage helpers, tests, frozen cases, canonical runner/evidence, manifest/status reports, workflow, and `OP-097.md` plus `OP-098.md`.
- Code/data/training/simulation: baseline and follow-up values call the real recommendation engine; score changes preserve common candidates and entry/exit. Explicit service subject IDs and all-used-source storage consent are mandatory. Class/origin pairs and longitudinal profile/class/origin boundaries fail closed. No training, frozen-data change, provider integration, deployment, operation, or external validation occurred.
- Stage/result: OP-097 is COMPLETE at required `INTEGRATED`; OP-098 is PARTIAL at claimed `IMPLEMENTED` versus required `OPERATED`. Completion counts are `69/28/22/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: coverage is `20/120`, not 120/120; `100` remain. Total report text is `151,107` characters. OP-097 is `4,948` characters and OP-098 is `5,225` characters. Toss easy-finance references guided only the Korean explanatory structure.
- Independent review: initial Critical `0`, Important `2`, Minor `2`; all-used-source storage consent, explicit service subject identity, origin-claim wording, and candidate entry/exit coverage were corrected. Final result is Critical `0`, Important `0`, Minor `0`.
- Validation: focused selection `75 passed`; CI exact selection `669 passed, 1 skipped`; tracked-Python Ruff PASS; audit PASS with `97` claims and `266` evidence files; completion check and every canonical smoke PASS. Full regression collected `1,115`: `1,020 passed`, `95 failed`, all outside this change. Frozen evaluation has `256` cases, seven zero deltas, and unchanged weakest categories.
- Publication: R&D implementation/evidence HEAD `b96d642d2f1b68ab867b1e064719aadc214a0aa8` is on `origin/main`; final CI run `29885050044` passed. The service stays at `a24b6c3308cc76627c3ca29807db1705e32c2178`, and its pre-existing user changes were preserved.
- Five current bottlenecks: `100/120` reports remain; OP-098 lacks operating evidence; no authenticated production device-provider feed exists; OP-099/100 still need event deduplication and production-only source metrics; the legacy full suite retains `95` absent-artifact and CGM failures.
- Next three loops: OP-099/100 duplicate-event blocking and production-only W/C/G macro evaluation; OP-101/102 deployment contracts without public deployment; OP-001 through OP-078 report backfill from primary evidence and Git history only.

## 2026-07-22 OP-095/096 handoff

- Chosen stage/tasks: `original plan / wearable·CGM·genetic integration`; OP-095 returns file-level schema failures and partial-success counts, and OP-096 stores raw-file and normalized-result lineage.
- Primary dataset and cases: `data/original_plan/op095_op096_sensor_file_ingestion_cases_v1.json`, `7` frozen cases. Canonical evidence is `data/original_plan/evidence/op095_op096_sensor_file_ingestion_lineage_smoke_v1.json`, SHA-256 `882CD29412BAE087FB77D32DC8B6A0A620947CAD748245861176C33D16DF4206`; source identity is `d25279ea200b5954391ea7088aae368ef83fceb7`.
- Main files: authenticated interim route, `sensor_file_ingestion.py`, schema-v12 `InterimStore`, shared sensor parser, frozen cases, canonical runner/evidence, tests, manifest/status reports, CI workflow, and `OP-095.md` plus `OP-096.md`.
- Code/data/training/simulation: exact Base64-decoded bytes are hashed before parsing; normalized canonical JSON receives a separate hash; success and failed attempts can share the append-only lineage table without raw content. Multirow CSV validation now matches existing normalizers. No training, frozen-data change, provider integration, deployment, operation, or external validation occurred.
- Stage/result: OP-095 is COMPLETE at required `IMPLEMENTED`; OP-096 is PARTIAL at claimed `IMPLEMENTED` versus required `OPERATED`. Completion counts are `68/27/24/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: coverage is `18/120`, not 120/120; `102` remain. Total report text is `140,934` characters. OP-095 is `4,528` characters and OP-096 is `5,032` characters. Toss easy-finance references guided only the Korean explanatory structure.
- Independent review: initial Critical `0`, Important `2`, Minor `1`; report claims about unknown sources, stored columns/ID inputs, and error descriptions did not match code. The reports were corrected. Final result is Critical `0`, Important `0`, Minor `0`.
- Validation: focused selection `94 passed`; CI exact selection `659 passed, 1 skipped`; tracked-Python Ruff PASS; audit PASS with `95` claims and `261` evidence files; completion check and every canonical smoke PASS. Full regression collected `1,105`: `1,010 passed`, `95 failed`, all outside this change in absent historical report artifacts and the known CGM geometry group. Frozen evaluation has `256` cases, seven zero deltas, and unchanged weakest categories.
- Publication: R&D HEAD `3af7bf7d4301a42e8787fc47478d45bf457d57b7` is on `origin/main`; final CI run `29883787699` passed. The service stays at `a24b6c3308cc76627c3ca29807db1705e32c2178`, and its pre-existing user changes were preserved.
- Five current bottlenecks: `102/120` reports remain; OP-096 lacks operating evidence; OP-097/098 do not yet connect device values to score/follow-up and data classes; no production device/provider ingestion exists; the legacy full suite depends on missing historical report artifacts and retains CGM geometry failures.
- Next three loops: OP-097/098 device score/follow-up integration and production-vs-simulation data class; OP-099/100 duplicate-event blocking and W/C/G source macro evaluation; OP-001 through OP-078 report backfill from primary evidence and Git history only.

## 2026-07-22 OP-093/094 handoff

- Chosen stage/tasks: `original plan / wearable·CGM·genetic integration`; OP-093 preserves normalized variant interpretation provenance, and OP-094 excludes non-consented genetic data from recommendation influence and local persistence.
- Primary dataset and cases: `data/original_plan/op093_op094_genetic_normalization_consent_cases_v1.json`, `8` frozen cases. Canonical evidence is `data/original_plan/evidence/op093_op094_genetic_normalization_consent_smoke_v1.json`, SHA-256 `A1F6264F19728A1C1697704CF03C412ACDF563AAA33481E1D13D4285121B9A24`; source identity is `7ebac677f7e54c6935ce789f4261fd71028c3cab`.
- Main files: recommendation schema, sensor parser, intake consent gate, Data Lake profile persistence, parser/consent/lineage tests, frozen dataset, canonical runner and evidence, requirement manifest, generated completion reports, workflow, and `OP-093.md` plus `OP-094.md`.
- Code/data/training/simulation: structured variants require gene, identifier, genotype, bounded interpretation, criterion, laboratory, and ISO date; malformed or conflicting provenance fails closed. Denied genetic data is removed before input hashing and scoring and omitted from actual SQLite storage. Approved legacy tags remain the only genetic score input. No training, frozen-data change, provider integration, deployment, operation, or external validation occurred.
- Stage/result: OP-093 and OP-094 are COMPLETE at required `IMPLEMENTED`. Completion counts are `67/26/26/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: OP-079 through OP-094 have separate explanatory prose reports. Coverage is `16/120`, not 120/120; `104` remain. Total report text is `131,374` characters. OP-093 is `5,642` characters and OP-094 is `5,687` characters. Reference basis was the Toss easy-finance explanatory article family.
- Independent review: initial Critical `0`, Important `1`, Minor `0`; non-string identifiers, genotypes, criteria, and laboratory values had been coerced to text. Strict type rejection and regressions fixed the defect. Final result is Critical `0`, Important `0`, Minor `0`.
- Validation: focused/completion selection `97 passed`; CI exact selection `650 passed, 1 skipped`; tracked-Python Ruff PASS; audit PASS with `93` claims and `257` evidence files; completion check PASS; every canonical smoke PASS. Full regression collected `1,096`: `1,019 passed`, `77 failed`, exactly the known `73 + 4` groups. Frozen evaluation has `256` cases, seven zero deltas, and unchanged weakest categories.
- Publication: R&D HEAD `2750d136128920f4408874131c4c1467bfb5aa65` is on `origin/main`; final CI run `29882424484` passed. The service stays at `a24b6c3308cc76627c3ca29807db1705e32c2178`, and its pre-existing user changes were preserved.
- Five current bottlenecks: `104/120` reports remain; OP-095/096 are not implemented; no raw genetic-file hash/result lineage exists; no production genetic provider or laboratory integration exists; the legacy suite retains `77` known absent-report and CGM failures.
- Next three loops: OP-095/096 partial-success and raw-hash lineage; OP-097/098 device score/follow-up integration and production-vs-simulation data class; OP-001 through OP-078 report backfill from primary evidence and Git history only.

## 2026-07-22 OP-091/092 handoff

- Chosen stage/tasks: `original plan / sensor integration`; OP-091 normalizes bounded Fitbit and Apple Health daily activity summaries, and OP-092 normalizes bounded CGM daily summaries with fail-closed unit and alias handling.
- Primary dataset and cases: `data/original_plan/op091_op092_sensor_daily_normalization_cases_v1.json`, `8` frozen cases. Canonical evidence is `data/original_plan/evidence/op091_op092_sensor_daily_normalization_smoke_v1.json`, SHA-256 `82C016013D247BE2A992E91872C93D986374705B3E2B325A3A4BEC272685C860`; source identity is `603eeb1993ec4f02edcf21bd4cb1898603714486`.
- Main files: `src/wellnessbox_rnd/domain/sensor_parser.py`, sensor parser and file-schema tests, the frozen cases, canonical smoke runner and evidence, requirements manifest, generated status reports, CI workflow, and `docs/original_plan/research_reports/OP-091.md` plus `OP-092.md`.
- Code/data/training/simulation: explicit and generic glucose aliases now compare after unit normalization; contradictory aliases and ambiguous time-in-range bounds fail closed; Apple Health units use narrow per-metric allowlists; tests resolve repository paths portably. No provider integration, raw time-series ingestion, model training, frozen-evaluation change, deployment, production operation, or external validation occurred.
- Stage/result: OP-091 and OP-092 are COMPLETE at required `IMPLEMENTED`. Completion counts are `65/26/28/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: OP-079 through OP-092 have separate explanatory prose reports. Coverage is `14/120`, not 120/120; `106` remain. Total report text is `120,045` characters. OP-091 is `8,671` characters and OP-092 is `9,035` characters.
- Independent review: initial Important findings covered conflicts inside alias groups and unit-aware conflict checks between explicit and generic postprandial values. All findings were fixed. Final result is Critical `0`, Important `0`, Minor `0`.
- Validation: focused sensor/schema `24 passed`; local workflow-equivalent `642 passed`; tracked-Python Ruff PASS; audit PASS with `91` claims and `255` evidence files; completion check PASS; final CI canonical smokes and exact contract selection PASS. Full regression collected `1,086`: `1,009 passed`, `77 failed`, exactly the known `73 + 4` groups. Frozen evaluation has `256` cases, seven zero deltas, and unchanged weakest categories.
- Publication: R&D HEAD `9f4bbbd36ecef532112cf55792b55da1ab195b7a` is on `origin/main`; CI run `29881297071` passed every evidence, contract-test, and lint step. The service remains at source identity `a24b6c3308cc76627c3ca29807db1705e32c2178`; pre-existing user changes there were preserved.
- Five current bottlenecks: `106/120` research reports remain; OP-093/094 are not implemented; no production Apple Health API ingestion exists; no production CGM provider or raw-series ingestion exists; the legacy suite still has `77` known failures from absent reports and CGM geometry.
- Next three loops: OP-093/094 genetic normalization and consent gating; OP-095/096 partial-result behavior and raw-hash lineage; OP-001 through OP-078 report backfill from primary evidence and Git history only.

## 2026-07-22 OP-089/090 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-089 returns a structured deterministic answer when the optional provider fails, and OP-090 freezes question-type QA and exercises the real service TypeScript client against the real local R&D HTTP API.
- Primary dataset and cases: `8` frozen cases, `7` first-pass injected provider failures, `1` urgent provider bypass, and two fresh process/database runs. Canonical evidence is `data/original_plan/evidence/op089_op090_counseling_fallback_api_e2e_v1.json`, SHA-256 `49a3152436fb59e392110999729e82ae64360dd86cf430d7345f6a128577394d`; source commits are R&D `d1273da965da098f8689434e9b140a83bb285cd7` and service `a24b6c3308cc76627c3ca29807db1705e32c2178`.
- Main implementation: explicit external-provider consent, structured failure metadata, durable answer/verifier snapshots, same-turn conflict rejection, cross-thread and cross-worker serialization, stored-binding replay, frozen QA, actual HTTP/TypeScript E2E, full-answer determinism, and complete direct source/data identity.
- Stage/result: OP-089 is COMPLETE at `IMPLEMENTED`. OP-090 is `IMPLEMENTED/PARTIAL` against required `INTEGRATED`. Completion counts are `63/26/30/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: OP-079 through OP-090 have separate explanatory prose reports. Coverage is `12/120`, not 120/120; `108` remain. Total report text is `102,339` characters. OP-089 is `9,793` characters and OP-090 is `12,150` characters.
- Independent review: final result Critical `0`, Important `0`, Minor `0` after fixing consent, concurrent execution, multi-worker locking, lock cleanup, full-answer comparison, and all direct source-identity omissions.
- Validation: focused interim API `25 passed`; exact workflow selection `618 passed`; tracked-Python Ruff PASS; service build/typecheck/ESLint/QA PASS; audit PASS with `89` claims and `253` evidence files; completion check PASS; `28` canonical smokes PASS. Full regression is `997 passed`, `77 failed`, exactly the known `73 + 4` groups. Frozen eval has `256` cases, seven zero deltas, and unchanged weakest categories.
- Publication: service source commit `a24b6c3308cc76627c3ca29807db1705e32c2178` and R&D source/evidence commit `5593c6a0af6ef397e1eeb54a34172fd356476884` are on `origin/main`. CI run `29878812400` passed every evidence, contract-test, and lint step.
- Current bottlenecks: `108/120` research reports remain; OP-090 lacks `/api/chat` plus isolated Prisma evidence; no production R&D counseling endpoint, production operation, or external counseling validation exists.
- Next loops: OP-091/092, then continue through OP-120 while backfilling OP-001 through OP-078 only from primary source, Git history, tests, and canonical evidence.

## 2026-07-22 OP-087/088 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-087 binds counseling answers to one service session, one turn, one verifier decision, and one recommendation run; OP-088 adds the thin WellnessBox-to-R&D adapter inside the existing chat path.
- Primary dataset and cases: `24` passages from `19` sources and frozen evaluation `256` cases. Canonical evidence is `data/original_plan/evidence/op087_op088_counseling_session_service_adapter_smoke_v1.json`, SHA-256 `729f61d599590870df9aa6e2c18948a72523461e2b597021adb02646ef93984d`; R&D source commit `8c5f1f0fdf9f62acd3f7f94dc45ce1f5d3e9d8c2`; service source commit `f78604c74795c127a004a7be64cb67c7fe112803`.
- Main files: the existing interim route and store, committed counseling corpus, existing chat route and save route, existing R&D client, service QA scripts, focused tests, canonical smoke, manifest, generated completion reports, CI workflow, and two long-form research reports.
- Code/data/training/simulation: a strict counseling turn contract, stable session binding, full semantic replay hash, concurrent recommendation idempotency, pseudonymous profile mapping, and transactional service persistence are implemented. No model training, frozen-data change, deployment, production operation, production database write, external validation, or live language-model inference occurred.
- Stage/result: OP-087 is `IMPLEMENTED` against required `OPERATED`; OP-088 is `IMPLEMENTED` against required `INTEGRATED`. Both are PARTIAL. Completion counts are `62/25/32/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: OP-079 through OP-088 have separate explanatory prose reports. Coverage is `10/120`, not 120/120; `110` remain. Total current report text is `80,291` characters. OP-087 is `11,381` characters and OP-088 is `9,862` characters.
- Independent review: the review sequence found Critical `1`, Important `10`, Minor `0` in total. Fixes cover session-scoped message identity, changed-payload replay rejection, concurrent insertion, privacy allowlists, truthful consent scopes, persisted binding evidence, atomic Prisma writes, stable retries, migration compatibility, and actual `UserProfile` mapping. Final review is Critical `0`, Important `0`, Minor `0`.
- Validation: exact workflow selection `613 passed`; full Ruff PASS; audit PASS (`87` claims, `249` evidence files); completion check PASS; canonical bytes and source hashes verified twice. Full regression is `992 passed`, `77 failed`, with no new failure group. Frozen eval has seven zero metric deltas and unchanged weakest categories.
- Publication: WellnessBox service HEAD `f78604c74795c127a004a7be64cb67c7fe112803` and R&D source/evidence commit `9f7a71c9fc96f265ed554a1e179a87c3c58dbc2e` are on `origin/main`. `Original plan evidence` run `29848036378` passed all `27` canonical smokes, `613` contract tests, and workflow lint.
- Current bottlenecks: `110/120` reports remain; OP-087 lacks production operation; OP-088 lacks `/api/chat` plus isolated Prisma database evidence; no deployed R&D counseling process or production telemetry exists; external counseling validation remains absent.
- Next loops: finish R&D push and CI, then OP-089/090, while reconstructing OP-001 through OP-078 reports only from primary source, Git history, tests, and canonical evidence.

## 2026-07-21 OP-085/086 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-085 blocks unsupported claims, omitted risks, forbidden expressions, and policy/query-evidence mismatch; OP-086 places deterministic emergency guidance before retrieval, recommendation, and provider calls.
- Primary dataset and cases: `24` passages from `19` sources; normal/urgent/negated/contrast answer cases; `5` common urgent phrasing cases; `7` tamper/policy probes; frozen evaluation `256` cases. Canonical evidence is `data/original_plan/evidence/op085_op086_counseling_verifier_urgent_safety_smoke_v1.json`, SHA-256 `e7dcfe8248d7ba73769efd618cd29cb3deb99675df8ee4e5af5aff54280d2a36`; source commit `c6ca444488e7af34b416e3da208016972010315d`; source SHA-256 `14022f4617560b4ae386c047eddb88269903b463fdbd2414edac7f9af9528b9c`; data SHA-256 `11f257c44f05db6d0286de3701cf72c428cbe46991b44f190729371ca167f228`.
- Main files: `src/wellnessbox_rnd/chat/answering.py`, `retrieval.py`, `verifier.py`, the existing OpenAI adapter, `data/knowledge/counseling_answer_verifier_policy_v1.json`, focused tests, canonical smoke, manifest, completion reports, CI workflow, and the two long-form research reports.
- Code/data/training/simulation: final prose is server-owned; verifier decisions are recomputed from repository policy, the original query, current bounded retrieval, and exact selected evidence. No model training, frozen-data change, WellnessBox service code change, deployment, production operation, external validation, or live language-model inference occurred.
- Stage/result: OP-085 and OP-086 are COMPLETE at required stage `IMPLEMENTED`. Completion counts are `62/23/34/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: OP-079 through OP-086 have separate explanatory prose reports. Coverage is `8/120`, not 120/120; `112` remain. Total current report text is `48,961` UTF-8 characters. OP-085 is `6,647` characters and OP-086 is `7,308` characters.
- Independent review: initial Critical `2`, Important `1`, Minor `0`; after the first fixes Critical `0`, Important `0`, Minor `1`; after threshold replay and CI portability fixes final Critical `0`, Important `0`, Minor `0`. Fixed cases are common urgent aliases, query/evidence relevance recomputation, repository-relative policy loading, non-default support-score replay, and CI service-evidence-root resolution.
- Validation: focused `50 passed`; exact workflow selection `609 passed`; all `26` workflow smokes PASS; Ruff PASS; audit PASS (`85` claims, `242` evidence files); completion check PASS; canonical bytes and source/data hashes independently verified.
- Full regression: `1,065` collected, `988 passed`, `77 failed`; known split `73` absent-report + `3` CGM geometry + `1` CGM closed-loop; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: R&D HEAD `bfe7c813c80a29c523a9367b2dc291b1df4d5537` is on `origin/main`. CI run `29841093182` failed only because the smoke assumed a sibling service checkout; commit `c6ca444` fixed it using `WELLNESSBOX_EVIDENCE_ROOT`. Final `Original plan evidence` run `29841384466` passed. The WellnessBox service repository remains at `4d904f43b028a35524a29206aaf7c6b99f58a97b` with preserved user-owned changes.
- Five current bottlenecks: `112/120` reports remain; OP-087/088 session persistence and service adapter are not implemented; no deployed R&D counseling process exists; no authenticated production service-to-R&D counseling call exists; no external counseling validation or production telemetry exists.
- Next three loops: OP-087/088, OP-089/090, and OP-091/092, with one full prose report per newly verified requirement and evidence-grounded backfill for OP-001 through OP-078.

## 2026-07-21 OP-083/084 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-083 repository-bounded retrieval and OP-084 answer provenance, validity dates, and explicit uncertainty.
- Primary dataset and cases: `24` passages from `19` sources, `4` answer cases, `8` rejection probes, and frozen evaluation `256` cases. Canonical evidence is `data/original_plan/evidence/op083_op084_bounded_rag_answer_provenance_smoke_v1.json`, SHA-256 `cfb10b0bdb9d02fbd1851cddde8b32c914a1ac00929b47f60e514c343fffb04d`; source SHA-256 `03c86d65261517c360e4120a9d2f3039cc30fa8db568c9bebe431e558e026f5f`.
- Main files: bounded retrieval and answer contracts, the existing OpenAI adapter, the repository scope registry, focused tests, canonical smoke, manifest, generated completion reports, CI workflow, and `docs/original_plan/research_reports/OP-083.md` plus `OP-084.md`.
- Code/data/training/simulation: retrieval and answer validation now use repository-pinned knowledge identity and reconstruct provenance on the server. No model training, frozen-data change, service code change, deployment, production operation, external validation, or live language-model inference occurred.
- Stage/result: OP-083 and OP-084 are COMPLETE at required stage `IMPLEMENTED`. Completion counts are `60/23/36/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: only OP-079 through OP-084 have individual long-form reports. Coverage is `6/120`, not 120/120; `114` reports remain. The six files total `35,006` UTF-8 characters. Final completion requires 120 separate reports, one for every OP.
- Writing requirement: a research report is a continuous, explanatory human document, not a compact activity log. Every report must spell out the requirement, existing implementation path, evidence examined, reasoning, work performed, failed approaches and corrections, reproducible verification, unresolved limitations, and the distinction among implementation, integration, operation, and external validation. Abbreviations must be expanded on first use, and bullets or machine evidence may support but cannot replace the prose.
- Validation: focused regression `39 passed`; workflow-equivalent `596 passed`; full Ruff PASS; audit PASS (`83` claims, `238` evidence files); completion check PASS; `27` smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `975 passed`, `77 failed`; known split `73` absent-report + `3` CGM geometry + `1` CGM closed-loop; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence HEAD `67d65c3160a004c0ec1f6030a645c3ef9dbda8ee` was pushed; GitHub Actions `Original plan evidence` run `29838281957` passed.
- Five current bottlenecks: `114/120` reports are still missing; OP-085/086 are not implemented; no deployed R&D counseling process exists; no authenticated production service-to-R&D counseling call exists; no external counseling validation or production telemetry exists.
- Next three loops: OP-085/086, OP-087/088, and OP-089/090, with one full prose report per newly verified requirement and evidence-grounded backfill for OP-001 through OP-078.

## 2026-07-21 OP-081/082 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-081 passage-level evidence collection with source/effective dates and OP-082 extraction of health goals, ingredients, drugs, and risk signals.
- Primary dataset and cases: `24` passages from `19` sources and `9` question cases, including `4` urgent cases; frozen eval `256` cases. Canonical evidence is `data/original_plan/evidence/op081_op082_counseling_passage_entity_smoke_v1.json`, SHA-256 `03c0efdc6110208f4e2e185c17524099d5b8fcdc5f27366cf6bd47c5ecb332f4`; source SHA-256 `ab6ffef24a9d936a9374d82a3a385943ad7a8b2600999b909ce7bc413d918d68`.
- Main files: `src/wellnessbox_rnd/chat/retrieval.py`, `scripts/build_chat_retrieval_assets.py`, the existing chat adapter and learned-runtime audit fixture, focused tests, canonical smoke, manifest, generated completion reports, CI workflow, and `docs/original_plan/research_reports/OP-081.md` plus `OP-082.md`.
- Code/data/training/simulation: existing reference and runtime-knowledge data now produce source-span-verified passages and deterministic entity traces. No model training, frozen dataset change, service code change, deployment, production operation, external validation, or LLM inference occurred.
- Stage/result: OP-081 and OP-082 are COMPLETE at required stage `IMPLEMENTED`. Completion counts are `58/23/38/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: separate prose reports now exist for OP-079 through OP-082, so coverage is `4/120`, not 120/120. OP-081 and OP-082 are about 6,500 characters each; all four current reports total `27,023` characters. The remaining 116 reports require evidence-grounded writing and must not be represented by manifest rows alone.
- Validation: focused/downstream regression `51 passed`; workflow-equivalent `584 passed`; full Ruff PASS; audit PASS (`81` claims, `232` evidence files); completion check PASS; `26` smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `968 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence HEAD `fd41644949479fbbc4219eb40fa31d7b4b13a30f` was pushed; GitHub Actions `Original plan evidence` run `29835498939` passed.
- Five current bottlenecks: only `4/120` long-form reports exist; OP-083/084 bounded answer generation is not implemented; no deployed R&D counseling process; no authenticated production service-to-R&D counseling call; no external counseling validation or production telemetry.
- Next three loops: OP-083/084 bounded RAG and evidence validity/uncertainty; OP-085/086; OP-087/088, with one full prose report per newly verified OP and continuing report backfill.

## 2026-07-21 OP-079/080 handoff

- Chosen stage/tasks: `original plan / closed-loop execution`; OP-079 lifecycle transition E2E and OP-080 strict separation between plan state and order state.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `5` authenticated API cases. Evidence SHA-256 is `2d51305ff69306061528a7ac0f6becabb6351d6a7025e439885dc73282246308`; source SHA-256 is `53f79c6cabb636782b9be23b5797ae42861890319a642b9848100096883d5a4f`.
- Main files: `src/wellnessbox_rnd/interim/plan_lifecycle.py`, `jobs.py`, `data_mutation.py`, `store.py`, the existing interim API route, OP-079/080 smoke, focused tests, manifest, completion reports, and both long-form reports.
- Code/data/training/simulation: existing execution lineage now stores and replays guarded transitions and real replacement candidates. No model training, frozen dataset change, service code change, deployment, production operation, or order mutation occurred.
- Stage/result: both requirements are proven only to `IMPLEMENTED` and remain PARTIAL because both require `OPERATED`. Completion counts are `56/23/40/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: two full prose reports exist, so overall coverage is `2/120`, not 120/120. The remaining 118 reports require evidence-by-evidence backfill.
- Validation: focused lifecycle regression `45 passed`; workflow-equivalent `559 passed`; full Ruff PASS; audit PASS (`79` claims, `226` evidence files); completion check PASS; 23 smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `948 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence HEAD `fadf80fc68f6bc93817b8111a8f01cd9d7aa8060` was pushed; GitHub Actions `Original plan evidence` run `29832628539` passed.
- Five current bottlenecks: only `2/120` long-form reports exist; no deployed R&D process; no durable production R&D database/queue; no authenticated production service-to-R&D lifecycle call; no observed production lifecycle or order-boundary telemetry.
- Next three loops: OP-081/082 passage indexing and entity extraction; OP-083/084 bounded RAG with evidence validity and uncertainty; OP-085/086, with report backfill included in each loop.

## 2026-07-21 OP-077/078 handoff

- Chosen stage/tasks: `original plan / closed-loop execution`; OP-077 fail-closed job guards and OP-078 pharmacist-review creation/completion postconditions.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `5` cases. Evidence SHA-256 is `df67af2cf7ecd9f99edc7a98dcf6a607d633983da8a6f9cd65630973b6a0b2d4`; source SHA-256 is `58746132ddc4d840a479a9fe4075423fff45c4cd4cf9c78a10d431ed74fae978`.
- Main files: `src/wellnessbox_rnd/interim/jobs.py`, `reviews.py`, `store.py`, `agent.py`, the existing interim API route, OP-077/078 smoke, focused tests, manifest, completion reports, and affected shared canonical evidence.
- Code/data/training/simulation: existing ledgers, jobs, consent records, and review tasks now enforce pinned guards and immutable review completion. No model training, frozen dataset change, service code change, deployment, or production operation occurred.
- Stage/result: both requirements are proven only to `IMPLEMENTED` and remain PARTIAL because both require `OPERATED`. Completion counts are `56/21/42/1/0` for complete/partial/pending/external/contradicted.
- Validation: focused `59 passed`; workflow-equivalent `541 passed`; full Ruff PASS; audit PASS (`77` claims, `220` evidence files); completion check PASS; 22 smokes regenerated; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `930 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence/docs HEAD `de7f493415618d11a492f782f8bbd20b3939b206` was pushed; GitHub Actions `Original plan evidence` run `29829346647` passed.
- Five current bottlenecks: no deployed R&D process; no durable production R&D database/queue; no production worker timeout/stale-evidence telemetry; no authenticated production service-to-R&D round trip; no observed pharmacist review operation.
- Next three loops: OP-079/080 lifecycle E2E and separate order state; OP-081/082 passage/source indexing and question entity extraction; OP-083/084 bounded RAG and answer evidence/validity/uncertainty.

## 2026-07-21 OP-075/076 handoff

- Chosen stage/tasks: `original plan / closed-loop execution`; OP-075 follow-up input next-job selection and OP-076 serious-adverse-event plan/recommendation stop.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `3` cases. Evidence SHA-256 is `847f861085d44916bfcab9c6a51ed2d9048262023c9c8e4b031b716b8285dd97`; source SHA-256 is `4e33d0f4560699ceb9e06eb894671f4312be9fcfd734a85ce60dbce73b4c7a28`.
- Main files: `src/wellnessbox_rnd/interim/agent.py`, `jobs.py`, `apps/inference_api/routes/interim.py`, the OP-075/076 smoke, focused tests, manifest, completion reports, and affected shared canonical evidence.
- Code/data/training/simulation: existing ledgers and queues now decide revision-bound PRO/device reevaluation work and enforce a fail-closed serious-AE hold. No model training, frozen dataset change, service code change, deployment, or production operation occurred.
- Stage/result: both requirements are proven only to `IMPLEMENTED` and remain PARTIAL because both require `OPERATED`. Completion counts are `56/19/44/1/0` for complete/partial/pending/external/contradicted.
- Validation: focused `30 passed`; workflow-equivalent `532 passed`; full Ruff PASS; audit PASS (`75` claims, `216` evidence files); completion check PASS; 21 smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `921 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence/docs HEAD `b08cc0744b6f662ac23b5a6bc5fc01d419b2a650` was pushed; GitHub Actions `Original plan evidence` run `29827163566` passed.
- Five current bottlenecks: no deployed R&D process; no durable production R&D database/queue; no production PRO/device ingestion observation; no authenticated production service-to-R&D round trip; no production serious-AE stop/hold telemetry.
- Next three loops: OP-077/078 fail-closed execution and pharmacist-review lifecycle; OP-079/080 lifecycle E2E and separate order state; OP-081/082 consent revocation and minimum-data-state handling.

## 2026-07-21 OP-073/074 handoff

- Chosen stage/tasks: `original plan / closed-loop execution`; OP-073 shared follow-up/reminder queue and OP-074 due-plan reevaluation Cron.
- Primary dataset and cases: `data/original_plan/evidence/op073_op074_followup_job_queue_cron_smoke_v1.json`; two follow-ups and four Cron runs; SHA-256 `5399806ac1e2af79d8390b4456bf54a6bea8de7b5ca8cf7b0b07b2cc099b3ea2`.
- Main files: `src/wellnessbox_rnd/interim/jobs.py`, `store.py`, `agent.py`, `apps/inference_api/routes/interim.py`, both queue/Cron scripts, focused tests, manifest, completion reports, and shared canonical evidence files.
- Code/data/training/simulation: schema v10 links follow-ups/jobs to the existing execution ledger and adds claim/lease/ack/retry state. No model training, frozen dataset change, service code change, deployment, or production operation occurred. Simulation evidence remains explicitly local.
- Stage/result: both requirements are proven only to `IMPLEMENTED` and remain PARTIAL because both require `OPERATED`. Completion counts are `56/17/46/1/0` for complete/partial/pending/external/contradicted.
- Validation: focused `46 passed`; workflow-equivalent `504 passed`; full Ruff PASS; audit PASS (`73` claims, `214` evidence files); completion check PASS; 20 smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `914 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: pushed HEAD `97a124b035cda1b525a709b2c2bb0d9a1d8da04a`; GitHub Actions Original plan evidence run `29824602501` succeeded.
- Five current bottlenecks: no deployed R&D process; no durable production R&D database/queue; no deployed CronJob observation; no authenticated production service-to-R&D round trip; no production worker lease/ack/retry telemetry.
- Next three loops: OP-075/076 next-job selection and serious-AE stop; OP-077/078 fail-closed execution and pharmacist-review lifecycle; OP-079/080 lifecycle E2E and separate order state.

Older handoff entries are archived in `docs/archive/SESSION_HANDOFF-archive-1.md`.

## 2026-07-21 closed-loop state and ordered execution handoff

- Chosen stage and tasks: `original plan / closed-loop execution`; OP-071 and OP-072.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke has `5` cases covering success, safety block, missing evidence, direct-move rejection, and idempotent retry.
- Primary evidence: `data/original_plan/evidence/op071_op072_closed_loop_state_order_smoke_v1.json`; SHA-256 `6bb772f0448722ce8efc6f010160f356b9789f026b76be997cd59e3cd0f607e1`; source SHA-256 `021b82bc4ff11faeb23e79b934431d4af2205a42f96070de450c94c27fca8460`.
- Source identity: R&D `26941e94554f21766823c043b635c865257e4646`; no service source is claimed for OP-071/072.
- Main changes: authoritative state/operation contract; strict trace models; exact safety-to-plan order; candidate/safety binding; evidence-constrained optimization; durable steps; direct-state bypass rejection; cross-worker SQLite claims; changed-payload idempotency rejection; existing interim API reuse. No service, training, data-generation, or simulation behavior changed.
- Honest stage: OP-071 and OP-072 are PARTIAL at `IMPLEMENTED`, below required `OPERATED`. Local SQLite behavior and API contract are proven. Service integration, deployment, production operation, and actual plan activation are not.
- Validation: focused/governance `63 passed`; workflow-equivalent `505 passed`, `1 skipped`; full Ruff PASS; `19` workflow smokes PASS; audit PASS with `71` claims and `208` evidence files; independent review Critical `0`, Important `0`.
- Full regression: `902 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: R&D HEAD `61b16929ebd2647438717e450fbceb954e92c140`; Original plan evidence run `29822306554` succeeded. The service repository retained all user changes and received no loop commit.
- Five bottlenecks: production operation evidence for OP-071; production operation evidence for OP-072; actual follow-up job queue for OP-073; due-plan CronJob for OP-074; trusted restoration of `73` absent report artifacts plus separate CGM-geometry investigation.
- Next three loops: OP-073/074, OP-075/076, OP-077/078.

## 2026-07-21 stock substitution and approval-gated cart integration handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-069 and OP-070.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `8` previous combinations, `4` current combinations, `1` missing offer, `3` cart items, `1` active safety rule, and `1` active exclusion.
- Primary evidence: `data/original_plan/evidence/op069_op070_product_combination_stock_cart_smoke_v1.json`; SHA-256 `9b40f6a05e73e82dde8582f7c0e7e043f9e1481214cd3d825c0d19e03a15e139`; combined source SHA-256 `07f8f483bcc013fd51627f27aa58e0e03c6c8cc208dc987abf987600049830ca`.
- Source identity: R&D `a2ae7a289ae3f0923145db707f3c042e868cd059`; WellnessBox `4d904f43b028a35524a29206aaf7c6b99f58a97b`.
- Main changes: strict previous replay context; current-catalog stock loss detection; existing optimizer reuse; independent previous/current ranking validation; exact safety-policy and recommendation-input binding; fail-closed cart suppression on non-stock changes; existing cart-item contract conversion; source scan for cart, order, and payment mutations; manifest, reports, workflow, tests, and canonical evidence. No training or simulation behavior changed.
- Honest stage: OP-069 and OP-070 are COMPLETE at `INTEGRATED`. Existing route-function integration and approval-gated candidate construction are proven. Actual Prisma execution, browser cart mutation, user approval, Order/OrderItem/Payment creation, production deployment, and production operation are not.
- Validation: focused `26 passed`; workflow-equivalent `505 passed`; full Ruff PASS; service QA/typecheck/lint PASS; `18` service-dependent smokes PASS; audit PASS with `69` claims and `203` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `886 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: service commit `4d904f43b028a35524a29206aaf7c6b99f58a97b`; R&D commit `06debd77c39581c6cbe90beefa3be3095336f606`; Original plan evidence run `29819257210` succeeded.
- Five bottlenecks: actual Prisma catalog-query evidence; production catalog freshness; deployed service/R&D operation; OP-071 unified state-transition contract; OP-072 enforced orchestration order.
- Next three loops: OP-071/072, OP-073/074, OP-075/076.

## 2026-07-21 product-combination top-k and reproducibility integration handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-067 and OP-068.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `4` evaluated combinations, top-k `3`, and `1` non-selection reason.
- Primary evidence: `data/original_plan/evidence/op067_op068_product_combination_top_k_smoke_v1.json`; SHA-256 `f510f7c09aea3e23af64275001b53ae6a14b0c45760a3a0a112cb390dd5153ae`; combined source SHA-256 `b78acd6e01dc75eab4dfe18622c975ba810877d6ae3321a5d7847a5452482613`.
- Source identity: R&D `dc8e145b3a62897af6238f2c9b74dd35a75f4714`; WellnessBox `a27de7c0beee507114641e24a058827d46ad2ef0`.
- Main changes: global eligible-combination ranking before response limiting; precise non-selection reasons; fail-closed truncated search; content-addressed optimization and catalog identities; duplicate offer-ID rejection; independent R&D ranking and provenance validation; manifest, reports, workflow, tests, and canonical evidence. No training or simulation behavior changed.
- Honest stage: OP-067 and OP-068 are COMPLETE at `INTEGRATED`. Existing route-function integration is proven, but actual Prisma execution, production data freshness, deployment, production operation, ordering, and payment are not.
- Validation: focused `20 passed`; workflow-equivalent `499 passed`; full Ruff PASS; service QA/typecheck/lint PASS; `17` service-dependent workflow smokes PASS; audit PASS with `67` claims and `200` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `880 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: service commit `a27de7c0beee507114641e24a058827d46ad2ef0`; R&D commit `0635b17c2dd18c9f861c012c5f865fb5f720abf3`; Original plan evidence run `29816477275` succeeded.
- Five bottlenecks: actual Prisma catalog-query evidence; production catalog freshness; deployed service/R&D operation; stock-change substitution evidence for OP-069; approval-gated cart conversion for OP-070.
- Next three loops: OP-069/070, OP-071/072, OP-073/074.

## 2026-07-21 product-combination constraint and safety integration handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-065 and OP-066.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `4` constraint-filter inputs, `1` product-side safety-filter input, and `1` actual localhost R&D-to-service constraint response.
- Primary evidence: `data/original_plan/evidence/op065_op066_product_combination_filter_smoke_v1.json`; SHA-256 `87c16d1e39d2a7ea9b64f16ba46f0bcb5946da8265aa87c75e40a53611de2a3f`; combined source SHA-256 `ace71663d00cb8999affafc0cd2fad9c24ccc3390264bba0a895fb1703ead1c0`.
- Source identity: R&D `275674c5d667e4a76f42dd6aa62dbcadf5baec50`; WellnessBox `7f248485f522fd85ca09a71a9252cf1ec8dc5896`.
- Main changes: strict R&D product constraints; existing service-route validation before zero-result return; budget and maximum-product filters applied before the eligible cap; product-side ingredient safety exclusion; fail-closed recommendation re-entry protection; independent R&D filter recomputation; manifest, reports, workflow, tests, and canonical evidence. No training or simulation behavior changed.
- Honest stage: OP-065 and OP-066 are COMPLETE at `INTEGRATED`. Actual localhost R&D constraint transport is proven, but the actual READY filter path, Prisma execution, production data freshness, deployment, production operation, ordering, and payment are not.
- Validation: focused `27 passed`; workflow-equivalent `492 passed`; full Ruff PASS; service QA/typecheck/lint PASS; `16` workflow smokes PASS; audit PASS with `65` claims and `198` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `873 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, and unchanged metric-specific weakest categories.
- Publication: service commit `7f248485f522fd85ca09a71a9252cf1ec8dc5896` passed Encoding Guard run `29813747636`. R&D commit `c085d467a6447316fc865b84996e6085fa7b928d` passed Original plan evidence run `29813998092`.
- Five bottlenecks: actual READY R&D filter-path evidence; actual Prisma catalog-query evidence; production catalog freshness; deployed service/R&D operation; OP-067 top-k non-selection reasons.
- Next three loops: OP-067/068, OP-069/070, OP-071/072.

## 2026-07-21 product combination and aggregate-dose integration handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-063 and OP-064.
- Primary dataset and cases: frozen eval `256` cases; service fixture `7` products and `8` recommendations; canonical smoke `4` generated combinations with `2` independently validated representative combinations.
- Primary evidence: `data/original_plan/evidence/op063_op064_product_combination_dose_smoke_v1.json`; SHA-256 `64821bf96e724cfcb21be2b4e0d011dd3c364b072614ca7505dda8659b1e9ea8`; combined source SHA-256 `3c48c1b8fecac69e3b8b088830e0efa7c6bcc4b9784f81af72a0dcc39d69ce05`.
- Source identity: R&D `00fbd06f275e7ba2a486e398fdd56591388df6ad`; WellnessBox `6c599ebeebca73e8d769426b02f12d4e7be19073`.
- Main changes: the existing `/api/tips` adapter converts strict selling-product declarations into deterministic ingredient combinations, reuses the existing in-stock offer selection, deduplicates shared products, normalizes mass to integer nanograms and IU to milli-IU, and reports total declared dose by ingredient and unit. Duplicate ingredients require distinct product IDs. Search is memoized, bounded to `4096` states, and capped at `64` unique combinations. Ambiguous ranges and missing target amounts fail closed. The R&D model independently revalidates identities, costs, totals, duplicates, limits, and source identity. No training or simulation logic changed.
- Honest stage: OP-063 and OP-064 are COMPLETE at `INTEGRATED`. The existing service route and R&D validation contract are connected, but actual Prisma execution, production catalog freshness, deployment, production operation, ordering, and payment are not proven.
- Validation: product-combination tests `10 passed`; exact workflow selection `482 passed`; full Ruff PASS; service QA/typecheck/lint/build PASS; all `15` workflow smokes reproduce byte-identically; audit PASS with `63` claims and `196` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `863 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: service commit `6c599ebeebca73e8d769426b02f12d4e7be19073` passed Encoding Guard run `29811071339`. R&D commit `23d5c43efc8b029f78c2f62c92665bc5960307de` passed Original plan evidence run `29811445770`.
- Five bottlenecks: actual Prisma catalog-query evidence; production catalog freshness; deployed service/R&D operation; OP-065 budget and maximum-product exclusion; OP-066 safety-block preservation.
- Next three loops: OP-065/066, OP-067/068, OP-069/070.

## 2026-07-21 optimization constraints and selling-product contract handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-061 and OP-062.
- Primary dataset and cases: frozen eval `256` cases; canonical constraint smoke `6` cases; service product fixture covers `8` mapped ingredient IDs.
- Primary evidence: `data/original_plan/evidence/op061_op062_optimization_product_catalog_smoke_v1.json`; SHA-256 `aaa917bb4256e648d62fa12564353c26fe01717cb38360aa23e0495e1f22f480`; combined source SHA-256 `83118c67e45f96e6eba41e6ee853977278da8d9a8043239ca35bb3d97da10429`.
- Source identity: R&D `ea3bc72484708002065ee4929dc62ca006ce980c`; WellnessBox `a85767d9dc9418a23a9adeb2372d14a75d10b865`.
- Main changes: immutable R&D constraint contract and evaluator; existing service catalog query extended with detail facts and in-stock offers; existing `/api/tips` adapter extended with normalized amount, price, stock, and formulation facts; strict fail-closed QA; manifest, generated reports, workflow, tests, and canonical evidence.
- Honest stage: OP-061 is COMPLETE at `IMPLEMENTED`. OP-062 is COMPLETE at `INTEGRATED` because the existing service route function consumes the extended adapter contract. Actual Prisma execution, production freshness, deployment, operation, ordering, and payment remain unproven.
- Validation: optimizer `16 passed`; CI-equivalent `472 passed`; full Ruff PASS; service QA/typecheck/lint/build PASS; all `14` workflow smokes byte-identical; audit PASS with `61` claims and `192` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `853 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: service Encoding Guard run `29808830876` and R&D Original plan evidence run `29808907535` passed. Evidence commit is `e50ba258e6b965f3a3af9aa5b078e00e8d690647`.
- Five bottlenecks: actual Prisma catalog query evidence; production catalog freshness; deployed service/R&D operation; product-to-ingredient combination generation; duplicate-ingredient and total-dose enforcement across combinations.
- Next three loops: OP-063/064, OP-065/066, OP-067/068.

## 2026-07-21 PRO worsening actions and outcome-class integration handoff

- Chosen stage and tasks: `original plan / pre-post outcome quantification and PRO`; OP-059 and OP-060.
- Primary dataset/evidence: frozen eval `256` cases; four authenticated real-world-class enrollment/follow-up pairs and one synthetic paired case. Canonical evidence SHA-256 `ec14bf87025c9b1651462a936092cc3e2089956df2a72cfb826fa3594f22318d`; combined source SHA-256 `8e6969aac2e5e4d17bc9dfbb5176207874f697bd111955ea9fca6d06d107f7eb`.
- Source identity: R&D `a580d813abfc1bed0292477c9ba6dc88ec4f8f4f`; WellnessBox `5ec3adf1f3948e910c1f4498083b43c701eaf557`.
- Implementation: `metrics/pro_actions.py` validates the exact four decisions and rejects mutated derived output. The existing plan service, interim route, strict execution events, service proxy/client, TIPS PRO state, and UI carry the decision and selected outcome class. No second recommendation engine, event store, API, or product system was added.
- Result: serious adverse events select stop; other adverse events select reduce; low adherence or missed doses select maintain; interpretable worsening selects re-optimize. Observed numeric change is not adjusted and no causal effect is claimed. `REAL_WORLD_OUTCOME` is a contract class only; no production or real patient data was used.
- Honest stage: OP-059 and OP-060 are `INTEGRATED` and COMPLETE at their required stage. Production deployment, operation, real-data provenance, and action execution remain unproven.
- Validation: focused `54 passed`; workflow-equivalent `456 passed`; full suite `837 passed`, `77 failed` in the known `73 + 4` groups; frozen 256 evaluation has seven zero deltas and identical weakest slices; full Ruff and service build/lint/typecheck/QA PASS; 13 workflow smokes are stable; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: R&D is published through `b068edac16e889dc6d18e004cf87726eb39e214d`; service through `5ec3adf1f3948e910c1f4498083b43c701eaf557`; R&D Original plan evidence run `29807082270` and service Encoding Guard run `29807015490` succeeded.
- Biggest remaining bottlenecks: required operation evidence for OP-021~030, OP-040, OP-053, and OP-058; qualifying external labels for OP-039; OP-061~120 implementation; missing trusted report archive for 73 tests; four CGM geometry failures.
- Protected user files remain untouched. Existing `etc/` files remain untracked and were not used as canonical evidence.
- Next three loops: OP-061/062; OP-063/064; OP-065/066.

## 2026-07-21 corrected PRO service contract and lineage handoff

- Chosen stage and tasks: `original plan / pre-post outcome quantification and PRO`; OP-057 and OP-058.
- Primary dataset/evidence: frozen eval `256` cases; one synthetic authenticated enrollment, one follow-up creation, and one correction over two strict PRO events. Canonical evidence SHA-256 `67ffac5637d9281cd5b99ae4e435049669842ad2e4abdc54f69b71cbdd90a711`; combined source SHA-256 `10662658664b0ba08112a61582e1a0d22e0d2e3eada875c44bffcf314a016092`.
- Source identity: R&D `86823c364094b275e0e9d41a2b78ed22833b383e`; WellnessBox `9dfc1d0b2034ed15777385802b7283a3ffc78c02`.
- Changed paths: R&D recommendation schema/service, execution ledger, PRO runtime/correction/follow-up services, interim endpoints, contracts, tests, smoke/workflow, manifest/evidence/report; service TIPS PRO UI, authenticated plan/effect routes, existing R&D client/profile adapter, and QA scripts. No new database or duplicate event store was added.
- Result: the service UI persists the R&D execution, plan, and baseline identities. Recommendation and optimization events plus the observed effect share one plan ID; the corrected raw score is `10 -> 8 -> 7`. Duplicate retries are idempotent, while changed baseline or ownership conflicts return HTTP 409 or fail closed.
- Honest stage: OP-057 is `INTEGRATED` and COMPLETE. OP-058 is `INTEGRATED` and PARTIAL below `OPERATED`. Browser rendering behind authenticated login, production operation, real-world outcomes, deployment, and causal effects are not proven.
- Validation: focused `127 passed`; workflow-equivalent `446 passed`; full suite `827 passed`, `77 failed` in the known `73 + 4` groups; frozen 256 evaluation has seven zero deltas and identical weakest slices; full Ruff and service build/lint/typecheck/encoding checks PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: R&D is published through `a431cc448e26155ded2bd694715fa3b541009c53`; service through `9dfc1d0b2034ed15777385802b7283a3ffc78c02`; R&D Original plan evidence run `29805184034` and service Encoding Guard run `29804815958` succeeded.
- Biggest remaining bottlenecks: required operation evidence for OP-021~030, OP-040, OP-053, and OP-058; qualifying external labels for OP-039; OP-059~120 implementation; missing trusted report archive for 73 tests; four CGM geometry failures.
- Protected user files remain untouched. Existing `etc/` files remain untracked and were not used as canonical evidence.
- Next three loops: OP-059/060; OP-061/062; OP-063/064.

## 2026-07-21 personal and group PRO uncertainty handoff

- Chosen stage and tasks: `original plan / pre-post outcome quantification and PRO`; OP-055 and OP-056
- Primary dataset and evidence: `data/frozen_eval/frozen_eval_v1.jsonl` has `256` cases. `data/original_plan/evidence/op055_op056_pro_personal_group_uncertainty_smoke_v1.json` has `100` synthetic personal interpretations plus a separate group estimate and SHA-256 `4a458659b2c44cf35cf4589ac9f09e70ae63de37d7c2891356ce6e9c67fd4eb9`.
- Source identity: commit `56d0542e9506992621c8e356752ee41aec7b09d3`; source bundle SHA-256 `974bc53e20a0ad73308150eacc6218fe11f8182d563d872e6f7112763b619c34`.
- Implementation: `metrics/pro_group_effects.py` retains validated personal effects and derives a separately named group estimate. `metrics/statistics.py` now supplies the same seeded percentile bootstrap used by the existing interim KPI path. Cohorts fail closed on duplicate identities and mixed timepoint, data-class, or scoring identities; derived output mutation is rejected.
- Result: sample size `100`; fully interpretable `100`; mean health-Z change `0.67`, 95% CI `[0.616666, 0.723333]`; mean health-percentile change `25.779542`, 95% CI `[23.82636, 27.745993]`; uncertainty reasons `observational_association_not_causal` and `non_real_world_outcome_data`.
- Files changed: the new group contract, group metrics/statistics modules, deterministic smoke, focused tests, metrics exports, interim KPI helper call, evidence workflow, manifest, generated completion files, and governance tests. Existing OP-051~054 evidence source identities were refreshed because shared metrics files changed. The WellnessBox service repository was unchanged.
- Evidence stage: OP-055 and OP-056 are `IMPLEMENTED` and COMPLETE at their required stage. Counts are complete `43`, partial `12`, pending `64`, external `1`, contradicted `0`. This loop proves only synthetic local implementation; it does not prove real-world outcomes, service integration, operation, deployment, or causal effect.
- Validation: focused `43 passed`; workflow-equivalent `425 passed`; full Ruff PASS; audit PASS with `55` claims and `171` evidence files; report check PASS; full suite `806 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups; frozen eval has seven zero deltas and unchanged weakest slices; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: source commits `5b9dedcc62ff3bcb4c36d882f7f28ebaf2784968` and `56d0542e9506992621c8e356752ee41aec7b09d3`, evidence commit `0a1f102877a09f90195c64fdeeb67a73843f4913`, and Original plan evidence run `29799527985` are published and successful.
- Biggest remaining bottlenecks: OP-021 through OP-030, OP-040, and OP-053 still lack required operation evidence; OP-039 lacks qualifying independent labels; OP-057 through OP-120 contain `64` pending requirements; the trusted archive for `73` report-dependent tests is absent; `4` CGM geometry assertions remain unresolved.
- Protected files remain untouched: `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` and `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`.
- Next three loops: OP-057/058 corrected PRO and plan-linked outcome lineage; OP-059/060 observed-worsening actions and real-outcome data classes; OP-061/062 optimization constraints and the existing service product contract.

## 2026-07-21 PRO follow-up persistence and interpretation handoff

- Chosen stage: `original plan / pre-post outcome quantification and PRO`
- Chosen tasks: OP-053 and OP-054
- Primary dataset and evidence: `data/frozen_eval/frozen_eval_v1.jsonl` has `256` cases; `data/original_plan/evidence/op053_op054_pro_followup_interpretation_smoke_v1.json` has `4` ordered synthetic PRO persistence events and SHA-256 `b57a6ef61310fc70727cb6bca9e3c4addc117d163bf627a72d0fb263d82392fc`.
- Source identity: commit `83997c11684fc482462668865afc843f7cf211ff`; source bundle SHA-256 `6d5829f753148e2c879c4dd546d2a0e5b58fd105f6129653f75147c4cea64e34`.
- Implementation: the existing execution ledger persists strict pre-intake, week-2, week-4, and discontinuation events in order. The interpretation API returns unchanged observed score deltas plus explicit adherence, missed-dose, and adverse-event limitations. It never claims causal effect.
- Fail-closed fixes: strict PRO payloads cannot be stored as conversation events; generic and strict payloads cannot be interconverted by correction; interpretation rejects duplicate assessment IDs, reversed observation time, cross-plan pairs, and cross-distribution pairs.
- Files changed: `src/wellnessbox_rnd/interim/data_lake.py`, `src/wellnessbox_rnd/metrics/pro_followup.py`, `scripts/run_pro_followup_adherence_interpretation_smoke.py`, `tests/test_pro_followup_effects.py`, manifest/evidence/generated completion files, and governance expectation tests. The WellnessBox service was unchanged.
- Evidence stage: OP-053 `IMPLEMENTED` below required `OPERATED`, so it is PARTIAL. OP-054 `IMPLEMENTED`, so it is COMPLETE. Counts are complete `41`, partial `12`, pending `66`, external `1`, contradicted `0`.
- Validation: focused `90 passed`; workflow-equivalent `407 passed`; full Ruff PASS; audit PASS with `53` claims and `165` evidence files; report check PASS; full suite `788 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups; frozen eval has seven zero deltas and unchanged weakest slices; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: commits `83997c11684fc482462668865afc843f7cf211ff`, `706fb4ad22710ab0c5f6d5364ecd5aa3e694fe39`, and `0e7ea31bdf240cab0f4b7a34d35e7722e0a09e2e` are on `origin/main`; Original plan evidence run `29797963682` passed.
- Biggest remaining bottlenecks: OP-053 lacks production operation; OP-021 through OP-030 and OP-040 remain below `OPERATED`; OP-039 lacks qualifying external labels; the trusted archive for `73` report-dependent tests is absent; `4` CGM geometry assertions remain unresolved.
- Protected files remain untouched: `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` and `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`.
- Next three loops: OP-055/056 separate personal and group effects with uncertainty; OP-057/058 recalculate corrected PRO and link outcome lineage; OP-059/060 connect observed worsening to actions and real outcome data classes.

## 2026-07-17 versioned PRO scoring and baseline-percentile handoff

- Chosen stage: `original plan / pre-post outcome quantification and PRO`
- Chosen tasks: OP-051 and OP-052
- Primary evidence: `data/original_plan/evidence/op051_op052_versioned_pro_scoring_smoke_v1.json`; current deterministic SHA-256 `b14d8a69e7e62ca40837dab30552482c638de31452030168afecaf24eb7c5ddf`; source commit `334bd706f72593b7c948785ad2b8630fb65b8911`; source bundle SHA-256 `b9d49513fffb58d6f0a1bcda58741e637fca79c14ab09697492be771b9ba9169`
- Raw scores: the existing R&D PRO module now applies one strict contract to PSQI seven-component sums (`0..21`), ISI seven-item sums (`0..28`), and PSS-10 ten-item sums with items `4, 5, 7, 8` reversed (`0..40`). PSQI 19-item derivation and questionnaire text are intentionally outside this contract.
- Standardization: versioned `BASELINE` observations of one instrument/version produce an order-independent mean and sample standard deviation. Lower problem scores map to higher health Z scores and percentiles. The smoke fixes Z scores `1, 0, -1` to percentiles `84.134475, 50, 15.865525` for all three instruments.
- Fail-closed boundary: public functions revalidate supplied model instances; output models enforce canonical score metadata and ranges; distributions verify source scores, statistics, role, version, and SHA-256; standardized outputs embed the validated distribution. Rounding method and operation order are part of the committed contract.
- Evidence boundary: `SYNTHETIC_OUTCOME_PROXY` only. No service code, authorized questionnaire text, production data, clinical interpretation, deployment, or production operation is claimed.
- Evidence stage: OP-051 and OP-052 are `IMPLEMENTED`. Generated counts: complete `40`, partial `11`, pending `68`, external `1`, contradicted `0`.
- Validation: related scoring tests `38 passed`; CI-equivalent `388 passed`; full Ruff PASS; audit PASS with `51` claims and `160` evidence files; full suite `769 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups; frozen eval has seven zero deltas and no weakest-slice changes; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: commits `fd7e4a3d1d6edb630d6c25cdb0fde11129d98975` and `3bfdfed8d1aabfbfbbcca908bfb17f154aba4e46` are on `origin/main`; Original plan evidence run `29515937856` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-053/054 add follow-up PRO events and adherence/adverse-event interpretation; OP-055/056 separate personal/group effects and return uncertainty; OP-057/058 add user correction and plan-linked outcome lineage.

## 2026-07-17 learned replay and product-candidate handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-049 and OP-050
- Primary evidence: `data/original_plan/evidence/op049_op050_replay_product_candidates_smoke_v1.json`; deterministic SHA-256 `ff3b58d106ac4d8678df1ed6925b01232387880c8d5e6b4064a93d5ef4cdc2e1`; R&D source `584c6c7ca3d053c9ae3430b214eae23f35009b15`; WellnessBox source `a6b8ab1e92a112f6d2e904436bfe44ba688fc4e8`
- Replay result: all `256` frozen requests use paired baseline/learned execution. Learned applies to `12`; `244` are `not_eligible`; true fallback count is `0`; selection changes `4`; rank/score changes `5`; response status, next action, and full safety payload changes are all `0`.
- Service result: the existing ingredient map and `product.catalog` in-stock Prisma path resolve all `8` mapped service ingredients against the captured live-catalog snapshot. The route returns explicit candidates or `NO_MATCH` and fails closed for invalid catalogs and unmapped identifiers. Product and ingredient contract versions must match exactly.
- Boundary: actual R&D HTTP observation is the safety-blocked path only. READY product conversion uses the test-only route seam and captured catalog snapshot. No READY two-process proof, production operation, or deployment is claimed.
- Evidence stage: OP-049 `IMPLEMENTED`; OP-050 `INTEGRATED`. Generated counts: complete `38`, partial `11`, pending `70`, external `1`, contradicted `0`.
- Validation: focused `5 passed`; service QA covers `8/8` mappings; CI-equivalent `350 passed`; full Ruff PASS; audit PASS with `49` claims and `155` evidence files; full suite `751 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups; frozen eval has seven zero deltas and no weakest-slice changes; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: WellnessBox Encoding Guard runs `29511317388` and `29511798649` passed. R&D commits through `3ed17debdbfc0646c819066d4f7a8cbfec36a159` are on `origin/main`; Original plan evidence run `29513104957` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-051/052 version PSQI, ISI, and PSS-10 scoring plus percentile conversion; OP-053/054 add follow-up events and adherence/adverse-event interpretation; OP-055/056 separate personal/group effects and return uncertainty.

## 2026-07-16 decision uncertainty and learned-fallback handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-047 and OP-048
- Primary evidence: `data/original_plan/evidence/op047_op048_decision_uncertainty_learned_fallback_smoke_v1.json`; deterministic SHA-256 `55eae7c9a7a99557fa47ecc687e622bc0a959550b7d629db4e7008e0f5d7d158`; source commit `22aca5e9d64a493562f9d17b302bead2ca02c555`
- Main result: the existing recommendation response now returns versioned numeric uncertainty for missing inputs, review state, candidate availability, and the preselection top-two margin. The score is explicitly not a clinical probability. Every post-safety candidate has a complete ranked score trace with full breakdown, reason, rules, goals, catalog priority, and evidence linkage.
- Fallback result: learned reranking exposes one explicit decision status. Missing, malformed, unsupported, suspicious, or runtime-failing artifacts discard all partial learned results and return the exact deterministic recommendations and `deterministic_baseline_v1` mode. Valid artifacts require explicit model/target identity, supported runtime features, catalog-valid candidate keys, closed-domain values, compatible dimensions, and bounded finite coefficients.
- Fail-closed boundary: response and current-version contract validators reconcile the ranking snapshot and all selected/unselected scores against the post-safety pool, catalog, goal-prior, signal, and safety registries. They reject score/status/selection mutations, partial diagnostics removal, and schema downgrade. Legacy V1 contract validation is available only through explicit compatibility mode.
- Evidence stage: OP-047 and OP-048 are `IMPLEMENTED`. Generated counts are complete `36`, partial `11`, pending `72`, external `1`, contradicted `0`. No WellnessBox service change, deployment, or production operation was performed.
- Validation: focused selection `60 passed`; exact CI-equivalent selection `345 passed`; full Ruff PASS; manifest audit PASS with `47` claims and `145` checked evidence files; completion report check PASS; independent final review Critical `0`, Important `0`, Minor `0`; full suite `746 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: source commit `22aca5e9d64a493562f9d17b302bead2ca02c555` and evidence commit `ae38c36963f00d9c7f0f84cf4cd5597a1e271645` are on `origin/main`; Original plan evidence run `29509159767` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-049/050 compare learned/baseline replay and convert ingredients to service products; OP-051/052 implement versioned PRO scoring and percentile conversion; OP-053/054 implement follow-up state and change calculation.

## 2026-07-16 candidate-pool and structured-reason handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-045 and OP-046
- Primary evidence: `data/original_plan/evidence/op045_op046_candidate_pool_structured_reasons_smoke_v1.json`; current deterministic SHA-256 `86cc00d7662d96a2a350dfabc7b41395987b65db1f418d3bcd7de5741e6d335e`; source identity refreshed to commit `22aca5e9d64a493562f9d17b302bead2ca02c555`
- Main result: the existing optimizer and response now preserve one shared pre-safety/excluded/post-safety candidate partition and selected subset. Global blocking retains the pool for audit but returns no selection. User avoidance, current-regimen overlap, and safety exclusions remain distinguishable.
- Structured reason result: every selected candidate returns goal and applied input signals, all 14 score terms, exact rule/reference/claim IDs, limitations, evidence links, and a total that reconciles to the candidate score. Safety-review scoring preserves the triggering safety rule and scoring-time status. Learned reranking rebuilds the same reason after its bonus is applied.
- Fail-closed boundary: schemas and the recommendation contract reject partition identity drift, duplicate evidence links, incomplete terms, score/component mismatches, forged or empty evidence IDs, wrong ownership, wrong learned markers, and unexpected fields. Candidate selection and trace generation share one partition function instead of duplicating filter logic.
- Evidence stage: OP-045 and OP-046 are `IMPLEMENTED`. Generated counts are complete `34`, partial `11`, pending `74`, external `1`, contradicted `0`. No WellnessBox service change, deployment, or production operation was performed.
- Validation: focused selection `203 passed`; exact local CI-equivalent selection `315 passed`; full Ruff PASS; manifest audit PASS with `45` claims and `140` checked evidence files; completion report check PASS; independent final review Critical `0`, Important `0`, Minor `0`; full suite `716 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: commits `f7479d710e227fe428d96977a91ce2ab66438d06`, `c8c636c61497929a3afb3933236520226c555072`, `92cf53a8f0c2050e7b4ae2368d36b95d2396c9df`, and `0cd4db94c87ac223f7062ae75e6a2ac02267c722` are on `origin/main`; Original plan evidence run `29504825809` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-047/048 quantify uncertainty and enforce learned-artifact fallback; OP-049/050 compare learned/baseline replay and convert to service products; OP-051/052 implement versioned PRO scoring and percentile conversion.

## 2026-07-16 candidate signal scoring handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-043 and OP-044
- Primary evidence: `data/original_plan/evidence/op043_op044_candidate_signal_scoring_smoke_v1.json`; current deterministic SHA-256 `b949483625e5fba4bdbea96afe9cb8ade1f7e45cbc1d5db2955b1e10f6f30052`; source identity refreshed to commit `22aca5e9d64a493562f9d17b302bead2ca02c555`
- Main result: existing candidate scores now expose separate symptom, laboratory, lifestyle, dietary, wearable, CGM, and genetic terms with observed values, bounded points, versioned rule IDs, exact reference/claim IDs, and limitations. The recommendation contract includes every new term in its total.
- Safety boundary: source-specific recommendation consent is explicit for snapshots. CGM TIR scoring requires a verified 70–180 mg/dL range, nonpregnant diabetes context, and a blood-glucose goal. Unknown genetic tags, custom TIR ranges, invalid aliases/bounds, and unscoped tags add zero. The scorer executes only the registry embedded in the validated runtime artifact.
- Evidence stage: OP-043 and OP-044 are `IMPLEMENTED`. Generated counts are complete `32`, partial `11`, pending `76`, external `1`, contradicted `0`. No WellnessBox service change, deployment, or production operation was performed.
- Validation: focused selection `70 passed`; exact CI-equivalent selection `301 passed`; manifest audit PASS with `43` claims and `134` checked evidence files; stored runtime equals fresh; full Ruff PASS; independent final review Critical `0`, Important `0`, Minor `0`; full suite `705 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: source commit `1465db1c153b71b8b636231eb6487c32e469c85b` and evidence commit `64d67eceef2996869c897e9a0bc02b33a549010f` are on `origin/main`; Original plan evidence run `29501666136` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-045/046 preserve pre/post safety candidate sets and return structured reasons; OP-047/048 quantify uncertainty and preserve deterministic fallback; OP-049/050 compare learned/baseline replay and convert candidates to service products.

## 2026-07-16 ingredient identity and goal-prior handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-041 and OP-042
- Primary evidence: `data/original_plan/evidence/op041_op042_ingredient_mapping_goal_prior_smoke_v1.json`; deterministic SHA-256 `fd37111339773f86904cc3d4f6f2b5fda45ff2d51e4f1b8a6a5ff35d5013e8a6`
- Main files: byte-identical service/R&D identifier contracts; service mapping and final-authority modules; R&D goal-prior registry, validator, scorer integration, reference/runtime artifacts, official-source notes, focused tests, two-process smoke, manifest, generated status, and both CI workflows
- Current result: every service and R&D catalog identifier is mapped or explicitly unmapped. Relationship and direction are validated. The actual `/api/tips` export enriches a mapped R&D recommendation with the service ID and returns a service-owned fail-closed block for an unmapped ID.
- Goal-prior result: `24` catalog-supported pairs cover all `9` goals. Registered points preserve the prior `35/18` candidate ordering and are explicitly not efficacy probabilities. Clinical evidence labels are derived from exact scoped claim types; policy-only records cannot be promoted, and unrelated references or forged policy claims are rejected.
- Evidence stage: OP-041 is `INTEGRATED`; OP-042 is `IMPLEMENTED`. Generated counts are complete `30`, partial `11`, pending `78`, external `1`, contradicted `0`. No deployment or production operation was performed.
- Validation: focused selection `48 passed`; exact CI-equivalent selection `283 passed`; manifest audit PASS with `41` claims and `124` checked evidence files; stored runtime equals fresh and fresh builds are deterministic; full Ruff PASS; independent final review Critical `0`, Important `0`; full suite `683 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: WellnessBox commit `58246f9a086c81bb3a38d4a1f33f5205b388d2b8` is on `origin/main`, and Encoding Guard run `29496255239` passed. R&D source commit `6a1f874b95fadbffbab796eefcbecd71284b6d9e` and evidence commit `da2936206d0ebe8b2ef12d9e0b79f048f2239b10` are on `origin/main`; Original plan evidence run `29496879246` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-043/044 candidate filtering and auditable scoring; OP-045/046 post-filter preservation and structured reasons; OP-047/048 uncertainty and deterministic fallback.

## 2026-07-16 external high-risk gate and final safety-authority handoff

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-039 and OP-040
- Primary evidence: `data/original_plan/evidence/op040_final_safety_authority_integration_smoke_v1.json`; actual `POST /api/tips` export and localhost R&D `POST /v1/interim/recommendations`, deterministic SHA-256 `c01eca4f667cfcea00c95f7830ebd8f9711482d81e40e6f4b23629719b9c5183`
- Main files: R&D interim route and safety evaluator; external high-risk evaluator, contracts, empty trust roots, tests, and CLI; service `/api/tips` route, R&D client, final-authority validator, test-only dependency hook, QA scripts, and both repositories' CI workflows
- Current result: stored and current risk facts are conservatively combined before model execution, including multi-key dynamic predicates split across sources. Hard failures do not call the model and return zero recommendations. The service preserves a valid R&D final block and fails closed on transport or contract failure.
- OP-039 boundary: no externally labeled high-risk dataset, detached attestation, independent verification receipt, or repository-approved trust-root entry exists. OP-039 therefore remains unclaimed at `EXTERNAL`; internal synthetic tests are contract verification only.
- Evidence stage: OP-040 is `INTEGRATED`, not `OPERATED`. Generated counts are complete `28`, partial `11`, pending `80`, external `1`, contradicted `0`. The smoke explicitly records `production_operation_proven=false`.
- Validation: focused selection `19 passed`; exact CI-equivalent selection `268 passed`; full Ruff PASS; manifest audit PASS with `39` claims and `113` checked evidence files; completion report check PASS; runtime stored/fresh equality PASS with zero issues; final independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `673 passed`, `77 failed`, matching the known `73` absent-report and `4` CGM-geometry groups. Official frozen eval: `256` cases, seven zero metric deltas, unchanged overall and metric-specific weakest-slice categories.
- Publication: WellnessBox service commit `9609ce804ad06c609b794f455d4f6127b59361ac` is on `origin/main` and Encoding Guard run `29492239202` passed. The R&D implementation source commit is `e830c7debd4b103b756bba494fdbc73d7f0bad3a`; evidence publication and Original plan evidence CI remain the final loop steps.
- Biggest bottlenecks: qualifying independent OP-039 labels and approvals; deployed R&D process; production `WB_RND_*` configuration; durable production storage; observed production final-block behavior.
- Next three loops: OP-041/042 identifier mapping and evidence-backed goal priors; OP-043/044 candidate filtering and auditable scoring; OP-045/046 post-filter preservation and structured recommendation reasons.

## 2026-07-16 dose-limit and rule-metadata handoff

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-037 and OP-038
- Primary dataset path and case count: `data/original_plan/evidence/op037_op038_dose_limit_rule_metadata_smoke_v1.json`; `7` deterministic dose-evaluation cases
- Main files: safety rule DSL and models; runtime knowledge records and stored artifact; recommendation schema and safety service; Data Lake replay projection; focused parser, API, replay, and runtime-boundary tests; smoke runner; manifest, generated reports, CI workflow, and implementation plan
- Current result: complete compatible doses use the existing aggregate and normalized unit for upper-limit comparison. Supplied but partial, non-convertible, compound, ranged, or schedule-qualified legacy evidence excludes the affected ingredient with `dose_evidence_incomplete` and no fabricated total. Optional absent doses do not claim evaluation. Complete above-limit totals retain blocker behavior.
- Parser boundary: comma-grouped amounts parse correctly; multiple amount-unit pairs, single-unit ranges, `twice daily`/`bid`/`N x` schedules, and compound product doses fail closed. Compound segments including modifiers and `plus` are recognized separately. Fuzzy title matching is accepted only when exactly one ingredient remains.
- Metadata result: every runtime safety record has a positive version derived from its rule metadata or knowledge-artifact suffix. Every returned rule includes the same version. `SafetySummary.applied_at` is timezone-aware; smoke injects `2026-07-16T00:00:00Z`. Replay omits that volatile timestamp only from deterministic output comparison.
- Evidence stage: `IMPLEMENTED`. OP-037 and OP-038 are complete at their required stage. Generated counts are complete `28`, partial `10`, pending `81`, external `1`, contradicted `0`. No service code, deployment, or production two-process integration changed.
- Validation: focused selection `240 passed`; exact CI-equivalent selection `252 passed`; full Ruff PASS; deterministic smoke hash `2a34f58b4564b903560341bf0862d1ce12016a0a84f6b4efd298616255347dbb`; manifest audit PASS with `38` claims and `105` checked evidence files; completion report check PASS; runtime stored/fresh equality PASS with zero issues; final independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `657 passed`, `77 failed`, matching the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Biggest bottlenecks: externally labeled high-risk cases for hard false-negative proof; production final-block authority across the real service/R&D boundary; deployed R&D process; durable production R&D storage; authenticated two-process round trip.
- Next three loops: OP-039/040 high-risk and production blocking evidence; OP-041/042 identifier mapping and evidence-backed goal priors; OP-043/044 candidate filtering and auditable scoring.

## 2026-07-16 interaction evidence and dose aggregation handoff

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-035 and OP-036
- Primary dataset path and case count: `data/original_plan/evidence/op035_op036_interaction_dose_aggregation_smoke_v1.json`; `10` deterministic recommendation/replay cases
- Main files: NIH ODS raw reference and regenerated knowledge artifacts; safety rule DSL and models; runtime knowledge validation; recommendation and interim safety paths; structured safety response; focused tests; smoke runner; manifest, generated reports, CI workflow, and implementation plan
- Current result: every runtime drug-ingredient interaction rule has non-empty, cross-validated reference and claim IDs, and duplicate claim IDs are rejected. The warfarin/omega-3 policy returns the exact NIH ODS citation, while the evidence artifact distinguishes the possible INR effect, mostly negative 3–6 g/day findings, FDA-approved pharmaceutical package-insert monitoring language, and the repository's conservative candidate-exclusion policy. The interim replay finding preserves the same IDs for both warfarin and Coumadin.
- Dose result: the existing extraction path now produces one structured aggregate per recognized current ingredient. The result records product occurrences and names, a cross-product duplicate flag, normalized total and unit when available, observation count, and whether every contributing product supplied a usable dose. The same aggregate amount feeds upper-limit comparison, preventing a separate summation path.
- Evidence stage: `IMPLEMENTED`. OP-035 and OP-036 are complete at their required stage. Generated counts are complete `26`, partial `10`, pending `83`, external `1`, contradicted `0`. No service code, R&D deployment, or production two-process integration changed.
- Validation: focused selection `53 passed`; exact CI-equivalent selection `228 passed`; full Ruff PASS; deterministic smoke hash `9c001cb799b34e65899103f47f959b0d2c9a2125ed8be1bea847fb1daf9f554a`; manifest audit PASS with `36` claims and `102` evidence files; completion report check PASS; independent final review found zero Critical, Important, or Minor issues. Full suite is `635 passed`, `77 failed`, matching the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval metric deltas: `256` cases; recommendation coverage `0`, efficacy improvement `0`, next-action accuracy `0`, explanation-quality accuracy `0`, safety-reference accuracy `0`, yearly adverse-event count `0`, sensor/genetic integration rate `0`.
- Replay/slice deltas: every weakest-slice category is unchanged; the interim DDI replay keeps the new reference and claim IDs.
- Biggest bottlenecks: incomplete/non-convertible dose evidence is not yet fail-closed; safety responses lack rule version/application time; external high-risk labels for hard false-negative proof are absent; the production service has no final two-process safety-block proof; no deployed durable R&D service exists.
- Next three loops: OP-037/038 unit and temporal rule metadata; OP-039/040 high-risk and production blocking evidence; OP-041/042 identifier mapping and evidence-backed goal priors.

## 2026-07-16 event idempotency and data-mutation handoff

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-027 and OP-028
- Primary dataset path and case count: `data/original_plan/evidence/op027_op028_event_idempotency_data_mutation_smoke_v1.json`; `3` actual FastAPI route cases
- Main files: schema `8` in `src/wellnessbox_rnd/interim/store.py`; new `src/wellnessbox_rnd/interim/data_mutation.py`; existing execution and behavior record models; authenticated interim routes; focused tests; smoke runner; manifest, generated reports, CI workflow, and execution plan
- Current result: execution and behavior events both return the existing record on an identical replay and reject a changed replay with `409`, even after the effective payload changes. Mutation routes require a configured internal token, verify profile ownership, preserve the immutable ingestion hash, update the effective payload in one immediate transaction, and append an indexed canonical hash-chain record plus audit row.
- Deletion boundary: the event payload becomes `{"deleted":true,"mutation_id":"..."}`. A separate cleanup row remains `PENDING` until SQLite `secure_delete`, WAL truncation, and compaction finish; identical-request retry and store-startup recovery resume interrupted cleanup. Raw-file regressions cover normal deletion, injected cleanup failure, restart recovery, and an active reader. Mutation and audit tables contain identifiers and hashes only. The event ID, execution ID, ingestion fingerprint, and knowledge-lineage foreign keys remain intact.
- Correction boundary: a new correction may follow an earlier correction and extends previous-mutation ID/hash pointers. No new correction may follow deletion. Append-only triggers reject mutation or data-mutation audit updates and deletes. Replaying an accepted mutation returns its original record without adding a row; 16 concurrent identical requests produce one mutation and one audit row.
- Evidence stage: `IMPLEMENTED`. OP-027/028 remain partial because `OPERATED` requires a deployed R&D process, durable production database, and postcondition re-query. No service code, R&D deployment, or production two-process integration changed in this loop.
- Validation: exact CI-equivalent selection `192 passed`; focused persistence regression `46 passed`; new smoke byte-identical across reruns; full Ruff PASS; manifest audit PASS with `30` claims and `81` evidence files; completion-report stale check PASS; independent final review found no findings. Full suite is `602 passed`, `78 failed`, matching the known `74` absent ignored-report and `4` CGM geometry groups.
- Frozen evaluation: `256` cases; zero delta for all seven tracked metrics against `docs/02_eval/05_baseline_gap_report.md`. Replay/slice delta: not applicable.
- Biggest bottlenecks: deployed R&D URL; durable production R&D storage; authenticated service-to-R&D round trip; production mutation postcondition re-query; deterministic whole-session replay and service UI.
- Next three loops: OP-029/030 replay API and service UI; OP-033/034 pregnancy/lactation and condition safety expansion; OP-035/036 evidence-linked interactions and combined-dose calculation.
- Publication: implementation commit `e2cfc54` was pushed to `main`; `Original plan evidence` run `29464603258` passed all steps.
# 2026-07-22 OP-103/104 handoff

- Chosen stage/tasks: production-service integration; OP-103 environment contract and OP-104 result-origin display.
- Primary dataset/cases: `data/original_plan/op103_op104_environment_result_origin_cases_v1.json`, `8` cases. Canonical evidence is `data/original_plan/evidence/op103_op104_environment_result_origin_smoke_v1.json`; service source commit is `5f1d42015d6a467a717d69f3aaa8a7e2afd06931`.
- Files: WellnessBox environment/origin/client/UI/QA; R&D dataset, smoke, evidence, manifest/status, workflow, and OP-103/104 reports.
- Changes: enabled runtime requires production HTTPS, safe URL, 32-character token, and bounded timeout. Remote execution and local snapshot are exclusive, identified origins. No training, frozen-data, simulation-policy, Vercel, public deployment, or production traffic change.
- Stage/result: OP-103 `IMPLEMENTED / PARTIAL`; OP-104 `INTEGRATED / PARTIAL`. Counts `70/33/16/1/0`.
- Validation: service focused QA, existing preview regression, TypeScript, encoding, R&D Ruff, canonical smoke, audit, and completion generation pass. Independent review moved from `0/1/2` to corrected findings.
- Frozen/replay deltas: no recommendation, safety, training, frozen dataset, replay, or slice behavior changed; prior 256-case seven-zero-delta baseline remains applicable.
- Five bottlenecks: `94/120` reports remain; Vercel values are not registered; no public browser evidence; OP-105/106 roundtrip/review integration is pending; legacy full suite retains known absent-artifact/CGM failures.
- Next three loops: OP-105/106; OP-001~078 report backfill; approved provider/browser operation.
# 2026-07-22 OP-105/106 handoff

- Stage/tasks: production-service integration; profile/recommendation roundtrip and pharmacist review queue.
- Dataset: `data/original_plan/op105_op106_profile_review_roundtrip_cases_v1.json`, 8 cases; evidence `data/original_plan/evidence/op105_op106_profile_review_roundtrip_smoke_v1.json`; service commit `fb00e4ebd972a6630235dda8b09593d27e277ccd`.
- Changes: actual service client called separate FastAPI for profile, stored-risk blocked recommendation, scoped review list, completed decision, and immutable replay rejection. No training, frozen-data, simulation-policy, public deployment, or production operation changed.
- Result: both `INTEGRATED / PARTIAL`; counts `70/35/14/1/0`; reports `28/120`.
- Validation: TypeScript, encoding, Ruff, canonical two-process smoke, audit, and generated completion status pass. Independent review started at Critical/Important/Minor `0/1/1`, then `0/2/0`; route execution, both auth denials, both ID overrides, and real 409 preservation were fixed. Frozen/replay/slice deltas remain zero.
- Bottlenecks: 92 reports; OP-101~106 lack provider operation; OP-107/108 pending; no real pharmacist browser evidence; legacy absent-artifact/CGM failures.
- Next loops: OP-107/108; report backfill; approved provider/browser operation.
# 2026-07-22 OP-107/108 handoff

- Stage/tasks: 관리자 실제 상태 API와 상품 후보 계약. OP-107은 `INTEGRATED / PARTIAL`, OP-108은 `IMPLEMENTED / PARTIAL`이며 둘 다 요구 단계 `OPERATED`보다 낮다.
- Dataset/evidence: `data/original_plan/op107_op108_admin_product_integration_cases_v1.json`, 8 cases. 증거는 서비스 커밋 `e95592a126cdb2bfeec156d4f4d7de43487e2a63`, R&D 커밋, runner·dataset·API blob SHA를 기록한다.
- Changes: 실제 HTTP로 데이터·출처·규칙·모델·실행 상태를 순차 조회하고 빈 KPI만 `UNAVAILABLE`로 분리했다. 상품 QA는 fixture 결합, 재고 대체, 안전 제외, 잘못된 카탈로그 fail-closed만 증명한다. 실제 Prisma, 주문, 결제, 공개 배포는 실행하지 않았다.
- Validation: 집중 API 테스트 51개, 서비스 TypeScript·인코딩, Ruff, canonical smoke 재생 diff, manifest 감사, completion report가 통과했다. 독립 리뷰는 최초 `0/3/1`에서 최종 `0/0/0`이 됐다. frozen 평가, 학습 데이터, replay 동작 변화는 없다.
- Five bottlenecks: 보고서 90개, OP-109/110, OP-108 실제 Prisma+R&D 통합, 승인된 provider 운영, 실제 브라우저 증거. Next three loops: OP-109/110, 보고서 보강, 승인된 운영 검증.
# 2026-07-22 OP-109/110 handoff

- Stage/tasks: 주문 mutation 경계와 주문 상태의 계획 읽기 전용 환류. OP-109/110은 `IMPLEMENTED / PARTIAL`이며 요구 단계는 `OPERATED`다.
- Dataset/evidence: `data/original_plan/op109_op110_order_plan_context_cases_v1.json`, 8 cases; `data/original_plan/evidence/op109_op110_order_plan_context_smoke_v1.json`; service commit `59399e2569c6152c644c4010ac52e26e876d1040`.
- Changes: 인증된 서비스 라우트가 사용자·주문·execution·plan이 모두 일치하는 주문의 최소 필드만 읽고 여섯 상태를 정규화해 실제 R&D HTTP API로 보낸다. `createOrder`는 서버에서 결제를 다시 검증하고 DB 상품 가격과 비교한다. paymentId unique 제약과 트랜잭션이 중복 주문·재고 차감을 닫는다. R&D는 plan state와 이벤트 수를 보존한다.
- Boundaries: 실제 Prisma 조회·mutation, PostgreSQL, payment sandbox, 브라우저 승인, 생산 운영은 실행하지 않았다. Frozen 평가, 학습 데이터, 모델, safety, replay 로직 변화는 0이다.
- Validation: 서비스 TypeScript·인코딩·lint·build, 계획 생명주기 포함 집중 테스트 70개, Ruff, two-process canonical replay diff, manifest 감사, completion report가 통과했다. 독립 리뷰는 `1/2/1`→`0/2/1`→최종 `0/0/0`이다. 서비스 Encoding Guard `29891500251`도 통과했다. Bottlenecks: 보고서 88개, OP-111/112, 실제 Prisma·결제 제공자, 승인된 운영, 실제 브라우저. Next: OP-111/112, 보고서 보강, 격리 DB 통합.
- Final CI/publication: R&D `Original plan evidence` 실행 `29893387739`가 전 단계 증거 재생성, 계약 테스트, Ruff를 포함해 통과했다. 검증된 R&D 소스·증거 커밋 `07fff30f2ed5cbd4e22b5b85fc944412892c287b`와 서비스 HEAD `59399e2569c6152c644c4010ac52e26e876d1040`는 `origin/main`에 있다.

# 2026-07-22 OP-111/112 handoff

- 단계/과제: production-service security integration; OP-111 내부 API 인증·역할 권한, OP-112 최소 수집·가명화·로그 마스킹. 둘 다 `INTEGRATED / COMPLETE`다.
- 데이터셋/증거: `data/original_plan/op111_op112_security_boundary_cases_v1.json`, 8건; canonical evidence는 `data/original_plan/evidence/op111_op112_security_boundary_smoke_v1.json`이다.
- 변경: 실제 profile 저장 프록시 strict schema, HMAC profile ID, 내부 토큰 왕복, user/pharmacy/admin route 분기와 공유 guard 판정 함수, 서버 소유 scope, 재귀 로그 마스킹, bounded public error를 검증했다.
- 검증: focused pytest 18건, Ruff, manifest audit, completion stale check, canonical 재실행 diff가 통과했다. 감사 결과는 주장 `111`, 증거 파일 `305`, 상태 `72/39/8/1/0`, 보고서 `34/120`이다.
- 독립 검토: 최초 `Critical 1 / Important 4 / Minor 0`; 최종 `0/0/0`. 서비스 HEAD `1912f127a02d158a159ed7edd135f389308a1e6e`, Encoding Guard `29894827365` 성공.
- R&D CI: 커밋 `354a5caf20c10d3e1bb7b5634e7fdf8ffc18e1c5`, Original plan evidence `29895612666` 성공. 전체 계약 선택은 `699 passed, 2 skipped`였고 Ruff도 통과했다.
- 경계/delta: production identity provider, production log sink, public deployment는 검증하거나 변경하지 않았다. frozen 데이터, 모델 학습, safety 규칙, replay·slice 결과 변경은 모두 0이다.
- 병목 5개: 보고서 86개, production identity provider 증거, production log sink 관찰, OP-113/114, 승인된 실제 사용자·약사·관리자 운영 증거.
- 다음 세 루프: OP-113/114; 보고서 보강; 승인된 production 인증·로그 관찰.

# 2026-07-22 OP-113/114 handoff

- 단계/과제: production-service resilience and contract integration. OP-113 장애 복원력과 OP-114 OpenAPI·TypeScript drift 차단은 모두 `INTEGRATED / COMPLETE`다.
- 데이터셋/증거: `data/original_plan/op113_op114_resilience_contract_cases_v1.json`, 8건; canonical evidence는 `data/original_plan/evidence/op113_op114_resilience_contract_smoke_v1.json`이다.
- 변경: retryable GET 1회 재시도, POST 무재시도, 실제 timeout signal, retryable 오류 전용 circuit, half-open 단일 probe, bounded fallback, FastAPI OpenAPI generator, registry-derived client type/runtime guard를 추가했다.
- 계약 규모: OpenAPI interim path 31개, reachable component schema 63개, 서비스 operation 19개. 양쪽 snapshot은 byte-equivalent하다.
- 검증: 서비스 TypeScript·lint·build와 두 QA, R&D runner canonical diff, generator check, focused pytest 40건, Ruff, manifest audit, completion stale check가 통과했다. 상태 `74/39/6/1/0`, 주장 `113`, 증거 파일 `313`, 보고서 `36/120`이다.
- 독립 검토: `0/5/0`→`0/1/0`→최종 `0/0/0`. 서비스 HEAD `d07123903072f5eac7ef7f5021cf8278ca02c9c9`, Encoding Guard `29896967812` 성공.
- R&D CI: HEAD `811f5e46f8d6408915c677c3e273718b8f241d29`, Original plan evidence `29897044861` 성공. 전체 canonical smoke, requirement 계약 테스트, Ruff가 모두 통과했다.
- 경계/delta: production outage, 다중 인스턴스 circuit, rolling deployment, 배포 artifact hash는 검증하지 않았다. frozen 데이터, 모델 학습, safety, replay·slice 변화는 0이다.
- 병목 5개: 보고서 84개, OP-115/116, 승인된 production 장애 훈련, 다중 인스턴스 circuit 관찰, 배포된 양쪽 artifact hash·호환성 증거.
- 다음 세 루프: OP-115/116; 보고서 보강; 승인된 production 장애·artifact 관찰.
# 2026-07-22 OP-115/116 handoff

- 단계/과제: 최종 검사 행렬과 health alias 통합. OP-115는 `INTEGRATED / COMPLETE`, OP-116은 `INTEGRATED / PARTIAL`이다.
- 데이터셋: `data/original_plan/op115_op116_test_matrix_health_alias_cases_v1.json`, 8건, SHA-256 `898745db62e724200ecc12f463f8765d704c1f1e0cdad407038e27901de3f93c`.
- 구현: WellnessBox GET `/api/internal/rnd/health`, fail-closed health client, 실제 handler·장애 QA, 두 저장소 검사 행렬 runner, 양쪽 CI build/replay gate.
- 검증: focused pytest 40 passed, 배포 계약 15 passed, 프로세스 smoke 8건, Ruff·wheel·alias QA·encoding·typecheck·Next build passed, manifest audit PASS, completion `75/40/4/1/0`.
- source: WellnessBox `b37bf99a8f2a5a7eb50fe61016740579011d2aa3`; R&D canonical source `275a2c5bee47a051532c1bbc0fa0505c384c21c0`.
- stage boundary: local process와 실제 Next GET handler는 입증했다. production deployment/traffic은 false이며 OP-116 OPERATED는 미충족이다.
- frozen/replay delta: 256건 평가의 7개 지표, weakest slice, 학습 artifact, safety, replay 변화 모두 0이다.
- 병목 5개: 한국어 보고서 82개, 승인된 production 배포·health 증거, OP-117 브라우저 핵심 경로, OP-118 전체 비외부 운영 증거, OP-119 외부 책임·교체 계약.
- 다음 세 loop: OP-117 브라우저 재현; 누락 연구보고서 보강; 승인 후 OP-116 production 관측.
- 독립 리뷰: 최초 `0/4/1`, 1차 수정 후 `0/1/1`, 최종 `0/0/0`이다.
- GitHub Actions: WellnessBox `29900597777`, R&D `29901559427` 모두 성공했다.

# 2026-07-22 OP-117/118 handoff

- 단계/과제: 브라우저 역할 경로와 비외부 운영 증거 원장. OP-117과 OP-118은 모두 `IMPLEMENTED / PARTIAL`이다.
- 데이터셋: `data/original_plan/op117_op118_browser_operational_evidence_cases_v1.json`, 8건, SHA-256 `6b9b7ae733b0f204e0947fb98409208603e9f4e5086256afae78210b71a36249`.
- 변경: 실제 Chromium 사용자 화면, 약사 인증 경계, 관리자 인증 화면과 비외부 119건의 evidence·OPERATED gap 원장을 추가했다.
- 검증: browser 3건, focused pytest 22건, Ruff, manifest audit와 completion stale check가 통과했다. 상태 `75/42/2/1/0`, 주장 117, 증거 파일 322, 보고서 `40/120`이다.
- 경계/delta: production 배포·traffic, 약사 인증 세션, 모든 비외부 OPERATED는 false다. frozen·학습·모델·safety·replay·slice 변화는 0이다.
- 병목 5개: 한국어 보고서 80개, production 배포·traffic, 실제 약사 인증 세션, 비외부 OPERATED 119건, OP-119 외부 책임·교체 계약.
- 다음 세 loop: OP-119; 누락 보고서 보강; 승인 후 OP-116~118 production 관측.

# 2026-07-22 OP-119 handoff

- 단계/과제: 외부 의존성 책임·입력·교체 계약 원장. OP-119는 `IMPLEMENTED / COMPLETE`다.
- 데이터셋: `data/original_plan/op119_external_dependency_registry_cases_v1.json`, 8건, SHA-256 `12fd157f0946427fb86735d9fd2273e7016c9750978e7aa75d0ec46a0274064c`.
- 변경: OP-039 책임 역할 1개, 외부 공급 역할 1개, 필수 입력 4종, replacement contract 2개, trust root 기반 차단 사유 4개와 promotion condition을 strict Pydantic 원장으로 고정했다.
- 검증: registry pytest 11건과 focused requirement pytest 48건, Ruff, manifest audit, completion 생성·check, workflow YAML parse를 통과했다. 현재 상태 `76/42/1/1/0`, 주장 118, 증거 파일 328, 보고서 `41/120`이다.
- 경계/delta: 외부 입력·승인·OP-039 독립 검증은 모두 false다. frozen 평가, 학습 데이터, 모델, safety, replay·slice 변화는 0이다.
- 병목 5개: 한국어 보고서 79개, OPERATED 미달 비외부 요구사항, OP-039 실제 외부 입력 4종, production 배포·traffic, 실제 약사 인증 세션.
- 다음 세 loop: OP-120 fail-closed 최종 감사 계약; 누락 보고서 보강; 승인된 production·external evidence 관찰.
# 2026-07-22 OP-001/002 연구보고서 보강 handoff

- 단계/과제: 원본 요구사항과 증거 기준 고정; OP-001/002 한국어 장문 연구보고서 보강. 두 요구사항은 `IMPLEMENTED / COMPLETE`이며 더 높은 단계는 주장하지 않는다.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `bc4fd0d1ac5d17f15bb5e7ccbdc22445795f2cfc863731800b0830019df34108`.
- 파일: `docs/original_plan/research_reports/OP-001.md`, `OP-002.md`, `OP-120.md`, OP-120 사례와 `data/original_plan/evidence/op120_final_completion_audit_v1.json`.
- 변경: OP-001은 SHA-256 `31291e6f93977fa2d5d083d0161743c49debef25caf12dccf6edc7fa1c2197d4`의 단위 테스트·canonical 감사 책임을 구분했다. OP-002는 59쪽 전체 접촉 시트와 경계 페이지 확대 검토를 기록했다. 코드, 서비스 데이터, 학습, 모델, 시뮬레이션은 변경하지 않았다.
- 검증: 관련 pytest `31 passed`, Ruff PASS, completion stale 없음, canonical runner 2회 동일 SHA-256 `8facfc9566f29c3bf51bd44fea0e415565a86ec7b2ba5f394f7867223d2863e0`. 독립 검토 최종 `Critical 0 / Important 0 / Minor 0`.
- CI: R&D `Original plan evidence` 실행 `29913248935` 성공. canonical evidence 재생,  requirement contract tests, Ruff를 모두 통과했다.
- 결과: OP-120 유효 보고서 `22`, 누락·부적합 `98`, 전체 최종 감사 `BLOCKED`. 상태 `76/43/0/1/0`; 비외부 단계 미달 43개와 OP-039 외부 검증 부족은 그대로다.
- source/evidence 커밋: 보고서 `2552d15`, 검토 수정 `0acf01d`, 최종 canonical evidence `2ce044d`. WellnessBox의 보호된 사용자 변경은 건드리지 않았다.
- frozen/replay/slice delta: 모두 `0`. 이 반복은 문서와 감사 사례만 바꿨다.
- 병목 5개: 보고서 98개, 단계 미달 43개, OP-039 외부 검증, 전체 검증 영수증, 독립 검토 영수증.
- 다음 세 반복: OP-003/004, OP-005/006, OP-007/008 보고서 보강.
# 2026-07-22 OP-003/004 연구보고서 보강 handoff

- 단계/과제: 원본 요구사항과 증거 기준 고정; OP-003/004 한국어 장문 연구보고서 보강. 두 요구사항은 `IMPLEMENTED / COMPLETE`이며 더 높은 단계를 주장하지 않는다.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `bfb0e4d0070ac87d807fe2e88c2206b5508e89bcdb641025a96b589080a8436d`.
- 파일: `docs/original_plan/research_reports/OP-003.md`, `OP-004.md`, `OP-120.md`, OP-120 사례와 `data/original_plan/evidence/op120_final_completion_audit_v1.json`.
- 변경: p.15 여섯 블록을 manifest 그룹과 연결하고 p.16~24 입력·처리·출력을 master context와 대조했다. 원문 직접 계약과 후속 구현의 계보·동의·운영 상태를 분리했다. 코드, 서비스 데이터, 학습, 모델, 시뮬레이션은 변경하지 않았다.
- 검증: 관련 pytest `31 passed`, Ruff PASS, completion stale 없음, canonical runner 2회 동일 SHA-256 `fc2f01bec47c55373fac397b9704691deb5f0dabcbde745b6d89e19d15918143`. 독립 검토 최종 `Critical 0 / Important 0 / Minor 0`.
- CI: R&D `Original plan evidence` 실행 `29914515047` 성공. canonical evidence 재생, requirement contract tests, Ruff를 모두 통과했다.
- 결과: OP-120 유효 보고서 `24`, 누락·부적합 `96`, 전체 최종 감사 `BLOCKED`. 상태 `76/43/0/1/0`; 비외부 단계 미달 43개와 OP-039 외부 검증 부족은 그대로다.
- source/evidence 커밋: 보고서 `2d262ec`, 검토 수정 `1aa8c86`, canonical evidence `1e201e2`. WellnessBox의 보호된 사용자 변경은 건드리지 않았다.
- frozen/replay/slice delta: 모두 `0`. 이 반복은 문서와 감사 사례만 바꿨다.
- 병목 5개: 보고서 96개, 단계 미달 43개, OP-039 외부 검증, 전체 검증 영수증, 독립 검토 영수증.
- 다음 세 반복: OP-005/006, OP-007/008, OP-009/010 보고서 보강.

## 2026-07-24 인계

- 현재 최종 감사 차단은 `external_validation_gaps:1` 하나다. OP-039은 권혁찬 실제 검토 전까지 의도적으로 BLOCKED다.
- 운영 준비 확인 명령: `.\.venv-interim\Scripts\python.exe scripts\report_operational_session_readiness.py`.
- 현재 관측: 서로 다른 실제 프로필 1/5개, 대기 약사 초안 0건. 실제 운영 입력 없이 초안이나 영수증을 만들지 않는다.
- 상품 매핑 계약은 `l_theanine→ING:L_THEANINE`, `soluble_fiber→ING:PSYLLIUM`을 포함한 `2026-07-24.1`이다. 미매핑은 성분 키와 실패 이유를 반환하고 차단한다.
