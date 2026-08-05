# PROGRESS

## 2026-08-04 최종 감사 재확인

- 정답 출처 감사는 KPI-1·3·4·5 모두 `PASS`이고, 승인 전용 데이터셋은 6건·위반 0건으로 `READY`다.
- 연구계획 요건 감사도 `PASS`다. 관련 회귀시험 44건이 통과했다.
- `scripts/run_final_completion_audit.py`는 `BLOCKED`다. 최종 검증·독립 검토 영수증의 `source_commit`은 `f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`인데, 현재 외부 서비스 저장소 커밋은 `7054d76670870bc31130006a84df3fa10aa46c78`로 바뀌어 영수증 검증이 실패한다.
- 감사 실패 결과도 `data/original_plan/evidence/op120_final_completion_audit_v1.json`에 `BLOCKED`로 저장되도록 고쳤다. 과거 `READY` 결과를 현재 상태로 오인하지 않는다.
- 영수증 재발급, 실제 프로필·서명 입력, 배포, 실사용자 수집, H-003 학습은 실행하지 않았다.

## 2026-08-04 승인 전용 데이터셋 검증

- `scripts/build_approved_draft_dataset.py`를 읽기 방식으로 실행했다. 승인 전용 manifest 6건, 위반 0건, 데이터셋 SHA-256 일치로 `READY`였다.
- 결과 파일은 `data/original_plan/final_session/approved_draft_dataset_manifest_v1.json`이며 재계산 데이터셋 SHA-256은 `f03f949b576ca7473a0e7bf1ca53c73fdef2cee1e70793ca04164d488b0aca`이다.
- H-003 학습 게이트는 NO-GO이므로 학습·승격은 실행하지 않았다.

## 2026-08-04 KPI-5·KPI-4 연구단계 내부 측정

- KPI-5 봉인 SHA-256 `7e84c39b106e4ee868d67cfdbb5f95fe85cf606a2e9030f01a25684ad7d31e0a`의 100건을 안전 엔진에 입력했다. 실행 실패 0건, 후조건 실패 0건, 정확도 0.0%, 목표 95% 미달이다.
- KPI-5 엔진은 `depletion`·`absorption_interaction` 관계 라벨과 외부 참고문헌 쪽수 필드를 반환하지 않는다. 엔진이 실제 반환한 상태·제외 성분·규칙·인용만 기록했고, 봉인 정답을 엔진 출력에 넣지 않았다.
- KPI-5 결과 파일은 `data/original_plan/kpi/measurements/kpi5_internal_measurement_v1.json`, SHA-256 `8b2497fc3db974eba21324b09e328a8b81d53e12ba204111835c744b7159268a`이다.
- KPI-4 봉인 SHA-256 `a0f2e70392e0c94bf8e9315833bc800cb6856d5fed41c767f4f0df9414287c5e`의 100건을 상담 어댑터의 결정론적 폴백으로 실행했다. 실행 실패 0건, 후조건 실패 0건, 정확도 0.0%, 목표 91% 미달이다.
- KPI-4 외부 API 호출은 비활성화했다. 어댑터가 반환한 `out_of_scope` 상태와 검증 결과만 기록했으며, 답변 성분을 보완하지 않았다.
- KPI-4 결과 파일은 `data/original_plan/kpi/measurements/kpi4_internal_measurement_v1.json`, SHA-256 `18b4b85ba483dde78c67946120082e4294847c873d9c311bf8536d790fb07234`이다.

## 2026-08-04 KPI-1 연구 단계 내부 측정

- 봉인 SHA-256 `a3e62d0211d91d509641f41bac697d69cd19d3843dffbcf5e84470d13a044629`을 검증한 뒤 KPI-1 사례 100건을 `wellnessbox-recommendation-engine-v1`에 실행했다.
- 문항의 영역·판정·나이·복용약을 9개 구조화 추천 목표와 `RecommendationRequest`로 바꾸는 입력 어댑터를 고정했다. 답안은 엔진 출력 생성에 전달하지 않았고, 출력 생성 뒤 봉인 정답과 대조했다.
- 실행 실패 0건, 후조건 실패 0건이다. 평균 점수는 51.0833%로 계획 목표 80%에 미달했고, 완전 일치 사례는 42/100건이다.
- 목표 미달을 숨기거나 어댑터를 조정하지 않았다. 결과는 `data/original_plan/kpi/measurements/kpi1_internal_measurement_v1.json`, SHA-256 `cbc71b7b409b2ffe7071487b485e3c12ec50b994e976bc0ec546be479ab2ea96`다.
- 측정 환경은 `research_phase_internal_measurement`다. 배포·실제 트래픽·훈련·최종 영수증 재발급은 실행하지 않았다.

## 2026-08-04 KPI-3 연구 단계 내부 측정

- 봉인 SHA-256 `510f57ab18329a9c3a2eab551aa9bd9b35b0470f393aef828943cff26ca6d2ea`을 먼저 검증한 뒤 KPI-3 사례 100건을 `wellnessbox-next-action-engine-v1`에 실행했다.
- 블라인드 문항의 임상 표현을 엔진 이벤트로 바꾸는 입력 어댑터를 별도 함수로 고정했다. 정답지는 엔진 출력 생성 함수의 인자가 아니며, 출력 생성이 끝난 뒤에만 봉인 정답과 비교한다.
- 실제 `BoundedAgent`가 임시 SQLite 상태 저장소에서 행동을 선택하고 상태 전이를 기록했다. 실행 실패 0건, 후조건 실패 0건이다.
- 결과는 91/100, 정확도 91.0%로 계획 목표 80%를 충족했다. 불일치 9건은 모두 `변화 없음` 상황에서 정답 `maintain`, 엔진 `reoptimize`였다.
- 측정 환경은 `research_phase_internal_measurement`다. 결과 파일은 `data/original_plan/kpi/measurements/kpi3_internal_measurement_v1.json`, SHA-256은 `f3f5f4eb721378c8b3d7b07746ed15a992fb8af00cc7ae72668aa669bd78f76f`다.
- 배포·실제 트래픽·훈련·최종 영수증 재발급은 실행하지 않았다.

## 2026-08-04 KPI-1 추가 교체 Claude 의견 반영

- `kpi1_second_replacement_completed.zip` SHA-256 `0cdd0ec7d8507ab9cd91be12ad0564a19a91d379be82add232a8bebeaa2e6b86`을 검증·보존했다.
- 두 사례 모두 `claude-opus-5`/Anthropic 의견이며, Codex/OpenAI 초안과 제공자 계열이 분리됐다. 패킷 해시, 등록 신원, 답 어휘, 2건 완전성, 엔진 미열람, 필수 블라인딩 경로를 모두 확인했다.
- 두 사례 모두 초안과 의견이 다르고 위험·불확실성 표시가 있어 최종 선택 2건을 유지했다.
- 마지막 입력 패키지는 `second_replacement/kpi1_second_replacement_final_review_package.zip`, SHA-256 `fd58fd4d5ea0ad2ab325030b09682a4980c7878220f95b4f01b2796a048abaf3`이다. 두 행 모두 독립 2차 의견을 권고안 B로 미리 제시했다.

## 2026-08-04 교체 65건 최종 판정 반영

- 반환 ZIP SHA-256 `b6ba0b82ea945a1adb391d7266dd7ddcf9e25e0a89b5831152c5a4ee28f0e471`을 원문 그대로 보존했다. 65건의 결과는 `ACCEPT` 51건, `EDIT` 12건, `REJECT` 2건이다.
- 원본 문항·참조안·권고안 불변성, 등록 신원, 답 어휘, 시간대 포함 시각, 건당 최소 1초, 시간 중복 여부를 검사했다. 모든 기록은 8초이며 서로 겹치지 않는다.
- KPI-4 7건과 KPI-5 9건은 모두 확정 가능하다. KPI-1은 49건 중 47건이 확정 가능하고 `kpi1-repl-022`, `kpi1-repl-027`은 거절됐다.
- 거절 2건을 덮어쓰지 않고 새 KPI-1 문항 2건을 만들었다. Anthropic 2차 의견 입력 패키지는 `second_replacement/kpi1_second_replacement_claude_package.zip`, SHA-256 `efcaf122dae3dae001d6cbeb2ce4f231fa0739762ed5fb1a1468f4235348f89d`이다.

## 2026-08-04 Claude 교체 응답과 최종 검토 자료

- `kpi_replacement_completed.zip` SHA-256 `acd6ffc496b8e065d6d3f0f41abb66dd51273929e64a628661012fe457576cd7`의 Claude 응답 65건을 검증·보존했다.
- KPI-4는 `claude-opus-5` 1차 초안과 보관된 `gpt-5.6-pro` 응답을 2차 의견 역할로 연결했다. GPT 응답이 Claude보다 먼저 primary 형식으로 생성됐고 나중에 2차 역할로 등록됐다는 순서, 역할 provenance, 원본 ZIP SHA-256을 유지했다.
- 최소 상세 검토 수는 KPI-1 49건, KPI-4 7건, KPI-5 9건으로 총 65건이다. 모든 사례에 불일치 또는 위험·불확실성 표시가 있어 더 줄이지 않았다.
- `kpi_replacement_final_review_package.zip`에는 65개 권고안이 미리 입력돼 있다. 이상이 없으면 `ACCEPT`, 수정이 필요할 때만 `EDIT`, 사용할 수 없으면 `REJECT`를 기록한다. 패키지 SHA-256은 `7e78ad7aca90578b4fcc4794828c10d6a8a64a6a11963170423034013a65fd65`이다.

## 2026-08-04 OpenAI 교체 응답 보존과 Claude 재처리 패키지

- 반환 ZIP SHA-256 `99ef845a5d2451889ecf2d16aa40de65263f38919d389d64337b418e560ff43d`은 65건을 모두 담았지만, 세 응답의 기록 모델이 계약상 필요한 `claude-opus-5`가 아니라 `gpt-5.6-pro`여서 정식 교체 응답으로 가져오지 않았다.
- 원본 ZIP과 판정은 `replacement_round/openai_submission/`에 보존했다. KPI-1·5 응답은 Codex 초안과 같은 OpenAI 계열이라 독립 2차 의견으로 사용할 수 없다.
- KPI-4 응답 7건은 패킷·블라인딩·답 형식 검증을 통과했다. Anthropic 1차 초안이 먼저 들어오면 원래 역할과 모델 provenance를 보존한 OpenAI 2차 의견으로 재사용할 수 있다.
- 입력이 끝난 신원 확인을 유지한 `kpi_replacement_claude_retry_package.zip`을 만들었다. SHA-256은 `29fb4d0639edc09b5a965ec3a21c07af7ee0ff24630c11b1b3599540a8cf372d`이다.

## 2026-08-03 반려 65건 교체 입력 패키지

- KPI-1 49건, KPI-4 7건, KPI-5 9건의 새 후보를 `replacement_round/kpi_replacement_candidates_v1.json`에 만들었다. 기존 반려 문항과 현재 300개 문항은 재사용하지 않았다.
- KPI-1은 기존 수락 사례의 서로 다른 49개 판정을 사용해 새 상태·복용약 조합을 만들고 어린이·성인 나이 불일치를 제거했다. 49개 문항이 모두 고유하며 답 조합은 44개다.
- KPI-4는 기존 수락 주제에서 7개 새 상담 질문을 만들었고 정답은 넣지 않았다. Anthropic 계열 1차 초안이 들어온 뒤 OpenAI 계열 2차 의견을 생성해야 제공자 분리가 성립한다.
- KPI-5는 반려된 세 약물 관계를 제외하고, 9개 관계의 라벨과 원문 근거를 함께 묻는 고유 문항으로 바꿨다.
- `kpi_replacement_input_package.zip`에는 세 개의 Anthropic 요청, 등록 신원 선택 파일, 반환 ZIP 생성 명령만 담았다. 정답·근거가 있는 내부 후보 파일은 블라인딩을 위해 ZIP에서 제외했다. SHA-256은 `aa1ec8fa1cdaa46ec4a89deb04f150f552408fb53f305d01e880871b56835cba`이다.
- 반환 importer는 ZIP을 한 번만 메모리에 읽고, 등록 신원 참조·실제 Anthropic 모델명·패킷 해시·답 어휘·사례 완전성·블라인딩을 검증한다. 적용 시 같은 메모리 스냅샷의 원본 ZIP과 응답을 함께 보존하며 정답 확정이나 사람 판단은 대신 만들지 않는다.
- 검증: 관련 집중 시험 171건 PASS. 전체 pytest는 기준선과 같은 90건 실패, 전체 Ruff는 기준선과 같은 28건이며 신규 실패·오류는 0건이다.

## 2026-08-03 최종 검토 반영과 신원 확인 보완

- 반환 ZIP SHA-256 `a9587f2c425510dc2490857de2ab67210b0c0b9894170db80e222563f1834e3c`을 원문 그대로 보존하고, KPI-1·3·4·5 각 100건의 결정을 적용했다.
- 제출된 `DISCARD` 판단에 따라 KPI-1·5의 과속 봉인 원본과 이력을 archive에 보존했다. 다만 제출 기록의 검토자명이 `비식별 검토자`이고 추적 가능한 신원 확인값이 없어 정식 폐기로 계산하지 않는다. 두 지표의 `formal_disposal_count`는 0이다.
- KPI-3은 반려가 없지만 같은 신원 확인값 누락으로 무결성 감사가 실패한다. 앞서 만든 KPI-3 봉인은 유효하지 않아 제거했으며, 신원 확인 전에는 다시 봉인하지 않는다.
- KPI-1 49건, KPI-4 7건, KPI-5 9건은 반려됐다. 총 65건은 삭제하거나 답을 대신 채우지 않고 `kpi_replacement_required_v1.json`에 질문·두 의견·반려 메모·결정 provenance를 보존했다.
- 반환 자료의 선택값과 시각은 임의로 바꾸지 않았다. 현재 네 지표 모두 신원 확인값 누락으로 차단되며, KPI-1·4·5에는 교체 사례 65건 차단도 함께 남는다.
- importer는 ZIP을 한 번만 메모리에 읽고 같은 바이트를 검증·반영한다. 검증 직후 원본 ZIP이 바뀌어 다른 내용이 적용되는 문제를 회귀 시험으로 차단했다.
- 신원 참조는 해시 형식만 검사하지 않는다. `op039_reviewer_identity_registry_v1.json`의 등록 참여자 기록에서 계산되는 값과 일치해야 하며 임의의 64자리 해시는 실패한다.
- 검증: 집중 시험 131건 PASS. 전체 pytest는 기준선과 같은 90건 실패, 전체 Ruff는 기준선과 같은 28건이며 신규 실패·오류는 0건이다.

## 2026-08-03 일괄 검토·반환 패키지

- Claude의 교차 의견 400건은 모두 반영됐다. 추가 Claude 또는 다른 AI 실행은 없다.
- `kpi_final_review_package.zip`은 검토자가 작성할 CSV 4개와 JSON 2개를 명확히 구분한다.
- `START_HERE.txt`에 허용 선택값, 시각 형식, 봉인 처리 판단값과 반환 절차를 기록했다.
- `MAKE_RETURN_ZIP.cmd`는 작성 대상 6개만 `kpi_completed_review.zip`으로 묶는다. 실제 실행 결과 ZIP 항목은 정확히 6개였다.
- 가져오기 명령은 `seal_disposal_review.json`의 작성자·사유·시각·DISCARD/KEEP를 검증한다. `--apply`는 DISCARD 판단의 감사 이력을 남기고 새 결정을 적용하므로 추가 확인 입력이 필요 없다.
- 이 절에서 준비한 패키지는 이후 제출돼 반영됐다. 현재 결과는 위 절이 최신 상태다.

## 2026-08-03 작성된 검토 CSV 가져오기 게이트

- `scripts/import_kpi_reviewer_package.py`를 추가했다. 기본 실행은 읽기 전용 검증이며 `--apply`가 있을 때만 네 워크벤치를 한꺼번에 갱신한다.
- CSV의 사례 ID·질문·안 A·안 B·근거·신뢰도·표시가 바뀌면 차단한다. 빈 선택, 허용 답 밖 CUSTOM 값, 시간대 없는 시각, 건당 1초 미만, 겹치는 검토 구간도 차단한다.
- 네 CSV를 모두 검증한 뒤에만 저장하며 저장 중 오류가 나면 네 워크벤치를 원래 바이트로 복구한다.
- `reviewer_details.json`에는 2차년도 기록값 `pharmacist_candidate_preliminary_safety_review`를 미리 넣었다. 이름·소속·검토일은 비워 두었다.
- 현재 미작성 ZIP을 검증하면 `reviewer_detail_missing:reviewer_name`으로 정상 차단된다.

## 2026-08-03 Claude 응답 반영과 최종 검토 자료 생성

- `claude-opus-5` 응답 4개, 총 400건이 Anthropic 계열·패킷 해시·답 어휘·100건 완전성 검증을 통과했다.
- KPI-1·3·5에는 Claude 2차 의견을 반영했다. KPI-4에는 Claude 1차 초안을 먼저 반영하고 기존 Codex 2차 의견을 반영했다.
- 실제 교차 비교 결과는 KPI-1 합의 1·불일치 99·표시 89, KPI-3 합의 41·불일치 59·표시 100, KPI-4 합의 7·불일치 93·표시 98, KPI-5 합의 0·불일치 100·표시 82다.
- 불일치 또는 위험·불확실성 표시가 전 사례를 덮으므로 검사를 느슨하게 하지 않는 최소 상세 검토 수는 지표별 100건, 총 400건이다.
- `kpi_final_review_package.zip`에 안 A·안 B·근거·신뢰도·표시를 나란히 담은 UTF-8 CSV 4개와 작성 양식을 넣었다. 각 CSV는 100개 고유 사례이며 ZIP 무결성 검사를 통과했다.
- 정답 확정, 승인, 봉인, KPI-1·5 과거 봉인 폐기는 아직 반영하지 않았다.

## 2026-08-03 반환 OpenAI 응답의 독립성 차단

- 반환 ZIP에는 KPI-1·3·4·5 각 100건, 총 400건이 있으며 구조·답 어휘·confidence·패킷 해시는 통과했다.
- 사용자가 생성 모델을 `ChatGPT 5.6 Sol Pro`로 확인했고 Windows 다운로드 출처도 `chatgpt.com`이었다. 원본 응답의 모델 필드는 모두 `not_recorded`였다.
- KPI-1·3·5는 기존 초안과 OpenAI 계열이 같아 검증기가 `ai_review_agent_matches_drafting_agent_family`로 차단했다. KPI-4도 OpenAI 상담 모듈과 같은 계열이라 정식 측정용 1차 초안으로 사용할 수 없다.
- 반환 ZIP은 `review_handoff/rejected_openai_responses/`에 보조 의견과 실패 근거로 보존했다. 워크벤치·정답·승인·봉인에는 반영하지 않았다.
- 외부 요청 생성기와 ZIP 안내문은 Anthropic 실제 모델명, `claude.ai` 실행, `not_recorded` 금지를 명시하도록 강화했다.

## 2026-08-01 외부 Claude 실행 경로 점검

- 실제 KPI-3 Claude 응답 생성을 시도하기 전에 로컬 실행 경로를 점검했다. Claude CLI, `ANTHROPIC_API_KEY`, Anthropic Python 패키지는 모두 없었다.
- 브라우저 경로는 Claude 로그인 페이지까지 연결됐지만 인증된 세션이 없었다. Chrome 연결도 사용할 수 없었다. 로그인·계정 생성·요금제 선택·결제는 대신하지 않았다.
- KPI-3 요청 JSON은 Claude에 전송하지 않았고 외부 응답 파일도 만들지 않았다. 로그인 탭만 사용자가 이어갈 수 있도록 인계했다.
- 다음 진행에는 사용자가 열린 Claude 탭에 로그인한 뒤 이 작업에 준비됐다고 알려야 한다. 그다음 새 Claude 대화에 `kpi3_claude_review_request_v1.json` 하나만 전달한다.
- 코드·데이터·워크벤치·사람 판단·봉인·frozen eval·replay·slice는 바꾸지 않았다. delta 0이다.

## 2026-08-01 Claude 블라인드 요청 번들·사전검증 완성

- KPI-1·3·5 독립 2차 의견과 KPI-4 독립 1차 초안을 위한 Claude 요청 JSON 4개를 `data/original_plan/kpi/ai_review_requests/`에 생성했다. 각 파일은 사례 100건, 허용 답 어휘, 빈 응답 skeleton, 패킷·요청 SHA-256을 포함한다.
- 새 Claude 작업에는 요청 JSON 하나만 전달한다. 요청 계약은 저장소·엔진 규칙·엔진 출력·기존 정답 열람을 금지하고 JSON만 반환하도록 명시한다. 실제 사례에는 `case_id`와 `prompt`만 들어 있다.
- `validate-ai-response`를 추가했다. 제공자 계열, 역할별 메타데이터, 패킷 해시, 블라인딩 경로 9개, 사례 ID 100개, 답 어휘, confidence·flags 스키마를 실제 가져오기 함수로 검사하되 deepcopy 워크벤치만 바꾼다. 성공 출력은 `READY_TO_IMPORT`, `mutated: false`다.
- KPI-1·3·5 요청은 Anthropic 계열 review, KPI-4 요청은 Anthropic 계열 primary로 고정했다. OpenAI 초안에 OpenAI 2차 의견을 요청하면 생성 단계에서 거부한다.
- 네 요청 파일의 자체 해시, 고유 사례 100건, 사례 필드 제한, 단독 입력 계약을 재검증했다. 관련 회귀 시험 124건과 변경 파일 Ruff가 통과했다. 전체 pytest 실제 실행은 기준선과 같은 90건 실패·실패 파일 73개다.
- Claude 응답·사람 판단·승인·봉인은 아직 만들지 않았다. 엔진·채점·frozen eval·replay·slice delta는 0이다.

## 2026-08-01 전체 pytest 기준선 오진 정정

- 전체 pytest 실패가 90건에서 114건으로 늘었다는 직전 보고를 재현·추적했다. 제품 코드 실패가 늘어난 것이 아니라 `.pytest_cache/v/cache/lastfailed`에 현재 존재하지 않는 테스트 node ID 24개가 남아 있었고, 캐시 항목 수를 실제 실패 수로 잘못 해석한 보고 오류였다.
- 캐시를 사용하지 않고 `python -m pytest -q --tb=no`의 실제 `FAILED` 줄을 직접 집계한 결과는 **90 failed / 73 failed files**다. 기록된 기준선 90건과 일치하므로 이번 KPI 변경의 신규 전체-test 실패는 0건이다.
- 대표 stale node ID 4개를 현재 파일에서 직접 실행했을 때 모두 `not found`로 재현됐다. 현재 커밋의 관련 회귀 시험 121건은 별도로 PASS다.
- 부모 커밋을 저장소 내부 임시 worktree에서도 실행해 보았으나 여러 시험이 절대 경로와 저장소 위치에 의존해 실패 집합이 달라졌다. 이 비교는 기준선 증거로 사용하지 않았고 임시 worktree는 제거했다.
- 앞으로 전체 실패 수는 `lastfailed` JSON 길이로 보고하지 않는다. 실제 pytest 실행 출력의 `FAILED` 항목이나 최종 요약만 사용한다.
- 코드·데이터·엔진·frozen eval·replay·slice는 바꾸지 않았다. 이 loop의 공식 metric delta는 0이다.

## 2026-08-01 KPI-3 블라인드 Codex 1차 초안 도입

- 별도 블라인드 작업이 만든 `data/original_plan/kpi/ai_review_responses/kpi3_codex_blind_response_v1.json` 100건을 KPI-3의 실제 1차 초안으로 가져왔다. 기존 `미정_검토자가_판단` placeholder 100건은 채점 답으로 쓰지 않는다.
- 응답은 KPI-3 패킷 SHA-256 `9206684fd6644a92b310539fd15d0b203789f93a4e383f87716545b91c4d8d81`과 일치하고, 엔진 로직 9개를 보지 않았다고 선언하며, 엔진 출력 열람은 `false`다. 답은 허용된 KPI-3 행동 어휘 안에 있고 사례 ID 100개가 정확히 일치했다.
- 원본 응답이 `reviewing_agent` 형식으로 생성됐으므로 `--promote-review-response`를 명시해야만 1차 초안으로 전환한다. 워크벤치는 `input_response_role: independent_ai_review_promoted_to_primary`와 원본 파일 SHA-256 `9e2ef4b2f03255c394ed475aec5f74493aafd8332b743b6ecbce5bfed7896015`를 보존한다. 역할 전환 사실을 숨기지 않는다.
- 단일 답 문자열은 가져올 때 1개짜리 배열로 정규화한다. 저장된 증거와 봉인 감사는 계속 배열만 허용해 사후 스키마 변조를 차단한다.
- KPI-4 Codex 응답 100건도 패킷 해시는 맞지만 OpenAI 상담 모델과 같은 제공자 계열이다. 따라서 KPI-4 1차 초안으로 가져오지 않았다. Claude 1차 초안이 들어온 뒤 2차 의견으로만 검증할 수 있다.
- 현재 KPI-3은 `complete_independent_ai_review_required`로 차단된다. 다음 입력은 Anthropic 계열처럼 Codex와 다른 제공자 계열의 독립 응답 100건이다. 사람 판단·승인·봉인은 만들지 않았다.
- 관련 회귀 시험 121건은 통과했다. 전체 pytest 실제 실행은 기준선과 같은 90건 실패로 신규 실패 0건이다. 직전 114건 보고는 stale `lastfailed` 캐시를 센 오류였으며 위 절에서 정정했다. 지정 Ruff 범위는 기존 `run_counseling_full_service_roundtrip_smoke.py` 오류 2건만 남는다.
- 엔진·안전 규칙·채점 로직·frozen eval·replay·slice는 바꾸지 않았다. 공식 delta는 0이다.

## 2026-08-01 KPI-3·4 Codex 독립 의견 생성

- 서로 분리된 Codex 작업 두 개가 KPI-3·4 블라인드 패킷만 읽고 각각 100건, 총 200건의 독립 의견을 만들었다.
- 패킷 SHA-256, 문항 수와 ID, 답변 어휘, 블라인드 선언을 검사했고 두 파일 모두 구조 검증을 통과했다.
- KPI-3 Codex 응답은 원래 역할을 provenance에 보존하고 독립 1차 초안으로 가져왔다. KPI-3에는 비 OpenAI 계열의 2차 의견이 필요하다.
- KPI-4는 OpenAI 상담 모듈을 측정하므로 Codex 응답을 1차 초안으로 쓸 수 없다. 비 OpenAI 계열의 1차 초안을 먼저 가져온 뒤 Codex를 2차 의견으로 가져온다.
- Claude 응답 0건, 사람 상세 판단 0건, 사람 일괄 승인 0건, 신규 봉인 0건이다. 따라서 완료 상태는 정상적으로 `BLOCKED`다.
- 다음 순서는 KPI-3 Claude 2차 의견과 KPI-4 Claude 1차 초안 확보 → KPI-4 Codex 2차 의견 가져오기 → 최소 사람 검토·일괄 승인이다.

## 2026-08-01 미확인 오류 봉인의 읽기 전용 상태 확인

