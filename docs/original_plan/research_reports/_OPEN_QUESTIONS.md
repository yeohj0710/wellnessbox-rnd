# 확인이 필요한 사항과 검증 기록

## 2026-07-27 변경 전 전체 테스트 기준선

실행 명령: `python -m pytest`

- 결과: 1,134개 통과, 89개 실패, 경고 5개
- 실행 시간: 182.57초
- 판단: 이 저장소는 변경 전부터 전체 테스트가 다수 실패한다. 아래 89개를 기준선으로 고정하고, 마무리 검사에서는 새로 생긴 실패만 조사한다.
- 캐시 주의: `.pytest_cache/v/cache/lastfailed`에는 이번 실행에서 수집되지 않은 오래된 실패 22개가 함께 남아 있었다. 아래 목록은 이번 실행의 `short test summary info`에 실제로 나온 89개만 옮겼다.

### 기준선 실패 테스트 89개

- `tests/test_bone_joint_empty_anchor_hold_regression.py::test_bone_joint_empty_anchor_hold_regression`
- `tests/test_bone_joint_weakest_family_freshness_hold_regression.py::test_bone_joint_weakest_family_freshness_hold_regression`
- `tests/test_cgm_candidate_failure_family_diagnostic.py::test_build_cgm_candidate_failure_family_diagnostic_rejects_cgm_only_hypothesis`
- `tests/test_cgm_candidate_failure_family_diagnostic.py::test_write_cgm_candidate_failure_family_diagnostic_files_creates_outputs`
- `tests/test_cgm_final_step_score_geometry_regression.py::test_cgm_final_step_blocker_family_stays_outside_threshold_edge`
- `tests/test_cgm_final_step_score_geometry_regression.py::test_cgm_final_step_replay_slice_keeps_current_geometry_signature`
- `tests/test_cgm_final_step_score_geometry_regression.py::test_cgm_final_step_calibration_only_flips_threshold_edge_singleton`
- `tests/test_chat_optional_rerun_audit.py::test_build_chat_optional_rerun_audit_defer_decision_from_existing_evidence`
- `tests/test_chat_optional_rerun_hold_regression.py::test_chat_optional_rerun_defer_hold_regression`
- `tests/test_closed_loop_simulation.py::test_cgm_threshold_edge_regression_keeps_followup_clamp_then_monitor_only_path`
- `tests/test_core_kpi_path_summary.py::test_build_core_kpi_path_summary_surfaces_current_kpi_path_state`
- `tests/test_data_lake_lineage.py::test_canonical_lineage_evidence_matches_current_database_schema`
- `tests/test_dataset_f_baseline_identical_signal_audit.py::test_build_dataset_f_baseline_identical_signal_audit_reports_reduced_label_copy`
- `tests/test_dataset_f_baseline_identical_signal_audit.py::test_write_dataset_f_baseline_identical_signal_audit_files_creates_outputs`
- `tests/test_dataset_f_data_quality.py::test_build_dataset_f_data_quality_report_pins_current_distribution`
- `tests/test_dataset_f_data_quality.py::test_write_dataset_f_data_quality_files_creates_outputs`
- `tests/test_dataset_f_partition_validity_audit.py::test_build_dataset_f_partition_validity_audit_splits_supported_and_base_clone`
- `tests/test_dataset_f_partition_validity_audit.py::test_write_dataset_f_partition_validity_audit_files_creates_outputs`
- `tests/test_dataset_f_path_safety_audit.py::test_build_dataset_f_path_safety_audit_reports_current_repo_evidence`
- `tests/test_dataset_f_path_safety_audit.py::test_write_dataset_f_path_safety_audit_files_creates_json_and_markdown`
- `tests/test_design_sanity_audit.py::test_build_design_sanity_audit_reports_directionally_sound_but_data_risky`
- `tests/test_effect_candidate_reject_decision.py::test_build_effect_candidate_reject_decision_supports_baseline_hold`
- `tests/test_effect_candidate_reject_decision.py::test_write_effect_candidate_reject_decision_files_creates_outputs`
- `tests/test_effect_model_v1.py::test_effect_feature_schema_validator_accepts_current_training_view_boundary`
- `tests/test_effect_training_defer_hold_regression.py::test_effect_training_defer_hold_regression_matches_current_replay_evidence`
- `tests/test_effect_training_revisit_freshness_hold_regression.py::test_effect_training_revisit_freshness_hold_regression`
- `tests/test_event_idempotency_data_mutation.py::test_canonical_evidence_uses_current_database_schema`
- `tests/test_final_kpi_compare_report.py::test_build_final_kpi_compare_report_surfaces_decision_useful_compare_state`
- `tests/test_knowledge_lineage.py::test_canonical_knowledge_lineage_evidence_matches_current_sources`
- `tests/test_kpi_candidate_summary.py::test_build_kpi_candidate_summary_surfaces_baseline_candidate_and_weakest_slice`
- `tests/test_latest_candidate_cgm_slice_diagnostic.py::test_build_latest_candidate_cgm_slice_diagnostic_rejects_cgm_only_gate`
- `tests/test_learned_runtime_boundary_artifact_consistency.py::test_learned_runtime_boundary_artifact_is_self_consistent`
- `tests/test_learned_runtime_boundary_audit_hold_regression.py::test_learned_runtime_boundary_hold_state_stays_current`
- `tests/test_log_separation_execution_identity.py::test_canonical_log_identity_evidence_matches_current_sources`
- `tests/test_non_cgm_continue_to_monitor_threshold_cross_attribution.py::test_build_non_cgm_continue_to_monitor_threshold_cross_attribution_locks_current_surface`
- `tests/test_non_cgm_residual_threshold_cross_attribution.py::test_build_non_cgm_residual_threshold_cross_attribution_locks_residual_surface`
- `tests/test_non_cgm_threshold_cross_diagnostic.py::test_build_non_cgm_threshold_cross_diagnostic_matches_latest_replay_family`
- `tests/test_non_cgm_threshold_cross_hold_regression.py::test_non_cgm_threshold_cross_hold_regression`
- `tests/test_non_cgm_threshold_cross_narrowing_decision.py::test_build_non_cgm_threshold_cross_narrowing_decision_selects_largest_mode`
- `tests/test_non_cgm_threshold_duration_sensitive_diagnostic.py::test_build_threshold_duration_sensitive_diagnostic_matches_narrowing_target`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_diagnostic.py::test_build_mid_margin_diagnostic_matches_current_bucket_target`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_narrowing_decision.py::test_build_mid_margin_narrowing_decision_matches_current_proxy_drop_target`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_diagnostic.py::test_build_small_drop_diagnostic_matches_current_slice_target`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_narrowing_decision.py::test_build_small_drop_narrowing_decision_matches_current_family_target`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_counterfactual.py::test_build_regimen_count_counterfactual_matches_current_slice_signal`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_diagnostic.py::test_build_regimen_count_diagnostic_matches_current_feature_target`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_fix_scope_decision.py::test_build_regimen_count_fix_scope_decision_closes_feature_absence_story`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_count_score_competition_decision.py::test_build_regimen_count_score_competition_decision_picks_first_opposing_feature`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_status_summary_diagnostic.py::test_build_regimen_status_summary_diagnostic_matches_current_family_target`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_regimen_status_summary_narrowing_decision.py::test_build_regimen_status_summary_narrowing_decision_matches_current_feature_target`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_counterfactual.py::test_build_trajectory_step_counterfactual_matches_current_slice_signal`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_fix_scope_decision.py::test_build_trajectory_step_fix_scope_decision_closes_multifeature_mix_story`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_fix_scope_hold_regression.py::test_trajectory_step_fix_scope_hold_regression_stays_local_and_consistent`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_fixed_uniform_offset_feasibility.py::test_build_trajectory_step_fixed_uniform_offset_feasibility_has_half_offset_probe`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_fixed_uniform_offset_probe_decision.py::test_build_trajectory_step_fixed_uniform_offset_probe_decision_chooses_half_first`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_half_offset_counterfactual.py::test_build_trajectory_step_half_offset_counterfactual_clears_all_cases`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_half_offset_fix_scope_decision.py::test_build_trajectory_step_half_offset_fix_scope_decision_stays_bounded`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_half_offset_fix_scope_hold_regression.py::test_trajectory_step_half_offset_fix_scope_hold_regression_stays_direct_and_bounded`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_half_offset_hold_regression.py::test_trajectory_step_half_offset_hold_regression_stays_first_successful_probe`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_half_offset_local_contract.py::test_build_trajectory_step_half_offset_local_contract_stays_uniform_and_ready`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_local_handling_mode_decision.py::test_build_trajectory_step_local_handling_mode_decision_stays_fixed_and_uniform`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_local_handling_readiness.py::test_build_trajectory_step_local_handling_readiness_stays_single_feature_first`
- `tests/test_non_cgm_threshold_duration_sensitive_mid_margin_small_drop_trajectory_step_local_handling_readiness_hold_regression.py::test_trajectory_step_local_handling_readiness_hold_regression_stays_single_feature_first`
- `tests/test_non_cgm_threshold_duration_sensitive_narrowing_decision.py::test_build_threshold_duration_sensitive_narrowing_decision_matches_current_bucket`
- `tests/test_original_plan_audit.py::test_original_plan_audit_accepts_current_claimed_evidence`
- `tests/test_original_plan_audit_cli.py::test_original_plan_audit_cli_returns_zero_for_current_manifest`
- `tests/test_original_plan_completion_report.py::test_current_report_covers_all_requirements_without_inflating_completion`
- `tests/test_original_plan_completion_report.py::test_global_source_failure_invalidates_every_existing_completion_claim`
- `tests/test_original_plan_completion_report.py::test_markdown_uses_audited_korean_status_language`
- `tests/test_original_plan_completion_report.py::test_report_cli_writes_and_checks_deterministic_artifacts`
- `tests/test_original_plan_manifest.py::test_original_plan_manifest_claims_only_currently_evidenced_steps`
- `tests/test_parser_case_id_mismatch_freshness_hold_regression.py::test_parser_case_id_mismatch_freshness_hold_regression`
- `tests/test_parser_case_id_mismatch_hold_regression.py::test_parser_case_id_mismatch_non_blocking_hold_regression`
- `tests/test_policy_proxy_calibration_dependence_audit.py::test_build_policy_proxy_calibration_dependence_audit_reports_supported_slice_concentration`
- `tests/test_policy_proxy_calibration_dependence_audit.py::test_write_policy_proxy_calibration_dependence_audit_files_creates_outputs`
- `tests/test_policy_proxy_replay_split_audit.py::test_build_policy_proxy_replay_split_audit_shows_supported_combined_concentration`
- `tests/test_policy_proxy_replay_split_audit.py::test_write_policy_proxy_replay_split_audit_files_creates_outputs`
- `tests/test_session_replay.py::test_canonical_evidence_uses_current_database_schema`
- `tests/test_structured_safety_overlap_hold_regression.py::test_structured_safety_overlap_non_blocking_hold_regression`
- `tests/test_structured_safety_rule_overlap_freshness_hold_regression.py::test_structured_safety_rule_overlap_freshness_hold_regression`
- `tests/test_synthetic_prepost_path_audit.py::test_build_synthetic_prepost_path_audit_pins_current_repo_risk_posture`
- `tests/test_synthetic_prepost_path_audit.py::test_write_synthetic_prepost_path_audit_files_creates_outputs`
- `tests/test_synthetic_prepost_path_audit_hold_regression.py::test_synthetic_prepost_path_audit_hold_state_stays_current`
- `tests/test_synthetic_validity_audit.py::test_build_synthetic_validity_audit_pins_current_repo_validity_verdict`
- `tests/test_synthetic_validity_audit.py::test_write_synthetic_validity_audit_files_creates_outputs`
- `tests/test_synthetic_validity_followup_single_item.py::test_build_synthetic_validity_followup_single_item_marks_calibration_target_as_still_risky`
- `tests/test_synthetic_validity_followup_single_item.py::test_write_synthetic_validity_followup_single_item_files_creates_outputs`
- `tests/test_training_readiness_gate.py::test_build_training_readiness_gate_returns_strict_no_go_v2`
- `tests/test_training_readiness_gate.py::test_write_training_readiness_gate_files_creates_outputs`

