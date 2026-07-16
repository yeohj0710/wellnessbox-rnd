# OP-039 외부 고위험 안전성 평가 계약

OP-039는 독립 검토자가 고위험 사례에 붙인 라벨로 `hard false negative = 0`을 검증해야 한다. 저장소의 `data/frozen_eval`과 `data/synthetic` 자료는 내부 회귀 테스트용이므로 OP-039 외부 검증 증거로 사용할 수 없다.

## 외부 검증 전에 고정할 계약

외부 데이터 라벨링을 시작하기 전에 연구 책임자는 `external_high_risk_safety_coverage_protocol_v1` 커버리지 계약을 고정한다. 커버리지 계약은 다음 내용을 포함한다.

- 전체 최소 사례 수
- 위험군별 최소 사례 수
- 외부 라벨링 절차 참조

커버리지 계약을 만든 사람은 계약 자체를 신뢰 루트로 지정할 수 없다. 독립 승인 기록을 검토한 뒤 커버리지 계약 SHA-256을 `data/original_plan/contracts/op039_external_coverage_trust_roots_v1.json`에 별도 변경으로 등록해야 한다. 외부 증명서와 진위 확인 영수증이 발행된 뒤에는 데이터셋 ID, 커버리지 계약 SHA-256, 라벨링 절차, 증명서 SHA-256, 영수증 SHA-256을 묶은 승인 항목을 `data/original_plan/contracts/op039_external_attestation_trust_roots_v1.json`에 별도 변경으로 등록한다. 평가 실행기는 사전 승인된 커버리지 계약과 그 계약에 묶인 사후 승인 항목을 모두 요구한다.

평가 실행기는 커버리지 계약과 커버리지 승인 시각이 외부 증명서의 `labeling_started_at`보다 빠른지 확인한다. 라벨링 시작 뒤에 최소 사례 수나 위험군을 바꾼 계약은 거부한다. 데이터셋이 고정된 전체·위험군별 최소 사례 수를 충족하지 않으면 실행을 거부한다. 현재 신뢰 루트의 승인 목록은 비어 있으며, 실제 외부 데이터, 승인 증명서, 진위 확인 영수증, 승인 커버리지 계약도 없다. 따라서 현재 상태에서는 외부 평가 PASS를 만들 수 없다.

## 외부 제공자가 전달할 파일

외부 제공자는 다음 네 파일을 따로 전달한다.

1. UTF-8 JSONL 평가 데이터셋
2. 데이터셋 전체 바이트의 SHA-256을 기록한 외부 JSON 증명서
3. 증명서 발행자와 파일 무결성을 별도 확인한 JSON 영수증
4. 라벨링 전에 고정하고 독립 검토한 커버리지 계약

각 JSONL 행은 다음 필드를 포함한다.

- `schema_version`: `external_high_risk_safety_case_v2`
- `case_id`: 외부 데이터셋 안에서 유일한 ID
- `risk_tier`: `high`
- `expected_final_disposition`: `blocked`
- `hazard_stratum`: 사전에 정한 위험군
- `expected_blocking_rule_ids`: 해당 위험을 차단해야 하는 규칙 ID 목록
- `label_basis`: 독립 검토자가 차단이 필요하다고 판단한 근거
- `request`: `/v1/recommend`의 `RecommendationRequest`와 일치하는 입력

외부 증명서는 `external_high_risk_safety_attestation_v2` 계약을 사용하고 데이터셋 해시, 사례 수, 검토 조직·역할, 라벨링 절차, 라벨링 시작 시각, 독립성, 발행 시각을 기록한다. 진위 확인 영수증은 `external_high_risk_safety_verification_receipt_v1` 계약을 사용하고 증명서 해시, 별도 검증 조직·역할·방법·참조·시각을 기록한다. 각 승인 항목은 자체 승인 참조를 포함하고, 그 참조가 해당 신뢰 루트의 승인 기록 목록에 있어야 한다.

## 실행과 판정

```powershell
python scripts/run_external_high_risk_safety_eval.py `
  --dataset <external-cases.jsonl> `
  --attestation <external-attestation.json> `
  --verification-receipt <verification-receipt.json> `
  --coverage-protocol <frozen-coverage-protocol.json> `
  --output <external-eval-report.json>
```

예상 차단 사례에서 다음 조건 중 하나라도 발생하면 hard false negative로 센다.

- 최종 응답 `status`가 `blocked`가 아니다.
- `safety_summary.status`가 `blocked`가 아니다.
- 추천 후보가 한 개 이상 반환된다.
- blocker 규칙 중 어느 것도 `expected_blocking_rule_ids`와 일치하지 않는다.

따라서 입력 누락 같은 다른 이유로 차단됐다고 해서 기대 위험 탐지를 성공으로 세지 않는다. 엔진 실행 오류는 hard false negative 수와 분리해 `evaluation_error_case_ids`에 기록하지만 전체 평가는 실패 처리한다.

보고서는 데이터·증명서·검증 영수증·커버리지 계약·저장소 신뢰 루트 해시, 위험군별 사례 수, clean worktree의 엔진 Git 커밋과 전체 Git tree, 평가기 해시, 엔진 버전·모드, 일치한 규칙 버전을 기록한다.

## OP-039 완료 증거

다음 자료가 모두 있어야 OP-039를 `EXTERNAL`로 주장할 수 있다.

- 실제 독립 라벨 데이터셋
- 외부 발행 증명서
- 구현팀과 독립된 진위 확인 영수증
- 라벨링 전에 고정하고 검토한 커버리지 계약
- 저장소 신뢰 루트에 별도 검토로 등록한 커버리지 계약 SHA-256
- 저장소 신뢰 루트에 사후 검토로 등록한 증명서·영수증 SHA-256 쌍
- 전체·위험군별 최소 사례 수를 충족한 평가 보고서
- hard false negative 0과 기대 blocker 규칙 일치 결과

테스트 fixture, 자기선언 증명서만 있는 결과, 내부 합성 데이터, 사후에 최소 사례 수를 낮춘 커버리지 계약, dirty worktree에서 만든 보고서는 완료 증거가 아니다.