- `discard-status --indicator <KPI-ID>`를 추가했다. 명령은 활성 봉인과 사람이 확인하기 전에 `seals/discarded/`로 옮겨진 봉인을 찾고, 파일 SHA-256·내장 봉인 해시·정식 폐기 이력 수를 출력한다.
- 상태 확인은 파일·워크벤치·폐기 이력을 바꾸지 않는다. 현재 KPI-1·5는 모두 `AWAITING_HUMAN_CONFIRMATION`, `formal_disposal_count: 0`, `mutated: false`다.
- KPI-1 파일 SHA-256은 `8918fd6fea2e839251cad4a47d3f3a1169bc37537c864d35d94b40cacdd7cf26`, KPI-5는 `8822b96d2de196a39bf424f1e6d7255603f319cd442ea17bfae9f82d90b5eb61`이다. 이 값은 증거 파일 자체의 해시이며, JSON 안의 과거 봉인 해시와 용도가 다르다.
- 사람의 폐기 판정·확인 문구·서명은 입력하지 않았다. 미추적 증거 파일도 커밋하지 않았다. 정식 폐기는 사람이 기존 `discard-seal`을 실행해야 생긴다.
- 회귀 시험 2건을 추가했다. 사전 이동 봉인의 무변경 상태 보고와, 과거 이력만 있고 현재 후보가 없을 때의 `NO_SEAL_CANDIDATE`를 검증한다.
- 엔진 지식베이스·안전 규칙·채점 로직·frozen eval·replay·slice는 바꾸지 않았다. 공식 delta는 모두 0이다.

## 2026-08-01 KPI 정답지의 사람 상세 검토를 최소화하는 교차 AI 절차

- KPI-1·3·4·5의 측정 사례는 지표별 100건으로 유지한다. 연구계획서의 측정 표본은 줄이지 않고, 사람이 자세히 읽어야 하는 사례만 줄였다.
- 서로 다른 제공자 계열 AI가 모든 사례를 독립적으로 답한다. 사람은 모든 불일치, 모든 위험 플래그, SHA-256으로 고른 합의 사례 5건을 상세 검토한다. 표본에서 1건을 고치면 20건, 2건을 고치면 모든 합의 사례로 확대한다.
- 남은 AI 합의안은 자동 확정하지 않는다. 같은 사람이 `<KPI-ID> AI 합의안 일괄 승인`을 직접 입력해야 최종 결정이 생긴다. 기록은 `detailed_review_count`와 `batch_approved_count`를 분리하며 일괄 승인 사례를 개별 검토로 표시하지 않는다.
- 모든 AI가 합의하고 위험 플래그가 없을 때 사람 상세 검토 하한은 지표별 5건, 네 지표 합계 20건이다. 불일치·위험·표본 수정이 있으면 늘어나며 최악에는 400건 전수 검토로 돌아간다. 5건은 통계적·임상적 타당성 표본이 아니라 오류 탐지용 운영 하한이다.
- KPI-3은 미정 표시를 답으로 세지 않는다. 첫 블라인드 AI 응답을 `import-primary-ai-draft`로 1차 초안에 넣고 다른 계열 AI가 같은 패킷을 다시 판단한다. KPI-4의 측정 대상은 OpenAI 상담 모듈이므로 Claude 같은 비-OpenAI 계열 1차 초안과 새 블라인드 Codex 검수를 사용하며, 같은 제공자 계열이면 봉인을 거부한다.
- 블라인드 패킷은 1차 답·근거와 엔진 로직·출력을 제외하고 SHA-256으로 묶는다. 불완전한 응답, 같은 계열 검수, 엔진 출력 열람, 누락된 블라인딩 경로, 변조된 응답·일괄 승인은 감사와 봉인 단계에서 차단한다.
- 봉인은 `reference_standard_seal_v2` 전체 payload를 해시한다. 정답뿐 아니라 무결성 감사, AI 응답 지문, 사람 승인, 측정 대상 ID·제공자 계열도 봉인 지문에 포함한다. 현재 워크벤치의 최종 답과 provenance가 봉인과 다르면 완료 감사가 실패한다. 반려·중복 사례나 100건 미만 봉인은 파일을 쓰기 전에 차단한다.
- 저장된 JSON을 사람이 고쳐도 우회하지 못하도록 제공자 계열·출처·답 어휘·응답 스키마·일괄 승인 문구·검토/승인 시간 순서·유한한 검토 시간을 봉인 직전에 다시 계산한다. 1차와 2차 AI 양쪽의 위험 플래그가 상세 검토 대상에 포함된다.
- 현재 저장소에는 실제 Claude/Codex 응답과 사람 판단·일괄 승인·봉인이 없다. 현재 Codex 작업은 엔진 정책을 이미 읽었으므로 블라인드 검수자 역할을 대신하지 않았다. `minimal-status`는 실제 독립 AI 응답이 들어오기 전까지 `BLOCKED`다.
- 검증: 관련 기능·봉인·완료 게이트 테스트 190건이 통과했다. 전체 pytest는 기준선과 같은 90건 실패로 신규 실패 0건이다. 전체 Ruff는 기준선과 같은 28건이며 변경 파일 Ruff는 0건이다. 지정 Ruff 범위에는 기존 `run_counseling_full_service_roundtrip_smoke.py` 오류 2건만 남는다. 엔진 입력 레지스트리 재생성 diff가 없고 정답지 무결성 감사는 KPI-1·3·4·5 모두 PASS다. 사람 결정과 봉인이 없으므로 완료 상태만 정상적으로 `BLOCKED`다.
- 사람 판정·서명·봉인, 배포, 실제 트래픽, 훈련, frozen eval은 실행하지 않았다. KPI-1·5의 과속 봉인 폐기도 사람이 확인해야 하므로 기록을 대신 만들지 않았다.
- 한계: 외부 AI가 실제로 패킷만 보았는지는 응답의 자기 진술과 별도 실행 증빙에 의존한다. AST 감사는 파일 단위여서 읽은 파일을 정답에 썼는지까지 구분하지 못한다. 제공자 계열 판별은 알려진 이름에 대한 휴리스틱이고, 1초 하한은 자동 입력 차단용 임의 기준이다. 원문 성분 234종 중 209종은 카탈로그 밖이라 채점에서 빠진다.

## 2026-07-31 KPI 정답지 무결성 게이트 완성

- 선택 단계·과제: TIPS KPI-1·3·4·5 정답지의 출처 독립성과 실제 사람 검토를 봉인 전 필수 조건으로 만들었다. 최종 작업 브랜치는 `fix/kpi-answer-key-integrity-clean`이다.
- 감사기 오탐 수정: AST가 `open`, `Path.open`, `read_text`, `read_bytes`로 이어지는 경로만 실제 읽기로 판정한다. `BLINDED_FROM` 같은 선언 전용 상수는 제외하지만, 반복문이나 컴프리헨션이 그 상수를 실제 읽기 경로에 쓰면 위반으로 잡는다. 출처 인덱스는 `(indicator_id, draft_source)`를 키로 쓰고 출처 이름에 생성 모듈을 붙여 KPI-4·5의 모듈을 구분한다. KPI-1·3·4·5의 현재 초안 출처 감사가 모두 PASS다.
- 봉인 폐기 경로: `discard-seal` 명령이 폐기자·사유·시각·봉인 SHA-256을 기록하고 기존 봉인과 워크벤치를 archive에 보존한다. 정확한 확인 문구를 입력하기 전에는 파일을 바꾸지 않는다. 폐기 이력은 다음 봉인의 `prior_seal_disposals`에 포함된다. 사람이 확인하기 전에 `seals/discarded/`로 옮겨진 봉인도 같은 명령으로 정식 폐기 기록을 만들 수 있다.
- KPI-1·5 오류 봉인 상태: 두 봉인은 건당 약 0.038초, 수정률 0%인 무효 검토에서 만들어졌다. 현재 파일은 `data/original_plan/kpi/seals/discarded/`에 있지만, 폐기자·폐기 시각·폐기 사유가 있는 사람 확인 기록은 아직 없다. 따라서 두 봉인의 이동은 정식 폐기로 인정하지 않는다. 원본 파일은 미추적 감사 증거로 보존하고, 판단 기록을 임의로 복원하거나 사람 폐기를 대신 기록하지 않았다.
- 저장·봉인 차단: 1.0초 미만 입력은 건별 판단으로 저장하지 않는다. 두 봉인 CLI는 현재 워크벤치의 무결성 감사와 검토 시간 판정이 PASS이고 전 건 판단이 끝난 경우에만 봉인한다. 완료 마법사의 `ANSWER_KEYS` 단계와 최종 감사도 같은 결과가 PASS인 봉인 4종을 요구한다.
- provenance: 각 초안에 `drafting_agent`와 엔진 로직 9개를 담은 `blinded_from`을 기록한다. 기존 필드가 없는 워크벤치도 로드된다. KPI-4 봉인은 상담 모듈 에이전트 계열을 추가로 받고, `codex`와 `OpenAI GPT`처럼 제공자 계열이 같으면 거부한다.
- CI: `original-plan-evidence.yml`에 엔진 입력 레지스트리 재생성, diff 확인, 무결성 감사와 회귀 시험을 추가했다.
- 검증: `python scripts/audit_answer_key_integrity.py --json`은 초안 출처 4/4 PASS와 `completion_status: BLOCKED`를 함께 반환했다. 사람 판단과 새 봉인이 없으므로 KPI 네 종 모두 완료 차단 상태다. 전체 pytest는 기준선과 같은 90건 실패, 전체 Ruff는 기준선과 같은 28건이며 신규 실패·오류는 0건이다. YAML 파싱과 엔진 입력 레지스트리 재생성 diff도 통과했다.
- 커밋: `1700616` 감사기 기반, `e9bf924` 감사 가능한 폐기 경로, `f8a272d` 저장·봉인·완료 게이트와 provenance 강화.
- 경계: 엔진 지식베이스·안전 규칙·채점 로직·frozen eval·replay·slice·학습·시뮬레이션을 바꾸지 않았다. 공식 지표 delta는 0이다. 사람 판정·서명·봉인을 만들지 않았다.

## 2026-07-31 KPI-3·4 초안 감사와 KPI-2 경로 기록

- 선택 단계·과제: `NEXT_STEPS.md` 3번 "KPI-3·4 초안도 같은 기준으로 출처 독립성을 감사한다"를 수행했다. 브랜치는 `kpi2-decision-record`다.
- 요청받은 정답 400건 확정은 수행하지 않았다. `review` 는 각 건을 `decided_by` 로 사람 이름에 귀속시켜 저장하므로, 세션이 대신 누르면 있지도 않은 사람의 판정이 기록된다. 워크벤치 400건은 전부 `pending` 이고 `reviewers` 는 비어 있다.
- 감사 결과 2건. (1) **KPI-3 무효.** 정답이 `closed_loop_next_action_policy_v1.json` 의 `action` 값이고, 엔진도 `src/wellnessbox_rnd/interim/next_action.py:79` 에서 같은 파일을 읽는다. 문항은 `_describe_condition(rule["when"])` 으로 그 규칙 자신의 발동 조건을 서술해 만든다. 규칙 9개 → 고유 정답 9개이며 정책 action 집합의 부분집합이다. 정확도가 구조적으로 100%가 된다. 기존 근거 `op071_op080_closed_loop_next_action_policy_v1.json` 의 130/130 100%는 성능이 아니라 이 자기 참조의 지문이다. KPI-5가 탈락한 것과 같은 구조다. (2) **KPI-4 미달.** 고유 문항이 57개뿐이라 계약의 100문항 요건을 못 채운다. 고유 정답은 5개로, 템플릿에 하드코딩된 채점 기준 문구가 20건씩 반복된다. 문항별 라벨 정답이 아니다.
- 부수 확인: KPI-3·4 워크벤치의 `draft_source` 가 둘 다 `goal_ingredient_priors_v1+ingredient_catalog` 로 실제 출처와 다르다. `assert_source_is_independent` 는 출처 문자열만 보므로 이 라벨 오류가 있으면 독립성 검사가 실제 출처를 못 본다.
- KPI-2: 경로를 A(운영 서비스 사용자 확보) + 측정 시점 3차년도로 계약 파일 `KPI-2.open_decision.chosen` 과 `chosen_detail` 에 기록했다. 오너가 판단을 세션에 위임해 `decision_mode: owner_delegated_to_ai_session` 으로 남겼고, 이의가 있으면 그 필드만 바꾸면 된다. 100명 요건 자체는 바뀌지 않으며 수집은 아직 착수되지 않았다.
- 경계: 코드 변경 0건. 초안·봉인·엔진·안전 규칙·채점 로직·frozen eval 모두 그대로다. push·배포·훈련 없음. 미추적 영수증과 `uploads/` 는 건드리지 않았다.
- 검증: 전체 `pytest -q --tb=no` 90 failed로 기준선(89 + 영수증 1) 대비 신규 0건. `ruff check .` 28건으로 신규 0건.

## 2026-07-31 KPI-1·5 정답 초안을 독립 참조 코퍼스로 교체

- 선택 단계·과제: KPI-1과 KPI-5 정답 초안의 출처 독립성을 감사하고 대체 출처를 붙였다. 브랜치는 `book-corpus-answer-keys`다.
- 감사 결과 2건: (1) KPI-1 초안 100건의 서로 다른 정답 조합이 7개뿐이었고, 사례가 `복용약 warfarin`·`임신 중`을 적어도 정답이 바뀌지 않았다. warfarin 사례 1건은 정답에 omega3가 남아 있어 `SAFETY-ANTICOAG-001` 로 올바르게 배제하는 엔진이 오히려 감점된다. (2) KPI-5 초안이 엔진 자신의 `data/rules/safety_rules.json` 등록값을 되묻는 형태라 엔진이 정의상 100%를 맞힌다.
- 대체 출처: `건강상담 Checker`. 프로젝트 오너 저술, 엔진보다 먼저 출판, 저작권자 동일. 엔진 지식베이스 19건(NIH ODS·NCCIH·CDC·ADA·PubMed·master_context)과 근거가 겹치지 않고 저장소 전체 인용 0건임을 확인했다.
- 추출: `scripts/build_health_checker_reference_extract.py` 가 원본 SHA-256과 함께 성분 매핑 25종, 판정 사례 138건, 약물 맥락 7종을 `data/knowledge/external/health_checker_reference_extract_v1.json` 에 쓴다. 카탈로그 12키를 모두 커버한다.
- 초안: `reference_corpus_drafters.py` 가 판정 상태 × 약물 맥락을 교차해 KPI-1·5 각 100건을 만든다. 정답이 맥락을 따라 움직인다 — Furosemide 사례는 원문 권장에 루프이뇨제 고갈 성분 3종이 붙고(p236), Levothyroxine은 흡수 간섭형이라 배제 대신 4시간 간격 상담 문구를 근거에 남긴다(p239). 서로 다른 정답 조합이 7개에서 67개로 늘었다.
- 경계: 기존 `answer_key_drafters.py` 와 작업대 CLI는 건드리지 않았다. 기존 CLI의 `--cases` 경로로 초안 파일만 넘긴다. 엔진 지식베이스·안전 규칙·채점 로직·frozen eval은 그대로다. 사람 확정과 봉인은 하지 않았다.
- 한계: 원문 성분 234종 중 카탈로그에 없는 209종은 채점에서 빠지고 `out_of_catalog_nutrients` 로만 남는다. 소아·임신 영역과 성인 약물의 기계적 교차는 `검토자 확인 필요` 로 표시했고 임상 판단은 검토자 몫이다.
- 검증: `pytest tests/test_reference_corpus_drafters.py` 12건 통과, `tests/test_answer_key_workbench.py` 32건 통과, `-k "answer_key or reference_standard or reference_corpus"` 66건 통과. 신규 파일 Ruff 0건.

## 2026-07-30 연구 마감 원스텝 실행기 추가

- 선택 단계·과제: 사람이 켜서 Enter만 누르며 끝까지 갈 수 있는 안내 실행기를 만들었다. 브랜치는 `one-step-completion-wizard`다.
- 진입점: 저장소 루트의 `research-complete.cmd` 하나다. 12단계를 순서대로 안내하고, 필요한 화면을 자동으로 띄우며, 사람이 끝냈다고 하면 저장소를 다시 읽어 실제 저장을 확인한다. `--status`는 아무것도 실행하지 않고 현재 진행 상황만 읽는다.
- 12단계: 사전 점검, 서버 켜기, 실제 프로필 5건, AI 초안 전수 검토, 승인 전용 데이터셋, 후보 학습, 안전 회귀·교체 판정, 정책 9규칙, 문체 승인, 고위험 10건, 최종 영수증, 최종 감사다. 자동 5개, 사람 7개다.
- 세션 경계: 실행기는 시작 시각을 기록하고 그 이전 완료 기록을 이번 세션 근거로 세지 않는다. 저장된 H-002~H-007 완료는 모두 2026-07-23~24 기록이라 지금은 `이번 세션 시작 전입니다`로 표시되고 다시 하라고 안내한다. 프로필과 초안도 `created_at`·`reviewed_at` 기준으로 이번 세션 몫만 센다.
- H-005 추가 검사: 저장된 검토에 자격 단계 표시가 없으면 중립 화면 이전 기록으로 보고 다시 검토하라고 알린다.
- 학습 게이트: NO-GO인 6·7단계는 실패가 아니라 `skipped_gate_closed`로 처리해 흐름을 막지 않는다. 훈련은 실행하지 않고 실행 계획만 남긴다.
- 경계: 판정을 대신 고르거나 완료로 표시만 하고 넘어가지 않는다. 운영 DB에는 쓰지 않고 확인은 전부 읽기 전용이다. push·배포·영수증 위조도 하지 않는다.
- 검증: `pytest tests/test_completion_wizard.py` 34건 통과. 실제 저장소에 `--status`를 돌려 2/12 단계만 끝난 상태를 정확히 읽는 것을 확인했다. 전체 pytest `1,235 passed / 89 failed`, 신규 실패 0건. Ruff 28건으로 신규 오류 0건이다.

## 2026-07-30 검토자 자격 구조를 예비 약사 기준으로 재설정

- 선택 단계·과제: 안전 검토자의 자격 표현을 사실에 맞게 다시 세웠다. 과제 참여자 두 사람은 2026-07 현재 약사 면허가 없고 2027-01 취득 예정이다. 브랜치는 `pre-licensure-reviewer-model`다.
- 사실 기준: 2차년도인 지금 수행하는 검토는 예비 약사 사전 검토다. 3차년도에 면허를 받은 뒤 같은 사례를 약사 자격으로 다시 검토한다. 최종 마감 2027-10 안에 재검토를 마칠 수 있다. 2차년도에는 연구를 완료할 의무가 없으므로 지금 "약사가 검토했다"고 쓰지 않는다.
- 입력 간소화: H-005 화면에서 면허 번호와 자격 확인 방법 칸을 없앴다. 아직 존재하지 않는 값을 받으면 `not_collected` 같은 자리표시자가 남고 그것이 자격 확인 근거로 잘못 읽히기 때문이다. 남은 입력은 검토자 성명, 소속, 서명 세 개뿐이며 이름과 소속은 과제 등록 정보와 대조한다.
- 자격 게이트: `reviewer_credentials.py`가 오너·시스템 계정 차단, 등록 참여자 확인, 소속 일치, H-003 초안 원장 교차확인, `licensed_pharmacist` 허위 주장 차단을 수행한다. 자격 단계 계약은 `op039_reviewer_identity_registry_v1.json`에 있고 3차년도에는 이 파일의 `qualification_stage`만 바꾸면 된다.
- 단계 승격 차단: 예비 약사 검토는 OP-039를 `EXTERNAL`로 올리지 않는다. 완료 기록에 `review_character=pharmacist_candidate_preliminary_safety_review`와 `requires_licensed_reconfirmation=true`가 남는다.
- 문서: 새 `docs/original_plan/REVIEWER_QUALIFICATION_POLICY.md`가 두 단계의 구분과 3차년도 전환 절차를 정한다. 실행서, 체크리스트, 운영 절차, 빠른 안내, 비전문가 요약, OP-039 보고서를 모두 예비 약사 기준으로 고쳤다.
- 검증: `pytest tests/test_reviewer_credentials.py` 30건, `tests/test_op039_reviewer_form_neutrality.py` 7건, `tests/test_final_session_console.py` 27건이 통과했다. 전체 pytest와 사전 점검 결과는 아래 최종 항목에 적는다.
- 경계: push, 배포, 훈련, 사람 판정·서명 생성은 하지 않았다. 과거 운영 영수증과 저장된 검토 기록은 이력으로 보존했고 고치지 않았다.

## 2026-07-27 H-005 중립화와 H-003 학습 계보 구현 완료

- 선택 단계·과제: 사람 최종 세션을 막고 있던 두 결함을 실제로 고쳤다. H-005 검토 화면 중립화와 H-003 승인 초안→학습→후보 평가→안전 회귀→교체·rollback 계보 구현이다. 브랜치는 `h005-neutral-h003-lineage`다.
- H-005 결과: 고위험 10건 화면에서 `타당` 선입력, AI 의견 선입력, `not_collected` 면허, `project_owner_attestation` 자격 확인, 이름 자동 복사 서명, 하드코딩 `was_ai_draft_reviewer=false`를 모두 없앴다. 라디오 20개 전부 미선택, 의견란 10개 전부 공백으로 열린다. 면허 번호·자격 확인 방법·서명은 빈 입력란이며 비면 제출이 막힌다.
- 사전 점검 결과: 실제 preflight가 처음으로 `READY`, 종료 코드 0, 차단 0건을 반환했다. H-005 선택 10/10→0/0, 의견 10/10→0/0이다. DB 본체·WAL·SHM, 제어 파일, 최종 세션 직접 파일 13개, 운영 영수증 15개의 다섯 저장 경계가 모두 `true`였고 잔류 listener도 없었다.
- H-003 결과: 승인 전용 데이터셋 manifest 빌더와 검증기, 게이트로 잠긴 후보 학습 명령, 후보 artifact를 주입하는 고정 평가, 안전 회귀 gate, 교체·유지 판정과 rollback 영수증을 만들었다. 실제 원장으로 manifest를 만든 결과 승인 6건은 모두 권혁찬 검토였고 웰니스박스 계정 검토 1건이 사유와 함께 제외됐다. DB SHA-256은 읽기 전용 실행 전후 동일했다.
- 학습 경계: 학습 게이트가 여전히 NO-GO이므로 훈련을 실행하지 않았다. `train_approved_draft_candidate.py`는 게이트가 닫혀 있으면 종료 코드 2로 멈추고 초안 ID·`dataset_sha256`·argv·`config_sha256`을 담은 실행 계획만 남긴다. 후보 모델이 없으므로 후보 평가와 교체 판정도 실제 값으로 실행하지 않았다.
- 감사 결과: H-005 중립화로 감사 대상 파일이 바뀌어 기록된 blob이 재현되지 않았다. 현재 파일 내용으로 다시 실행해 120/120, `READY`, `goal_complete=true`, 차단 0건으로 정본을 갱신했다. 감사 입력의 R&D 커밋은 `4b5b9e9`다.
- 최종 pytest: `1,170 passed / 89 failed / 5 warnings`, 실측 167초다. 시험 26건(중립성 6, 학습 계보 20)을 추가했고 실패 89개는 `main` 기준선과 같은 집합이므로 새 실패는 0건이다.
- Ruff: 32건에서 29건으로 줄었다(E501 25, I001 3, UP034 1). 다시 쓴 `build_op039_external_review_package.py`의 기존 3건이 사라졌고 신규 오류는 0건이다.
- 백엔드 자격 검증: 같은 날 이어서 네 구간을 채웠다. 오너 차단은 정규화 뒤 별칭 원장과 대조하고, 면허 번호는 자리표시자와 숫자 부족을 거부하며, 자격 확인 방법은 자기 확인류와 짧은 값을 거부하고, `was_ai_draft_reviewer`는 실제 H-003 초안 원장과 대조한다. 전용 시험 28건이 통과한다.
- 외부 기관 평가 위치 정정: OP-039 외부 기관 평가는 연구 종료 후 외부 기관이 수행하는 별개 단계다. 이번 세션의 선행 조건이 아니며 지금 섭외할 일도 아니다. 두 신뢰 원장이 0건이라 그 경로는 현재 발동하지 않는다. 이전 기록에서 이 경로를 "약사 자격 없이 완료되는 우회 경로"라고 쓴 것은 잘못이라 바로잡았다.
- 남은 사람 작업: 시스템은 면허 번호의 형식만 본다. 실제 발급 여부는 조회하지 않으므로 운영 보조자가 현장에서 면허증 원본을 직접 확인하고 그 방법을 사실대로 적어야 한다.
- 변경 경계: push, 배포, 실제 트래픽, 훈련, frozen eval 실행, 사람 판정·승인·서명 생성을 하지 않았다. 추천·안전 규칙과 replay·slice 산출물도 바꾸지 않아 공식 frozen/replay/slice delta는 0이다.

## 2026-07-27 보고서 근거 심화와 사람 세션 직전 정리 완료

- 선택 단계·과제: 단계 0~5 전체다. OP-031~078, OP-105·106, OP-117~119 보고서 53편의 모든 등록 근거를 다시 읽고, 감사 정본화와 사람 세션 사전 점검까지 마쳤다.
- 보고서 결과: 53편의 총 분량은 235,277자다. 최소 2,830자, 중앙값 4,203자, 최대 7,242자이며 3편 이상 반복 문장·문단은 0개다. `docs/original_plan/EVIDENCE_VERIFICATION_REPORT.md`는 등록 파일 경로 492건 모두 존재, 바로잡은 보고서 32편, 최종 내용 불일치 0건을 기록한다.
- 감사 결과: 첫 실행은 OP-060 의미 단어 누락 때문에 119/120 `BLOCKED`였다. OP-060의 실제 요구를 명시하고 커밋한 뒤 두 번째 실행이 120/120, 누락·단계·외부 격차 0, `READY`, `goal_complete=true`를 반환했다. 감사 입력의 R&D 커밋은 `821a5a5`, 감사 JSON 커밋은 `8ee93cc`다.
- 사전 점검: `scripts/run_final_session_preflight.py`는 실제 DB의 본체와 WAL을 임시 복사하고 임시 상태 루트만 사용한다. 복사 전후 본체·WAL·SHM 해시가 다르면 멈추고 임시 DB에 `PRAGMA integrity_check`를 돌린다. 저장 불변은 DB 세 파일, 제어 파일 3종, 최종 세션 직접 파일 13개, 운영 영수증 15개의 다섯 경계를 각각 비교한다. 서버·콘솔·사용자·약사 화면은 모두 정상 응답했고 다섯 경계가 모두 `true`였다. H-005는 원본 HTML이 아니라 Chromium이 렌더링한 DOM을 읽으며, 10건이 모두 사전 선택되고 의견도 10건 채워져 있어 결과는 의도대로 `BLOCKED`, 차단 항목은 `H005_FORM_NOT_NEUTRAL` 하나였다.
- 근거 추적: 447개 OP-경로 판정을 행 단위로 담은 `data/original_plan/evidence/evidence_verification_ledger_v1.json`(SHA-256 `21d1388ed3912174126ae435a85aa80baa991ebd65d1b6aeb3ad0b9816319257`)과 검증기 `scripts/verify_evidence_verification_ledger.py`를 추가했다. 현재 결과는 `READY`, 보고서 53편, 등록 경로 492건, 고유 경로 447건, 고유 파일 189개, 누락 0건, 내용 불일치 0건이다.
- 사람 검증 경계: DB의 서로 다른 프로필 5/5와 감사 `READY`는 다섯 건의 유효한 사람 세션을 입증하지 않는다. H-005는 면허·자격 확인 방법·별도 서명 검증이 부족하고, H-003은 승인 초안에서 학습·후보 평가·안전 회귀·교체 또는 유지로 이어지는 실제 명령 계보가 없다.
- 최종 pytest: `1,144 passed / 89 failed / 5 warnings`, 실측 177초다. 연속 2회 실행에서 수치와 실패 함수 목록이 같았다. 사전 점검 전용 시험을 4개에서 10개로 늘려 통과 수가 6개 늘었다. 새 실패 0건은 `main`(`bebed41`) worktree에서 같은 72개 시험 파일을 돌려 함수 단위로 대조했다. main은 96개가 실패했고 이번 브랜치의 89개는 그 부분집합이다.
- Ruff: 기존 파일 5개의 32건(E501 27, I001 4, UP034 1)이 그대로다. 모든 진단 줄은 main 조상 커밋에서 들어왔고 이번 브랜치 신규 오류는 0건이다.
- 변경 경계: 공개 배포, push, 실제 트래픽, 사람 판정·서명, 훈련, frozen eval, 모델, 추천·안전 규칙과 replay·slice 산출물은 바꾸지 않았다. 공식 frozen/replay/slice delta는 0이다.
- 병합 판정: 감사 120/120 `READY`, 보고서 내용 불일치 0건, pytest 새 실패 0건의 세 조건을 모두 충족했다. 최종 문서 커밋 뒤 `main`에 fast-forward 병합하며 push는 하지 않는다.

