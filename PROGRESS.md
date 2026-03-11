# PROGRESS

## Current loop

- Chosen stage: `P2/P3`
- Chosen task: `calibrated synthetic effect richness + effect_model_v3 retrain + guarded replay rerun`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## What changed

- Added calibrated low-risk effect cohort generation:
  - `src/wellnessbox_rnd/synthetic/rich_longitudinal_v4.py`
  - `scripts/generate_synthetic_longitudinal_v4.py`
  - `data/synthetic/synthetic_longitudinal_v4.jsonl`
- Added retrained effect artifact with policy-facing calibration:
  - `scripts/train_effect_model_v3.py`
  - `artifacts/models/effect_model_v3.json`
  - `artifacts/reports/effect_model_v3_eval.json`
  - `artifacts/reports/effect_model_v3_feature_schema.json`
- Added calibrated effect proxy path to the model artifact:
  - `src/wellnessbox_rnd/models/effect_model_v1.py`
  - `src/wellnessbox_rnd/training/effect_model_v1.py`
- Changed replay rerank to score only the guarded near-tie survivor set:
  - `src/wellnessbox_rnd/simulation/closed_loop_v0.py`
  - `scripts/run_closed_loop_batch_simulation.py`
- Added v4 regression coverage:
  - `tests/test_effect_model_v1.py`
  - `tests/test_rich_synthetic_longitudinal_v3.py`
  - `tests/test_rich_synthetic_longitudinal_v4.py`

## Synthetic v4 snapshot

- `synthetic_longitudinal_v4`
  - `96 users`
  - `480 records`
  - `5 steps per user`
- risk counts:
  - `low = 325`
  - `high = 155`
- next-action counts:
  - `continue_plan = 250`
  - `monitor_only = 94`
  - `trigger_safety_recheck = 75`
  - `reduce_or_stop = 48`
  - `ask_targeted_followup = 10`
  - `re_optimize = 3`
- modality counts:
  - `wearable = 420`
  - `genetic = 265`
  - `cgm = 100`

## Learned effect / policy / deterministic boundary

- frozen eval remains deterministic
- runtime safety remains deterministic
- learned effect is still replay-only
- learned effect still runs only after deterministic candidate filtering
- learned effect now scores only the guarded near-tie survivor set
- learned effect rerank is allowed only when:
  - safety status is `ok`
  - risk tier is `low`
  - no pregnancy
  - no medications
  - no conditions
  - no explicit avoid ingredients
- learned policy remains replay-only and bounded by the deterministic ceiling

## Effect model v3 result

- training dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
- artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/effect_model_v3.json`
- split sizes:
  - `train = 275`
  - `val = 125`
  - `test = 80`
- calibration:
  - `policy_proxy_slope = 3.11735613`
  - `policy_proxy_intercept = 0.09283873`
- test metrics:
  - `mean_domain_mae = 0.005517`
  - `aggregate_mae = 0.003698`
  - `aggregate_r2 = 0.986755`
  - `policy_proxy_mae = 0.040029`
  - `zero_baseline_policy_proxy_mae = 0.1903`

## 4-mode replay snapshot

- replay artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_compare.json`
- markdown summary:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_compare.md`
- trace samples:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_trace_samples.json`

Full-run aggregate on `96` synthetic users:

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
  - `raw_ranking_disagreement_count = 66`
  - `raw_policy_disagreement_count = 218`
  - final actions still follow guarded policy more than learned effect

## Cohort slice snapshot

- `low_risk_users = 65`
  - deterministic final action: `continue_plan:65`
  - learned-effect final actions: `continue_plan:40, monitor_only:1, re_optimize:24`
  - `deterministic_vs_learned_disagreement_count = 171`
- `single_goal_users = 76`
  - learned-effect final actions: `ask_targeted_followup:11, continue_plan:40, monitor_only:1, re_optimize:24`
  - `deterministic_vs_learned_disagreement_count = 171`
- `high_risk_users = 31`
  - learned-effect final divergence stayed `0`
- `cgm_users = 20`
  - learned-effect final divergence stayed `0`
- `genetic_users = 53`
  - learned-effect final actions: `continue_plan:16, monitor_only:1, re_optimize:16`

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

- combined mode is still policy-dominated even after effect calibration
- low-risk final action mix still has only `1` `monitor_only` case at terminal step
- structured safety coverage, especially `dose_limits`, is still shallow
- official eval bottleneck modality is still `cgm = 72.0%`
- learned artifacts are still simulation-only

## Validation

- `python scripts/generate_synthetic_longitudinal_v4.py`
- `python scripts/train_effect_model_v3.py`
- `python scripts/run_closed_loop_batch_simulation.py`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_eval`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final_eval`
