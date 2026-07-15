# NEXT_STEPS

## 2026-07-15 original plan completion program

The authoritative execution ledger is `docs/plans/2026-07-15-original-plan-completion-program.md`, the machine-readable source is `data/original_plan/requirements_manifest_v1.json`, and the generated status report is `docs/original_plan/COMPLETION_STATUS.md`. OP-001 through OP-010, OP-031, and OP-032 are complete. Do not mark OP-015 complete until dietary-pattern input is implemented and tested.

Next three loops:

1. Implement OP-011 and OP-012: complete the biometric profile, structured symptom severity, and urgent-risk input contracts without duplicating the existing safety fields.
2. Implement OP-013 and OP-014: complete medication and current-supplement dose/unit contracts before building the cross-repository profile adapter.
3. Implement OP-015 and OP-016: normalize dietary and lifestyle inputs, then add timestamped laboratory observations with units and reference ranges.

Continue OP-011 through OP-020 in bounded slices and add the lossless `wellnessbox` profile-to-R&D adapter.

Keep OP-101 through OP-110 open until an independently deployed R&D FastAPI process, internal authentication, persistent storage, service environment variables, and real two-process E2E evidence exist. Current proxy code alone is not integration evidence.

The legacy full-test baseline remains red for two independent reasons: 73 ignored report files are absent and four CGM geometry assertions do not match current execution. Restore report evidence only from a trusted hash-verified source; investigate the CGM drift separately instead of changing expected values to force PASS.

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