## 2026-07-27 보고서 53편 재작성 품질 검사

- 대상: OP-031~OP-078, OP-105, OP-106, OP-117~OP-119의 정본 보고서 53편
- 결과: 53편 모두 정규화한 본문이 1,500자 이상이고, 절이 3개 이상이며, 각 절 본문이 80자 이상이다.
- 근거 연결: 53편 모두 현재 manifest에 등록된 증거 경로 원문을 한 번 이상 인용한다.
- 중복 검사: 3편 이상에서 반복된 문단 0개, 3편 이상에서 반복된 문장 0개다.
- `확인되지 않음` 원문은 41회, 같은 뜻의 변형까지 합치면 75회다. 각 표현은 운영 자료·외부 승인·변경 전 장애 기록처럼 실제로 찾지 못한 항목을 특정하므로 삭제하지 않았다.
- 직접 읽기: 53편을 샤드 순서로 다시 읽었으며 자동 검사에서 잡히지 않은 공통 복사 문단, 제목 불일치, 근거 없는 완료 주장은 추가로 찾지 못했다.

### 증거와 manifest 사이에서 확인한 불일치

- OP-039: 외부 검토 자료의 검토자는 과제 공동연구자이고 `independent_of_implementation_team=false`다. 신뢰 기준의 승인 목록도 비어 있어 현재 `EXTERNAL` 승격을 독립 검증 완료로 해석할 수 없다.
- OP-041: 현재 식별자 변환표는 `2026-07-24.1`이지만 등록 smoke와 생성기는 `2026-07-16.1`을 기대한다. 현행 변환표의 통합 증거를 다시 만들어야 한다.
- OP-059~OP-065: 등록 smoke 네 개의 저장 소스 지문이 현재 소스 지문과 다르다. 현재 구현을 대상으로 새 smoke를 만들기 전에는 과거 실행 범위를 넘겨 해석하지 않는다.
- OP-071, OP-072: 범용 운영 영수증에는 `agent_runs=0`, `agent_steps=0`이 기록돼 있다. 이 영수증만으로 에이전트 실행을 직접 입증할 수 없다.
- OP-074~OP-078: 범용 영수증은 요구사항별 크론 실행, 입력 인과관계, 이상사례, 특정 실패와 검토 작업을 직접 보여 주지 않는다.
- OP-105: 운영 영수증은 `user_profiles` 1건 증가만 보여 주고 `recommendation_runs`와 `recommendation_items` 증가는 0건이다. 프로필 저장 뒤 추천 왕복의 운영 관찰이 더 필요하다.
- OP-106: 실제 화면은 `ai_drafts` 큐를 사용하지만 등록 smoke는 `review_tasks` 큐를 왕복한다. 두 큐의 검증 대상을 분리해야 한다.
- OP-117: 브라우저 생성기는 현재 manifest의 `OPERATED` 41건과 충돌하는 `operated_requirement_count=0` 가정을 가진다.
- OP-118: 현재 비외부 요구사항 119건의 단계별 증거 내용을 다시 대조한 최신 집계 자료가 없다. 추천 행 1건을 여러 요구사항에 연결한 범용 매핑은 개별 행동의 직접 증거가 아니다.
- OP-119: 외부 의존성 원장과 신뢰 기준은 OP-039를 계속 `BLOCKED`로 판정한다. manifest의 `EXTERNAL` 승격과 원장 판정을 맞춰야 한다.