## 2026-07-23 OP-027/028 연구보고서 backfill 완료

- OP-027 이벤트 idempotency와 OP-028 정정·삭제 mutation 계보를 구현·테스트·원문 PDF와 대조했다. 둘 다 `IMPLEMENTED / COMPLETE`이며 production 운영은 주장하지 않는다.
- 주 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `d32cfd1b8830f5c727696556bc6ecc247abc01ca54e3c2f5d461ea76cdf077da`다. event mutation smoke는 3건, SHA-256 `980e5677adcb54db684679a3111b0a6927b4e5fc47d6ddc7c9cc8bf6ab19dfb8`이다.
- stale database schema 8 증거를 현재 schema 14로 재생성하고 canonical evidence 현재성 회귀 테스트를 추가했다. 동일 smoke를 두 번 생성한 결과는 byte-identical이다.
- 물리 보고서 70개, 유효 48/120, 누락·부적합 72개, 총 327,598자다. completion은 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`; OP-120은 `BLOCKED`, evidence SHA-256은 `e9d00582015a0ea0581d107eb212601ded346468030004641304c486ddba281d`다.
- focused pytest 106건, tracked Ruff, manifest audit, completion check가 통과했다. 독립 검토는 `Critical 0 / Important 0 / Minor 0`, GitHub Actions `29970576517`은 성공했다.
- 서비스·production·원천/frozen/학습 데이터·모델·simulation은 변경하지 않았다. frozen 256건의 7개 지표, replay와 weakest-slice 입력이 그대로여서 delta는 모두 0이다.
- 병목 5개: 보고서 72개, required-stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt. 다음 loop: OP-029/030, OP-031/032, OP-033/034.

## 2026-07-23 OP-025/026 연구보고서 backfill 완료

- OP-025 행동·연구평가 로그의 table·vocabulary·API 분리와 OP-026 model·engine·commit·dataset·config 실행 identity를 원본 PDF 16쪽, schema, recorder, identity builder, trace와 테스트에 대조했다. 둘 다 `IMPLEMENTED / COMPLETE`이며 production 운영은 주장하지 않는다.
- 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `99245ed22d1401e07898138da4efd1b8853edf085e1e6c4fec443dd2ee2198a1`다. 물리 보고서 68개, 유효 46/120, 누락·부적합 74개, 총 316,581자다.
- schema 8 stale smoke를 schema 14로 재생하고 dataset identity 기대값을 `RUNTIME_DATASET_ARTIFACTS`에서 계산하도록 고쳤다. evidence 현재성 회귀 테스트를 추가했으며 smoke 2건 SHA-256은 `4bda8974a6eba797d9d585a2eff8fd15611cdffdf169dee27be95540041ac221`이다.
- 독립 검토 Minor 1건은 OP-025가 `occurred_at`·`data_class`를 두 table 공통 열로 잘못 설명한 문제였다. behavior 전용 열과 공통 열을 바로잡은 뒤 최종 `Critical 0 / Important 0 / Minor 0`이다.
- OP-120 evidence는 수정 뒤 두 번 byte-identical로 재생됐고 SHA-256은 `68aaa12d6c0541324fe27f888b9392d30ddff03dcbbf8a432b0ff11a2bca426b`다. completion은 `76/43/0/1/0`, 최종 감사는 `BLOCKED`다.
- focused pytest 92건, tracked Ruff, manifest audit, completion check가 통과했다. GitHub Actions `29969740776`도 성공했다. production·서비스·원천/frozen/학습 데이터·모델·simulation 변경 없음; frozen/replay/slice delta 0.
- 병목 5개: 보고서 74개, stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt. 다음: OP-027/028, OP-029/030, OP-031/032.

## 2026-07-23 OP-023/024 연구보고서 backfill 완료

- OP-023 source→passage→claim→rule→execution output 계보와 OP-024 source type·license·effective/retired metadata 저장을 원본 PDF 16쪽, parser, runtime DB, normalized registry, API trace와 테스트에 대조했다. 둘 다 `IMPLEMENTED / COMPLETE`이며 production 운영은 주장하지 않는다.
- 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `39e363ecae5f1f7187e0edd25a01cc553cc77bdf816252491f85f64007749970`다. 물리 보고서 66개, 유효 44/120, 누락·부적합 76개, 총 304,015자다.
- stale smoke의 schema 8과 초기 artifact count `3/5/5/5/5` 하드코딩을 발견했다. 현재 schema 14와 정본 19 sources·24 passages/claims·5 rules/links를 직접 읽도록 재생기를 고치고 현재성 회귀 테스트를 추가했다. smoke 1건 SHA-256은 `b13b97b0ccb20ba4cda96bc8f4b32acc398f49a683adda20ab09d06685d504fd`다.
- 독립 검토의 Important 1건은 registry quarantine을 실제 recommendation runtime gate로 과장한 문구, Minor 1건은 claim-rule 테스트 방향 설명이었다. 한계를 명시하고 바로잡은 뒤 최종 `Critical 0 / Important 0 / Minor 0`이다.
- OP-120 evidence는 수정 뒤 두 번 byte-identical로 재생됐고 SHA-256은 `17189085bee1c02a4a350d8bbf333a1d5da082938d6f15704ec8566d1f138c16`이다. completion은 `76/43/0/1/0`, 최종 감사는 `BLOCKED`다.
- focused pytest 87건, tracked Ruff, manifest audit, completion check가 통과했다. GitHub Actions `29968699617`도 성공했다. production·서비스·원천 지식·frozen/학습 데이터·모델·simulation 변경 없음; frozen/replay/slice delta 0.
- 병목 5개: 보고서 76개, stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt. 다음: OP-025/026, OP-027/028, OP-029/030.

## 2026-07-23 OP-021/022 연구보고서 backfill 완료

- OP-021 프로필·동의 버전 스냅샷과 OP-022 다섯 이벤트의 공통 `execution_id` 연결을 원본 PDF 16쪽, SQLite schema, ledger, FastAPI, 테스트와 canonical smoke에 대조했다. 둘 다 `IMPLEMENTED / COMPLETE`이며 production 운영은 주장하지 않는다.
- 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `eb6fa5b6bdfdadf0f81d28aec9d941847f951b0cbfda08408dc38313936ecd02`다. 물리 보고서 64개, 유효 42/120, 누락·부적합 78개, 총 292,110자다.
- 독립 검토가 오래된 schema version 8 smoke를 Important로 발견했다. 현재 schema 14로 재생하고 evidence와 `SCHEMA_VERSION`을 직접 비교하는 회귀 테스트를 추가했다. smoke SHA-256은 `4ed927ba7a081b74b5fd1a7dff62a67ac797ba7450dd90fcb489b7e210e0da97`다.
- OP-120 evidence는 수정 뒤 두 번 byte-identical로 재생됐고 SHA-256은 `d8059938b8487452b68c3c4a26ffa8f24429f6119750286d725cf2d6941dccb6`다. completion은 `76/43/0/1/0`, 최종 감사는 `BLOCKED`다.
- 수정 후 R&D focused pytest 109건, 서비스 adapter QA 17 checks, tracked Ruff, manifest audit, completion check가 통과했다. 재검토는 `Critical 0 / Important 0 / Minor 0`, GitHub Actions `29940069699`도 성공했다.
- 서비스 보호 변경·production·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen 256건 7개 지표, replay, weakest slice delta 0.
- 병목 5개: 보고서 78개, stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt. 다음: OP-023/024, OP-025/026, OP-027/028.

## 2026-07-23 OP-019/020 연구보고서 backfill 완료

- OP-019 WellnessBox profile adapter와 OP-020 미지원 입력 오류·지원 결측 `missing_information` 계약을 양쪽 schema, adapter, preview route, 공유 fixture, API 테스트와 Git 이력에 대조했다. 둘 다 `INTEGRATED / COMPLETE`이며 production 운영·외부 검증은 주장하지 않는다.
- 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `a0c4255339a2945dce61bd330d427693ef4f797799c246db603028447206a545`다. 물리 보고서 62개, 유효 40/120, 누락·부적합 80개, 총 282,078자다.
- OP-120 evidence는 두 번 byte-identical로 재생됐고 SHA-256은 `6318bd672f8202dfe5513641f4edad694c47123a082e0fc0390f45a79752a6b7`다. completion은 `76/43/0/1/0`, 최종 감사는 `BLOCKED`다.
- R&D focused pytest 72건, 서비스 adapter QA 17 checks, tracked Ruff, manifest audit, completion check가 통과했다. 독립 검토 `Critical 0 / Important 0 / Minor 0`.
- GitHub Actions `29937570061` 최초 시도는 관련 없는 OP-115/116 과거 build 재생에서 stderr 없이 실패했다. 동일 source failed-job 재실행은 전체 성공해 일시적 CI build 실패로 판정했다.
- 서비스 보호 변경·production·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen 256건 7개 지표, replay, weakest slice delta 0.
- 병목 5개: 보고서 80개, stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt. 다음: OP-021/022, OP-023/024, OP-025/026.

## 2026-07-23 OP-017/018 연구보고서 backfill 완료

- OP-017의 다섯 데이터 출처별 추천 사용·영구 저장 동의와 OP-018의 canonical snapshot·SHA-256 동일성 계약을 schema, intake, API, 테스트, Git 이력, 원본 PDF 16쪽에 대조했다. 둘 다 `IMPLEMENTED / COMPLETE`이며 운영·외부 검증은 주장하지 않는다.
- 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `b5991cc307f5fa6cea20fb3165d57798a9389d50338adb89da51c807debbcf6d`다. 물리 보고서 60개, 유효 38/120, 누락·부적합 82개, 총 274,237자다.
- OP-120 evidence는 두 번 byte-identical로 재생됐고 SHA-256은 `ca11bc8843c4f7a92a3336f16e09f1e0d268b16e2879d8d5f0e8d56074b98bb0`다. completion은 `76/43/0/1/0`, 최종 감사는 `BLOCKED`다.
- focused pytest 62건, tracked Ruff, manifest audit, completion check, canonical 재생이 통과했다. 독립 검토 `Critical 0 / Important 0 / Minor 0`; GitHub Actions `29935977162` 성공.
- 서비스·production·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen 256건 7개 지표, replay, weakest slice delta 0.
- 병목 5개: 보고서 82개, stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt. 다음: OP-019/020, OP-021/022, OP-023/024.

## 2026-07-23 OP-015/016 연구보고서 backfill 완료

- OP-015 알레르기·식이·생활 습관과 OP-016 검사 관측값의 기존 구현을 schema, intake, 모델 feature, API, 테스트, Git 이력, 원본 PDF 16쪽에 대조했다. 둘 다 `IMPLEMENTED / COMPLETE`이며 통합·운영·외부 검증은 주장하지 않는다.
- 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `9911c8b9344d82478bfa5aad41524f7507c9dbc9185df0501bd3b7372be7e1eb`다. 물리 보고서 58개, 유효 36/120, 누락·부적합 84개, 총 267,068자다.
- OP-120 evidence는 두 번 byte-identical로 재생됐고 SHA-256은 `ad43403b9105a3bdd49ddf23d616d35e47da559db7b11e692ed4832ed8bd2c8e`다. completion은 `76/43/0/1/0`, 최종 감사는 `BLOCKED`다.
- focused pytest 57건, tracked Ruff, manifest audit, completion check, canonical 재생이 통과했다. 전체 pytest의 실패는 기존 artifact 부재와 CGM 계열뿐이며 OP-015/016 신규 실패는 없다. 독립 검토는 Minor 2건을 고친 뒤 `Critical 0 / Important 0 / Minor 0`; GitHub Actions `29934330927` 성공.
- 서비스·production·원천/frozen/학습 데이터·모델·simulation 변경 없음. frozen 256건 7개 지표, replay, weakest slice delta 0.
- 병목 5개: 보고서 84개, stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt. 다음: OP-017/018, OP-019/020, OP-021/022.

## 2026-07-22 OP-013/014 연구보고서 보강 완료

- OP-013 약물 구조와 OP-014 건강기능식품 제품·성분·1일 용량 보고서를 완성했다. 둘 다 `IMPLEMENTED / COMPLETE`이며 더 높은 단계는 주장하지 않는다.
- 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `183b3b8e61134046df7dc8245d9ce40da9b1b0aec01c1c381b89ea98af448dbe`다. 물리 보고서 56개, 유효 34/120, 누락·부적합 86개, 총 259,631자다.
- 공용 `DoseAmount`가 boolean을 숫자로 변환하던 결함을 red-green 회귀로 수정했다. OP-120 audited commit/blob provenance의 self-reference, shallow service history, CI evidence root portability도 함께 수정했다.
- schema-dependent canonical smoke 10개와 workflow service root 기반 OP-049/050·057/058·059/060 evidence를 재생성했다. 최종 OP-120 evidence SHA-256은 `103014005b229e778fde4e71e018743643305baa2eebf7efd69a96f72fa6b7c8`다.
- 검증: focused pytest 87건, tracked Ruff, manifest audit, completion check PASS. 독립 검토 최종 `Critical 0 / Important 0 / Minor 0`. GitHub Actions `29931855632` 성공.
- 코드 변경은 입력 검증과 evidence provenance에 한정했다. production·학습·simulation은 변경하지 않았고 frozen 256건의 7개 지표, weakest slice와 replay 결과 의미 delta는 0이다.
- 병목 5개: 보고서 86개, stage gap 43개, OP-039 외부 검증, validation receipt, independent-review receipt. 다음: OP-015/016, OP-017/018, OP-019/020.

## 2026-07-22 OP-013/014 연구보고서 보강 진행 중

- OP-013/014 장문 보고서와 OP-120 inventory를 갱신했다. 물리 56개, 유효 34/120, 누락·부적합 86개, 259,631자다.
- 독립 검토 Important 1건으로 `DoseAmount(amount=True)`가 1.0으로 변환되는 공용 결함을 재현했다. 회귀 테스트를 먼저 실패시킨 뒤 boolean before-validator를 추가해 수정했다.
- focused pytest 86건, 약물·보충제 44건, tracked Ruff, manifest audit, completion check가 통과했다. evidence SHA-256은 `1d8653bf098fa8dd57ebca445497e56e1bda8e07a13d3010683cfe837aa8018f`다.
- 수정 HEAD `9a02008`; GitHub Actions `29924086385`와 독립 재검토가 진행 중이다. 두 결과 전에는 이 loop를 완료로 처리하지 않는다.

## 2026-07-22 OP-011/012 연구보고서 보강

- 단계/과제: 구조화 건강 입력; OP-011 개인 프로필과 OP-012 질환·증상·응급 위험 신호 보고서 backfill. 둘 다 `IMPLEMENTED / COMPLETE`다.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `6faeb8fc5d5a61ccd5c02e068c7be2df166176b2e888671c740769778ababb84`.
- 결과: 물리 54개, 유효 32/120, 누락·부적합 88개, 254,619자. completion `76/43/0/1/0`, 최종 감사 `BLOCKED`.
- 검증: 관련 pytest 49건, tracked Ruff, manifest audit, completion check 통과. evidence 2회 동일 SHA-256 `5a8c90de500aa12ff871df36a8bdd2758f6637a730399b803701521e9f8c9873`. 독립 검토 `0/0/0`, CI `29922469760` 성공.
- 변경 경계: 보고서·OP-120 사례·evidence만 변경. 서비스·코드·원천/frozen/학습 데이터·모델·simulation 변경 없음. 256건 7개 지표, weakest slice와 replay delta 0 유지.
- 병목: 보고서 88개, stage gap 43개, OP-039, validation receipt, independent-review receipt. 다음: OP-013/014, OP-015/016, OP-017/018.

## 2026-07-22 OP-009/010 연구보고서 보강

- 선택 단계와 과제: 원본 요구사항 감사 자동화; OP-009 감사 CLI·CI gate와 OP-010 자동 completion report를 기존 구현·테스트·Git 이력에 대조해 한국어 장문 보고서로 backfill했다. 두 항목은 `IMPLEMENTED / COMPLETE`이며 통합·운영·외부검증은 주장하지 않는다.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `345006573b8cbdd16765c16dc6b2dd125154413f664d3012bd8a25af3752e791`.
- 변경 파일: OP-009·010 보고서, OP-120 보고서, OP-120 사례와 canonical evidence. 코드, 서비스, 원천·학습·frozen 데이터, 모델, simulation은 변경하지 않았다.
- 결과: 물리 보고서 52개, 유효 보고서 30개, 누락·부적합 90개, 전체 246,876자. completion은 `76/43/0/1/0`, 최종 감사는 `BLOCKED`다.
- 검증: 관련 계약 pytest `31 passed`; manifest audit PASS `120/119`, issue 0; completion `--check` PASS; tracked Python Ruff PASS. canonical runner 2회 SHA-256 `0b649dd9d14bc13f511a1a369533103838ca083ff68a064988a4552e8246a574`로 동일했다. 전체 Ruff의 `etc/` 33건은 보호된 checkout의 기존 오류이며 tracked 검사 대상에서 제외했다.
- 독립 검토: 최종 `Critical 0 / Important 0 / Minor 0`. reviewer가 report 판정, dataset hash, source/audited commit과 두 번의 evidence hash를 독립 대조했다.
- frozen/replay/slice: 추천 코드와 평가 입력을 바꾸지 않아 이전 256건의 7개 지표 delta, weakest slice, replay delta는 모두 0으로 유지된다. 이번 loop에서 학습이나 simulation을 실행하지 않았다.
- 커밋과 CI: 보고서 `5e16abb`, OP-120 사례 `0978351`, evidence `0b44a5f`; `Original plan evidence` run `29921069084` 성공.
- 남은 병목 5개: 보고서 90개, 비외부 stage gap 43개, OP-039 외부 검증, 전체 validation receipt, 독립 review receipt.
- 다음 세 loop: OP-011/012, OP-013/014, OP-015/016 보고서 backfill.

## 2026-07-22 OP-007/008 연구보고서 backfill

- 선택 단계와 작업: original plan 거버넌스의 OP-007/008 `IMPLEMENTED` 근거를 다시 조사했다. OP-007은 `IMPLEMENTED`, `INTEGRATED`, `OPERATED`, `EXTERNAL` 단계와 최소 evidence 목록을 strict Pydantic schema로 고정한다. OP-008은 파일형 evidence 경로의 저장소 소유권, root 경계, 파일 존재와 Git 추적 여부, 원본 PDF SHA-256을 감사한다.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `0b5e2cb31533798c6281574761723c2fbc71f156e17652f099814e1e2f5c6b5b`.
- 변경 파일: `docs/original_plan/research_reports/OP-007.md`, `OP-008.md`, `OP-120.md`, OP-120 frozen audit case와 canonical evidence. 구현 코드, manifest, 서비스 저장소는 바꾸지 않았다.
- 연구 결과: OP-007은 6,523자, OP-008은 7,507자다. 전체 물리 보고서 파일은 50개, 유효 보고서는 28개, 미작성·부적합 보고서는 92개, 전체 보고서 본문은 233,130자다. OP-007/008은 required stage와 claimed stage가 모두 `IMPLEMENTED`라 COMPLETE다.
- 코드·데이터·학습·시뮬레이션: 코드, 원천·frozen·학습 데이터, 모델, 시뮬레이션 정책, 서비스 저장소를 변경하지 않았다. 공식 frozen evaluation 256건의 일곱 지표 delta는 모두 0이다. replay와 weakest-slice 입력·결과도 바뀌지 않아 delta는 0이다.
- 검증: 관련 manifest·audit·completion 선택 31개 통과, Ruff 통과, manifest audit PASS(120 requirements, 119 claims, 333 evidence files, source hash match), completion check PASS. 독립 검토의 file-field 범위 Minor 1을 고친 뒤 최종 Critical 0 / Important 0 / Minor 0이다.
- canonical evidence: OP-120 evidence를 두 번 생성해 byte-identical SHA-256 `1be4ea55dcca71849aaed7332ee6859fdb419061561177ddf8eb2e7120a4ce01`을 확인했다. 감사 상태는 계속 `BLOCKED`, completion 상태는 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`다.
- 커밋과 CI: `031c913` 보고서, `75a8538` 감사 기대값, `6edb1c0` 검토 수정, `5419fb3` canonical evidence를 push했다. GitHub Actions `Original plan evidence` run `29919479757`이 성공했다.
- 현재 병목 5개: 보고서 92개, required-stage 미달 43건, OP-039 외부 검증, 전체 validation receipt, 전체 독립 감사 receipt.
- 다음 3개 loop: OP-009/010, OP-011/012, OP-013/014 연구보고서 backfill.

## 2026-07-22 OP-005/006 연구보고서 보강 및 KPI-1 분모 수정

