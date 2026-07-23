# PROGRESS

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
