# NEXT_STEPS

## OP-007/008 이후 다음 bounded loop

1. OP-009/010의 workflow gate와 generated completion report를 PDF·manifest·구현·테스트·Git 이력에 대조해 두 장문 보고서를 작성한다.
2. OP-011/012의 사용자 기본 프로필 schema와 source availability 계약을 같은 기준으로 backfill한다.
3. OP-013/014의 약물·질환·알레르기 입력과 목표 우선순위 계약을 같은 기준으로 backfill한다.

현재 유효 연구보고서는 28/120이고 92개가 남았다. completion 상태는 `76 COMPLETE / 43 PARTIAL / 0 PENDING / 1 EXTERNAL / 0 CONTRADICTED`다. 마지막 OP-120 evidence SHA-256은 `1be4ea55dcca71849aaed7332ee6859fdb419061561177ddf8eb2e7120a4ce01`, 성공 CI는 `29919479757`이다.

## Next after OP-120

1. 누락 연구보고서 92개를 기존 manifest·증거·커밋과 대조해 작성하거나 보강하고 보고서 감사를 통과시킨다.
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