- 선택 단계와 작업: original plan의 OP-005/006 `IMPLEMENTED` 근거를 다시 조사하고 각각의 장문 연구보고서를 작성했다. OP-005는 PDF 25~26쪽의 7개 KPI 정의와 현재 계산 경로를 대조했고, OP-006은 요구사항별 소유 저장소·구현·테스트·운영 증거 manifest를 설명했다.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `a552b4418c8c523c5ae8c6ef370a1b521be9fe59363d8625f35563c3a3bbfbce`.
- 변경 파일: `docs/original_plan/research_reports/OP-005.md`, `OP-006.md`, `OP-120.md`, OP-120 감사 데이터·evidence, `src/wellnessbox_rnd/interim/kpi.py`, `src/wellnessbox_rnd/interim/reports.py`, 관련 테스트와 감사 문서, 그리고 KPI 코드의 source identity를 포함하는 OP-055/056·OP-099/100 evidence를 갱신했다.
- 코드 수정: 빈 추천 reference와 빈 예측을 100점으로 처리하던 KPI-1 결함을 fail-closed로 고쳤다. 직접 계산은 빈 reference를 거부하고, 집계는 빈 reference 1,456건을 분모에서 제외해 유효 3,544건만 평가한다. 전체 입력 5,000건과 제외 1,456건은 결과 details에 남는다.
- 데이터·학습·시뮬레이션: 원천 데이터, 학습 데이터, 모델, 시뮬레이션 정책은 바꾸지 않았다. KPI-1 프록시 점수는 유효 표본에서 100%로 유지되지만 보고 표본 수는 5,000에서 3,544로 바로잡혔다. frozen evaluation 256건의 7개 지표, replay, weakest slice delta는 모두 0이다.
- 검증: 관련 선택 테스트 38개, 후속 OP-055/056 테스트 24개, OP-099/100 테스트 15개와 OP-120 계약 테스트 9개가 통과했다. Ruff, manifest audit, completion check, diff 검사가 통과했다. 독립 재검토는 Critical 0 / Important 0 / Minor 0이다.
- 결과: 연구보고서는 유효 26개, 미작성 94개, 물리 파일 48개다. completion 상태는 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`로 유지된다. 최종 OP-120 evidence SHA-256은 `6d761eba95504e84b5de02fe1efdca62604cdad2235d4fecfff9db1c7e3e6b71`이다.
- 배포 확인: source/report `468f2ca`, KPI 수정 `06031be`, 최초 감사 `47980fc`, 연쇄 source-identity 정리 `336f851`, `6bc3d0e`, `32f3eb1`, `8e67412`를 push했다. GitHub Actions `Original plan evidence` run `29917930551`이 성공했다.
- 현재 병목 5개: 연구보고서 94개 미작성, required-stage 미달 43건, OP-039 외부 검증 부재, 실제 운영 validation receipt 부재, 최종 전체 120개 독립 감사 receipt 부재.
- 다음 3개 bounded loop: OP-007/008 보고서, OP-009/010 보고서, OP-011/012 보고서 backfill.

## 2026-07-22 OP-120 bounded loop

- OP-120 최종 완료 감사기를 구현했다. 요구 단계, 외부 검증, 연구보고서, canonical evidence, 최종 검증 영수증과 독립 검토 영수증을 모두 통과해야 `READY`가 된다.
- OP-120은 `IMPLEMENTED / PARTIAL`이다. 전체 상태는 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, 감사 주장은 119건이다. 보고서 파일은 42개지만 강화된 검증을 통과한 보고서는 `20/120`이다.
- 고정 데이터셋은 8건이다. SHA-256은 `e6506727ab9a01a65e53f4de27ed4383e0a6419e29832e081ae1bb0dd2ff3883`이다.
- 현재 감사는 `BLOCKED`다. required stage 부족 43건, OP-039 외부 검증, 누락·부적합 보고서 100건, 최종 검증·독립 검토 영수증이 남았다.
- frozen·학습·모델·safety·replay·weakest slice delta는 모두 0이다.
- 검증된 구현·증거 HEAD는 `914c4572e23e385fe34f0b1f9362137fa6118f7b`이며 GitHub Actions `29911825838`이 성공했다. 독립 검토는 Critical 0, Important 0, Minor 1이다.

## 2026-07-22 deployment-contract and endpoint-inventory loop

- Chosen stage/tasks: `original plan / production service integration`, OP-101 and OP-102.
- Dataset/cases: `data/original_plan/op101_op102_deployment_contract_endpoint_cases_v1.json` contains `8` Git-blob-pinned cases. Canonical evidence is `data/original_plan/evidence/op101_op102_deployment_contract_endpoint_smoke_v1.json`, SHA-256 `5F5DB9FF4157BD183F96A647ABC4866DF57F159CF54473DA89A282D95091F108`; source identity is commit `98345fce92b1f6b94e8a203c1b8f6b77290365b5`.
- Implementation: staging/production startup now requires a fail-closed deployment target/ID, code SHA matching an image-build identity file, absolute SQLite path with provider-persistent-volume declaration, one actual worker across both aliases, provider secret reference, and a complex 32-byte internal token. Public health exposes only contract status and a route-derived inventory for health, recommendation, state machine, device, and counseling.
- Integration evidence: two separate localhost API processes reused one absolute SQLite database. Health/recommendation/device returned 200, unauthorized interim access returned 401, state-machine/counseling routes reached request validation at 422, and a post-restart device replay returned the original session with one persisted row.
- Evidence stage: OP-101 and OP-102 are both `INTEGRATED / PARTIAL` versus required `OPERATED`. No provider deployment, public URL, production volume, provider secret injection, or production traffic is claimed.
- Research reports: OP-079 through OP-102 have separate prose reports. Coverage is `24/120`; `96` remain. Total text is `168,510` characters. OP-101 has `4,523` characters and OP-102 has `4,660` characters.
- Generated status: complete `70`, partial `31`, pending `18`, external `1`, contradicted `0`; audit PASS with `101` claims and `279` checked evidence files.
- Validation: focused deployment/API/state/device/chat selection `127 passed`; final CI exact selection `696 passed, 2 skipped`; tracked-Python Ruff, canonical smoke, audit, and completion check PASS. Full regression collected `1,138`: `1,061 passed`, `77` known absent-artifact/CGM failures. Frozen evaluation has `256` cases and seven zero metric deltas. Independent review moved from Critical `0`, Important `5`, Minor `0` through packaging/data/FastAPI-version checks to final `0/0/0`.
- Frozen-data/training/simulation delta: no frozen dataset, model training, simulation policy, safety rule, or service-repository change. Replay/slice metrics and weakest categories remain unchanged.
- Publication: R&D source/evidence HEAD `8eab198cbb76ff0ca643e396e238840e0ce464ff` is on `origin/main`; Original plan evidence run `29888020924` passed. The service remains at `a24b6c3308cc76627c3ca29807db1705e32c2178`, and its pre-existing user changes were preserved.
- Next loops: OP-103/104 environment-variable and result-origin contracts without provider mutation; OP-105/106 profile roundtrip and review-queue integration; OP-001 through OP-078 report backfill.

## 2026-07-22 device-event deduplication and linkage-macro loop

- Chosen stage/tasks: `original plan / wearable·CGM·genetic integration`, OP-099 and OP-100.
- Dataset/cases: `data/original_plan/op099_op100_device_dedup_linkage_cases_v1.json` contains `7` frozen cases. Canonical evidence is `data/original_plan/evidence/op099_op100_device_dedup_linkage_smoke_v1.json`, SHA-256 `7C11B895B37BF42CACCAAAC05B8B492A20015A2DBACBF02678785DC585ABFE4C`; source identity is commit `029f606ed5191d34132fe78e3b21fef8d88cd75f`.
- Implementation: a canonical JSON tuple of profile/source/provider record identifies events independently of retry session IDs. Exact replay returns the first session, changed payload and reused session identities return 409, invalid timezone-aware observation times fail, and immutable schema-v14 receipts preserve the denominator. Production W/C/G rates read immutable receipts and use equal-weight macro averaging.
- Evidence stage: OP-099 is implemented but PARTIAL versus required `OPERATED`; no real provider traffic or production operation is claimed. OP-100 is COMPLETE at required `IMPLEMENTED`.
- Research reports: OP-079 through OP-100 have separate prose reports. Coverage is `22/120`; `98` remain. Total text is `159,327` characters. OP-099 has `4,141` characters and OP-100 has `4,079` characters.
- Generated status: complete `70`, partial `29`, pending `20`, external `1`, contradicted `0`; audit PASS with `99` claims and `272` checked evidence files.
- Validation: focused connector/KPI/API/agent selection `49 passed`; final CI exact selection `681 passed, 2 skipped`; canonical smoke, tracked-Python Ruff, audit, completion check PASS. Full regression collected `1,124`: `1,029 passed`, `95` known absent-artifact/CGM failures. Frozen evaluation has `256` cases and seven zero metric deltas. Independent review initially found Critical `0`, Important `4`, Minor `2`; all findings were fixed and final review is `0/0/0`.
- Frozen-data/training/simulation delta: no frozen dataset, model training, simulation policy, safety rule, or service repository change. Weakest categories remain unchanged.
- Publication: R&D source/evidence through `cb75d92410f2e95c0076476dcd70e4c7cb385838` is on `origin/main`; Original plan evidence run `29886594091` passed. The service remains at `a24b6c3308cc76627c3ca29807db1705e32c2178`, and its pre-existing user changes were preserved.
- Next loops: OP-101/102 deployment contracts without public deployment; OP-103/104 service environment and two-process contracts without production mutation; OP-001 through OP-078 report backfill.

## 2026-07-22 device-value follow-up and data-class loop

- Chosen stage/tasks: `original plan / wearable·CGM·genetic integration`, OP-097 and OP-098.
- Dataset/cases: `data/original_plan/op097_op098_device_followup_data_class_cases_v1.json` contains `7` frozen cases. Canonical evidence is `data/original_plan/evidence/op097_op098_device_followup_data_class_smoke_v1.json`, SHA-256 `20C3B6FEE428E2AFB12E97ED6A51532EA3ED624374695177A14E2BACD10DC635`; final source identity is commit `7dde4d66b6f56ac60eac4914d7e4251a54e001bb`.
- Implementation: authenticated device assessments call the real recommendation engine, persist wearable/CGM score snapshots, and calculate follow-up value/score deltas plus candidate entry/exit. Explicit service subject IDs and storage consent for every used source are required. Production-device and simulation-fixture class/origin pairs cannot cross, and follow-ups cannot cross profile, class, or origin.
- Evidence stage: OP-097 is COMPLETE at required `INTEGRATED`. OP-098 is implemented but remains PARTIAL because its required stage is `OPERATED`; no production provider traffic, deployment, or operation is claimed.
- Research reports: OP-079 through OP-098 have separate full-prose reports. Coverage is `20/120`; `100` remain. Total text is `151,107` characters. OP-097 has `4,948` characters and OP-098 has `5,225` characters.
- Generated status: complete `69`, partial `28`, pending `22`, external `1`, contradicted `0`; audit PASS with `97` claims and `266` checked evidence files.
- Validation: focused device/consent/store/API selection `75 passed`; CI exact selection `669 passed, 1 skipped`; Ruff and every canonical smoke PASS. Full regression collected `1,115`: `1,020 passed`, `95 failed`, all outside this change in absent historical report artifacts and the known CGM geometry group. Frozen evaluation has `256` cases, seven zero metric deltas, and unchanged weakest categories.
- Independent review: initial Critical `0`, Important `2`, Minor `2`; storage-consent, explicit-subject, origin-claim wording, and candidate-set transition findings were fixed. Final result is Critical `0`, Important `0`, Minor `0`.
- Publication: implementation/evidence HEAD `b96d642d2f1b68ab867b1e064719aadc214a0aa8` is on `origin/main`; final CI run `29885050044` passed. The service remains at `a24b6c3308cc76627c3ca29807db1705e32c2178`, and its pre-existing user changes were preserved.
- Next loops: OP-099/100 duplicate-event blocking and production-only W/C/G macro evaluation; OP-101/102 deployment contracts without public deployment; OP-001 through OP-078 report backfill.

## 2026-07-22 sensor-file partial-success and lineage loop

- Chosen stage/tasks: `original plan / wearable·CGM·genetic integration`, OP-095 and OP-096.
- Dataset/cases: `data/original_plan/op095_op096_sensor_file_ingestion_cases_v1.json` contains `7` frozen cases. Canonical evidence is `data/original_plan/evidence/op095_op096_sensor_file_ingestion_lineage_smoke_v1.json`, SHA-256 `882CD29412BAE087FB77D32DC8B6A0A620947CAD748245861176C33D16DF4206`; implementation source identity is commit `d25279ea200b5954391ea7088aae368ef83fceb7`.
- Implementation: the authenticated API returns per-file schema failures and total/success/failure/normalized/persisted counts. Exact raw-byte and canonical normalized-result hashes share an append-only SQLite lineage row. Consent denial skips decode/hash/storage; storage denial skips persistence; raw content is never stored; exact replay deduplicates.
- Evidence stage: OP-095 is COMPLETE at required `IMPLEMENTED`. OP-096 is implemented locally but remains PARTIAL because its required stage is `OPERATED`; no deployment, production traffic, production database, backup recovery, or operating evidence is claimed.
- Research reports: OP-079 through OP-096 have separate full-prose reports. Coverage is `18/120`; `102` remain. Total text is `140,934` characters. OP-095 has `4,528` characters and OP-096 has `5,032` characters.
- Generated status: complete `68`, partial `27`, pending `24`, external `1`, contradicted `0`; audit PASS with `95` claims and `261` checked evidence files.
- Validation: focused selection `94 passed`; CI exact selection `659 passed, 1 skipped`; Ruff PASS; every canonical smoke PASS. Full regression collected `1,105`: `1,010 passed`, `95 failed`; failures remain outside this change in absent historical report artifacts and the known CGM geometry group. Frozen evaluation has `256` cases, seven zero metric deltas, and unchanged weakest categories. Independent review initially found Important `2` and Minor `1`, all in report wording; corrections left Critical `0`, Important `0`, Minor `0`.
- Publication: R&D HEAD `3af7bf7d4301a42e8787fc47478d45bf457d57b7` is on `origin/main`; final CI run `29883787699` passed. The service remains at `a24b6c3308cc76627c3ca29807db1705e32c2178`, and its pre-existing user changes were preserved.
- Next loops: OP-097/098 device score/follow-up integration and production-vs-simulation data class; OP-099/100 event deduplication and source macro evaluation; OP-001 through OP-078 report backfill.

## 2026-07-22 genetic normalization and consent boundary loop

- Chosen stage/tasks: `original plan / wearable·CGM·genetic integration`, OP-093 and OP-094.
- Dataset/cases: `data/original_plan/op093_op094_genetic_normalization_consent_cases_v1.json` contains `8` frozen cases for alias normalization, deterministic ordering, legacy tags, missing/invalid/conflicting provenance, recommendation denial, and persistent-storage denial/allowance. Canonical evidence is `data/original_plan/evidence/op093_op094_genetic_normalization_consent_smoke_v1.json`, SHA-256 `A1F6264F19728A1C1697704CF03C412ACDF563AAA33481E1D13D4285121B9A24`; source identity is commit `7ebac677f7e54c6935ce789f4261fd71028c3cab`.
- Reuse/integration: the implementation extends the existing sensor/genetic snapshot, parser, intake consent gate, bounded candidate scoring, and source-partitioned Data Lake profile snapshot. It adds no genetic provider, variant database, diagnostic engine, or parallel persistence path.
- Implementation: each structured variant requires normalized gene, variant identifier, genotype, bounded interpretation, interpretation criterion, testing laboratory, and ISO test date. Conflicting aliases, duplicate variants, unsupported interpretations, missing provenance, non-string text fields, and invalid dates fail closed. Recommendation denial removes tags and variants before hashing/scoring; storage denial excludes them from actual SQLite profile persistence.
- Evidence stage: OP-093 and OP-094 are COMPLETE at required `IMPLEMENTED`. No laboratory/provider integration, raw genetic-file ingestion, deployment, production operation, medical reinterpretation, external privacy review, or model training is claimed.
- Research reports: OP-079 through OP-094 have separate full-prose reports. Coverage is `16/120`; `104` remain. The sixteen reports total `131,374` characters. OP-093 has `5,642` characters and OP-094 has `5,687` characters.
- Generated status: complete `67`, partial `26`, pending `26`, external `1`, contradicted `0`; audit PASS with `93` claims and `257` checked evidence files.
- Validation: focused and completion-contract selection `97 passed`; CI exact selection `650 passed, 1 skipped`; tracked-Python Ruff passed; all canonical workflow evidence passed. Full suite collected `1,096`: `1,019 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM groups. Frozen evaluation has `256` cases, seven zero metric deltas, and unchanged overall and metric-specific weakest categories.
- Independent review: the first review found Important `1` because non-string provenance was coerced to text. Strict type rejection and regressions fixed it. Final review is Critical `0`, Important `0`, Minor `0`.
- Publication: implementation/evidence HEAD `2750d136128920f4408874131c4c1467bfb5aa65` is on `origin/main`. CI run `29882285639` exposed stale downstream source identities; all affected canonical evidence was regenerated against the clean service checkout. `Original plan evidence` run `29882424484` then passed every step.
- Next loops: OP-095/096 partial-success and raw-file lineage; OP-097/098 device-value integration and data-class boundary; evidence-grounded OP-001 through OP-078 report backfill.

## 2026-07-22 sensor normalization and fail-closed alias loop

