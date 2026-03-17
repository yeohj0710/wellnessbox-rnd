# NEXT_STEPS

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
- the shared PRO baseline/follow-up path is now directly wired:
  - `PROImprovementSummaryV1` is derived from `baseline_followup_pro_event_v1`
  - `baseline_follow_up_same_normalized_structure_case_count = 480`
  - `delta_pp_matches_percentile_diff_all_valid_cases = true`
- learned artifacts remain replay-only and optional to runtime

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
   - current bounded surface:
     - `threshold_duration_sensitive`
     - `mid_margin`
     - `small_drop`
     - `trajectory_step`
     - `fixed_uniform_offset`
     - `0.5` half-offset
     - local contract `uniform_score_gap_offset`

5. narrow synthetic-validity go/no-go memo
   - status: `current_no_go_memo_written`
   - implication:
     - no training rerun on current synthetic evidence

6. strict training-readiness gate
   - status: `current_no_go_gate_written`
   - proof:
     - `authorized_now = false`
     - `decision = no_go_keep_training_blocked`

7. optional chat/OpenAI triage
   - status: `defer_live_rerun_optional_only`
   - keep below replay, synthetic validity, weakest-slice residual proof, `cgm`, and training-boundary work

## Open bottlenecks 5

Order these by current evidence:

1. the dominant replay regression family is still unresolved above the already-explained `5/26` slice
   - family: `non_cgm_continue_to_monitor_threshold_cross`
   - this is still the single required pre-rerun loop

2. synthetic validity remains the principal project blocker
   - supported effect-enriched rows still remain:
     - `exact_reconstruction_rate_pct = 100.0`
     - `assignment_top2_match_rate_pct = 100.0`
     - materially calibration-coupled to `expected_effect_proxy`

3. weakest-slice lineage is still bridge-connected rather than fully closed
   - requested `weakest_slice_lineage_proof_v1.json` is absent
   - current closest lineage anchor still has:
     - `audit_layer_gap_count = 4`
     - sample-fixture based parser/CGM joins
     - partial structured-safety overlap

4. `cgm` final-step geometry still has unresolved structural overlap
   - status: `structural_continue_plan_overlap_persists`
   - outside-band unresolved cases still dominate over the single threshold-edge win

5. further training reruns remain blocked by evidence quality, not infrastructure
   - current gate is strict `NO-GO`
   - PRO contract wiring is no longer the blocker

## Next 3 bounded loops

1. `P3/P4`: replay-only residual attribution for `non_cgm_continue_to_monitor_threshold_cross`
   - this is still the single loop the current gate says must happen first
   - do not repeat the already-explained `small_drop` slice
   - start with residual `threshold_duration_sensitive / mid_margin`:
     - `large_drop`
     - `medium_drop`
   - success output:
     - one replay artifact that says whether `trajectory_step` still dominates or whether a new local opposing surface explains the residual bucket

2. `P3/P4`: one narrow synthetic-validity follow-up tied to the existing no-go memo
   - only if loop 1 completes or stalls cleanly
   - stay on exactly one item:
     - pre-policy-proxy vs post-policy-proxy rerun gating
     - or supported-vs-unsupported validity split proof

3. `P2/P4`: `cgm` outside-band final-step geometry only
   - only after the replay-first requirement is satisfied or intentionally deferred

## Priority rule

- runtime/core KPI path outranks everything else
- replay-only evidence still outranks every other training-adjacent task because the current gate names it as the required precondition
- synthetic-validity follow-up stays above weakest-slice cleanup, `cgm`, and any training churn
- training rerun stays blocked until the current gate materially changes from `no_go_keep_training_blocked`
- optional chat/OpenAI stays below replay, PRO, weakest-slice, `cgm`, synthetic-validity, and training-boundary work

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