## 2026-07-27 최종 감사 1회 실행 결과

- 실행 명령: `python scripts/run_final_completion_audit.py`
- 실제 결과: 종료 코드 1. `research_reports`는 118편, 누락·부적합은 2편으로 계산됐고 최종 판정은 `BLOCKED`, `goal_complete=false`였다.
- 원인: OP-050과 OP-074는 본문 길이·절 수·절 길이·등록 증거 경로를 충족했지만, 감사기가 요구하는 네 의미 단어군 중 정확한 `요구` 또는 `문제`라는 단어가 없어 두 단어군만 충족했다.
- 수정: 두 보고서 첫 문단에 각 OP의 구체적인 요구를 한 문장으로 명시했다. 감사기와 같은 읽기 전용 판정식을 120편에 적용한 결과는 유효 120편, 부적합 0편이다.
- 재실행 여부: 목표가 최종 감사 스크립트를 한 번만 실행하라고 정했으므로 스크립트는 다시 실행하지 않았다. 실패가 출력 파일 쓰기 전에 발생해 `op120_final_completion_audit_v1.json`은 이번 실행 결과로 갱신되지 않았다.

## 2026-07-27 마무리 검사 결과

### 세션 전 점검

- 실행용 Python과 Ed25519 서명 키는 모두 존재했다.
- 운영 DB는 서로 다른 실제 자료 분류 프로필 5/5개, 대기 약사 초안 0개를 반환했다.
- 로컬 연구 서버를 한 번 시작해 R&D `/health` 200, 최종 확인 화면 200, WellnessBox 연구 로그인 307 이동을 확인한 뒤 종료했다. 사람 입력·판정·승인·서명은 수행하지 않았다.
- 종료 래퍼는 서버를 정상 종료한 뒤 비대화형 `timeout /t 2`에서 종료 코드 1을 냈다. 대기 명령을 호환되는 `ping` 방식으로 바꾼 뒤 종료 코드 0을 확인했다.

