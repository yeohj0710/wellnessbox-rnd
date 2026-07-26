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