- Chosen stage/tasks: `original plan / sensor integration`, OP-091 and OP-092.
- Dataset/cases: `data/original_plan/op091_op092_sensor_daily_normalization_cases_v1.json` contains `8` frozen cases for Fitbit, Apple Health, and continuous glucose monitoring (CGM) daily summaries. Canonical evidence is `data/original_plan/evidence/op091_op092_sensor_daily_normalization_smoke_v1.json`, SHA-256 `82C016013D247BE2A992E91872C93D986374705B3E2B325A3A4BEC272685C860`; source identity is commit `603eeb1993ec4f02edcf21bd4cb1898603714486`.
- Reuse/integration: the implementation extends the existing sensor parser, file-schema validation, canonical evidence workflow, requirement manifest, and completion generator. It adds no provider client, raw-series store, parallel sensor model, or production ingestion route.
- Implementation: glucose means and postprandial peak/rise aliases compare only after unit normalization. Conflicting standardized, generic, explicit, or duplicate aliases fail closed. Generic time-in-range values require explicit 70/180 bounds. Apple Health step count accepts only `count`; resting heart rate accepts the bounded rate-unit allowlist. Repository-relative test paths now work on Linux CI as well as Windows.
- Evidence stage: OP-091 and OP-092 are COMPLETE at required `IMPLEMENTED`. No Apple Health API call, CGM-provider call, raw time-series ingestion, deployment, production operation, external validation, or model training is claimed.
- Research reports: OP-079 through OP-092 have separate full-prose reports. Coverage is `14/120`; `106` remain. The fourteen reports total `120,045` characters. OP-091 has `8,671` characters and OP-092 has `9,035` characters.
- Generated status: complete `65`, partial `26`, pending `28`, external `1`, contradicted `0`; audit PASS with `91` claims and `255` checked evidence files.
- Validation: focused sensor/schema tests `24 passed`; local workflow-equivalent selection `642 passed`; final CI exact selection and every canonical smoke passed; tracked-Python Ruff passed. Full suite collected `1,086`: `1,009 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM groups. Frozen evaluation has `256` cases, seven zero metric deltas, and unchanged overall and metric-specific weakest categories. Independent review ended Critical `0`, Important `0`, Minor `0`.
- Publication: R&D implementation/evidence HEAD `9f4bbbd36ecef532112cf55792b55da1ab195b7a` is on `origin/main`. Earlier CI runs exposed stale downstream source identities, a dirty service-checkout product hash, and Windows-only test working directories; each cause was corrected. `Original plan evidence` run `29881297071` passed in full.
- Next loops: OP-093/094 genetic normalization and consent gating; OP-095/096 partial-result and raw-hash lineage; evidence-grounded OP-001 through OP-078 report backfill.

## 2026-07-22 counseling fallback and frozen API E2E loop

- Chosen stage/tasks: `original plan / counseling RAG`, OP-089 and OP-090.
- Dataset/cases: frozen counseling QA has `8` cases covering two interaction questions, two goal questions, citation structure, unsupported cure claims, out-of-scope weather, and urgent chest pain with breathing difficulty. The canonical smoke uses a real localhost FastAPI process, the real WellnessBox TypeScript client, a local 503 provider, and two fresh SQLite databases. Canonical SHA-256 is `49a3152436fb59e392110999729e82ae64360dd86cf430d7345f6a128577394d`; R&D source commit is `d1273da965da098f8689434e9b140a83bb285cd7`; service source commit is `a24b6c3308cc76627c3ca29807db1705e32c2178`.
- Reuse/integration: the implementation extends the existing bounded retrieval, answer verifier, `agent_runs`, `agent_steps`, `recommendation_runs`, interim API, and service R&D client. It adds no parallel counseling engine, event store, recommendation store, or service chat route.
- Implementation: provider failure returns a structured deterministic fallback snapshot. External health-query processing requires explicit `counseling:external-provider` consent. Same-turn requests are serialized across threads and supported multi-worker processes with a database-scoped byte-range lock, and every retry returns the durable stored binding. Full answers, verifier results, and direct code/data dependencies are included in deterministic and source-identity checks.
- Independent review: the first review found Important `4`; subsequent reviews found the multi-worker lock gap, memory retention, and three source-identity omissions. Every finding was fixed. Final review is Critical `0`, Important `0`, Minor `0`.
- Evidence stage: OP-089 is COMPLETE at required `IMPLEMENTED`. OP-090 is `IMPLEMENTED` and PARTIAL against required `INTEGRATED`; the real service client and R&D HTTP API ran, but `/api/chat`, an isolated Prisma database, public deployment, and production traffic were not observed.
- Research reports: OP-079 through OP-090 now have separate full-prose reports. Coverage is `12/120`; `108` remain. The twelve reports total `102,339` characters. OP-089 has `9,793` characters and OP-090 has `12,150` characters.
- Generated status: complete `63`, partial `26`, pending `30`, external `1`, contradicted `0`; audit PASS with `89` claims and `253` checked evidence files.
- Validation: focused interim API `25 passed`; exact workflow pytest selection `618 passed`; all `28` workflow canonical smokes and tracked-Python Ruff passed. Service build, typecheck, ESLint, and adapter QA passed. Full suite collected `1,074`: `997 passed`, `77 failed`, with the unchanged `73` absent-report plus `4` CGM groups. Frozen evaluation has `256` cases, seven zero metric deltas, and unchanged overall and metric-specific weakest categories.
- Publication: service source commit `a24b6c3308cc76627c3ca29807db1705e32c2178` and R&D source/evidence commit `5593c6a0af6ef397e1eeb54a34172fd356476884` are on `origin/main`. CI run `29850808600` exposed a dirty-local-service source hash in OP-049/050 evidence; clean-checkout regeneration fixed it. `Original plan evidence` run `29878812400` then passed all steps.
- Next loops: implement OP-091/092 and continue evidence-grounded full-prose backfill for OP-001 through OP-078.

## 2026-07-22 counseling session and service-adapter loop

- Chosen stage/tasks: `original plan / counseling RAG`, OP-087 and OP-088.
- Dataset/cases: the existing counseling corpus contains `24` passages from `19` sources. The canonical smoke starts a real localhost FastAPI process and calls it through the real WellnessBox TypeScript adapter. Two normalized executions are byte-identical. Canonical SHA-256 is `729f61d599590870df9aa6e2c18948a72523461e2b597021adb02646ef93984d`; R&D source commit is `8c5f1f0fdf9f62acd3f7f94dc45ce1f5d3e9d8c2`; service source commit is `f78604c74795c127a004a7be64cb67c7fe112803`.
- Reuse/integration: the implementation reuses `execution_events`, `agent_runs`, `agent_steps`, `recommendation_runs`, the existing interim recommendation path, `/api/chat`, `ChatSession`, `ChatMessage`, and the existing internal-token client. It adds no parallel event store, recommendation engine, counseling database, or chat route.
- Implementation: the new R&D turn route binds one stable service session and turn to a bounded answer, verifier result, recommendation run, and stored binding hash. Full semantic request hashing rejects changed same-turn replays before profile mutation. Nullable idempotency identities preserve historical recommendation rows while serializing new concurrent inserts. The service maps the actual `UserProfile` contract into a strict allowlist, uses conservative pregnancy and safety flags, pseudonymizes subjects, and atomically merges counseling metadata into the existing chat tables.
- Independent review: successive reviews found one Critical and ten Important defects across cross-session message IDs, semantic replay, concurrent inserts, profile over-sharing, consent claims, missing binding persistence, non-atomic writes, unstable retry timestamps, historical migration compatibility, and actual profile-field mapping. Every finding was fixed. Final review is Critical `0`, Important `0`, Minor `0`.
- Evidence stage: OP-087 and OP-088 are both `IMPLEMENTED` and PARTIAL. OP-087 requires `OPERATED`, but no production operation was observed. OP-088 requires `INTEGRATED`, but canonical evidence calls the service adapter directly and does not exercise `/api/chat` plus an isolated Prisma database. No deployment, production traffic, service database write, external medical validation, or live provider inference is claimed.
- Research reports: separate full-prose reports now exist for OP-079 through OP-088. Coverage is `10/120`; `110` remain. The ten reports total `80,291` characters. OP-087 has `11,381` characters and OP-088 has `9,862` characters.
- Generated status: complete `62`, partial `25`, pending `32`, external `1`, contradicted `0`; audit PASS with `87` claims and `249` checked evidence files.
- Validation: focused counseling/audit tests passed; exact workflow pytest selection `613 passed`; full Ruff PASS; completion check PASS; canonical smoke is byte-identical across reruns. The full suite is `992 passed`, `77 failed`; the failures remain the known absent-report and CGM groups, with no new failure group.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: WellnessBox service commit `f78604c74795c127a004a7be64cb67c7fe112803` and R&D source/evidence commit `9f7a71c9fc96f265ed554a1e179a87c3c58dbc2e` are on `origin/main`. GitHub Actions `Original plan evidence` run `29848036378` passed all `27` canonical smokes, the exact contract-test selection, and workflow lint.
- Next loops: implement OP-089/090 while separately backfilling evidence-grounded reports for OP-001 through OP-078.

## 2026-07-21 counseling verifier and urgent-safety loop

- Chosen stage/tasks: `original plan / counseling RAG`, OP-085 and OP-086.
- Dataset/cases: the existing counseling corpus contains `24` passages from `19` sources. The canonical smoke covers supported and urgent answers, explicit negation, contrast clauses, `5` common urgent phrasings, a service-working-directory policy load, and `7` independent tamper/policy probes. Frozen evaluation remains `256` cases. Canonical SHA-256 is `e7dcfe8248d7ba73769efd618cd29cb3deb99675df8ee4e5af5aff54280d2a36`; source commit is `c6ca444488e7af34b416e3da208016972010315d`; source SHA-256 is `14022f4617560b4ae386c047eddb88269903b463fdbd2414edac7f9af9528b9c`.
- Reuse/integration: reused the existing question-entity extractor, bounded retrieval scope, passage manifest, answer/citation contract, and OpenAI adapter. No parallel chat service, retrieval store, evidence registry, or emergency classifier was added.
- Implementation: the provider can select only a status and approved chunk identity; the server owns final prose. The verifier recomputes repository policy identity, question-to-evidence relevance, exact template grounding, required interaction risk, forbidden expressions, emergency precedence, evidence validity, uncertainty, and the request's minimum support score. Positive urgent signals return deterministic safety guidance before retrieval or provider use. Common chest-pain/breathing phrasings, negation, and contrast clauses are explicit regressions.
- Independent review: the first review found two Critical and one Important issue: common urgent phrasings were missed, a provider-selected unrelated chunk could pass verification, and policy loading depended on the current working directory. The second review found one fail-closed Minor around a non-default support threshold. All were fixed. Final review is Critical `0`, Important `0`, Minor `0`.
- Evidence stage: OP-085 and OP-086 are COMPLETE at required stage `IMPLEMENTED`. No WellnessBox service change, service integration, deployment, production operation, external medical validation, live provider inference, model training, or frozen-data change is claimed.
- Research reports: separate full-prose reports now exist for OP-079 through OP-086. Coverage is `8/120`; `112` remain. The eight reports total `48,961` UTF-8 characters. OP-085 has `6,647` characters and OP-086 has `7,308` characters and both include the independent-review failures and corrections.
- Generated status: complete `62`, partial `23`, pending `34`, external `1`, contradicted `0`; audit PASS with `85` claims and `242` checked evidence files.
- Validation: focused counseling tests `50 passed`; exact workflow selection `609 passed`; `26` workflow canonical smokes passed; full Ruff PASS; source/data hashes independently match; canonical smoke is byte-identical across reruns.
- Full suite: `1,065` collected, `988 passed`, `77 failed`; failures remain exactly the known `73` absent-report and `4` CGM cases, with no new failure group.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: source/evidence HEAD `bfe7c813c80a29c523a9367b2dc291b1df4d5537` was pushed. The first CI run `29841093182` exposed a non-portable smoke service path and failed; the path was fixed to use `WELLNESSBOX_EVIDENCE_ROOT`. GitHub Actions `Original plan evidence` run `29841384466` then passed every step.
- Next loops: OP-087/088, OP-089/090, and OP-091/092, with one full prose report per newly verified requirement and evidence-grounded backfill for OP-001 through OP-078.

## 2026-07-21 bounded RAG answer provenance loop

- Chosen stage/tasks: `original plan / counseling RAG`, OP-083 and OP-084.
- Dataset/cases: the approved counseling scope covers `24` passages from `19` sources. The canonical smoke contains `4` answer cases and `8` independent rejection probes. Frozen evaluation remains `256` cases. Canonical evidence SHA-256 is `cfb10b0bdb9d02fbd1851cddde8b32c914a1ac00929b47f60e514c343fffb04d`; source SHA-256 is `03c86d65261517c360e4120a9d2f3039cc30fa8db568c9bebe431e558e026f5f`.
- Reuse/integration: the implementation reuses the existing counseling passage index, reference registry, runtime knowledge records, and chat adapter. It does not create a second retrieval store, evidence registry, or answer service.
- Implementation: retrieval accepts only the repository-approved scope and filters source type, claim type, reference identifier, effective time, retirement time, and result limit. The server reconstructs citations and uncertainty from approved passages rather than trusting provider-supplied provenance. Contract verification rejects forged scopes, invalid dates, missing or duplicate citations, and mismatches between cited and used passages.
- Evidence stage: OP-083 and OP-084 are `IMPLEMENTED` and COMPLETE at their required `IMPLEMENTED` stage. No WellnessBox service change, deployment, production operation, external validation, live language-model inference, model training, or frozen-data change is claimed.
- Research reports: separate long-form prose reports now exist for OP-079 through OP-084. Coverage is only `6/120`, or 5 percent; `114` reports remain. The six files contain `35,006` UTF-8 characters in total. This count is an explicit incomplete-report backlog, not evidence that 120 reports exist.
- Research-log standard: every OP must end with its own human-readable report. Each report must explain the requirement, prior system, investigation, decision grounds, implementation, failures and corrections, verification, limitations, and operation/external-validation boundary in full prose. A manifest row, test log, evidence JSON, terse bullet list, or abbreviated handoff does not substitute for the report.
- Generated status: complete `60`, partial `23`, pending `36`, external `1`, contradicted `0`; audit PASS with `83` claims and `238` checked evidence files.
- Validation: focused regression `39 passed`; workflow-equivalent selection `596 passed`; `27` canonical smokes reproduced; full Ruff PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `975 passed`, `77 failed`; failures remain exactly `73` absent-report and `4` CGM cases, with no other failure group.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: implementation/evidence HEAD `67d65c3160a004c0ec1f6030a645c3ef9dbda8ee` was pushed; GitHub Actions `Original plan evidence` run `29838281957` passed.
- Next loops: OP-085/086, OP-087/088, and OP-089/090. Each new requirement receives one full prose report, while OP-001 through OP-078 are backfilled from verified evidence rather than reconstructed from summaries.

## 2026-07-21 counseling passage and question-entity loop

- Chosen stage/tasks: `original plan / counseling RAG`, OP-081 and OP-082.
- Dataset/cases: canonical index contains `24` passages from `19` sources; entity smoke contains `9` questions, including `4` urgent cases. Frozen eval remains `256` cases. Evidence SHA-256 is `03c0efdc6110208f4e2e185c17524099d5b8fcdc5f27366cf6bd47c5ecb332f4`; source SHA-256 is `ab6ffef24a9d936a9374d82a3a385943ad7a8b2600999b909ce7bc413d918d68`.
- Reuse/integration: reused the existing reference registry, parsed source files, runtime ingredient/drug aliases, retrieval manifest, and chat adapter. No parallel evidence store, terminology database, or counseling service was added.
- Implementation: every passage preserves source URI, parsed source URI, license status, effective/retired time, and exact source-line span. Asset generation rejects missing references, path escape, metadata mismatch, and source spans that do not contain the declared claim ID and claim text. Question parsing returns exact text spans for health goals, ingredients, drugs, and risk signals. It handles explicit negation locally, does not let negation cross contrast or coordinated propositions, and does not infer a specific subtype from generic magnesium or vitamin-D wording.
- Evidence stage: OP-081 and OP-082 are `IMPLEMENTED` and COMPLETE at their required `IMPLEMENTED` stage. No WellnessBox service change, deployment, production operation, external validation, or LLM inference is claimed.
- Research reports: separate long-form prose reports exist for OP-079 through OP-082. Coverage is `4/120`; 116 reports remain. OP-081 has `6,540` characters and OP-082 has `6,637` characters in the current files; all four reports total `27,023` characters.
- Generated status: complete `58`, partial `23`, pending `38`, external `1`, contradicted `0`; audit PASS with `81` claims and `232` checked evidence files.
- Validation: focused/downstream regression `51 passed`; workflow-equivalent selection `584 passed`; `26` canonical smokes reproduced; full Ruff PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `968 passed`, `77 failed`; failures remain exactly `73` absent-report and `4` CGM geometry cases, with no new failure group.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: implementation/evidence HEAD `fd41644949479fbbc4219eb40fa31d7b4b13a30f` was pushed; GitHub Actions `Original plan evidence` run `29835498939` passed.
- Next loops: OP-083/084, OP-085/086, OP-087/088, while adding a full prose report for every newly verified OP and continuing evidence-grounded backfill.

## 2026-07-21 plan lifecycle and order boundary loop

- Chosen stage/tasks: `original plan / closed-loop execution`, OP-079 and OP-080.
- Dataset/cases: frozen eval `256` cases; canonical smoke `5` API cases. Evidence SHA-256 is `2d51305ff69306061528a7ac0f6becabb6351d6a7025e439885dc73282246308`; source SHA-256 is `53f79c6cabb636782b9be23b5797ae42861890319a642b9848100096883d5a4f`.
- Reuse/integration: reused `execution_events`, `followups`, `workflow_jobs`, active consent snapshots, and the existing interim FastAPI route. No parallel lifecycle store, scheduler, order system, or WellnessBox service route was added.
- Implementation: lifecycle transitions replay from immutable events. Replacement requires one stored recommendation/optimization candidate and pins its event ID and actual payload SHA-256. The transition and consumed candidate resist ledger and direct SQLite mutation, including an existing-database migration path. Lifecycle requests reject order fields and never mutate order state.
- Evidence stage: OP-079 and OP-080 are `IMPLEMENTED`, below required `OPERATED`, so both remain PARTIAL. No deployed R&D process, service call, actual order mutation, or production operation is claimed.
- Research reports: canonical long-form prose reports exist for OP-079 and OP-080. Overall report coverage is `2/120`; the other 118 reports remain to be written from verified evidence.
- Generated status: complete `56`, partial `23`, pending `40`, external `1`, contradicted `0`; audit PASS with `79` claims and `226` checked evidence files.
- Validation: focused lifecycle regression `45 passed`; workflow-equivalent selection `559 passed`; 23 canonical smokes reproduced; full Ruff PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `948 passed`, `77 failed`; failures remain exactly `73` absent-report and `4` CGM geometry cases, with no new failure group.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: implementation/evidence HEAD `fadf80fc68f6bc93817b8111a8f01cd9d7aa8060` was pushed; GitHub Actions `Original plan evidence` run `29832628539` passed.
- Next loops: OP-081/082, OP-083/084, OP-085/086, while continuing evidence-grounded long-form report backfill.

## 2026-07-21 fail-closed jobs and pharmacist-review loop

- Chosen stage/tasks: `original plan / closed-loop execution`, OP-077 and OP-078.
- Dataset/cases: frozen eval `256` cases; canonical smoke `5` cases covering exact duplicate execution, stale evidence, missing consent, worker timeout, and pharmacist-review completion. Evidence SHA-256 is `df67af2cf7ecd9f99edc7a98dcf6a607d633983da8a6f9cd65630973b6a0b2d4`; source SHA-256 is `58746132ddc4d840a479a9fe4075423fff45c4cd4cf9c78a10d431ed74fae978`.
- Reuse/integration: reused `workflow_jobs`, `followups`, `execution_events`, active consent snapshots, `review_tasks`, and the existing FastAPI/admin-review path. No parallel event store, scheduler, review subsystem, or WellnessBox service route was added.
- Implementation: jobs pin active consent and effective execution evidence. Claim and acknowledgement cancel stale, consentless, or timed-out work, close related follow-ups/jobs, and create one deterministic review. Review completion stores a typed decision and hashed postcondition; backdated completion and later UPDATE/DELETE are rejected. Serious-AE exact retries retain the original review ID.
- Evidence stage: OP-077 and OP-078 are `IMPLEMENTED`, below required `OPERATED`, so both remain PARTIAL. No service change, deployment, production worker execution, or pharmacist operation is claimed.
- Generated status: complete `56`, partial `21`, pending `42`, external `1`, contradicted `0`; audit PASS with `77` claims and `220` checked evidence files.
- Validation: focused `59 passed`; workflow-equivalent selection `541 passed`; 22 canonical smokes regenerated; full Ruff PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `930 passed`, `77 failed`; failures remain exactly `73` absent-report and `4` CGM geometry cases, with no new failure group.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: implementation/evidence/docs HEAD `de7f493415618d11a492f782f8bbd20b3939b206` was pushed; GitHub Actions `Original plan evidence` run `29829346647` passed.
- Next loops: OP-079/080, OP-081/082, OP-083/084.

## 2026-07-21 follow-up input decision and serious-AE stop loop

- Chosen stage/tasks: `original plan / closed-loop execution`, OP-075 and OP-076.
- Dataset/cases: frozen eval `256` cases; canonical smoke `3` cases for PRO next-job creation, device next-job creation, and serious-AE immediate stop. Evidence SHA-256 is `847f861085d44916bfcab9c6a51ed2d9048262023c9c8e4b031b716b8285dd97`; source SHA-256 is `4e33d0f4560699ceb9e06eb894671f4312be9fcfd734a85ce60dbce73b4c7a28`.
- Reuse/integration: reused `execution_events`, `followups`, `workflow_jobs`, `agent_runs`, `recommendation_runs`, `review_tasks`, and the existing FastAPI routes. No parallel event store, scheduler, plan registry, or WellnessBox service route was added.
- Implementation: accepted PRO/device revisions create deterministic immediate plan-reevaluation jobs from stored input identity and effective observation time. A serious adverse event records the stop before accepting its PRO event, stops active plan/recommendation/agent work, cancels queued work, creates an urgent review, and blocks later recommendation/run creation. Run creation and the hold check share one `BEGIN IMMEDIATE` transaction.
- Evidence stage: OP-075 and OP-076 are `IMPLEMENTED`, below required `OPERATED`, so both remain PARTIAL. No service change, deployment, production queue execution, or production operation is claimed.
- Generated status: complete `56`, partial `19`, pending `44`, external `1`, contradicted `0`; audit PASS with `75` claims and `216` checked evidence files.
- Validation: focused agent/PRO regression `30 passed`; workflow-equivalent selection `532 passed`; 21 canonical smokes reproduced; full Ruff PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `921 passed`, `77 failed`; failures remain exactly `73` absent-report and `4` CGM geometry cases, with no new failure group.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: implementation/evidence/docs HEAD `b08cc0744b6f662ac23b5a6bc5fc01d419b2a650` was pushed; GitHub Actions `Original plan evidence` run `29827163566` passed.
- Next loops: OP-077/078, OP-079/080, OP-081/082.

## 2026-07-21 follow-up queue and due-plan Cron loop

- Chosen stage/tasks: `original plan / closed-loop execution`, OP-073 and OP-074.
- Dataset/cases: `data/original_plan/evidence/op073_op074_followup_job_queue_cron_smoke_v1.json`; two scheduled follow-ups and four deterministic Cron invocations; SHA-256 `5399806ac1e2af79d8390b4456bf54a6bea8de7b5ca8cf7b0b07b2cc099b3ea2`.
- Reused the existing `followups`, `executions`, `execution_events`, `BoundedAgent`, FastAPI route, and SQLite store. No parallel scheduler, plan registry, event store, or WellnessBox service route was added.
- Implementation: reminders and reevaluations share `workflow_jobs`; each follow-up is linked to a matching active execution-plan event. Workers use atomic claim tokens, leases, expiry recovery, acknowledgement, retry scheduling, and attempt counts. Scheduling, Cron enqueue, and worker claim all reject inactive plans. Closing or discontinuing a follow-up cancels READY/CLAIMED work. Legacy unlinked v9 work is quarantined during schema-v10 migration.
- Evidence stage: OP-073 and OP-074 are `IMPLEMENTED`, below required `OPERATED`, so both remain PARTIAL. No service change, deployment, production queue operation, or deployed CronJob is claimed.
- Generated status: complete `56`, partial `17`, pending `46`, external `1`, contradicted `0`; audit PASS with `73` claims and `214` checked evidence files.
- Validation: focused store/jobs/agent/API `46 passed`; GitHub workflow-equivalent selection `504 passed`; 20 canonical smokes reproduced without diff; full Ruff PASS; deterministic OP-073/074 smoke PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `914 passed`, `77 failed`; failures remain exactly `73` absent-report and `4` CGM geometry cases, with no new failure group.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: final source fix `948aca8`, final OP-073/074 evidence `f661211`, shared-source evidence refresh and pushed HEAD `97a124b035cda1b525a709b2c2bb0d9a1d8da04a`; Original plan evidence run `29824602501` passed.
- Next loops: OP-075/076, OP-077/078, OP-079/080.

Older loop entries are archived in `docs/archive/PROGRESS-archive-1.md`.

## 2026-07-21 closed-loop state and ordered execution loop

- Chosen stage: `original plan / closed-loop execution`; tasks OP-071 and OP-072.
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. Canonical smoke covers success, safety block, missing evidence, forbidden direct movement, and an identical idempotent retry.
- Primary evidence: `data/original_plan/evidence/op071_op072_closed_loop_state_order_smoke_v1.json`; SHA-256 `6bb772f0448722ce8efc6f010160f356b9789f026b76be997cd59e3cd0f607e1`; source SHA-256 `021b82bc4ff11faeb23e79b934431d4af2205a42f96070de450c94c27fca8460`; source commit `26941e94554f21766823c043b635c865257e4646`.
- Implementation: one strict R&D contract owns states, allowed operations, and forbidden transitions. Existing agent, ledger, safety, evidence, ranking, optimization, and interim API paths enforce the complete order. SQLite claims serialize workers, changed-payload idempotency conflicts fail closed, every transition is durable, and no manual-review operation is exposed. No training or simulation behavior changed.
- Evidence boundary: OP-071 and OP-072 prove only `IMPLEMENTED`; both remain PARTIAL below required `OPERATED`. The local plan-start record is an audit marker, not service plan activation. Service integration, deployment, production operation, and real plan execution are not proven.
- Generated status: complete `56`, partial `15`, pending `48`, external `1`, contradicted `0`. Audit PASS with `71` claims and `208` checked evidence files.
- Validation: focused and governance tests `63 passed`; workflow selection `505 passed`, `1 skipped`; full Ruff PASS; all `19` canonical workflow smokes PASS; independent review Critical `0`, Important `0`.
- Full suite: `902 passed`, `77 failed`; the unchanged failures are `73` absent report artifacts and `4` CGM geometry assertions.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: R&D HEAD `61b16929ebd2647438717e450fbceb954e92c140`; Original plan evidence run `29822306554` succeeded. The service repository was not changed.
- Recommended next loops: OP-073/074 follow-up job queue and due-plan CronJob; OP-075/076 next-job decisions and serious-AE stop; OP-077/078 fail-closed jobs and pharmacist review lifecycle.

## 2026-07-21 stock substitution and approval-gated cart integration loop

- Chosen stage: `original plan / product optimization`; tasks OP-069 and OP-070.
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. Canonical evidence compares `8` previous and `4` current combinations after `1` offer disappears, then validates a `3`-item cart candidate under `1` active safety rule and `1` active exclusion.
- Primary evidence: `data/original_plan/evidence/op069_op070_product_combination_stock_cart_smoke_v1.json`; deterministic SHA-256 `9b40f6a05e73e82dde8582f7c0e7e043f9e1481214cd3d825c0d19e03a15e139`; combined source SHA-256 `07f8f483bcc013fd51627f27aa58e0e03c6c8cc208dc987abf987600049830ca`; R&D source `a2ae7a289ae3f0923145db707f3c042e868cd059`; service source `4d904f43b028a35524a29206aaf7c6b99f58a97b`.
- Implementation: the existing `/api/tips` combination path accepts a strict previous replay context, detects missing in-stock offers, and recomputes the current global top combination with the existing bounded optimizer. Previous and current optimization inputs and active safety constraints must match; safety-policy or recommendation-input changes fail closed and suppress the cart candidate. The selected combination is converted to the existing client cart-item shape, while approval remains required and route/adapter source checks exclude cart-storage, Order, OrderItem, and Payment mutations. No new catalog, optimizer, cart store, order system, training path, or simulation path was added.
- Evidence boundary: OP-069 and OP-070 are `INTEGRATED` and COMPLETE at their required stages. Route-function integration is proven. Actual Prisma execution, browser cart mutation, user approval, order/payment creation, production deployment, and production operation are not proven.
- Generated status: complete `56`, partial `13`, pending `50`, external `1`, contradicted `0`. Audit PASS with `69` claims and `203` checked evidence files.
- Validation: focused tests `26 passed`; exact workflow selection `505 passed`; full Ruff PASS; service product QA, typecheck, and focused lint PASS; all `18` service-dependent canonical smokes PASS; independent review after fixes Critical `0`, Important `0`, Minor `0`.
- Full suite: `886 passed`, `77 failed`; the unchanged failures are `73` absent report artifacts and `4` CGM geometry assertions. No OP-069/070 regression was found.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: service commit `4d904f43b028a35524a29206aaf7c6b99f58a97b`; R&D evidence/workflow commit `06debd77c39581c6cbe90beefa3be3095336f606`; Original plan evidence run `29819257210` succeeded.
- Recommended next loops: OP-071/072 unified state-transition contract and ordered orchestration; OP-073/074 shared safety-rule engine and severity classes; OP-075/076 blocking, warning, and monitoring action semantics.

## 2026-07-21 product-combination top-k and reproducibility integration loop

- Chosen stage: `original plan / product optimization`; tasks OP-067 and OP-068.
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. Canonical evidence independently validates `4` evaluated combinations, top-k `3`, and `1` non-selection reason.
- Primary evidence: `data/original_plan/evidence/op067_op068_product_combination_top_k_smoke_v1.json`; deterministic SHA-256 `f510f7c09aea3e23af64275001b53ae6a14b0c45760a3a0a112cb390dd5153ae`; combined source SHA-256 `b78acd6e01dc75eab4dfe18622c975ba810877d6ae3321a5d7847a5452482613`; R&D source `dc8e145b3a62897af6238f2c9b74dd35a75f4714`; service source `a27de7c0beee507114641e24a058827d46ad2ef0`.
- Implementation: the existing `/api/tips` product-combination path now ranks every eligible combination by cost, product count, and deterministic ID before applying the `64`-combination response cap. It returns top-k identities and precise non-selection reasons. Search truncation returns no top-k and reports `SEARCH_TRUNCATED`. Replay identity hashes the complete optimization input and normalized catalog, including offer option, capacity, and mapped safety exclusions. R&D independently recomputes ranking, policy linkage, input hash, catalog version, and result hash. No new catalog, route, database, order, payment, training, or simulation path was added.
- Evidence boundary: OP-067 and OP-068 are `INTEGRATED` and COMPLETE at their required stages. Route-function integration is proven; actual Prisma execution, production catalog freshness, deployment, production operation, ordering, and payment are not proven.
- Generated status: complete `54`, partial `13`, pending `52`, external `1`, contradicted `0`. Audit PASS with `67` claims and `200` checked evidence files.
- Validation: focused tests `20 passed`; exact workflow tests `499 passed`; full Ruff PASS; service product QA, typecheck, and lint PASS; all `17` service-dependent canonical smokes PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `880 passed`, `77 failed`; the unchanged failures are `73` absent report artifacts and `4` CGM geometry assertions. No OP-067/068 regression was found.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: service commit `a27de7c0beee507114641e24a058827d46ad2ef0`; R&D implementation commit `0635b17c2dd18c9f861c012c5f865fb5f720abf3`; Original plan evidence run `29816477275` succeeded.
- Recommended next loops: OP-069/070 stock-aware safe substitution and approval-gated cart candidates; OP-071/072 unified state-transition contract and ordered orchestration; OP-073/074 safety-rule engine and severity classes.

## 2026-07-21 product-combination constraint and safety integration loop

- Chosen stage: `original plan / product optimization`; tasks OP-065 and OP-066.
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. Canonical evidence evaluates `4` materialized combinations for budget/product-count filtering, `1` product-side safety exclusion, and `1` actual localhost R&D-to-service constraint response.
- Primary evidence: `data/original_plan/evidence/op065_op066_product_combination_filter_smoke_v1.json`; deterministic SHA-256 `87c16d1e39d2a7ea9b64f16ba46f0bcb5946da8265aa87c75e40a53611de2a3f`; combined source SHA-256 `ace71663d00cb8999affafc0cd2fad9c24ccc3390264bba0a895fb1703ead1c0`; R&D source `275674c5d667e4a76f42dd6aa62dbcadf5baec50`; service source `7f248485f522fd85ca09a71a9252cf1ec8dc5896`.
- Implementation: the existing R&D request and service `/api/tips` path now carry strict budget, maximum-product, excluded-ingredient, and safety-rule constraints. The existing bounded product-combination search filters materialized combinations before its eligible-result cap. Product side ingredients are included in safety exclusion, excluded recommendations fail closed, and zero-recommendation blocked responses are contract-validated before return. No parallel catalog, optimizer, route, database, order, payment, training, or simulation path was added.
- Evidence boundary: OP-065 and OP-066 are `INTEGRATED` and COMPLETE at their required stages. The localhost blocked-response path is proven. An actual READY R&D filter path, Prisma execution, production catalog freshness, deployment, production operation, ordering, and payment are not proven.
- Generated status: complete `52`, partial `13`, pending `54`, external `1`, contradicted `0`. Audit PASS with `65` claims and `198` checked evidence files.
- Validation: focused tests `27 passed`; exact workflow tests `492 passed`; full Ruff PASS; service product QA, typecheck, and lint PASS; all `16` canonical smokes PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `873 passed`, `77 failed`; the unchanged failures are `73` absent report artifacts and `4` CGM geometry assertions. No OP-065/066 regression was found.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and every metric-specific weakest category is unchanged.
- Publication: service commit `7f248485f522fd85ca09a71a9252cf1ec8dc5896` passed Encoding Guard run `29813747636`. R&D commit `c085d467a6447316fc865b84996e6085fa7b928d` passed Original plan evidence run `29813998092`.
- Recommended next loops: OP-067/068 top-k explanations and deterministic reproduction; OP-069/070 stock-aware safe substitution and approval-gated cart candidates; OP-071/072 unified state-transition contract and ordered orchestration.

## 2026-07-21 product combination and aggregate-dose integration loop

- Chosen stage: `original plan / product optimization`; tasks OP-063 and OP-064.
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. The service fixture contains `7` products for `8` recommendations; canonical evidence contains `4` generated combinations and independently validates `2` representative combinations.
- Primary evidence: `data/original_plan/evidence/op063_op064_product_combination_dose_smoke_v1.json`; deterministic SHA-256 `64821bf96e724cfcb21be2b4e0d011dd3c364b072614ca7505dda8659b1e9ea8`; combined source SHA-256 `3c48c1b8fecac69e3b8b088830e0efa7c6bcc4b9784f81af72a0dcc39d69ce05`; R&D source `00fbd06f275e7ba2a486e398fdd56591388df6ad`; service source `6c599ebeebca73e8d769426b02f12d4e7be19073`.
- Implementation: the existing `/api/tips` product-candidate adapter now converts strict catalog declarations into deterministic product combinations. It reuses the lowest-priced in-stock offer, deduplicates shared products, normalizes fractional mass and IU values to exact integer base units, totals declared doses by ingredient and unit, and detects duplicate ingredients across distinct products. Memoized search is bounded to `4096` states and `64` unique combinations. Missing target amounts and ambiguous ranges fail closed. R&D independently validates every returned identity, product, offer, cost, total, duplicate, and search boundary. No new catalog, route, database, order, payment, training, or simulation system was added.
- Evidence boundary: OP-063 and OP-064 are `INTEGRATED` and COMPLETE at their required stages. Actual Prisma execution, production data freshness, deployment, production operation, ordering, and payment remain unproven.
- Generated status: complete `50`, partial `13`, pending `56`, external `1`, contradicted `0`. Audit PASS with `63` claims and `196` checked evidence files.
- Validation: focused tests `10 passed`; exact workflow tests `482 passed`; full Ruff PASS; service product QA, typecheck, lint, and production build PASS; all `15` canonical smokes reproduce byte-identically; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `863 passed`, `77 failed`; the unchanged failures are `73` absent report artifacts and `4` CGM geometry assertions. No OP-063/064 regression was found.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; the overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: service commit `6c599ebeebca73e8d769426b02f12d4e7be19073` passed Encoding Guard run `29811071339`. R&D commit `23d5c43efc8b029f78c2f62c92665bc5960307de` passed Original plan evidence run `29811445770`.
- Recommended next loops: OP-065/066 budget/product-count pruning and safety-block preservation; OP-067/068 top-k explanations and deterministic reproduction; OP-069/070 stock-aware safe substitution and pre-approval cart candidates.

## 2026-07-21 optimization constraints and selling-product contract loop

- Chosen stage: `original plan / product optimization`; tasks OP-061 and OP-062.
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. Canonical evidence evaluates `6` deterministic constraint cases and the existing service product-candidate QA fixture covers all `8` mapped service ingredient IDs.
- Primary evidence: `data/original_plan/evidence/op061_op062_optimization_product_catalog_smoke_v1.json`; deterministic SHA-256 `aaa917bb4256e648d62fa12564353c26fe01717cb38360aa23e0495e1f22f480`; combined source SHA-256 `83118c67e45f96e6eba41e6ee853977278da8d9a8043239ca35bb3d97da10429`; R&D source `ea3bc72484708002065ee4929dc62ca006ce980c`; service source `a85767d9dc9418a23a9adeb2372d14a75d10b865`.
- Implementation: the existing optimizer package now has an immutable, versioned contract for efficacy, safety, total cost, product count, daily-unit burden, and formulation preference. The existing service Product/PharmacyProduct catalog reader and `/api/tips` candidate adapter now expose normalized ingredient amounts, price, positive stock, and formulation. Incomplete product facts and malformed offers fail closed or are excluded before matching. No second catalog, route, database, optimizer, order, or payment path was added.
- Evidence boundary: OP-061 is `IMPLEMENTED`. OP-062 is `INTEGRATED` through the existing service route function and catalog adapter. The evidence records that an actual Prisma query, production data freshness, deployment, and production operation are not proven.
- Generated status: complete `48`, partial `13`, pending `58`, external `1`, contradicted `0`. Audit PASS with `61` claims and `192` checked evidence files.
- Validation: focused optimizer tests `16 passed`; CI-equivalent tests `472 passed`; full Ruff PASS; service product QA, typecheck, lint, and production build PASS; `14` canonical smokes reproduce byte-identically; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `853 passed`, `77 failed`; the unchanged failures are `73` absent report artifacts and `4` CGM geometry assertions. No OP-061/062 regression was found.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`; the overall weakest slice remains `safety_blocked`, and every metric-specific weakest category is unchanged.
- Publication: service commit `a85767d9dc9418a23a9adeb2372d14a75d10b865` passed Encoding Guard run `29808830876`. R&D evidence commit `e50ba258e6b965f3a3af9aa5b078e00e8d690647` passed Original plan evidence run `29808907535`.
- Recommended next loops: OP-063/064 product-to-ingredient combination conversion and duplicate/total-dose handling; OP-065/066 budget/product-count pruning and safety-block preservation; OP-067/068 top-k explanations and deterministic reproduction.

## 2026-07-21 PRO worsening actions and outcome-class integration loop

- Chosen stage: `original plan / pre-post outcome quantification and PRO`; tasks OP-059 and OP-060.
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. The integration smoke performs four authenticated real-world-class enrollments/follow-ups plus one synthetic paired case through the existing service and R&D APIs.
- Primary evidence: `data/original_plan/evidence/op059_op060_pro_action_real_outcome_smoke_v1.json`; deterministic SHA-256 `ec14bf87025c9b1651462a936092cc3e2089956df2a72cfb826fa3594f22318d`; combined source SHA-256 `8e6969aac2e5e4d17bc9dfbb5176207874f697bd111955ea9fca6d06d107f7eb`; R&D source `a580d813abfc1bed0292477c9ba6dc88ec4f8f4f`; service source `5ec3adf1f3948e910c1f4498083b43c701eaf557`.
- Implementation: the existing plan/follow-up API now derives `maintain`, `reduce`, `stop`, or `re_optimize` from observed worsening, adherence, missed doses, and adverse events. It maps the decision to the existing `NextAction` and projected workflow state. The same API accepts `SYNTHETIC_OUTCOME_PROXY` or `REAL_WORLD_OUTCOME`, preserves the class in strict events, and keeps synthetic as the backward-compatible default. The TIPS PRO UI uses the existing authenticated adapter and shows the four actions in Korean.
- Evidence boundary: the paired cases have identical semantic-input SHA-256 after excluding the required transport request ID and `dataClass`. The smoke proves localhost two-process integration and contract handling, not production data, production operation, deployment, or causal effect. OP-059 and OP-060 are `INTEGRATED` and COMPLETE at their required stages.
- Generated status: complete `46`, partial `13`, pending `60`, external `1`, contradicted `0`. Audit PASS with `59` claims and `187` checked evidence files.
- Validation: focused `54 passed`; exact workflow selection `456 passed`; full Ruff PASS; service PRO QA, typecheck, lint, encoding audit, and production build PASS; all 13 workflow smoke runners reproduce without file changes; independent review after fixes Critical `0`, Important `0`, Minor `0`.
- Full suite: `837 passed`, `77 failed`; failures remain the known `73` absent report artifacts and `4` CGM geometry assertions. Frozen eval has `256` cases, seven zero metric deltas, and no weakest-slice changes.
- Publication: service through `5ec3adf1f3948e910c1f4498083b43c701eaf557`, R&D through `b068edac16e889dc6d18e004cf87726eb39e214d`; service Encoding Guard run `29807015490` and R&D Original plan evidence run `29807082270` passed.
- Recommended next loops: OP-061/062 optimization constraints and existing product contract; OP-063/064 adherence and ingredient combination; OP-065/066 duplicate ingredients and dose calculation.

## 2026-07-21 corrected PRO service contract and lineage loop