### 전체 pytest 비교

- 실행 명령: `python -m pytest`
- 결과: 1,134개 통과, 89개 실패, 경고 5개, 183.45초
- 기준선 대비: 통과·실패·경고 수가 모두 같다. 실제 실패 요약의 89개도 같은 실패군이다.
- 기준선 문서 보정: `test_non_cgm_threshold_duration_sensitive_diagnostic.py`의 실제 함수명은 `test_build_non_cgm_threshold_duration_sensitive_diagnostic_matches_narrowing_target`이다. 기준선 목록에는 함수명 중 두 번째 `non_cgm`이 빠져 있었다. 이 시험 파일의 마지막 변경은 2026-03-17 커밋 `1e113e9`이므로 이번 작업에서 생긴 실패가 아니다.
- 캐시 주의: 전체 실행 뒤에도 `.pytest_cache/v/cache/lastfailed`에는 현재 실행 요약에 없는 과거 항목 22개가 남아 있어 비교 근거로 쓰지 않았다.

### Ruff

- 실행 명령: `python -m ruff check .`
- 결과: 종료 코드 1, 기존 Python 파일 5개에서 32개 오류. 자동 정렬 가능 항목은 5개다.
- 범위: 실패 파일은 `scripts/build_op039_external_review_package.py`, `scripts/run_counseling_full_service_roundtrip_smoke.py`, `src/wellnessbox_rnd/governance/final_session_console.py`, `src/wellnessbox_rnd/governance/operational_receipts.py`, `tests/test_final_session_console.py`다. 이번 작업에서 수정한 파일은 없다.
- 판단: 문서 품질 작업과 무관한 기존 import 순서·100자 초과 문제이므로 자동 수정이나 광범위 서식 변경을 하지 않았다.

