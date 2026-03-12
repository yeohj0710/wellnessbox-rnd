# PROGRESS

## Current loop

- Chosen stage: `P4`
- Chosen task: `effect-proxy conditioned combined replay policy`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## What changed

- Routed learned effect into combined replay policy features:
  - `src/wellnessbox_rnd/simulation/closed_loop_v0.py`
  - combined mode now overrides the policy feature `expected_effect_proxy` with the guarded learned effect proxy when rerank is actually applied
- Added replay diagnostics for effect-conditioned policy usage:
  - per-step fields `policy_effect_proxy_used`
  - per-step flag `policy_effect_proxy_override_applied`
  - per-mode aggregate `policy_effect_override_applied_count`
- Added regression coverage for the new replay-only wiring:
  - `tests/test_closed_loop_simulation.py`

## Why combined mode was policy-dominated

- Before this loop, combined replay used the learned-effect-selected candidate to compute the deterministic threshold action, but raw learned policy inference still read the original record feature `expected_effect_proxy`.
- That meant combined mode was action-identical to `learned_policy_guarded` even when learned effect changed candidate choice:
  - combined vs policy-only final action match: `96 / 96 = 1.0000`
  - combined vs policy-only trace action match: `299 / 299 = 1.0000`
  - effect-ranking-diff subset combined vs policy-only trace action match: `95 / 95 = 1.0000`

## Replay result after the wiring change

- replay artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_compare.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_compare.md`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_trace_samples.json`
- `learned_effect_and_policy_guarded`
  - `policy_effect_override_applied_count = 257`
  - `raw_policy_disagreement_count = 220`
  - `raw_ranking_disagreement_count = 63`
  - `differing_final_policy_user_ids = 45`
  - `differing_final_state_user_ids = 23`
- policy-dominance reduction vs pre-loop report:
  - combined vs policy-only final action match: `96 / 96 -> 83 / 96`
  - combined vs policy-only trace action match: `299 / 299 -> 262 / 299`
  - effect-ranking-diff subset combined vs policy-only trace action match: `95 / 95 -> 87 / 95`
- combined is still closer to policy-only than effect-only, but no longer collapsed onto it:
  - combined vs effect-only final action match: `54 / 96 -> 50 / 96`
  - combined vs effect-only trace action match: `183 / 356 -> 169 / 356`

## Cohort slice snapshot

- `low_risk_users = 65`
  - deterministic final action: `continue_plan:65`
  - policy-only final actions: `continue_plan:31, monitor_only:15, trigger_safety_recheck:19`
  - combined final actions: `continue_plan:20, monitor_only:22, trigger_safety_recheck:23`
  - combined `deterministic_vs_learned_disagreement_count = 209`
- `single_goal_users = 76`
  - combined divergence stayed non-zero and increased with the effect-conditioned policy path
- `high_risk_users = 31`
  - deterministic safety ceiling stayed intact
- `cgm_users = 20`
  - combined final actions stayed `ask_targeted_followup:10, trigger_safety_recheck:10`
  - CGM is still the weakest replay slice

## Deterministic baseline status

Frozen eval remained unchanged:

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.90291632090153`
- `next_action_accuracy_pct = 99.21875`
- `explanation_quality_accuracy_pct = 99.47916666666667`
- `safety_reference_accuracy_pct = 99.86979166666667`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 90.40247678018576`

## Current bottlenecks

- combined mode still remains closer to policy-only than effect-only after feature wiring
- low-risk combined terminal mix now over-shifts into `trigger_safety_recheck`
- structured safety coverage, especially `dose_limits`, is still shallow
- official eval bottleneck modality is still `cgm = 72.0%`
- learned artifacts are still replay-only and not runtime-eligible

## Validation

- `python -m ruff check src/wellnessbox_rnd/simulation/closed_loop_v0.py tests/test_closed_loop_simulation.py`
- `python -m pytest tests/test_closed_loop_simulation.py -q`
- `python scripts/run_closed_loop_batch_simulation.py`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_eval`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final_eval`