- Chosen stage: `original plan / pre-post outcome quantification and PRO`; tasks OP-057 and OP-058.
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. The integration smoke uses one synthetic authenticated service input, two strict PRO events, and one local R&D SQLite database.
- Primary evidence: `data/original_plan/evidence/op057_op058_pro_correction_plan_lineage_smoke_v1.json`; deterministic SHA-256 `67ffac5637d9281cd5b99ae4e435049669842ad2e4abdc54f69b71cbdd90a711`; combined source SHA-256 `10662658664b0ba08112a61582e1a0d22e0d2e3eada875c44bffcf314a016092`; R&D source `86823c364094b275e0e9d41a2b78ed22833b383e`; service source `9dfc1d0b2034ed15777385802b7283a3ffc78c02`.
- Implementation: the existing recommendation request, response, execution ledger, optimization event, baseline, follow-up, and correction paths now share one validated `plan_id`. The actual TIPS PRO component enrolls through the existing authenticated service adapter, persists execution/plan/baseline IDs, and creates or corrects strict PRO follow-ups. Retry conflicts fail closed without duplicate executions or orphan baselines.
- Evidence boundary: the actual UI client and authenticated service helpers reach the localhost R&D HTTP process. The smoke records score `10 -> 8 -> 7`, immediate recalculation, two strict PRO events, and recommendation/optimization/effect plan lineage. OP-057 is `INTEGRATED` and COMPLETE. OP-058 is `INTEGRATED` and PARTIAL below required `OPERATED`; authenticated browser rendering, production deployment/operation, real-world outcomes, and causal effect remain unproven.
- Generated status: complete `44`, partial `13`, pending `62`, external `1`, contradicted `0`. Audit PASS with `57` claims and `183` checked evidence files.
- Validation: focused `127 passed`; exact workflow selection `446 passed`; full Ruff PASS; service PRO QA, typecheck, lint, encoding audit, and production build PASS; all affected smoke files are byte-identical across reruns; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `827 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. Frozen eval has `256` cases, seven zero metric deltas, and an identical weakest-slice structure.
- Publication: service `9dfc1d0b2034ed15777385802b7283a3ffc78c02`, R&D through `a431cc448e26155ded2bd694715fa3b541009c53`; service Encoding Guard run `29804815958` and R&D Original plan evidence run `29805184034` passed.
- Recommended next loops: OP-059/060 worsening actions and real-outcome data-class compatibility; OP-061/062 optimization constraints and the existing product contract; OP-063/064 adherence and optimization-cycle integration.

## 2026-07-21 personal and group PRO uncertainty loop

- Chosen stage: `original plan / pre-post outcome quantification and PRO`
- Chosen tasks: OP-055 separate plan-linked personal observed change from the group mean; OP-056 attach sample size, deterministic 95% confidence intervals, and explicit uncertainty reasons to the group estimate
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. The deterministic smoke separately builds `100` synthetic week-2 personal PRO interpretations and one group estimate.
- Primary evidence: `data/original_plan/evidence/op055_op056_pro_personal_group_uncertainty_smoke_v1.json`; deterministic SHA-256 `4a458659b2c44cf35cf4589ac9f09e70ae63de37d7c2891356ce6e9c67fd4eb9`; source identity commit `56d0542e9506992621c8e356752ee41aec7b09d3`; source bundle SHA-256 `974bc53e20a0ad73308150eacc6218fe11f8182d563d872e6f7112763b619c34`
- Reused `PROFollowUpEffectInterpretationV1`, the versioned PRO scoring/baseline distribution, and the interim KPI bootstrap algorithm. The shared bootstrap implementation moved to `metrics/statistics.py`; no parallel PRO store, service path, or KPI system was added.
- The group summary retains canonical personal interpretations, rejects duplicate plan or assessment IDs and mixed data classes, timepoints, or score identities, and recomputes every derived value during validation. Input order cannot change the output.
- The 100-person smoke reports mean health-Z change `0.67` with 95% CI `[0.616666, 0.723333]` and mean health-percentile change `25.779542` with 95% CI `[23.82636, 27.745993]`. All `100` personal interpretations are fully interpretable. The remaining reasons are `observational_association_not_causal` and `non_real_world_outcome_data`.
- Evidence boundary: OP-055 and OP-056 are `IMPLEMENTED` and complete at their required stage. The data class is `SYNTHETIC_OUTCOME_PROXY`; no real-world outcome, WellnessBox service integration, production operation, deployment, or causal effect is claimed. Generated status: complete `43`, partial `12`, pending `64`, external `1`, contradicted `0`.
- Validation: focused selection `43 passed`; exact GitHub workflow pytest selection `425 passed`; full Ruff PASS; audit PASS with `55` claims and `171` checked evidence files; completion report check PASS; three affected canonical smoke files reproduce exactly and their source hashes/commits match; independent review Critical `0`, Important `0`, Minor `0` after fixing the initial smoke source-path omission.
- Full suite: `806 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-055/056 failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication: source commits `5b9dedcc62ff3bcb4c36d882f7f28ebaf2784968` and `56d0542e9506992621c8e356752ee41aec7b09d3`, plus evidence commit `0a1f102877a09f90195c64fdeeb67a73843f4913`, are on `origin/main`; Original plan evidence run `29799527985` passed.
- Recommended next loops: OP-057/058 corrected user PRO recalculation and plan-linked outcome lineage; OP-059/060 observed-worsening actions and real-outcome data-class compatibility; OP-061/062 optimization constraints and the existing service product contract.

## 2026-07-21 PRO follow-up persistence and interpretation loop

- Chosen stage: `original plan / pre-post outcome quantification and PRO`
- Chosen tasks: OP-053 persist strict PRO events for pre-intake, week 2, week 4, and discontinuation; OP-054 interpret observed change with adherence, missed-dose, and adverse-event context
- Primary dataset: `data/frozen_eval/frozen_eval_v1.jsonl`, `256` cases. The persistence smoke separately writes `4` synthetic PRO events to a temporary local SQLite database.
- Primary evidence: `data/original_plan/evidence/op053_op054_pro_followup_interpretation_smoke_v1.json`; deterministic SHA-256 `b57a6ef61310fc70727cb6bca9e3c4addc117d163bf627a72d0fb263d82392fc`; source commit `83997c11684fc482462668865afc843f7cf211ff`; source bundle SHA-256 `6d5829f753148e2c879c4dd546d2a0e5b58fd105f6129653f75147c4cea64e34`
- Reused the existing `execution_events`, `ExecutionLedger.append_event`, mutation ledger, recommendation execution, and versioned PRO scoring paths. No second event store or WellnessBox service implementation was added.
- Strict events require the fixed schema, plan and assessment identities, timezone-aware observation time, exact schedule, versioned scores, matching baseline distribution, reconciled adherence counts, and bounded adverse-event values. Strict payloads cannot use the conversation event type or cross the generic/strict correction boundary. Public interpretation rejects duplicate assessments and reversed observation time.
- Numeric raw-score, health-Z, percentile, and mean health-Z changes remain observed values. Adherence, missed doses, and adverse events change only interpretation status and reason codes. The contract forbids causal-effect claims.
- Evidence status: OP-053 is `IMPLEMENTED` and remains partial below required `OPERATED`; OP-054 is complete at required `IMPLEMENTED`. Generated status: complete `41`, partial `12`, pending `66`, external `1`, contradicted `0`.
- Validation: focused selection `90 passed`; exact GitHub workflow pytest selection `407 passed`; full Ruff PASS; audit PASS with `53` claims and `165` checked evidence files; completion report check PASS; deterministic smoke byte-identical across reruns; independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `788 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-053/054 failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication: source fix commit `83997c11684fc482462668865afc843f7cf211ff`, OP-053/054 evidence commit `706fb4ad22710ab0c5f6d5364ecd5aa3e694fe39`, and OP-051/052 source-identity refresh commit `0e7ea31bdf240cab0f4b7a34d35e7722e0a09e2e` are on `origin/main`; Original plan evidence run `29797963682` passed.
- Recommended next loops: OP-055/056 personal/group effect separation and uncertainty; OP-057/058 user correction and plan-linked outcome lineage; OP-059/060 effect-driven action and real-data-class compatibility.

## 2026-07-17 versioned PRO scoring and baseline-percentile loop

- Chosen stage: `original plan / pre-post outcome quantification and PRO`
- Chosen tasks: OP-051 fix PSQI, ISI, and PSS-10 raw-score algorithms to a versioned contract; OP-052 fix health-oriented Z scores and percentiles to a declared baseline distribution
- Primary evidence: `data/original_plan/evidence/op051_op052_versioned_pro_scoring_smoke_v1.json`; current deterministic SHA-256 `b14d8a69e7e62ca40837dab30552482c638de31452030168afecaf24eb7c5ddf`; source commit `334bd706f72593b7c948785ad2b8630fb65b8911`; source bundle SHA-256 `b9d49513fffb58d6f0a1bcda58741e637fca79c14ab09697492be771b9ba9169`
- Reused the existing `src/wellnessbox_rnd/metrics/pro_scoring.py` path and package exports. No parallel metrics system or WellnessBox service implementation was added.
- Raw-score contract: PSQI accepts seven already-derived component scores from `0..3` and sums to `0..21`; it does not reproduce or derive the licensed 19 self-rated items. ISI accepts seven item scores from `0..4` and sums to `0..28`. PSS-10 accepts ten item scores from `0..4`, reverses one-based positions `4, 5, 7, 8`, and sums to `0..40`. Floats, booleans, wrong counts/ranges, unknown instruments, metadata drift, and modified model instances fail closed.
- Baseline contract: every source observation declares the versioned `BASELINE` role. A cohort requires one instrument/scoring version, at least two observations, and nonzero spread. The distribution uses arithmetic mean and sample standard deviation (`ddof=1`), then computes `health_z=(baseline_mean-raw_problem_score)/baseline_sample_std` and `100*Phi(health_z)`. Six-decimal half-even rounding and operation order are fixed. The transformed output embeds the validated distribution and rejects source-score, statistic, hash, instrument, version, or role changes.
- Evidence boundary: all smoke cohorts use `SYNTHETIC_OUTCOME_PROXY`. The evidence does not claim authorized instrument text, clinical interpretation, service integration, production data, deployment, or production operation.
- Evidence status: OP-051 and OP-052 are complete at required stage `IMPLEMENTED`. Generated status: complete `40`, partial `11`, pending `68`, external `1`, contradicted `0`.
- Validation: related scoring tests `38 passed`; exact CI-equivalent selection `388 passed`; full Ruff PASS; deterministic smoke byte-identical across reruns; manifest audit PASS with `51` claims, `160` checked evidence files, and zero issues; completion report check PASS; independent final review Critical `0`, Important `0`, Minor `0`.
- Full suite: `769 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-051/052 failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication: source commit `fd7e4a3d1d6edb630d6c25cdb0fde11129d98975` and evidence commit `3bfdfed8d1aabfbfbbcca908bfb17f154aba4e46` are on `origin/main`; Original plan evidence run `29515937856` passed.
- Recommended next loops: OP-053/054 follow-up PRO events and adherence/adverse-event interpretation; OP-055/056 personal/group effects and uncertainty; OP-057/058 user correction and plan-linked outcome lineage.

## 2026-07-17 learned replay and service product-candidate loop

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-049 compare the learned reranker with the deterministic baseline on identical replay cases; OP-050 convert R&D recommendations through the existing service ingredient map into existing service product candidates
- Primary evidence: `data/original_plan/evidence/op049_op050_replay_product_candidates_smoke_v1.json`; deterministic SHA-256 `ff3b58d106ac4d8678df1ed6925b01232387880c8d5e6b4064a93d5ef4cdc2e1`; R&D source `584c6c7ca3d053c9ae3430b214eae23f35009b15`; WellnessBox source `a6b8ab1e92a112f6d2e904436bfe44ba688fc4e8`
- Reused `recommend()`, the frozen-eval runner, learned-artifact validator, `/api/tips`, versioned ingredient map, and existing `product.catalog` Prisma query. No parallel recommendation engine, route, ingredient catalog, or product catalog was added.
- The paired replay covers all `256` frozen cases. Learned reranking applies in `12`; `244` are ineligible and use the deterministic baseline; true fallback cases are `0`. Selection changes in `4` cases and rank or score changes in `5`. Response status, next action, and the complete safety payload have zero changes. The report rejects unknown decision states, incomplete status totals, forged deltas, and schema-version changes.
- The product contract is pinned to the ingredient-map version and covers all `8` mapped service ingredients. A snapshot captured from the configured in-stock Prisma catalog resolves them to existing product IDs `29`, `30`, `31`, `35`, `42`, and `44`; the runtime route queries the existing catalog path, returns bounded `MATCHED`/`NO_MATCH` candidates, and fails closed on invalid catalogs or unmapped identifiers.
- Integration boundary: the actual localhost R&D HTTP process proved only the `BLOCKED` safety path with zero recommendations. READY ingredient/product conversion and fail-closed cases used the existing test-only route dependency seam plus the captured catalog snapshot. `ready_two_process_product_conversion_proven=false` and `production_operation_proven=false`; no deployment was performed.
- Evidence status: OP-049 is complete at `IMPLEMENTED`; OP-050 is complete at `INTEGRATED`. Generated status: complete `38`, partial `11`, pending `70`, external `1`, contradicted `0`.
- Validation: focused replay tests `5 passed`; service ingredient/product QA covers all `8` mappings; exact CI-equivalent selection `350 passed`; full Ruff PASS; manifest audit PASS with `49` claims, `155` checked evidence files, and zero issues; completion report check PASS; independent final review Critical `0`, Important `0`, Minor `0`.
- Full suite: `751 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-049/050 failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication: WellnessBox commits `39a0d0f274f5e1b0c61db8aade903c64f413aafe` and `a6b8ab1e92a112f6d2e904436bfe44ba688fc4e8` passed Encoding Guard runs `29511317388` and `29511798649`. R&D source/evidence commits through `3ed17debdbfc0646c819066d4f7a8cbfec36a159` are on `origin/main`; Original plan evidence run `29513104957` passed.
- Recommended next loops: OP-051/052 versioned PRO scoring and percentile conversion; OP-053/054 follow-up events and adherence interpretation; OP-055/056 personal/group effects and uncertainty.

## 2026-07-16 decision uncertainty and learned-fallback loop

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-047 quantify decision uncertainty and additional-input conditions; OP-048 return to the deterministic baseline when a learned artifact is absent, invalid, suspicious, or fails during prediction
- Primary evidence: `data/original_plan/evidence/op047_op048_decision_uncertainty_learned_fallback_smoke_v1.json`; deterministic SHA-256 `55eae7c9a7a99557fa47ecc687e622bc0a959550b7d629db4e7008e0f5d7d158`, pinned to source commit `22aca5e9d64a493562f9d17b302bead2ca02c555`
- Reused the existing normalized request, safety-first candidate pool, deterministic scorer, optional learned reranker, response contract, and API route. No parallel recommendation system, catalog, or service route was added.
- `decision_uncertainty_v1` converts missing-input importance, review status, candidate availability, and the preselection top-two score margin into a bounded score and low/moderate/high band. The score scope explicitly states that it is ranking/input uncertainty, not a clinical probability. A complete ranked score trace preserves every post-safety candidate, full score and reason breakdowns, catalog priority, rules, goals, and evidence links; response and contract validators reconcile the snapshot against catalog, goal-prior, signal, and safety registries.
- Learned reranking now returns an explicit decision status. Missing paths/files, schema failures, unsupported or whitespace-polluted features, invalid closed-domain values, unknown catalog candidates, dimension errors, nonfinite or extreme coefficients, and prediction exceptions all discard partial learned results and return the exact deterministic recommendations and engine mode. Model and target identity are required fields.
- The diagnostics contract uses a distinct current schema version and rejects status, selection-count, score-trace, diagnostics-removal, and legacy-version downgrade mutations. Legacy V1 payloads remain parseable only through the explicit compatibility validation mode.
- Evidence status: OP-047 and OP-048 are complete at required stage `IMPLEMENTED`. Generated status: complete `36`, partial `11`, pending `72`, external `1`, contradicted `0`. No WellnessBox service code, R&D deployment, or production operation changed.
- Validation: focused decision/contract selection `60 passed`; exact local CI-equivalent selection `345 passed`; full Ruff PASS; all three affected smoke files reproduce byte-identically; manifest audit PASS with `47` claims, `145` checked evidence files, and zero issues; completion-report stale check PASS; independent final review Critical `0`, Important `0`, Minor `0`.
- Full suite: `746 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-047/048 failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication: source commit `22aca5e9d64a493562f9d17b302bead2ca02c555` and evidence commit `ae38c36963f00d9c7f0f84cf4cd5597a1e271645` are on `origin/main`; Original plan evidence run `29509159767` passed.
- Recommended next loops: OP-049/050 learned-versus-baseline replay and service-product conversion; OP-051/052 versioned PRO scoring and percentile conversion; OP-053/054 follow-up state and change calculation.

## 2026-07-16 candidate-pool preservation and structured-reason loop

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-045 preserve the candidate sets before and after safety filtering; OP-046 return recommendation reasons separated into input signals, score terms, and evidence IDs
- Primary evidence: `data/original_plan/evidence/op045_op046_candidate_pool_structured_reasons_smoke_v1.json`; current deterministic SHA-256 `86cc00d7662d96a2a350dfabc7b41395987b65db1f418d3bcd7de5741e6d335e`, with source identity refreshed to commit `22aca5e9d64a493562f9d17b302bead2ca02c555` after the shared recommendation diagnostics changed
- Reused the existing request normalization, catalog, goal priors, safety summary, candidate scorer, optimizer, recommendation response, and API route. Candidate selection and trace generation now call one shared partition function; no parallel filter, scorer, catalog, or recommendation system was added.
- `candidate_pool_trace` preserves the exact pre-safety pool, typed exclusions, post-safety pool, selected keys, applied safety rules, and global-block state. The schema rejects duplicate keys, identity drift across the partition, overlap between excluded and post-safety candidates, selections outside the post-safety pool, and selections under a global block.
- Each selected candidate returns `reason_breakdown` with normalized goal and applied input signals, all 14 score terms, rule IDs, evidence links, reference IDs, claim IDs, limitations, and a reconciled total. Safety adjustments preserve the scoring-time `needs_review` input and the exact triggered safety rule even when the final response safety status is later resolved to `ok`.
- The recommendation contract cross-checks goal-prior scores, applied-signal point sums, learned-bonus markers, safety provenance, candidate totals, and exact evidence ownership. Empty or forged IDs, wrong claim/reference/rule associations, unexpected fields, missing terms, duplicate evidence links, and internally consistent score tampering fail closed.
- Evidence status: OP-045 and OP-046 are complete at required stage `IMPLEMENTED`. Generated status: complete `34`, partial `11`, pending `74`, external `1`, contradicted `0`. No WellnessBox service code, R&D deployment, or production operation changed.
- Validation: focused recommendation/API/contract selection `203 passed`; exact local CI-equivalent selection `315 passed`; full Ruff PASS; both current smoke files reproduce without diff; manifest audit PASS with `45` claims, `140` checked evidence files, and zero issues; completion-report stale check PASS; independent final review Critical `0`, Important `0`, Minor `0`.
- Full suite: `716 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-045/046 failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication: source commit `f7479d710e227fe428d96977a91ce2ab66438d06`, evidence commit `c8c636c61497929a3afb3933236520226c555072`, source-identity fix `92cf53a8f0c2050e7b4ae2368d36b95d2396c9df`, and self-contained CI fixture fix `0cd4db94c87ac223f7062ae75e6a2ac02267c722` are on `origin/main`; Original plan evidence run `29504825809` passed.
- Recommended next loops: OP-047/048 uncertainty and missing-input quantification plus deterministic learned-artifact fallback; OP-049/050 learned-versus-baseline replay and service-product conversion; OP-051/052 versioned PRO scoring and percentile conversion.

## 2026-07-16 evidence-linked candidate signal scoring loop

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-043 make symptom, laboratory, lifestyle, and dietary inputs affect candidate scores; OP-044 convert wearable, CGM, and genetic observations into numeric candidate-score terms
- Primary evidence: `data/original_plan/evidence/op043_op044_candidate_signal_scoring_smoke_v1.json`; current deterministic SHA-256 `b949483625e5fba4bdbea96afe9cb8ade1f7e45cbc1d5db2955b1e10f6f30052`, with source identity refreshed to commit `22aca5e9d64a493562f9d17b302bead2ca02c555` after the shared recommendation diagnostics changed
- Reused the existing request, consent normalization, sensor parser, catalog, goal priors, safety-first recommendation path, scorer, response contract, runtime knowledge DB, and Data Lake projection. No parallel recommendation engine, service route, or catalog was added.
- The score breakdown now exposes separate symptom, laboratory, lifestyle, dietary, wearable, CGM, and genetic terms. Every applied signal includes the observed value or tag, bounded points, scoring version, rule ID, exact reference/claim IDs, and limitation. The returned total and recommendation-set contract reconcile every visible term.
- Laboratory scoring uses only the observation's supplied reference range. Adult sleep scoring uses the bounded seven-hour context rule. CGM scoring requires explicit source consent, type 1/type 2 diabetes context, a blood-glucose goal, a nonpregnant profile, and a verified 70–180 mg/dL TIR range. Genetic scoring accepts only the two master-context tag families; unknown or unscoped tags add zero and do not alter unrelated rationales.
- The runtime artifact embeds the strict scoring registry. Rule IDs, inputs, thresholds, weights, goal/ingredient scope, claim ownership, limitation text, score meaning, and version are fail-closed. TIR alias conflicts, invalid bounds, custom ranges, forged claims, unrelated references, stale runtime artifacts, and implicit sensor consent are rejected or contribute zero.
- Evidence status: OP-043 and OP-044 are complete at required stage `IMPLEMENTED`. Generated status: complete `32`, partial `11`, pending `76`, external `1`, contradicted `0`. No WellnessBox service code, R&D deployment, or production two-process operation changed.
- Validation: focused candidate/parser/contract selection `70 passed`; exact CI-equivalent selection `301 passed`; full Ruff PASS; deterministic smoke byte-identical across reruns; manifest audit PASS with `43` claims, `134` checked evidence files, and zero issues; completion-report stale check PASS; stored runtime equals a fresh deterministic build; independent final review Critical `0`, Important `0`, Minor `0`.
- Full suite: `705 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-043/044 failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication: source commit `1465db1c153b71b8b636231eb6487c32e469c85b` is pinned by the smoke; evidence commit `64d67eceef2996869c897e9a0bc02b33a549010f` is on `origin/main`; Original plan evidence run `29501666136` passed.
- Recommended next loops: OP-045/046 pre/post safety-candidate preservation and structured recommendation reasons; OP-047/048 uncertainty/missing-input quantification and deterministic fallback; OP-049/050 learned-versus-baseline replay and service-product candidate conversion.

## 2026-07-16 ingredient identity and evidence-linked goal-prior loop

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-041 version the WellnessBox service/R&D ingredient identifier mapping; OP-042 register evidence-linked candidate priors for every catalog-supported ingredient/goal pair
- Primary evidence: `data/original_plan/evidence/op041_op042_ingredient_mapping_goal_prior_smoke_v1.json`; actual service `/api/tips` export plus localhost R&D HTTP process, byte-identical across reruns (`fd37111339773f86904cc3d4f6f2b5fda45ff2d51e4f1b8a6a5ff35d5013e8a6`)
- Reused both existing ingredient catalogs, the existing `/api/tips` safety-authority path, the R&D candidate scorer, reference ingestion, and runtime knowledge DB. No parallel catalog, recommendation engine, or service route was added.
- The byte-identical mapping contract covers every service identifier and every R&D catalog key as mapped or explicitly unmapped. Equivalent pairs allow both directions; a broader service identifier allows only R&D-to-service conversion. The actual `/api/tips` route returns `ING:MAGNESIUM` for `magnesium_glycinate` and fails closed with HTTP `502` and zero recommendations for an unmapped R&D identifier.
- The versioned goal-prior registry covers all `24` current catalog-supported ingredient/goal pairs and all `9` recommendation goals. It preserves the established candidate-ordering points (`35` for a specific goal and `18` for general wellness); these points are selection policy, not clinical efficacy probabilities. Every record carries the fixed policy claim, and any clinical strength/direction must match a scoped claim type and the exact claim-owned reference set.
- Source scope is conservative: insufficient, mixed, inconclusive, deficiency-dependent, strain-specific, population-dependent, or small-trial evidence remains labeled with its limitation. Forged policy claims, unrelated references, evidence-strength promotion, duplicate IDs, stale runtime artifacts, and nondeterministic fresh builds fail validation.
- Evidence status: OP-041 is complete at required stage `INTEGRATED`; OP-042 is complete at required stage `IMPLEMENTED`. Generated status: complete `30`, partial `11`, pending `78`, external `1`, contradicted `0`. No R&D deployment or production two-process operation is claimed.
- Validation: focused mapping/prior/runtime selection `48 passed`; exact CI-equivalent selection `283 passed`; full Ruff PASS; manifest audit PASS with `41` claims, `124` checked evidence files, and zero issues; completion-report stale check PASS; stored/fresh runtime equality and fresh-build determinism PASS; independent final review Critical `0`, Important `0`.
- Full suite: `683 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication: WellnessBox commit `58246f9a086c81bb3a38d4a1f33f5205b388d2b8` passed Encoding Guard run `29496255239`. R&D source commit `6a1f874b95fadbffbab796eefcbecd71284b6d9e` and evidence commit `da2936206d0ebe8b2ef12d9e0b79f048f2239b10` are on `origin/main`; Original plan evidence run `29496879246` passed.
- Recommended next loops: OP-043/044 candidate filtering and auditable score decomposition; OP-045/046 safe-candidate preservation and structured recommendation reasons; OP-047/048 uncertainty/missing-input quantification and deterministic fallback.

## 2026-07-16 external high-risk gate and final safety-authority loop

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-039 define a fail-closed intake and evaluation contract for an independently labeled high-risk frozen evaluation; OP-040 prove final safety blocking authority across the existing WellnessBox `/api/tips` and R&D interim recommendation paths
- Primary evidence: `data/original_plan/evidence/op040_final_safety_authority_integration_smoke_v1.json`; actual service-route export plus localhost R&D HTTP process, byte-identical across reruns (`c01eca4f667cfcea00c95f7830ebd8f9711482d81e40e6f4b23629719b9c5183`)
- Reused the existing `POST /api/tips` route, interim profile/recommendation client, `POST /v1/interim/recommendations`, deterministic safety evaluator, evidence registry, and original-plan CI workflow. No parallel service route, safety engine, or recommendation system was added.
- The R&D interim route evaluates stored, current, and conservatively merged risk facts before model execution. A hard failure returns `BLOCKED`, no model ID, and zero recommendations. Dynamic multi-key predicates may draw each known risk fact from the stored or current source, so a later request cannot erase or split a blocking condition.
- The service validates the full R&D safety response. A valid R&D block remains authoritative as `rnd_final`; transport, HTTP, decode, or contract failure returns a service-owned `service_fail_closed` block with zero recommendations. The smoke observes `SAFE-EMERGENCY-001`, `STOP_AND_ESCALATE`, `BLOCKED`, and an invalid-contract HTTP `502` through the actual `/api/tips` export.
- OP-039 remains unclaimed at required stage `EXTERNAL`. The evaluator now requires a pre-approved coverage protocol, independently labeled cases, detached attestation, independent verification receipt, repository-pinned trust roots, chronological approvals, complete hazard-stratum coverage, a clean Git tree, and zero hard false negatives. Both trust-root allowlists are intentionally empty because no qualifying external dataset or approval exists.
- Evidence status: OP-040 is `INTEGRATED` and remains partial at required stage `OPERATED`. Generated status: complete `28`, partial `11`, pending `80`, external `1`, contradicted `0`. No R&D deployment, production environment configuration, durable production storage, or production operation is claimed.
- Validation: focused evaluator/interim selection `19 passed`; exact CI-equivalent selection `268 passed`; full Ruff PASS; manifest audit PASS with `39` claims, `113` checked evidence files, and zero issues; completion-report stale check PASS; runtime stored/fresh equality PASS with zero validation issues; independent final review Critical `0`, Important `0`, Minor `0`.
- Full suite: `673 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-039/040 or recommendation-boundary failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, the overall weakest category is unchanged, and every metric-specific weakest category is unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication boundary: WellnessBox service commit `9609ce804ad06c609b794f455d4f6127b59361ac` passed Encoding Guard run `29492239202`. R&D source commit `e830c7debd4b103b756bba494fdbc73d7f0bad3a` is pinned by the smoke evidence. The R&D evidence commit and CI result are recorded after publication.
- Recommended next loops: OP-041/042 service/R&D ingredient identity and evidence-backed goal priors; OP-043/044 candidate contraindication filtering and auditable candidate scoring; OP-045/046 post-filter candidate preservation and structured recommendation reasons.