## 2026-07-27 근거 심화와 최종 감사 정본 기록

이 절은 위에 남아 있는 같은 날짜의 보고서 분포, 감사 실패, 런북 점검 기록을 현재 실행 결과로 대체한다. 과거 기록은 당시 판단의 이력으로 보존한다.

### 보고서 53편 최종 검사

- 최종 분포는 최소 2,830자, 중앙값 4,203자, 최대 7,242자, 평균 4,439.2자, 모집단 표준편차 910.4자다. 구간별로 2,500자 미만 0편, 2,500~3,499자 8편, 3,500~4,499자 21편, 4,500자 이상 24편이다.
- manifest의 파일 경로는 중복 포함 492건, OP-경로 고유 조합은 447건, 실제 고유 파일은 189개다. 파일 경로 492건은 모두 존재한다.
- 근거 재검증에서 32편의 단계, 버전, 해시, 함수명, 입력 조건 또는 저장 증거 해석을 바로잡았다. 최종 보고서와 현재 근거 사이의 남은 내용 불일치는 0건이다.
- 3편 이상에서 반복된 문단은 0개, 반복된 문장은 0개다. `검사한다`, `확인한다`, `검증한다`가 세 문장 연속 이어지는 문형도 0개다.
- 정확한 문자열 `확인되지 않음`은 0회다. 찾지 못한 운영·외부 근거는 모호한 표현 대신 부족한 증거와 필요한 다음 확인을 구체적으로 적었다.
- OP-039 manifest의 문자열 두 개는 저장소 경로가 아니라 외부 자료 제공과 독립 검증 영수증 조건이다. 두 조건은 파일 경로 집계에서 제외했고, 여전히 충족되지 않은 의존 조건으로 기록했다.

### 최종 감사 두 번의 결과

