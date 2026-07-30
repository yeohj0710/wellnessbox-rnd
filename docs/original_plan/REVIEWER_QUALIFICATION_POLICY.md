# 검토자 자격 단계 정책

## 먼저 확인할 결론

이 과제의 안전 검토자 두 사람은 2026-07 현재 아직 약사 면허를 받지 않았다. 두 사람 모두 2027-01에 면허를 받을 예정이다. 따라서 2차년도인 지금 수행하는 안전 검토는 **예비 약사 사전 검토**이며, 면허를 받은 뒤인 3차년도에 같은 사례를 **약사 검토**로 다시 수행한다. 최종 연구 마감은 2027-10이므로 3차년도 재검토를 마칠 시간이 있다.

2차년도에는 연구를 완료할 의무가 없다. 그래서 지금 단계에서 "약사가 검토했다"고 쓰지 않는다. 쓰면 사실과 다르고, 3차년도 재검토의 의미도 사라진다.

## 두 단계의 구분

| 항목 | 2차년도 (지금) | 3차년도 (면허 취득 후) |
|---|---|---|
| 검토자 자격 | 예비 약사 (`pharmacist_candidate`) | 약사 (`licensed_pharmacist`) |
| 면허 상태 | `not_yet_licensed` | 면허 번호 보유 |
| 기록되는 증거 성격 | `pharmacist_candidate_preliminary_safety_review` | `licensed_pharmacist_expert_safety_review` |
| 보고서에 쓸 표현 | "과제 참여 예비 약사가 사전 검토했다" | "약사가 검토·평가했다" |
| OP-039 `EXTERNAL` 단계 승격 | 하지 않는다 | 별도 외부 기관 평가와 함께 판단한다 |
| 재검토 의무 | 있다 (`requires_licensed_reconfirmation: true`) | 없다 |

## 왜 지금 면허 번호를 받지 않는가

받을 값이 없기 때문이다. 예비 약사에게 면허 번호를 요구하면 빈 값이나 `not_collected` 같은 자리표시자가 들어가고, 그 자리표시자가 나중에 "자격을 확인했다"는 근거로 잘못 읽힌다. 실제로 2026-07-24 기록에는 `pharmacist_license_id: "not_collected"`와 `credential_verification_method: "project_owner_attestation"`이 남아 있었다.

그래서 2차년도 입력 화면은 **이름과 소속만** 받는다. 두 값은 과제 등록 정보와 대조한다. 검토자는 이미 과제 참여자로 등록돼 있으므로 신원 정보가 연동돼 있고, 별도 자격 서류를 다시 받을 이유가 없다.

3차년도에는 면허 번호와 확인 방법을 받는다. 그때는 실재하는 값이다.

## 시스템이 강제하는 것

`src/wellnessbox_rnd/governance/reviewer_credentials.py`가 아래를 검사한다. 자격 단계 계약은 `data/original_plan/contracts/op039_reviewer_identity_registry_v1.json`에 있다.

- 검토자 이름이 과제 오너나 시스템 계정이면 거부한다. 이름을 정규화한 뒤 별칭까지 대조하므로 `여 형준`이나 `Yeo Hyeongjun` 같은 변형도 막힌다.
- 검토자가 등록된 과제 참여자가 아니면 거부한다. 소속이 등록 정보와 다르면 거부한다.
- 검토자가 H-003 AI 초안 원장에 있는데 `was_ai_draft_reviewer`를 false로 신고하면 거부한다.
- 검토자가 `licensed_pharmacist`를 주장하면 거부한다. 현재 계약상 단계는 `pharmacist_candidate`다.
- 예비 약사 검토는 OP-039를 `EXTERNAL` 단계로 올리지 않는다. 완료 기록에 `requires_licensed_reconfirmation: true`가 남는다.

## 3차년도에 무엇을 바꾸는가

면허를 받은 뒤 `op039_reviewer_identity_registry_v1.json`의 `qualification_stage`를 아래처럼 바꾼다. 코드는 고치지 않아도 된다.

- `current_period`를 `year3`로
- `current_stage`를 `licensed_pharmacist`로
- `license_status`를 면허 보유 상태로
- 각 `registered_reviewers` 항목의 `qualification_stage`를 `licensed_pharmacist`로

그 뒤 같은 10개 사례를 다시 검토해 새 결과를 등록한다. 그때부터 기록되는 증거 성격이 `licensed_pharmacist_expert_safety_review`로 바뀌고, 보고서에서 "약사가 검토·평가했다"고 쓸 수 있다. 2차년도 예비 약사 검토 기록은 지우지 않고 사전 검토 이력으로 보존한다.

## 외부 기관 평가와의 관계

OP-039의 `EXTERNAL` 단계는 이 정책과 별개다. 외부 기관 평가는 연구가 끝난 뒤 외부 기관이 수행하며, 두 trust-root 계약(`op039_external_coverage_trust_roots_v1.json`, `op039_external_attestation_trust_roots_v1.json`)에 승인 기록이 등록돼야 성립한다. 두 계약은 현재 모두 빈 배열이다. 3차년도 약사 검토를 마쳐도 그것만으로 `EXTERNAL`이 되지는 않는다.