## 2026-07-16 dose-limit fail-closed and rule-metadata loop

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-037 compare unit-normalized upper limits and conservatively exclude ingredients when supplied dose evidence is ambiguous; OP-038 return the applied rule version and one timezone-aware application time
- Primary evidence: `data/original_plan/evidence/op037_op038_dose_limit_rule_metadata_smoke_v1.json`; seven deterministic dose cases, byte-identical across reruns (`2a34f58b4564b903560341bf0862d1ce12016a0a84f6b4efd298616255347dbb`)
- Reused the existing supplement parser, `IngredientDoseAggregate`, runtime knowledge database, deterministic safety service, recommendation response, Data Lake replay projection, and CI evidence workflow. No parallel dose calculator, safety engine, or recommendation path was added.
- Complete compatible doses are converted into the rule unit before comparison. The returned aggregate remains the only compared total. An optional dose that was not supplied has `dose_input_count=0` and does not claim an upper-limit evaluation. A supplied but partial, non-convertible, compound, ranged, or schedule-qualified legacy dose returns `dose_evidence_incomplete`, excludes each affected ingredient, and never invents a total or stops unrelated safe alternatives. Complete above-limit totals remain global blockers.
- Legacy parsing now accepts comma-grouped numbers, rejects multi-dose ranges and schedules, resolves each compound segment independently, and permits a fuzzy catalog title only when the text resolves to exactly one ingredient. Regression coverage includes `plus`/modifier compounds, `twice daily`, `bid`, `N x`, single-unit ranges, and branded single-ingredient titles.
- Every structured safety rule and runtime interaction, contraindication, and dose-limit record has a positive version. Every returned `RuleReference` exposes the applied version and bounded application reason. `SafetySummary.applied_at` is timezone-aware and can be injected for replay/smoke determinism. Session replay excludes only this volatile timestamp from its behavior fingerprint while retaining it in stored and API responses.
- Evidence status: OP-037 and OP-038 are complete at their required `IMPLEMENTED` stage. Generated status: complete `28`, partial `10`, pending `81`, external `1`, contradicted `0`.
- Validation: focused parser/safety/recommendation selection `240 passed`; exact CI-equivalent selection `252 passed`; full Ruff PASS; manifest audit PASS with `38` claims, `105` checked evidence files, and zero issues; completion-report stale check PASS; runtime stored artifact equals a fresh build with zero validation issues; independent final review found zero Critical, Important, or Minor issues.
- Full suite: `657 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-037/038 or recommendation-baseline failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, the overall weakest category is unchanged, and every metric-specific weakest category is unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Remaining boundary: this R&D-only loop did not change WellnessBox service code, deploy the R&D app, or prove production two-process integration. OP-039 still needs external high-risk labels for hard false-negative proof. OP-040 still needs real production evidence that final safety blocking authority cannot be bypassed.
- Recommended next loops: OP-039/040 high-risk false-negative and production final-block authority; OP-041/042 service/R&D ingredient identity and evidence-backed goal priors; OP-043/044 candidate contraindication filtering and auditable candidate scoring.

## 2026-07-16 evidence-linked interaction and dose-aggregation loop

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-035 connect drug-ingredient interaction rules to evidence IDs; OP-036 calculate duplicate ingredients and cross-product daily-dose totals
- Primary evidence: `data/original_plan/evidence/op035_op036_interaction_dose_aggregation_smoke_v1.json`; ten deterministic recommendation/replay cases, byte-identical across reruns (`9c001cb799b34e65899103f47f959b0d2c9a2125ed8be1bea847fb1daf9f554a`)
- Reused the raw-reference ingestion, runtime knowledge database, normalized `RecommendationRequest`, current supplement dose extraction, deterministic safety service, and interim replay safety path. No parallel interaction engine or dose calculator was added.
- `SAFETY-ANTICOAG-001` now carries `REF-NIH-ODS-OMEGA3-001` and `CLM-NIH-ODS-OMEGA3-WARFARIN-001`; the runtime validator rejects evidence-linked interaction records without valid reference or claim IDs. Recommendation safety returns the exact citation, and interim replay preserves the same stable IDs for both warfarin and its Coumadin alias. The NIH ODS source reports a possible INR effect, notes that most 3–6 g/day studies did not significantly change anticoagulant status, and attributes periodic INR monitoring to FDA-approved omega-3 pharmaceutical package inserts. The omega-3 candidate exclusion remains an explicitly conservative deterministic policy rather than a claim attributed to NIH.
- `SafetySummary` now returns per-ingredient product count and names, cross-product duplicate state, normalized total daily amount and unit, dose-observation count, and completeness. Two vitamin-D products return `4400 IU`; two undosed probiotic products return a duplicate with no invented total; one dosed plus one undosed vitamin-D product returns a partial `2000 IU` total with `dose_complete=false`; repeated lines inside one product do not count as a cross-product duplicate.
- Evidence status: OP-035 and OP-036 are complete at their required `IMPLEMENTED` stage. Generated status: complete `26`, partial `10`, pending `83`, external `1`, contradicted `0`.
- Validation: focused interaction/dose/reference selection `53 passed`; exact CI-equivalent selection `228 passed`; full Ruff PASS; manifest audit PASS with `36` claims, `102` checked evidence files, and zero issues; completion-report stale check PASS; deterministic smoke hash stable across reruns; independent final review found zero Critical, Important, or Minor issues.
- Full suite: `635 passed`, `77 failed`; the unchanged failure groups remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No new interaction, aggregation, lineage, or safety failure remains.
- Frozen evaluation: `256` cases; all seven tracked metric deltas and all weakest-slice category deltas are exactly `0` against `artifacts/reports/op029_op030_frozen_eval/eval_report.json`.
- Remaining boundary: incomplete or non-convertible dose evidence is now visible but is not yet conservatively blocked; OP-037 owns that decision. Rule version and application time remain absent until OP-038. No WellnessBox code, R&D deployment, or two-process production integration changed in this loop.
- Recommended next loops: OP-037/038 unit-normalized upper-limit fail-closed handling and rule version/application time; OP-039/040 high-risk false-negative evidence and production final-blocking authority; OP-041/042 service/R&D ingredient identity and evidence-backed goal priors.

## 2026-07-16 special-population and condition safety loop

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-033 separate pregnancy and lactation restrictions; OP-034 expand condition-specific contraindication and review-required rules
- Primary evidence: `data/original_plan/evidence/op033_op034_special_population_condition_safety_smoke_v1.json`; eight real schema-normalization-safety cases plus the interim replay decisions, byte-identical across reruns (`a3689cc0c1d5ad9cb73733ac7aeb42699f12083f26d589dc2ec16c5fd4f71a49`)
- Reused the strict `RecommendationRequest`, normalized intake, data-defined `SafetyRuleSet`, recommendation safety service, interim replay safety path, and runtime knowledge builder. No parallel safety engine or recommendation path was created.
- `UserProfile` now accepts an independent `lactating` flag. The false default remains present in OpenAPI but is omitted from serialized requests, preserving existing request payloads, normalized hashes, and the WellnessBox profile-adapter contract. Pregnancy keeps `SAFETY-PREG-001`; lactation uses `SAFETY-LACT-001`; both active states apply each rule once.
- Condition rules now declare `contraindication` or `review_required`. The data covers chronic kidney review, kidney failure or dialysis blocking, liver failure or cirrhosis blocking pending clinical review, and hemochromatosis exclusions for iron and vitamin C. Contraindication records cannot omit their excluded ingredients.
- Policy bases are scoped per rule and ingredient in the deterministic evidence. NIH NCCIH supports the ashwagandha pregnancy/lactation restriction, the NCBI-hosted MotherToBaby fact sheet supports the berberine pregnancy/lactation restriction, and NIH ODS supports the renal-magnesium and hemochromatosis iron/vitamin-C restrictions. The hepatic blocker is identified separately as the plan's conservative initial high-risk research-scope policy, not as an externally validated clinical rule. OP-035 evidence-ID lineage remains a separate requirement; this loop does not claim that drug-interaction evidence work.
- Evidence status: OP-033 and OP-034 are complete at their required `IMPLEMENTED` stage. Generated status: complete `24`, partial `10`, pending `85`, external `1`, contradicted `0`.
- Validation: exact CI-equivalent selection `208 passed`; focused safety/runtime selection `27 passed`; full Ruff PASS; manifest audit PASS with `34` claims, `99` checked evidence files, and zero issues; completion-report stale check PASS.
- Full suite: `621 passed`, `77 failed`; the unchanged failure groups remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No new safety-rule failure remains.
- Frozen evaluation: `256` cases; all seven tracked metric deltas are exactly `0` against `artifacts/reports/op029_op030_frozen_eval/eval_report.json`.
- Integration boundary: the current WellnessBox stored profile still exposes one combined `pregnantOrBreastfeeding` field. This loop implements distinct R&D inputs and rules but does not claim that the service can identify which state produced the combined source value.
- Recommended next loops: OP-035/036 evidence-linked drug interactions and cross-product aggregate dose; OP-037/038 normalized unit/upper-limit comparison and rule version/application time; OP-039/040 high-risk false-negative evaluation and production final-blocking authority.
# 2026-07-22 OP-103/104 bounded loop

- WellnessBox commit `5f1d42015d6a467a717d69f3aaa8a7e2afd06931` enforces the enabled R&D runtime contract: production HTTPS, credential/query/hash-free URL, 32-character token, and bounded timeout.
- Every preview response now has an exclusive `R&D 실행 결과` or `로컬 스냅샷 결과` origin; the evaluation screen renders its ID and fallback reason.
- OP-103 is `IMPLEMENTED / PARTIAL`; OP-104 is `INTEGRATED / PARTIAL`. No Vercel setting, public deployment, or production traffic was changed or claimed.
- Dataset/evidence: `data/original_plan/op103_op104_environment_result_origin_cases_v1.json`, 8 cases; canonical evidence `data/original_plan/evidence/op103_op104_environment_result_origin_smoke_v1.json`.
- Status is complete `70`, partial `33`, pending `16`, external `1`, contradicted `0`; audit PASS with `103` claims and `285` checked evidence files. Reports cover `26/120`; `94` remain.
- Independent review found Critical `0`, Important `1`, Minor `2`; runtime contract bypass, snapshot ID collision, and integration-test gaps were corrected. Final focused QA and TypeScript checks pass.
# 2026-07-22 OP-105/106 bounded loop

- Separate Node and FastAPI processes completed profile save, stored-risk recommendation, pharmacy-scoped review listing, immutable decision, and 409 replay rejection through the committed service client.
- OP-105 and OP-106 are `INTEGRATED / PARTIAL`; no public deployment or production user/pharmacist operation is claimed.
- Independent-review remediation dynamically executes 401 user denial, HMAC profile-ID override, pharmacist-session pharmacy-ID override, and authenticated profile/recommendation/review route handlers.
- Dataset/evidence: `data/original_plan/op105_op106_profile_review_roundtrip_cases_v1.json`, 8 cases; audit PASS with 105 claims and 289 evidence files. Counts are `70/35/14/1/0`; reports cover `28/120`.
# 2026-07-22 OP-107/108 bounded loop

- 인증된 관리자 라우트가 실제 R&D HTTP API에서 데이터, 출처, 규칙, 모델, 실행 상태를 읽는다. 빈 평가 저장소의 KPI는 `UNAVAILABLE`로 분리한다.
- OP-107은 `INTEGRATED / PARTIAL`이다. OP-108은 상품과 R&D 응답을 주입한 fixture 검증이므로 `IMPLEMENTED / PARTIAL`이다. 실제 Prisma 상품 조회나 R&D 상품 경로 통합을 주장하지 않는다.
- 서비스 커밋은 `e95592a126cdb2bfeec156d4f4d7de43487e2a63`이다. 완료 상태는 `70/37/12/1/0`, 보고서는 `30/120`, 감사 주장은 `107`, 확인한 증거 파일은 `292`개다.
- 독립 리뷰의 최초 결과 `Critical 0 / Important 3 / Minor 1`에 따라 규칙·모델·실행 API, 정직한 단계 판정, 장문 보고서, R&D 소스 커밋·blob 식별 정보를 보강했다.
- 최종 독립 재검토는 `Critical 0 / Important 0 / Minor 0`이다.
# 2026-07-22 OP-109/110 bounded loop

- 결제 결과 검증 뒤 기존 `createOrder`가 재고 차감과 주문 생성을 소유하는 경계를 고정했다. R&D 추천·계획 라우트는 주문을 변경하지 않는다.
- 최신 주문 상태를 소분·배송·재주문·취소 컨텍스트로 정규화하고 별도 FastAPI에 실제 HTTP로 전달한다. R&D는 호출 전후 실행 이벤트 수와 계획 상태를 보존한다.
- OP-109와 OP-110은 모두 `IMPLEMENTED / PARTIAL`이다. 실제 Prisma mutation과 조회, 실제 결제 제공자, 운영 사용은 증명하지 않았다.
- 데이터셋은 `data/original_plan/op109_op110_order_plan_context_cases_v1.json` 8건이다. 상태는 `70/39/10/1/0`, 보고서는 `32/120`, 감사 주장은 `109`, 확인한 증거 파일은 `300`개다.
- 이전 CI의 최신 서비스 파일 누락은 감사·completion·계약 테스트가 고정된 최신 OP-110 서비스 checkout을 사용하도록 수정했다.
- 독립 리뷰는 `1/2/1`에서 `0/2/1`로 줄었다. 추가 지적에 따라 R&D가 주문 생성 전에 사용자 소유 execution·plan을 검증하고, migration이 기존 paymentId 중복을 명시적으로 탐지하며, P2002 동시 재시도가 rollback 뒤 기존 주문을 반환하게 했다. 서비스 커밋은 `59399e2569c6152c644c4010ac52e26e876d1040`이다.
- 최종 독립 재검토는 `Critical 0 / Important 0 / Minor 0`이다. 서비스 Encoding Guard `29891500251`도 통과했다.
- R&D 전체 `Original plan evidence` 실행 `29893387739`가 통과했다. 실행 중 발견한 과거 증거 provenance를 현재 경로별 소스 식별자로 동기화했고, OP-105/106 생성기는 실행마다 바뀌는 ID를 안정된 표기로 정규화했다. 검증된 R&D 소스·증거 커밋은 `07fff30f2ed5cbd4e22b5b85fc944412892c287b`다.

# 2026-07-22 OP-111/112 bounded loop

- OP-111과 OP-112를 요구 단계인 `INTEGRATED`로 완료했다. 상태는 `72/39/8/1/0`, 감사 주장은 `111`, 확인한 증거 파일은 `305`, 한국어 보고서는 `34/120`이다.
- 8개 사례와 별도 FastAPI/Node smoke가 내부 토큰, user/pharmacy/admin 권한, HMAC 가명, 최소 수집, 로그 마스킹, 공개 오류 경계를 검증한다.
- 서비스는 중첩 프로필의 직접 식별자와 알 수 없는 필드를 저장 전에 거부한다. 실제 guard가 공유하는 역할 판정 함수를 허용·거부 사례에서 실행하고 실제 오류 로그 호출부를 재귀 마스킹한다.
- 서비스 커밋 `1912f127a02d158a159ed7edd135f389308a1e6e`의 Encoding Guard `29894827365`가 통과했다. 독립 재검토는 `Critical 0 / Important 0 / Minor 0`이다.
- R&D 커밋 `354a5caf20c10d3e1bb7b5634e7fdf8ffc18e1c5`의 Original plan evidence 실행 `29895612666`도 전체 증거 재생, 699개 통과·2개 건너뜀의 계약 테스트, Ruff를 포함해 성공했다.
- frozen 평가, 학습 데이터, 모델, safety 규칙, replay 결과 변화는 0이다. production identity provider와 production log sink는 검증하지 않아 `OPERATED`를 주장하지 않는다.

# 2026-07-22 OP-113/114 bounded loop

- OP-113과 OP-114를 요구 단계 `INTEGRATED`로 완료했다. 상태는 `74/39/6/1/0`, 감사 주장은 `113`, 증거 파일은 `313`, 한국어 보고서는 `36/120`이다.
- 8개 사례가 GET 단일 재시도, POST 무재시도, 실제 500ms timeout abort, retryable 오류 전용 circuit, 30초 half-open 단일 probe, 관리자 KPI fallback, OpenAPI snapshot, TypeScript operation registry를 검증한다.
- FastAPI가 생성한 31개 interim path와 reachable component schema 63개를 양쪽 저장소에 byte-equivalent하게 고정했다. 서비스 client는 registry-derived method/path union과 런타임 matcher로 미등록 operation을 fetch 전에 차단한다.
- 독립 검토는 최초 `Critical 0 / Important 5 / Minor 0`, 중간 `0/1/0`, 최종 `0/0/0`이다. 서비스 HEAD `d07123903072f5eac7ef7f5021cf8278ca02c9c9`의 Encoding Guard `29896967812`가 성공했다.
- R&D HEAD `811f5e46f8d6408915c677c3e273718b8f241d29`의 Original plan evidence `29897044861`도 전체 canonical 재생, 계약 테스트, Ruff를 포함해 성공했다.
- frozen 평가, 학습 데이터, 모델, safety 규칙, replay·slice 변화는 0이다. production 장애 주입, 다중 인스턴스 circuit 공유, 배포 artifact hash는 검증하지 않았다.
# 2026-07-22 OP-115/116 bounded loop

- OP-115는 `INTEGRATED / COMPLETE`, OP-116은 `INTEGRATED / PARTIAL`이다. 전체 상태는 `75/40/4/1/0`, 감사 주장은 `115`, 증거 파일은 `318`, 한국어 연구보고서는 `38/120`이다.
- 8건 동결 데이터셋과 canonical runner가 R&D focused pytest, 실제 FastAPI 프로세스 smoke, Ruff, wheel build, WellnessBox 실제 GET handler QA, 인코딩, typecheck, Next.js build를 실행한다. CI는 evidence를 재생성한 뒤 diff를 차단한다.
- WellnessBox `/api/internal/rnd/health`는 upstream `status=ok`와 `READY_FOR_PROVIDER_DEPLOYMENT`가 모두 참일 때만 200을 반환한다. degraded, NOT_READY, non-2xx, 비JSON, 비활성 상태는 503이다. 응답은 status와 alias만 공개한다.
- canonical evidence는 R&D source commit `275a2c5bee47a051532c1bbc0fa0505c384c21c0`과 WellnessBox commit `b37bf99a8f2a5a7eb50fe61016740579011d2aa3` 및 관련 blob을 고정한다. 동결 dataset SHA-256은 `898745db62e724200ecc12f463f8765d704c1f1e0cdad407038e27901de3f93c`다.
- frozen 평가·학습 데이터·모델·safety 규칙·replay·slice 변화는 0이다. production 배포와 production traffic은 검증하지 않아 OP-116을 OPERATED로 주장하지 않는다.
- GitHub Actions WellnessBox `29900597777`과 R&D `29901559427`은 모두 성공했다.

# 2026-07-22 OP-117/118 bounded loop

- OP-117과 OP-118은 모두 `IMPLEMENTED / PARTIAL`이다. 상태는 `75/42/2/1/0`, 감사 주장은 117, 증거 파일은 322, 한국어 보고서는 `40/120`이다.
- 8건 동결 데이터셋과 실제 Chromium이 사용자 `/survey`, 약사 인증 경계 `/pharm-login`, 임시 관리자 인증 뒤 `/admin`을 재현했다.
- 운영 증거 원장은 비외부 119건, evidence 연결 118건, OPERATED 0건과 미달 119건을 기록한다. production 배포·traffic과 약사 인증 세션은 증명하지 않았다.
- frozen 평가, 학습 데이터, 모델, safety 규칙, replay·slice 변화는 모두 0이다.

# 2026-07-22 OP-119 bounded loop

- OP-119는 `IMPLEMENTED / COMPLETE`다. 전체 상태는 `76/42/1/1/0`, 감사 주장은 118, 증거 파일은 328, 한국어 연구보고서는 `41/120`이다.
- 외부 요구사항 OP-039 한 건에 내부 책임 역할, 독립 외부 공급 역할, 필수 입력 4종, 교체 계약 2종, 검증된 차단 사유 4종과 승격 조건을 연결했다.
- 8건 동결 사례와 canonical runner가 manifest 외부 집합, 원장 집합, trust root JSON pointer 관측, 예상값 완전 일치, source blob을 검증한다.
- OP-039 외부 입력·승인·독립 검증은 계속 미충족이며 어떤 가짜 외부 증거도 만들지 않았다. frozen·학습·모델·safety·replay·slice 변화는 0이다.
# 2026-07-22 OP-001/002 연구보고서 보강 반복

- 선택 단계/과제: 원본 요구사항과 증거 기준 고정; OP-001 원본 SHA-256 동일성, OP-002 59쪽 시각 분류의 한국어 장문 연구보고서 보강.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `bc4fd0d1ac5d17f15bb5e7ccbdc22445795f2cfc863731800b0830019df34108`.
- 변경 파일: `docs/original_plan/research_reports/OP-001.md`, `OP-002.md`, `OP-120.md`, OP-120 고정 사례와 canonical evidence. 코드, 서비스 데이터, 학습 데이터, 모델, safety 규칙, 시뮬레이션은 변경하지 않았다.
- OP-001은 단위 테스트의 고정 manifest 검사와 canonical 감사의 PDF 바이트 재해시 역할을 분리했다. OP-002는 59쪽 전체를 여섯 접촉 시트로 확인하고 3~10·11~27·28~36·37~55·56~58·59쪽을 시장 문제·기술·준비·사업화·회사·안전보안으로 분류했다.
- OP-001/002는 요구 단계 `IMPLEMENTED`를 유지한다. 서비스 통합, 운영, 외부 공증은 새로 주장하지 않았다.
- 검증: 보고서 수용 검사 `True/True`, 관련 pytest `31 passed`, Ruff PASS, manifest/completion audit PASS, OP-120 재생 2회 SHA-256 `8facfc9566f29c3bf51bd44fea0e415565a86ec7b2ba5f394f7867223d2863e0` 동일. 독립 검토는 `0/2/1`에서 최종 Critical/Important/Minor `0/0/0`으로 끝났다.
- GitHub Actions `Original plan evidence` 실행 `29913248935`가 canonical 재생, requirement contract tests, Ruff를 포함한 전체 65단계 검사를 통과했다.
- OP-120 관측값: 유효 보고서 `20→22`, 누락·부적합 `100→98`; 전체 상태는 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, 최종 판정은 계속 `BLOCKED`다.
- frozen 평가와 replay/slice 변화: 제품 코드·데이터·모델을 바꾸지 않았으므로 기존 256건 평가의 일곱 지표 delta와 weakest-slice delta는 모두 `0`이다.
- 병목 5개: 누락·부적합 보고서 98개, 비외부 단계 미달 43개, OP-039 외부 검증, 전체 검증 영수증, 독립 검토 영수증.
- 다음 세 반복: OP-003/004 보고서 보강, OP-005/006 보고서 보강, OP-007/008 보고서 보강.
# 2026-07-22 OP-003/004 연구보고서 보강 반복

- 선택 단계/과제: 원본 요구사항과 증거 기준 고정; OP-003 p.15 여섯 기술 블록의 독립 등록과 OP-004 p.16~24 입력·처리·출력 대조 보고서 보강.
- 데이터셋: `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `bfb0e4d0070ac87d807fe2e88c2206b5508e89bcdb641025a96b589080a8436d`.
- 변경 파일: `docs/original_plan/research_reports/OP-003.md`, `OP-004.md`, `OP-120.md`, OP-120 고정 사례와 canonical evidence. 제품 코드, 서비스 데이터, 학습 데이터, 모델, 안전 규칙, 시뮬레이션은 변경하지 않았다.
- OP-003은 Data Lake, 안전, 효과 추론, 다중제약 최적화, Closed-loop, 바이오센서·유전자 블록을 manifest C~J의 독립 요구사항 묶음과 K/L 공통 통합·감사 항목에 연결했다.
- OP-004는 p.16~24의 입력·처리·출력을 master context 6.1~6.9와 대조했다. 독립 검토에 따라 원문 직접 계약과 후속 구현의 계보·동의·운영 상태를 명시적으로 분리했다.
- 두 요구사항은 `IMPLEMENTED / COMPLETE`다. 모든 하위 요구의 통합·운영·외부 검증 완료를 주장하지 않는다.
- 검증: 보고서 수용 검사 `True/True`, 관련 pytest `31 passed`, Ruff PASS, manifest/completion audit PASS, OP-120 재생 2회 SHA-256 `fc2f01bec47c55373fac397b9704691deb5f0dabcbde745b6d89e19d15918143` 동일. 독립 검토는 `0/1/0`에서 최종 Critical/Important/Minor `0/0/0`으로 끝났다.
- GitHub Actions `Original plan evidence` 실행 `29914515047`이 canonical 재생, requirement contract tests, Ruff를 포함한 전체 검사를 통과했다.
- OP-120 관측값: 유효 보고서 `22→24`, 누락·부적합 `98→96`; 전체 상태는 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`, 최종 판정은 계속 `BLOCKED`다.
- frozen 평가와 replay/slice 변화: 코드·데이터·모델을 바꾸지 않아 기존 256건 평가의 일곱 지표 delta와 weakest-slice delta는 모두 `0`이다.
- 병목 5개: 누락·부적합 보고서 96개, 비외부 단계 미달 43개, OP-039 외부 검증, 전체 검증 영수증, 독립 검토 영수증.
- 다음 세 반복: OP-005/006 보고서 보강, OP-007/008 보고서 보강, OP-009/010 보고서 보강.

## 2026-07-24 최종 감사 정직성 보정

- OP-039 오너 판정을 `self_review`로 보존하고 EXTERNAL 근거에서 제외했다. 권혁찬의 10개 판정은 모두 `pending`이다.
- 콘솔은 오너 등록을 차단하고 과제 공동연구원에게 `independent_of_implementation_team=false`를 강제한다. AI 초안 검토자와 동일인이면 경고를 기록한다.
- 운영 현황은 서로 다른 실제 프로필 1/5개, 새 대기 약사 초안 0건이다. 자동 데이터나 영수증은 생성하지 않았다.
- 최종 감사: `BLOCKED`, 비외부 단계 부족 0, 유효 보고서 120, 영수증 2종 유효, 차단 사유 `external_validation_gaps:1`만 남았다.
-
## 2026-08-04 KPI 교체 검토 완료

- KPI-1 최종 교체 2건을 검증했다. 결정은 `EDIT` 1건, `ACCEPT` 1건이며 추가 교체는 0건이다.
- KPI-1·4·5의 기존 거절 사례 65건을 검토 완료 교체 사례로 한 번에 반영했다. 지표별 사례와 결정은 각각 100건이며 거절 상태는 0건이다.
- 제출 ZIP과 CSV, 검토자 신원 선택 파일, 검증 결과를 원문 그대로 보존했다. CSV는 3행 23열로 다시 열어 표시 상태도 확인했다.
- 정답 무결성 감사의 남은 차단 사유는 기존 익명 검토 335건의 등록 신원 연결 부재다. 사례별 재검토가 아니라 기존 일괄 검토자와 등록 신원이 같은 사람이라는 확인 1회가 필요하다.
- 봉인, KPI 측정, 배포, 실제 트래픽, 훈련은 실행하지 않았다.

## 2026-08-04 기존 검토 신원 연결 자료

- 기존 익명 결정 335건을 KPI-1·3·4·5 전체에 한 번에 연결하는 단일 ZIP을 만들었다.
- 입력 필드는 `identity_link_status`와 `confirmed_at` 두 개뿐이다. 사례별 판정과 정답은 다시 입력하지 않는다.
- 원본 검토 ZIP SHA-256, 지표별 결정 수, 사례 ID 집합과 결정 내용의 SHA-256을 고정했다. 원문이나 범위가 바뀌면 가져오기를 차단한다.
- 유효한 반환 ZIP을 받으면 기존 결정의 검토자 이름과 등록 신원 참조만 바꾸고 나머지 결정 필드는 보존한다. 연결 기록은 봉인 provenance에 포함된다.

## 2026-08-04 신원 연결과 정답키 봉인 완료

- 등록 검토자의 확인을 과제 오너가 전달했다. 확인 시각은 검토자의 위임에 따라 전달을 받은 시각으로 기록했고 전달 경로와 시각 의미를 provenance에 분리했다.
- 기존 익명 결정 335건의 검토자 이름과 등록 신원 참조만 연결했다. 정답·판정·메모·판정 시각·검토 시간은 바꾸지 않았다.
- 교체 전·후 AI 응답은 하나의 패킷으로 가장하지 않고 KPI-1 3구간, KPI-4 2구간, KPI-5 2구간의 원본 패킷 해시로 묶었다.
- 정답 무결성 감사에서 KPI-1·3·4·5가 모두 PASS다. 네 봉인은 사례 100건, 최소 표본 100건을 충족하며 현재 사례·provenance와 일치한다.
- 최종 상태는 `status: READY`, `completion_status: READY`, 차단 사유 0건이다. 배포·실제 트래픽·훈련·최종 영수증 재발급은 실행하지 않았다.

## 2026-08-04 현재 외부 서비스 커밋 기준 재검증

- R&D local `main` HEAD는 `5ba4a99e77a54cdc6d35b6175c3d59201621bd81`, WellnessBox HEAD는 `7054d76670870bc31130006a84df3fa10aa46c78`이다. push·배포·실제 트래픽·훈련은 수행하지 않았다.
- `python scripts/run_final_session_preflight.py`는 `status=READY`, 종료 코드 0이다. R&D health, console, WellnessBox health는 모두 200이고 `/tips`, `/pharm/tips`는 로그인 307 뒤 200이다. H-005 화면은 사례 10개·선택 0개·사전 입력 주석 0개다. 운영 DB, runtime control, final state, operational receipt 파일 목록과 해시는 모두 변경되지 않았다.
- WellnessBox 정적 검증은 `npm run typecheck`, `npm run qa:syntax`, `npm run audit:encoding`, `npm run audit:route-method-exports`가 모두 종료 코드 0이다. 기존 서버를 전제로 한 `npm run qa:cde:regression`은 `localhost:3001/column` 연결 거부로 종료 코드 1이었고, 로컬 전용 preflight에서 동일 서비스의 읽기 전용 health·화면 검증은 READY였다.
- R&D 집중 테스트는 `tests/test_final_completion_audit.py`, `tests/test_completion_wizard.py`, `tests/test_final_session_preflight.py`를 실행했다. 유일한 실패는 `test_current_repository_is_ready_after_project_pharmacist_review`이며 현재 영수증의 `source_commit`이 최신 HEAD와 달라 READY를 기대할 수 없는 stale assertion이다. 구현을 바꿔 실패를 숨기지 않았다.
- 기존 두 영수증의 Ed25519 서명과 allowlist 공개키는 유효하지만 두 영수증의 `source_commit=f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`는 현재 R&D·WellnessBox HEAD와 모두 다르다. 최종 감사는 exit code 1, `status=BLOCKED`, `goal_complete=false`이며 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`이다.
- 사람 검토용 패킷을 `etc/final_completion_review_handoff_20260804/final_completion_review_handoff_20260804.zip`에 만들었다. 71개 파일, 중복 경로 0, 0바이트 항목 0, SHA-256 `c001e69a08445bc61e584b1591b596190d6933f3cb0533d76015b4481c12e072`이다. 개인키와 작업 지시문은 넣지 않았다.
- 완료 마법사는 현재 `3/13`이다. H-003 학습 게이트는 계속 NO-GO이며 학습·승격을 실행하지 않았다. 사람의 현재 커밋 검증·독립 검토·서명·실제 완료 마법사 기록이 없으므로 연구 완료로 판정하지 않는다.
## 2026-08-04 현재 세션 재확인