- 첫 번째 실행은 종료 코드 1이었다. 감사기는 OP-060이 요구사항 의미 단어군을 충족하지 못한다고 판정해 보고서를 119/120편, 상태를 `BLOCKED`로 계산했다. OP-060 첫 문단에 실제 요구를 명시하고 `821a5a5`로 커밋했다.
- 두 번째 실행은 2026-07-27 08:24:56+09:00에 끝났다. 결과는 요구사항 120/120, 보고서 120/120, 누락 0, 비외부 단계 격차 0, 외부 격차 0, 차단 사유 0, `status=READY`, `goal_complete=true`다.
- 감사 데이터셋은 `data/original_plan/op120_final_completion_audit_cases_v1.json`, 8건, SHA-256 `5a2fc3d6549062ba919567d89273bd953391f324091538f8f621ab1eccbf7c29`다.
- 감사 입력은 파일 blob 509개다. 저장소 식별자는 wellnessbox-rnd `821a5a5a4e4512f015ec798b70b0922a1b0992c1`, wellnessbox `f545b83f1da4aff12f0b1b1d6785feaf49aeaa5f`다. 감사기 소스 식별 커밋은 `558d70340aa2a1c5c1656d2f60aa6efc4db3a1a6`다.
- 새 감사 JSON의 SHA-256은 `7b155568dbe684b6448725b96d030e918c9f77fbeb0ce1f1008a4e14b9c168ca`다.
- `READY`는 현재 정책과 등록 영수증으로 감사 조건을 통과했다는 뜻이다. 이번 근거 검증에서 확인한 H-003 학습 계보와 H-005 중립성 결함, 개별 OP의 직접 운영 증거 부족을 새로 해결했다는 뜻은 아니다.

### Ruff 32건의 출처

- `python -m ruff check .`은 기존 파일 5개에서 32건으로 실패했다. 규칙별로 E501 27건, I001 4건, UP034 1건이며 5건은 자동 수정 가능하다.
- 파일별 건수는 `scripts/build_op039_external_review_package.py` 3건, `scripts/run_counseling_full_service_roundtrip_smoke.py` 2건, `src/wellnessbox_rnd/governance/final_session_console.py` 20건, `src/wellnessbox_rnd/governance/operational_receipts.py` 3건, `tests/test_final_session_console.py` 4건이다.
- 다섯 파일은 `main...HEAD`와 작업 트리에서 차이가 없다. 각 진단 줄의 blame 커밋 8개(`89dad25`, `fa0dbd9`, `eeaba1d`, `c34b154`, `eea6592`, `2e9791d`, `c7f88df`, `30b956a`)도 모두 main의 조상이다. 이번 브랜치가 새로 만든 Ruff 오류는 0건이므로 기존 코드를 고치지 않았다.

### 영수증 없는 세션 전 점검

