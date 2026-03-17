# NEXT_STEPS

## Current priority

The current repo state is:

- deterministic baseline remains the runtime reference
- replay compare is complete enough to keep the latest candidate held
- the latest held candidate is still:
  - `effect_model_v3_training_view_enforced_slice_balanced_candidate`
  - `decision = hold_baseline_candidate_not_ready`
  - `principal_blocker = synthetic_data_circularity_and_generator_contamination`
  - `dominant_replay_regression_family = non_cgm_continue_to_monitor_threshold_cross`
- PRO baseline/follow-up semantics are fixed on one package-level shared-event path
- weakest-slice frozen-eval wiring is connected enough for headline KPI reading, but not fully gap-free
- `cgm` final-step geometry still has one bounded threshold-edge win and a larger unresolved outside-band overlap
- learned artifacts remain replay-only and optional to runtime
- quick-read artifacts now exist for compare, core-path, and direction checks:
  - `artifacts/reports/final_kpi_compare_report_v1.json`
  - `artifacts/reports/core_kpi_path_summary_v1.json`
  - `artifacts/reports/design_sanity_audit_v1.json`

So the next session should return to the remaining replay/data blockers, not more summary formatting, optional chat work, more PRO cleanup, or another training rerun without new replay-only evidence.

## Closed-enough loops

These are closed enough for the current KPI path and should stay closed unless new evidence appears:

1. replay compare and baseline-vs-candidate judgement
   - status: `complete_candidate_held`
   - decision: `hold_baseline_candidate_not_ready`
   - reject/fork proof exists:
     - `decision = reject_candidate_keep_baseline`
     - `fork_recommendation = analysis_only_fork`
     - `overall_clearly_worse_than_baseline = true`

2. PRO baseline/follow-up contract wiring
   - status: `shared_event_path_connected`
   - proof:
     - `contract_id = baseline_followup_pro_event_v1`
     - `valid_case_count = 480`
     - `invalid_case_count = 0`
     - `package_public_summary_entrypoint = summarize_pro_improvement_from_event_v1`
     - `package_public_validator_entrypoint = validate_pro_improvement_summary_from_event_v1`

3. weakest-slice core audit path for headline KPI reading
   - current closed part:
     - parser -> CGM -> follow-up -> workflow -> structured safety path is explicit
     - `frozen_eval_compatible = true`
     - `path_status = bridge_connected_with_direct_gap`
     - next-action shared-contract drift is not the current blocker
   - implication:
     - do not reopen broad weakest-slice wiring work unless a specific remaining gap blocks a stricter KPI claim

4. learned artifact replay-only runtime boundary
   - status: `replay_only_boundary_preserved`
   - proof:
     - `core_path_count = 4`
     - `promoted_core_path_count = 0`
     - `all_core_paths_preserved = true`
     - `chat_optional_only = true`

5. summary / readability layer
   - closed-enough quick-read artifacts now exist:
     - `final_kpi_compare_report_v1`
     - `core_kpi_path_summary_v1`
     - `design_sanity_audit_v1`
   - implication:
     - do not spend another bounded loop on new summary layers unless one source artifact materially changes

6. bounded post-prereq training rerun
   - status: `completed_null_result_candidate_not_promoted`
   - latest heterogeneity-aware candidate produced no behavioral delta vs the current held candidate
   - implication:
     - training rerun is closed again until replay/data evidence changes

7. optional chat/OpenAI triage
   - status: `defer_live_rerun_optional_only`
   - keep below replay, synthetic validity, weakest-slice residual gaps, `cgm`, and training-boundary work

## Open bottlenecks 5

Order these by current evidence:

1. synthetic validity is still the principal blocker
   - anchor: `synthetic_data_circularity_and_generator_contamination`
   - current risk is concentrated in supported effect-enriched slice circularity, generator contamination, and calibration-target coupling

2. the dominant replay regression family is still unresolved
   - family: `non_cgm_continue_to_monitor_threshold_cross`
   - this remains the main actionable replay blocker on the candidate path
   - current smallest active replay surface is:
     - `threshold_duration_sensitive`
     - `mid_margin`
     - `small_drop`
     - `regimen_count`
     - `trajectory_step`
     - `fixed_uniform_offset`
     - `0.5` half-offset
     - local contract `uniform_score_gap_offset`

3. `cgm` final-step geometry still has unresolved structural overlap
   - status: `structural_continue_plan_overlap_persists`
   - current evidence says:
     - threshold-edge singleton can flip
     - 8 outside-band cases still do not

4. weakest-slice residual lineage gaps still exist
   - current remaining gaps are narrower than the already-closed core audit path:
     - parser case-id mismatch
     - sample-fixture scoped normalization proof
     - partial structured-safety overlap

5. further training reruns are blocked by missing replay/data evidence
   - newest rerun produced a null result
   - effect-training boundary validator is already in place
   - current blocker is not `run training again`, but `earn the right to rerun` by moving replay/data evidence first

## Next 3 bounded loops

These are the concrete next three loops unless the hold state changes:

1. `P3/P4`: replay-only `non_cgm_continue_to_monitor_threshold_cross`
   - stay on the currently selected smallest surface:
     - `threshold_duration_sensitive`
     - `mid_margin`
     - `small_drop`
     - `regimen_count`
     - `trajectory_step`
     - `fixed_uniform_offset`
     - `0.5` half-offset
     - local contract `uniform_score_gap_offset`
   - success output:
     - one replay artifact, validator, or smallest bounded fix that tests this exact local contract without widening to cycle-conditioned handling, second-feature competition, the wider family, or training

2. `P3/P4`: narrow synthetic-validity audit
   - only if loop 1 is complete or stalls cleanly
   - success output:
     - one proof artifact that pinpoints one of:
       - supported-slice circularity
       - generator contamination
       - calibration-target coupling
     - do not redesign the generator

3. `P2/P4`: `cgm` outside-band final-step geometry only
   - success output:
     - one replay/slice proof showing whether any bounded outside-band calibration can move more than the threshold-edge singleton while preserving current regression guards

## Priority rule

- runtime/core KPI path outranks everything else
- replay-only evidence outranks synthetic-audit breadth, weakest-slice cleanup, and training churn
- training rerun stays closed until replay/data evidence materially changes the current hold decision
- optional chat/OpenAI stays below replay, PRO, weakest-slice, `cgm`, synthetic-validity, and training-boundary work

## Manual backlog priority

- must-do: none
- optional:
  - rerun the latest OpenAI live smoke only if deeper provider-failure diagnosis is still needed later
  - keep this as the only optional manual backlog item unless a future loop creates a new blocked external dependency

## Guardrails

- Keep work inside `C:/dev/wellnessbox-rnd`
- Preserve deterministic baseline, frozen-eval comparability, safety precedence, bounded chat, and replay-only learned artifacts
- Do not widen `dataset_f_effect_training_view_v1`
- Do not reintroduce forbidden outcome-side features into effect training
- Prefer evidence-chain tightening over architecture churn