- 지정한 첫 확인 명령을 다시 실행했다. KPI-1·3·4·5 정답 무결성은 `4/4 READY`, 승인 전용 데이터셋은 `6건 READY`, 연구계획 요건 감사는 `120/120 PASS`였다.
- `C:\dev\wellnessbox`가 실제 저장소로 존재하고 HEAD는 `7054d76670870bc31130006a84df3fa10aa46c78`로 재확인됐다. R&D 소스 검증 기준은 `ac92ae0e47faa8362a9f7d6fb1fcc7bb4fab2ce0`이며 이후 local `main`에는 문서-only 인계 커밋만 포함됐다. 두 저장소 모두 push하지 않았다.
- 기존 최종 영수증 2개는 파일과 Ed25519 서명 자체는 읽히지만 `source_commit=f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`라서 현재 저장소 HEAD에 대한 영수증이 아니다. `run_final_completion_audit.py`는 `status=BLOCKED`, `goal_complete=false`를 반환했고 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`이다.
- `run_final_session_preflight.py`는 읽기 전용 임시 실행에서 `status=READY`였다. 그러나 완료 마법사 상태는 현재 세션 사람 단계 0건으로 `3/13`이며, H-003은 계속 `NO-GO`다. 사람의 검토·판정·서명은 대신 입력하지 않았다.
- 현재 세션에서 새 사람 자료나 새 서명 영수증은 확인되지 않았다. 기존 `operational_receipts/local-*.json`, `uploads/`, `seals/discarded/`는 수정·삭제·stage하지 않았다.
- 다음 실제 조건은 현재 서비스 커밋 기준 검증 결과와 독립 검토 결과를 사람이 제출하고, 그 결과에 사람이 직접 서명한 두 영수증을 저장한 뒤 완료 마법사를 실제 기록 기준으로 갱신하는 것이다. 그 전에는 연구 완료로 판정하지 않는다.

## 2026-08-04 fresh 외부 서비스 검증

- 지정한 첫 확인 명령을 fresh로 실행했다. `git log --oneline -3`의 local `main` 최신 커밋은 `b2be303`이며, 정답키 감사는 `4/4 READY`, 승인 전용 데이터셋은 `6건 READY`, 연구계획 요건 감사는 `120/120 PASS`였다.
- `python scripts/run_final_completion_audit.py`는 exit code `1`, `status=BLOCKED`, `goal_complete=false`를 반환했다. 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`이며, 감사 산출물 SHA-256은 `3430a4ab382b7403d9cc16e34f6e7d8c42f6ad0307e847e5a0db00a992f37c76`이다.
- WellnessBox HEAD `7054d76670870bc31130006a84df3fa10aa46c78` 기준 `run_final_session_preflight.py`는 `READY`였다. health 4개는 모두 200, `/tips`와 `/pharm/tips`는 로그인 307 후 페이지 200, H-005 화면은 10건·선택 0건·미리 입력된 근거 0건이었다. 실제 DB·runtime controls·final state·영수증 목록과 해시는 모두 unchanged였다.
- 같은 HEAD에서 WellnessBox `typecheck`, `qa:syntax`, `audit:encoding`, `audit:route-method-exports`는 모두 exit code `0`이었다. push·배포·실제 트래픽·훈련·승격은 실행하지 않았다.
- 완료 마법사 상태는 여전히 `3/13`이고 이번 세션의 실제 프로필·AI 초안 전수 검토·정책·문체·고위험 10건·최종 서명 기록이 없다. 새 업로드도 없으며, 기존 미추적 운영 자료는 수정·삭제·stage하지 않았다.

## 2026-08-04 반복 차단 재확인

- 첫 확인 명령을 다시 실행했다. 정답키 감사 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`였다.
- 현재 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`다. 차단 사유는 동일하게 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`이며 requirements/reports는 `120/120`, external gap은 0건이다.
- 완료 마법사 상태는 `3/13`이다. 이번 세션의 H-007·H-003·H-002·H-004·H-005·H-006 실제 기록이 없고, 기존 영수증은 계속 `source_commit=f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`다.
- 새 ZIP·업로드·독립 검토 결과·서명은 확인되지 않았다. 사람 자료 없이 영수증이나 판정을 생성하지 않았고, H-003 `NO-GO`를 유지했다.

## 2026-08-04 사용자 재개 fresh blocked audit 1

- 기준 파일 6개와 현재 저장소를 다시 읽었다. 첫 확인 명령은 정답키 `4/4 READY`, 승인 데이터셋 `6건 READY`, 연구계획 `120/120 PASS`를 반환했다.
- 현재 WellnessBox `7054d76670870bc31130006a84df3fa10aa46c78` 기준 final preflight는 `READY`였다. health는 모두 200, `/tips`·`/pharm/tips`는 307 후 200, H-005는 10건·선택 0건·미리 입력된 근거 0건이며 저장소 변경은 없었다.
- WellnessBox 정적 검증 4종은 모두 exit code `0`이다. 최종 감사는 `BLOCKED`, `goal_complete=false`이며 두 영수증 차단 사유가 반복됐다.
- 완료 마법사는 `3/13`이고 새 업로드는 0건이다. 기존 영수증 2개는 `status=PASS`지만 `source_commit=f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`다. 사람의 독립 검토·판정·서명을 만들지 않았다.

## 2026-08-04 사용자 재개 fresh blocked audit 2

- 지정 첫 명령 결과는 동일했다: 정답키 `4/4 READY`, 승인 데이터셋 `6건 READY`, 연구계획 `120/120 PASS`, 최종 감사 `BLOCKED`, 완료 마법사 `3/13`.
- 현재 서비스 HEAD는 `7054d76670870bc31130006a84df3fa10aa46c78`이다. 기존 final preflight와 정적 검증 결과는 `READY` 및 4종 exit code 0으로 유지된다.
- `op039_external_review_package.zip`은 SHA-256 `59c9abf83f648ef1089d5c853041031beff454e7be00fb0f70e58348b2681d9f`, 사례 10건, 중복 0건이며 실제 검토 결과·서명은 포함하지 않는다. handoff ZIP도 SHA-256 `c001e69a08445bc61e584b1591b596190d6933fcb0533d76015b4481c12e072`, 71건, 중복 0건이다.
- 새 서명 자료는 없으므로 두 차단 사유를 유지한다. 사람의 판정·서명과 H-003 `NO-GO`를 우회하지 않았다.

## 2026-08-04 사용자 재개 fresh blocked audit 3

- 지정 첫 명령을 다시 실행했다. 정답키는 `4/4 READY`, 승인 전용 데이터셋은 `6건 READY`, 연구계획 요건은 `120/120 PASS`였다.
- `python scripts/run_final_completion_audit.py`는 exit code `1`, `status=BLOCKED`, `goal_complete=false`를 반환했다. 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`로 동일하다.
- 현재 WellnessBox HEAD는 `7054d76670870bc31130006a84df3fa10aa46c78`이다. 새 검토 결과·서명·업로드는 없고, 기존 두 영수증은 `source_commit=f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`에 서명되어 현재 커밋과 불일치한다.
- 완료 마법사 상태는 `3/13`이며 이번 세션 프로필·정책·문체·고위험 검토·최종 서명 기록은 없다. H-003 `NO-GO`, frozen/replay/weakest-slice delta `0`을 유지했다.

## 2026-08-05 처리용 파일 묶음

- `etc/completion_processing_files.zip`을 생성했다. SHA-256은 `18af37078444a9b2b8c482c8bfa6f28a896f293cda003c8ad0dfa8ff6969dd7d`이다.
- 압축 파일은 처리 대상 71개, 중복 경로 0개, OP-039 사례 10건을 포함한다. README·Markdown과 새 작업 주체 문구는 포함하지 않았다.
- 현재 서비스 스냅샷, 최종 감사 자료, 기존 영수증 원본, OP-039 사례 원본과 원본 검토 양식을 포함했다. 원본 파일의 provenance·시각·서명 정보는 변경하지 않았다.

## 2026-08-05 사용자 재개 fresh blocked audit 1

- 지정 첫 감사 결과는 정답키 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`였다.
- WellnessBox HEAD `7054d76670870bc31130006a84df3fa10aa46c78` 기준 읽기 전용 preflight는 `READY`였다. health 4개는 모두 200, `/tips`·`/pharm/tips`는 307 후 200, H-005는 10건·선택 0건·미리 입력된 근거 0건이었다. 저장소·DB·runtime controls·final state·영수증 목록과 해시는 unchanged였다.
- WellnessBox 정적 검증 4종(`typecheck`, `qa:syntax`, `audit:encoding`, `audit:route-method-exports`)은 모두 exit code `0`이다.
- 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`이며 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`다. 완료 마법사는 UTF-8 모드에서 `3/13`이다.
- 업로드 폴더의 유일한 자료 `op039_external_validation.json`은 SHA-256 `7a4f44c6b35ca3dc6d40494ce2844b5a02516440197cb5cac58b03cec0ba0518`이고, 독립성 false·프로젝트 공동연구자 자료라서 새 외부 검토 자료로 반영하지 않았다. 기존 영수증과 H-003 `NO-GO`도 유지했다.

## 2026-08-05 사용자 재개 fresh blocked audit 2

- 지정 첫 명령 결과는 동일했다: 정답키 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`, 최종 감사 exit code `1` 및 `BLOCKED`, 완료 마법사 `3/13`.
- 현재 WellnessBox HEAD `7054d76670870bc31130006a84df3fa10aa46c78` 기준 preflight는 다시 `READY`였다. health 4개는 200, `/tips`·`/pharm/tips`는 307 후 200, H-005는 10건·선택 0건·미리 입력된 근거 0건이며 저장소와 운영 상태 해시는 unchanged였다.
- 최종 감사 산출물 SHA-256은 `3430a4ab382b7403d9cc16e34f6e7d8c42f6ad0307e847e5a0db00a992f37c76`이고, 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`로 동일하다.
- 새 ZIP·업로드·독립 검토·서명은 없었다. 기존 업로드와 두 영수증의 provenance·해시·불일치 상태를 유지하고, 사람의 판정·서명과 H-003 `NO-GO`를 우회하지 않았다.

## 2026-08-05 사용자 재개 fresh blocked audit 3

- 지정 첫 명령을 다시 실행했다. 정답키 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`였다.
- 현재 WellnessBox HEAD `7054d76670870bc31130006a84df3fa10aa46c78` 기준 preflight는 exit code `0`이다. 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`를 반환했다.
- 최종 감사 산출물 SHA-256은 `3430a4ab382b7403d9cc16e34f6e7d8c42f6ad0307e847e5a0db00a992f37c76`이고 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`로 세 번째 연속 반복됐다.
- 완료 마법사는 UTF-8 상태 출력 기준 `3/13`이다. 새 업로드·독립 검토·유효한 현재 커밋 영수증·서명은 없으며, 기존 자료와 H-003 `NO-GO`를 유지했다.

## 2026-08-05 반환 ZIP 처리

- 사용자가 반환한 `C:\Users\hjyeo\Downloads\completion_processing_files_completed.zip`을 원본 그대로 검사했다. ZIP SHA-256은 `c2143d565a33088ea32e9d57c9a575f8397a97fc65dc9694fd8871f9d662cd3a`, 파일 77개, 중복 경로 0개, OP-039 사례 10건이다.
- ZIP의 자체 처리 결과도 `BLOCKED`, `goal_complete=false`였다. 내장 검증기를 임시 압축 해제 경로에서 다시 실행한 결과는 TypeScript 모듈이 부분 ZIP에 없어 `FAIL`이었고, 전체 저장소·전체 build·canonical audit를 수행하지 못했다는 범위 제한이 확인됐다.
- `op039_preliminary_evidence_review_v1.json`은 10건 사전 근거 검토이며 `human_signature_present=false`, `licensed_reconfirmation_required=true`, `independent_external_validation_satisfied=false`다. 기존 두 영수증은 원문·해시·서명·`source_commit=f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`를 유지한다.
- 실제 반영 범위는 채팅 오류 노출 차단, 공백 입력 정규화, 스트림 실패 마커, 버튼·중복 이벤트 보정 7개 서비스 파일과 독립 검토 신뢰루트 분리 2개 R&D 파일이다. OP-039 `EXTERNAL`을 `IMPLEMENTED`로 바꾸는 manifest 변경은 외부 검증을 가장할 수 있어 반영하지 않았다.
- 반영 후 서비스 HEAD는 `0bbee48bdb6779ae338b121331b678aacc9ed777`, R&D local `main` HEAD는 `e295fd9bdfee15f3089621b5bc2492ce0d9d47a1`이다. R&D 집중 테스트 58개, 서비스 정적 검증 4종, preflight exit code 0을 확인했다. 최종 감사는 `BLOCKED`, `goal_complete=false`다.

## 2026-08-05 사용자 재개 fresh audit 2 재확인

- 지정 첫 확인 명령을 현재 상태에서 다시 실행했다. 정답키 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`였다.
- 현재 WellnessBox local `main` HEAD는 `0bbee48bdb6779ae338b121331b678aacc9ed777`, R&D local `main` HEAD는 `0574ccb`이다. push·배포·실제 트래픽·훈련은 실행하지 않았다.
- 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`다. 산출물 SHA-256은 `74c486b24b9b43d66f05ae202d2f6d234e6a1571f1870326644b3f99d973abd2`이며 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`다.
- 완료 마법사는 UTF-8 상태 출력 기준 `3/13`이다. 이번 세션의 실제 프로필·초안 검토·정책·문체·고위험 10건 검토·두 서명 기록은 충족되지 않았다. 기존 자료를 승격하지 않았고 H-003 `NO-GO`를 유지했다.

## 2026-08-05 사용자 재개 fresh audit 3 재확인

- 지정 첫 확인 명령을 세 번째로 다시 실행했다. 정답키 `4/4 READY`, 승인 전용 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`였다.
- 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`다. 감사 산출물 SHA-256은 `74c486b24b9b43d66f05ae202d2f6d234e6a1571f1870326644b3f99d973abd2`이며 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`가 세 번째 연속으로 반복됐다.
- 현재 local main은 R&D `9233539`, WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777`다. 다운로드 폴더에는 기존 반환 ZIP 외 새 자료가 없고, 완료 마법사는 `3/13`이다.
- 실제 현재 커밋 검증·독립 검토·두 서명·마법사 사람 기록이 없으므로 영수증·판정·서명을 생성하거나 기존 자료를 승격하지 않았다. H-003 `NO-GO`를 유지했다.

## 2026-08-05 반환 완료 ZIP 처리

- 사용자가 반환한 `C:\Users\hjyeo\Downloads\completion_human_processing_completed.zip`을 원본 그대로 검사했다. ZIP SHA-256은 `cd1ba3ef6a12fdff47dfbc68ba7a236996d3218b8ccdc4d063b2998b1c234bf1`, 항목은 76개, 중복 경로는 0개, 디렉터리 항목은 0개, OP-039 사례는 10건이다.
- `package_manifest.json`의 75개 파일 경로·바이트 수·SHA-256은 모두 ZIP 내용과 일치했고, 저장소 HEAD도 매니페스트의 R&D `2cb86496a64f354f73988a4a40599c2a5466d042` 및 WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777`와 일치했다. ZIP 항목 71개는 현재 저장소와 동일하고 변경 항목은 진행 기록·예비 OP-039 결과·사람 서명 기록 4개였다.
- OP-039 결과는 사례 ID·10건·판정 10건·사례 해시가 일치했지만 `PRELIMINARY_REVIEW_COMPLETE`, `identity_disclosed=false`, `signature_name` 공란이며 면허 재확인과 외부 독립 검증이 필요하다고 명시했다. 임시 저장소에서 실제 importer를 실행한 결과 `reviewer_name_missing, reviewer_organization_missing`으로 거부됐고 대상 저장 경로도 생성되지 않았다.
- 반환된 검증 영수증은 `source_commit=f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`라 현재 HEAD와 불일치했다. 독립 검토 영수증은 독립 검토 신뢰 루트가 비어 있어 검증되지 않았다. 두 영수증과 네 변경 기록은 현재 저장소에 반영하지 않았다.
- 현재 재감사 결과는 정답키 `4/4 READY`, 승인 데이터셋 `6건 READY`, 연구계획 요건 `120/120 PASS`, WellnessBox 정적 검증 4종 exit code `0`, 완료 마법사 `3/13`, 최종 감사 exit code `1`·`BLOCKED`·`goal_complete=false`다. 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`다. H-003 `NO-GO`를 유지했다.

## 2026-08-05 최종 영수증 경로 보완

- 최종 세션 콘솔의 실제 모드가 기존 서명 키를 사람이 제공하도록 바꾸고, 키가 없을 때 자동 생성하지 않도록 했다. 단일 키로 검증 영수증과 독립 검토 영수증을 함께 만드는 경로도 차단했다.
- 검증용·독립 검토용 Ed25519 키와 발급자를 각각 입력받고, 서로 다른 공개 키와 발급자인지 확인한 뒤 별도 신뢰 루트에 등록하도록 구현했다. 현재 영수증 파일과 정책에는 실제 서명 자료를 쓰지 않았다.
- 문구도 `예비 약사 사전 검토`로 정리했다. H-003 `NO-GO`와 KPI-2 3차년도 측정 경계는 유지했다.
- 브랜치 검증은 R&D 집중 테스트 `39 passed`, 서비스 정적 검증 4종 exit code `0`이다. 현재 R&D local `main` HEAD `94d28d0`, WellnessBox HEAD `0bbee48bdb6779ae338b121331b678aacc9ed777`이다.
- 현재 최종 감사는 exit code `1`, `status=BLOCKED`, `goal_complete=false`, 산출물 SHA-256 `4315fd5d383b36a3850642537f377abee7e47bd491d0bd3422e6a8b3fe2706ff`다. 차단 사유는 두 영수증의 현재 커밋·독립 신뢰 자료 부재로 동일하다.

## 2026-08-05 최신 처리 ZIP 갱신

- `etc/completion_human_processing_package.zip`을 현재 R&D `main`과 WellnessBox HEAD 기준으로 갱신했다. ZIP SHA-256은 `eabd758398faa9c26f3d3527111e5f67270f0e198f2e71f17a2a51fa58bb4d35`다.
- ZIP은 78개 항목·매니페스트 파일 77개·중복 경로 0개·OP-039 사례 10건이며, 매니페스트 내부 SHA-256과 현재 저장소 파일 바이트가 모두 일치한다.
- 별도 서명 경로를 포함한 완료 콘솔·테스트 파일 3개를 추가했고, 작업 지시 파일과 개인 키 파일은 포함하지 않았다. R&D HEAD는 `b5ff12cc1fb6e0ea823cbad9576f924bb6806784`, WellnessBox HEAD는 `0bbee48bdb6779ae338b121331b678aacc9ed777`다.
- 실제 검토·판정·서명은 아직 없으므로 최종 감사 `BLOCKED`, 완료 마법사 `3/13`, H-003 `NO-GO`를 유지한다.

## 2026-08-06 단일 처리 ZIP 및 importer 보완

- `scripts/import_completion_processing_package.py`를 추가했다. importer는 ZIP SHA-256, 중복·경로 이탈·지시 파일·개인 키, 매니페스트 내부 해시, 저장소 provenance, 현재 파일 바이트, OP-039 10건, 예비 약사 사전 검토 기록, 완료 마법사 13단계, 두 영수증의 현재 커밋·서명·독립 신뢰 루트를 검사한다.
- importer는 모든 자료가 READY일 때만 `--apply`로 사람 자료를 반영하고, 반영 전 원본을 `etc/import_backups`에 보관한다. 이번 세션에는 `--apply`를 실행하지 않았다.
- 집중 테스트는 `42 passed`다. 새 단일 ZIP은 `C:\dev\wellnessbox-rnd\etc\completion_human_processing_package.zip`, SHA-256은 `97b8b65b8638d33442ee617fa0b046c0d12f190836e0970efbd6b8acdf43acbe`, 81개 항목·매니페스트 파일 80개·중복 0건·OP-039 사례 10건이다.
- 현재 ZIP의 구조·provenance·파일 해시는 PASS지만, 사람 자료는 예비 OP-039 결과의 역할 불일치, 현재 커밋과 다른 두 영수증, 완료 마법사 `9/13`으로 `ready_to_apply=false`다. 사람의 판정·서명은 만들지 않았다. H-003 학습 게이트 `NO-GO`와 훈련·승격 금지는 유지한다.

## 2026-08-05 현재 상태 재감사

- 지정 첫 확인 명령을 현재 local `main`에서 다시 실행했다. R&D HEAD는 `7fa57da`, WellnessBox HEAD는 `0bbee48bdb6779ae338b121331b678aacc9ed777`다. push·배포·실제 트래픽·훈련은 실행하지 않았다.
- 정답키 감사는 `4/4 READY`, 승인 전용 데이터셋은 `6건 READY`·위반 0건, 연구계획 요건 감사는 `120/120 PASS`다. WellnessBox `typecheck`, `qa:syntax`, `audit:encoding`, `audit:route-method-exports`도 모두 exit code 0이다.
- 최종 감사는 exit code 1, `status=BLOCKED`, `goal_complete=false`이며 산출물 SHA-256은 `4315fd5d383b36a3850642537f377abee7e47bd491d0bd3422e6a8b3fe2706ff`다. 차단 사유는 `validation_receipt_missing_or_invalid`, `independent_review_receipt_missing_or_invalid`다.
- 완료 마법사는 `9/13`이다. TRAIN 단계는 `NO-GO`로 건너뛰었고, 실제 서버 응답·승인 전용 데이터셋 단계·최종 감사가 남아 있다. 다운로드 폴더에는 새 ZIP이 없고, 기존 반환 ZIP `cd1ba3ef...`은 현재 importer에서 구조 불일치 6건과 사람 자료 거부로 반영하지 않았다.

## 2026-08-05 현재 main 기준 ZIP 재생성

- local `main` fast-forward 뒤 실제 파일 바이트를 다시 담아 `etc/completion_human_processing_package.zip`을 갱신했다.
- 새 ZIP SHA-256은 `31e45c4d72657bbeba136202313d4b068709e85aab23ea98bd2bc80a70f54c8d`이며 81개 항목·매니페스트 80개·중복 0건·OP-039 사례 10건이다.
- 현재 importer 결과는 구조 `READY`, source byte 일치, `ready_to_apply=false`다. OP-039 역할 불일치, 이전 커밋 영수증, 완료 마법사 `9/13`이 남아 있다. 사람의 판정·서명은 생성하거나 반영하지 않았다.

## 2026-08-05 완료 마법사 산출물 재검증 보완

- `completion_wizard.py`가 저장된 승인 전용 manifest와 최종 감사 산출물을 직접 재검증하도록 보완했다. 기존 파일의 판정이나 서명은 변경하지 않았다.
- 집중 테스트는 `75 passed`다. 마법사 상태는 `10/13`으로 갱신됐고, DATASET은 승인 초안 6건으로 완료, AUDIT는 저장된 `BLOCKED` 결과로 표시된다.
- 현재 main은 R&D `c5e34e2`, WellnessBox `0bbee48bdb6779ae338b121331b678aacc9ed777`다. H-003 학습 게이트 `NO-GO`와 훈련·승격 금지는 유지한다.
- 현재 ZIP은 R&D `c5e34e2` 기준으로 재생성했으며 SHA-256은 `813967fe5ffac8cb20c967d7e4517a582ff2f543d78946c004899cf386db376d`다. importer 구조 검증은 `READY`, 사람 자료 `ready_to_apply=false`다.