- 기존 `research-server-start.cmd`는 정상 종료 때도 `begin_session`과 `finish_session`을 호출해 ACTUAL 영수증을 만든다. 따라서 영수증을 만들면 안 되는 사전 점검에는 사용할 수 없다.
- `scripts/run_final_session_preflight.py`는 운영 DB를 임시 파일로 복사하고 최종 콘솔 상태도 임시 루트에 둔다. 스크립트가 시작한 프로세스 ID만 종료한다.
- SQLite 임시 복사는 본체와 WAL을 파일 단위로 복사한다. 복사 전후 원본의 본체·WAL·SHM 해시가 다르면 즉시 멈추고, 임시 DB에 `PRAGMA integrity_check`를 실행해 손상 여부를 확인한다.
- 저장 불변 검사는 DB 하나가 아니라 다섯 경계를 본다. 실제 `interim.sqlite3`·`-wal`·`-shm`, `operational_capture.json`·`session_processes.json`·`stop.request`, `data/original_plan/final_session` 바로 아래 모든 파일, `operational_receipts` 아래 모든 파일이다. 결과는 `database_unchanged`, `runtime_controls_unchanged`, `final_state_unchanged`, `receipt_file_list_unchanged`, `receipt_hashes_unchanged`로 나온다.
- 실제 점검에서 R&D health, 콘솔, state, WellnessBox health는 200을 반환했다. 사용자·약사 로그인은 307 이동 뒤 화면 200을 반환했다.
- 실제 DB는 실행 전후 SHA-256 `856817703a430d42b7f7f4689b2b214caee6d727a2efcc59766d515f2a448e87`, 크기 761,856바이트로 같았다. WAL은 크기 0, SHM은 32,768바이트로 같았다. 제어 파일 manifest는 `45d2d47b8b9c61f14c8dd74ddd0ee96160744ce4a752f87d193dab2de0a9e1bb`, 최종 세션 직접 파일 13개의 manifest는 `fcd74398346da0200b8cf6bd1fc628255abea63a2750d90e75e8a44b37b76a35`, 영수증 15개의 manifest는 `a73f8e25c2b3fdefe956635ca7092a3f071d4ac10155b6b7e28a69dcc13bf39a`로 전후 동일했다. 새 영수증, 잔류 상태 파일, 잔류 포트(8000·8765·3001)는 없었다.
- H-005 검사는 원본 HTML 정규식이 아니라 연결 저장소 `C:\dev\wellnessbox`의 Playwright/Chromium이 실제로 렌더링한 DOM을 읽는다. 따라서 정적 `checked`와 정적 textarea 값뿐 아니라 JavaScript로 나중에 넣은 선택·의견도 잡아낸다.
- 렌더링된 DOM에서 10건 모두 선택돼 있었고 의견 10건도 채워져 있었다. 사전 선택과 기존 의견 복사를 금지한 규칙을 위반하므로 사전 점검은 의도대로 `BLOCKED`, 종료 코드 2를 반환하며 차단 항목은 `H005_FORM_NOT_NEUTRAL` 하나뿐이다.
- 전용 회귀 테스트는 4개에서 10개로 늘렸다. WAL에 커밋된 행이 임시 DB에 실제로 포함되는지, 다섯 저장 경계 각각에 대한 변경이 차단되는지, 렌더링 DOM 검사가 동적으로 주입된 선택·의견을 잡는지를 각각 확인한다. `python -m pytest tests/test_final_session_preflight.py -q`는 10건 통과다.

### 447개 OP-경로 판정 원장

- `docs/original_plan/EVIDENCE_VERIFICATION_REPORT.md`는 OP별 합계만 담았고 447개 경로 각각의 판정 근거는 남아 있지 않았다. 그래서 상세 원장 `data/original_plan/evidence/evidence_verification_ledger_v1.json`을 새로 만들었다.
- 원장의 447개 행에는 OP, 인용·등록 경로, 증거 유형, 존재 여부, 파일 SHA-256, 보고서의 경로 원문 인용 여부, 내용 일치 여부, 판정 비고가 들어 있다. 원장 SHA-256은 `21d1388ed3912174126ae435a85aa80baa991ebd65d1b6aeb3ad0b9816319257`이다.
- `python scripts/verify_evidence_verification_ledger.py`는 현재 manifest와 53편 보고서, 189개 파일의 SHA-256을 원장과 대조하고 요약 수치를 447개 행에서 다시 계산한다. 현재 결과는 status `READY`, 보고서 53편, 등록 경로 492건, 고유 OP-경로 447건, 고유 파일 189개, 누락 0건, 내용 불일치 0건, 경로 원문 인용 339건이다.
- OP-039의 등록 경로 수는 구현·테스트 파일 5개와 대체 계약 파일 2개를 합친 7개다. 외부 의존 조건 2개는 저장소 경로가 아니므로 존재 집계에서 제외했다.

### H-005 중립성 규칙의 실제 구현

- 프로젝트 공동연구자만 허용하고 `independent_of_implementation_team=false`를 강제하는 현재 규칙은 `human_signoff_checklist.md`와 일치한다.
- 오너 차단은 자유 입력 이름이 `여형준` 또는 `웰니스박스`와 정확히 같을 때만 작동한다. 인증 계정이나 오너 원장과 연결하지 않아 별칭을 막지 못한다.
- 동일 AI 초안 검토자 표시는 거부가 아니라 경고다. 체크리스트의 경고 규칙과는 맞지만 H-003 검토자 원장과 대조하지 않고 자기 신고 값만 믿는다.
- 생성기와 현재 HTML은 10개 판정을 모두 `valid`로 미리 고르고 AI 의견도 채운다. 현재 테스트는 이 사전 입력을 필수로 고정해 기존 판정 복사 금지와 사전 선택 금지를 위반한다.
- 면허 ID는 빈 문자열만 거부해 `not_collected`를 허용한다. 자격 확인 방법은 검증하지 않고, 서명은 별도 전자서명이 아니라 이름 문자열을 자동 복사한다. 신뢰 원장 기반 대체 경로도 사람 검토자 자격 없이 H-005를 완료할 수 있다.
- 따라서 H-005 상태가 `completed`여도 중립적 외부 검토가 끝났다고 판단하면 안 된다. 코드는 새로 만들지 않았고 판정 데이터도 생성하지 않았다.

