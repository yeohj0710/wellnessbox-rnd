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

- Chosen stage: `P2/P3`
- Chosen task: `calibrated synthetic effect richness + effect_model_v3 retrain + guarded replay rerun`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## New artifacts

- synthetic cohort:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
- retrained effect artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/effect_model_v3.json`
- replay compare:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_compare.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_compare.md`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_trace_samples.json`

## What changed technically

- added `synthetic_longitudinal_v4` with more modality-available low-risk users and threshold-edge near-tie trajectories
- effect artifact now stores a calibrated policy proxy on top of domain-delta predictions
- replay now reranks only inside the guarded near-tie survivor set instead of scoring the full candidate list then clamping
- `learned_effect_guarded` regained non-zero final divergence after calibration
- deterministic safety boundary and frozen eval stayed unchanged

## Guard boundary

- runtime recommendation and frozen eval remain deterministic
- learned effect remains replay-only
- learned effect stays behind deterministic candidate filtering and low-risk gating
- learned effect now scores only the near-tie survivor subset
- learned policy remains replay-only and bounded by the deterministic ceiling
- no human-review or handoff action was introduced

## 4-mode compare snapshot

- `deterministic_only`
  - `total_trace_steps = 356`
  - `final_actions = ask_targeted_followup:21, continue_plan:65, trigger_safety_recheck:10`
- `learned_effect_guarded`
  - `raw_ranking_disagreement_count = 71`
  - `effect_guard_applied_count = 0`
  - `differing_ranking_user_ids = 22`
  - `differing_final_policy_user_ids = 25`
  - `differing_final_state_user_ids = 24`
- `learned_policy_guarded`
  - `raw_policy_disagreement_count = 171`
  - `policy_guard_applied_count = 102`
  - `differing_final_policy_user_ids = 34`
  - `differing_final_state_user_ids = 19`
- `learned_effect_and_policy_guarded`
  - combined mode still mostly follows guarded policy output

## Cohort slice snapshot

- `low_risk_users = 65`
  - deterministic final action stayed `continue_plan`
  - learned-effect final actions shifted to `continue_plan:40, monitor_only:1, re_optimize:24`
  - `deterministic_vs_learned_disagreement_count = 171`
- `single_goal_users = 76`
  - learned-effect final divergence is also non-zero here
- `high_risk_users = 31`
  - deterministic safety ceiling stayed intact
- `cgm_users = 20`
  - learned-effect final divergence stayed `0`

## Validation snapshot

- `python -m ruff check .`
- `python -m pytest`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_eval`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final_eval`
- `python scripts/generate_synthetic_longitudinal_v4.py`
- `python scripts/train_effect_model_v3.py`
- `python scripts/run_closed_loop_batch_simulation.py`

## Recommended next loop

1. analyze why combined mode is still policy-dominated after effect calibration
2. expand `dose_limits` and structured safety coverage
3. increase terminal threshold-edge `monitor_only` density in low-risk trajectories
