# PROGRESS

## Current loop

- Chosen stage: `P2/P4`
- Chosen task: `run one bounded combined-replay override diagnostic on the fixed reshaped v4 cohort, comparing combined replay with effect override on vs off while keeping the current effect artifact and restored uniform policy artifact fixed`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
  - `case_count = 480`

## What changed

- Added a simulation-only replay flag in `src/wellnessbox_rnd/simulation/closed_loop_v0.py`:
  - `enable_policy_effect_proxy_override`
  - default stays `True`, so existing replay behavior remains unchanged
- Exposed that flag through `scripts/run_closed_loop_batch_simulation.py` as:
  - `--disable-policy-effect-override`
- Added `scripts/compare_combined_override_modes.py` to compare combined replay:
  - override on
  - override off
  - same dataset
  - same effect artifact
  - same restored uniform policy artifact
- Extended `tests/test_closed_loop_simulation.py` to verify override disabling sets `policy_effect_proxy_override_applied_count` to zero without changing deterministic fallback behavior.
- Generated comparison artifacts:
  - `artifacts/reports/combined_override_comparison_v1.json`
  - `artifacts/reports/combined_override_comparison_v1.md`
- Refreshed the default replay report and frozen eval.

## Why this loop was chosen

- `NEXT_STEPS.md` prioritized a bounded combined-replay diagnostic loop with effect override on vs off.
- Prior artifact retraining loops already showed:
  - policy-only retraining was not sufficient
  - effect-only retraining was not sufficient
- The smallest remaining measurable loop was therefore a replay-only diagnostic of the override gate itself.

## Replay delta

Override off versus override on in combined replay:

- effect override applications dropped:
  - `325 -> 0`
- low-risk combined final-action richness improved slightly:
  - `continue_plan: 65 -> 63`
  - `monitor_only: 0 -> 2`
- low-risk disagreement count improved:
  - `65 -> 60`
- `cgm` disagreement count improved:
  - `3 -> 0`
- but `cgm` terminal-action balance still did not improve:
  - `ask_targeted_followup: 10`
  - `continue_plan: 13`
  - `trigger_safety_recheck: 10`
  - `monitor_only: 0`
  - `re_optimize: 0`
- default replay behavior remains unchanged because the new flag defaults to enabled:
  - combined low-risk final actions in the default report still remain `continue_plan: 65`
  - combined `cgm` final actions in the default report still remain `ask_targeted_followup: 10`, `continue_plan: 13`, `trigger_safety_recheck: 10`

## Interpretation

- This loop localized the blocker further.
- The effect-conditioned override path is now confirmed to suppress the small amount of low-risk `monitor_only` richness that the restored policy artifact can produce.
- But even with override disabled, `cgm` terminal-action balance still does not improve.
- So the next minimal replay-only loop should target the combined override gate / prior thresholds specifically for the `cgm` and threshold-edge region, not more artifact retraining.

## Deterministic baseline status

Frozen eval remained unchanged:

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.90291632090153`
- `next_action_accuracy_pct = 99.21875`
- `explanation_quality_accuracy_pct = 99.47916666666667`
- `safety_reference_accuracy_pct = 99.86979166666667`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 90.40247678018576`

## Safety coverage delta

- rule count stayed flat:
  - `dose_limits = 5 -> 5`
- no deterministic runtime logic, safety rule, or precedence changed in this loop

## Current bottlenecks

- combined replay still produces no `cgm monitor_only` or `cgm re_optimize` final actions
- override off helps low-risk richness but not the `cgm` slice
- combined replay still defaults to the override-on path in the standard report
- the remaining blocker is now narrowed to the combined override gate / priors for `cgm` threshold-edge cases
- `cgm` remains the weakest official frozen-eval modality slice

## Validation

- `python -m ruff check src/wellnessbox_rnd/simulation/closed_loop_v0.py scripts/run_closed_loop_batch_simulation.py scripts/compare_combined_override_modes.py tests/test_closed_loop_simulation.py`
- `python -m pytest tests/test_closed_loop_simulation.py -q`
- `python scripts/compare_combined_override_modes.py`
- `python scripts/run_closed_loop_batch_simulation.py`
- `python -m ruff check .`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final_eval`