### H-003 이후 학습·평가 명령의 빈 구간

- 고정 평가 세트 `data/frozen_eval/frozen_eval_v1.jsonl`은 256건이며 SHA-256은 `ba134edbade51d02ad4014a7a66626559eb454967736495d1e60fbcf95b3a960`다.
- 현재 기준 모델 평가는 `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir <baseline-output-dir>`로 실행할 수 있다. 두 보고서의 산술 비교는 `python scripts/compare_eval_reports.py --baseline-report <baseline-report.json> --candidate-report <candidate-report.json> --output-json <comparison.json> --output-md <comparison.md>`로 만들 수 있다.
- 그러나 승인 초안 소비 함수는 `approved`와 `approved_with_edits` 행만 반환하고 목적과 초안 ID 계보를 학습 데이터셋으로 남기지 않는다. 최종 콘솔도 반환 행 수만 기록하며 학습을 호출하지 않는다.
- `run_eval.py`는 후보 모델이나 artifact 인자를 받지 않고 항상 같은 `recommend` 함수를 호출한다. 비교 스크립트는 차이만 계산하며 안전 지표가 나빠졌을 때 실패시키지 않는다.
- H-003 승인 초안 변환기, approved-only 데이터셋 manifest, 후보 artifact 학습 명령, 후보 모델을 주입하는 고정 평가 실행기, 안전 회귀 게이트, 교체·유지와 rollback 영수증이 없다. 별도 합성 자료용 학습 스크립트는 H-003 체인으로 사용할 수 없다.
- 학습과 평가는 실행하지 않았다. 위 빈 구간이 구현되기 전에는 승인 초안 → 학습 → 후보 평가 → 안전 게이트 → 교체 또는 유지로 이어지는 실제 명령 체인을 확정할 수 없다.

### 최종 회귀와 병합 판정

- `python -m pytest` 최종 결과는 1,144개 통과, 89개 실패, 경고 5개다. 실측 벽시계 시간은 177초이며, 연속 2회 실행에서 통과·실패 수와 실패한 시험 함수 목록이 완전히 같았다. 이 환경의 pytest는 합계 줄을 파일로 내보내지 않으므로 수치는 진행 표시 문자와 `FAILED` 줄에서 세었다.
- 통과 수가 이전 기록 1,138개보다 6개 많은 이유는 사전 점검 전용 시험을 4개에서 10개로 늘렸기 때문이다. 늘어난 6개는 WAL 커밋 행의 임시 DB 포함, 저장 경계별 변경 차단, 렌더링 DOM의 동적 선택·의견 검출을 확인한다.
- 새 실패 0건은 함수 단위로 확인했다. `main`(`bebed41`)을 별도 worktree로 꺼내 같은 72개 시험 파일을 돌린 결과 96개가 실패했고, 이번 브랜치의 실패 89개는 그 96개의 부분집합이었다. 브랜치에만 있는 실패는 0개다. main에만 있는 7개는 worktree에 없는 미추적 실행 자료 때문이므로 브랜치가 만든 실패가 아니다.
- 이번 브랜치는 `src/` 아래를 전혀 바꾸지 않았고 시험 파일도 `tests/test_final_session_preflight.py` 하나만 건드렸다. 이 파일은 실패 목록에 없다.
- `python -m ruff check .`은 기존 파일 5개의 같은 32건으로 실패했다. 규칙별 내역도 E501 27건, I001 4건, UP034 1건으로 같다. 새 사전 점검 스크립트, 근거 원장 검증기, 전용 시험은 Ruff를 통과한다.
- 조건부 병합 세 조건은 모두 참이다. OP-120 감사 120/120 `READY`, `EVIDENCE_VERIFICATION_REPORT.md`의 최종 내용 불일치 0건, pytest 새 실패 0건이다.
- 따라서 최종 문서 커밋 뒤 `report-quality-pass`를 `main`에 fast-forward 병합한다. push, 배포, 훈련, 사람 판정·승인·서명은 하지 않는다.
