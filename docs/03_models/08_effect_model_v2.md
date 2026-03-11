# Effect Model v2

## Loop choice

- chosen stage: `P2/P3`
- chosen task: `retrain learned effect on synthetic_longitudinal_v3 for guarded replay divergence`

## Why v2 exists

- `effect_model_v1` learned domain deltas, but the v2 replay evidence showed:
  - `32` raw ranking disagreements
  - `0` final-policy divergence
  - `0` final-state divergence
- the blocker was mostly data shape, not replay plumbing:
  - low-risk users collapsed to baseline-only effect windows
  - later-step safe near-tie candidates were scarce
  - schedule / dose / adherence patterns were too weak

## Inputs and targets

- training dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v3.jsonl`
- artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/effect_model_v2.json`
- target:
  - domain-level `delta_z_by_domain`
- aggregate effect:
  - computed as the mean of predicted domain deltas

## Feature changes

`effect_model_v2` keeps the same ridge-regression family as v1, but the input state is richer because the feature builder now includes:

- `trajectory_step`
- `day_index`
- `adherence_proxy`
- `side_effect_proxy`
- `risk_tier_low`
- `risk_tier_moderate`
- `risk_tier_high`
- richer schedule / regimen status combinations from v3

## Training result

- split sizes:
  - `train = 270`
  - `val = 105`
  - `test = 105`
- test metrics:
  - `mean_domain_mae = 0.0068`
  - `mean_domain_rmse = 0.010397`
  - `aggregate_mae = 0.004706`
  - `aggregate_rmse = 0.006304`
  - `aggregate_r2 = 0.989975`
  - `zero_baseline_aggregate_mae = 0.074547`

## Replay effect

On `synthetic_longitudinal_v3` replay:

- `learned_effect_guarded`
  - `raw_ranking_disagreement_count = 50`
  - `differing_ranking_user_ids = 13`
  - `differing_final_policy_user_ids = 54`
  - `differing_final_state_user_ids = 42`
- low-risk cohort:
  - deterministic final action: `continue_plan:54`
  - learned-effect final actions: `monitor_only:14, re_optimize:40`

## Boundary

- `effect_model_v2` is still replay-only
- deterministic safety remains upstream
- reranking still happens only after deterministic candidate filtering
- pregnancy / medication / condition / explicit avoid still block learned reranking

## Next recommended work

1. calibrate learned effect scale against deterministic fallback to avoid a trivially pessimistic effect shift
2. analyze why combined mode still mostly follows guarded policy output
3. expand structured safety `dose_limits` before any wider learned runtime use
