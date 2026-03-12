# SESSION_HANDOFF

## Scope guardrails

- Work only inside `C:/dev/wellnessbox-rnd`
- Do not read or reference:
  - `wellnessbox/`
  - `docs/03_integration/`
  - `docs/00_discovery/`
  - `docs/00_migration/`
  - `docs/legacy_from_wellnessbox/`

## Source of truth

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## What this loop did

- Chosen stage: `P4`
- Chosen task: `effect-proxy conditioned combined replay policy`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## Files changed

- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/simulation/closed_loop_v0.py`
- `C:/dev/wellnessbox-rnd/tests/test_closed_loop_simulation.py`
- `C:/dev/wellnessbox-rnd/PROGRESS.md`
- `C:/dev/wellnessbox-rnd/NEXT_STEPS.md`
- `C:/dev/wellnessbox-rnd/SESSION_HANDOFF.md`

## What changed technically

- combined replay now injects the guarded learned effect proxy into the learned policy feature `expected_effect_proxy`
- this wiring is replay/simulation-only and does not widen runtime learned usage
- added per-step diagnostics:
  - `policy_effect_proxy_used`
  - `policy_effect_proxy_override_applied`
- added per-mode aggregate:
  - `policy_effect_override_applied_count`
- added regression coverage proving combined replay can diverge from policy-only once effect proxy override is active

## Guard boundary

- runtime recommendation and frozen eval remain deterministic
- learned effect remains replay-only
- learned effect stays behind deterministic candidate filtering and low-risk gating
- learned policy remains replay-only and bounded by the deterministic ceiling
- no human-review or handoff action was introduced

## Replay snapshot

- `deterministic_only`
  - `total_trace_steps = 356`
  - `final_actions = ask_targeted_followup:21, continue_plan:65, trigger_safety_recheck:10`
- `learned_effect_guarded`
  - `raw_ranking_disagreement_count = 71`
  - `differing_final_policy_user_ids = 25`
  - `differing_final_state_user_ids = 24`
- `learned_policy_guarded`
  - `raw_policy_disagreement_count = 171`
  - `policy_guard_applied_count = 102`
  - `final_actions = ask_targeted_followup:21, continue_plan:31, monitor_only:15, trigger_safety_recheck:29`
- `learned_effect_and_policy_guarded`
  - `policy_effect_override_applied_count = 257`
  - `raw_policy_disagreement_count = 220`
  - `raw_ranking_disagreement_count = 63`
  - `final_actions = ask_targeted_followup:21, continue_plan:20, monitor_only:22, trigger_safety_recheck:33`

## Policy-dominance evidence

- before this loop:
  - combined vs policy-only final action match: `96 / 96`
  - combined vs policy-only trace action match: `299 / 299`
  - effect-ranking-diff subset combined vs policy-only trace action match: `95 / 95`
- after this loop:
  - combined vs policy-only final action match: `83 / 96`
  - combined vs policy-only trace action match: `262 / 299`
  - effect-ranking-diff subset combined vs policy-only trace action match: `87 / 95`
- interpretation:
  - the effect proxy now measurably reaches the policy path
  - combined is still closer to policy-only than effect-only, so P4 is improved but not finished

## Cohort slice snapshot

- `low_risk_users = 65`
  - deterministic final action: `continue_plan:65`
  - policy-only final actions: `continue_plan:31, monitor_only:15, trigger_safety_recheck:19`
  - combined final actions: `continue_plan:20, monitor_only:22, trigger_safety_recheck:23`
- `cgm_users = 20`
  - combined final actions stayed `ask_targeted_followup:10, trigger_safety_recheck:10`

## Deterministic baseline status

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.90291632090153`
- `next_action_accuracy_pct = 99.21875`
- `explanation_quality_accuracy_pct = 99.47916666666667`
- `safety_reference_accuracy_pct = 99.86979166666667`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 90.40247678018576`

## Validation snapshot

- `python -m ruff check src/wellnessbox_rnd/simulation/closed_loop_v0.py tests/test_closed_loop_simulation.py`
- `python -m pytest tests/test_closed_loop_simulation.py -q`
- `python scripts/run_closed_loop_batch_simulation.py`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_eval`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final_eval`

## Recommended next loop

1. tune effect-conditioned policy weighting within the guarded low-risk replay subset
2. expand `dose_limits` and structured safety coverage
3. enrich CGM and threshold-edge low-risk trajectories
