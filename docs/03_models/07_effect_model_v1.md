# Effect Model v1

## Loop choice

- chosen stage: `P3`
- chosen task: `train effect_model_v1 on synthetic_longitudinal_v2`

## Why this loop

- `policy_model_v1` already exists on the richer synthetic state space
- learned efficacy was still `v0` and only predicted a single proxy score
- the next missing learned module was a richer offline effect model that predicts domain-level outcome deltas from baseline state plus regimen structure

## Artifacts

- training dataset:
  - [synthetic_longitudinal_v2.jsonl](/c:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v2.jsonl)
- model artifact:
  - [effect_model_v1.json](/c:/dev/wellnessbox-rnd/artifacts/models/effect_model_v1.json)
- evaluation reports:
  - [effect_model_v1_eval.json](/c:/dev/wellnessbox-rnd/artifacts/reports/effect_model_v1_eval.json)
  - [effect_model_v1_eval.md](/c:/dev/wellnessbox-rnd/artifacts/reports/effect_model_v1_eval.md)
- feature schema:
  - [effect_model_v1_feature_schema.json](/c:/dev/wellnessbox-rnd/artifacts/reports/effect_model_v1_feature_schema.json)
  - [effect_model_v1_feature_schema.md](/c:/dev/wellnessbox-rnd/artifacts/reports/effect_model_v1_feature_schema.md)
- split artifact:
  - [effect_model_v1_splits.json](/c:/dev/wellnessbox-rnd/artifacts/reports/effect_model_v1_splits.json)

## Model design

- model family:
  - multi-target ridge regression implemented with `numpy`
- targets:
  - domain-level `delta_z_by_domain`
  - aggregate delta is derived as the mean of predicted domain deltas
- output domains:
  - `blood_glucose`
  - `bone_joint`
  - `energy_support`
  - `general_wellness`
  - `gut_health`
  - `heart_health`
  - `immunity_support`
  - `sleep_support`
  - `stress_support`

## Feature schema

- feature_count: `70`
- feature groups:
  - `scalar = 21`
  - `goal = 9`
  - `baseline = 9`
  - `regimen = 11`
  - `dose = 11`
  - `schedule = 5`
  - `regimen_status = 4`

Feature families include:

- personal state:
  - age
  - pregnancy
  - sleep hours
  - stress level
  - goals / symptoms / medications / conditions
- modality availability:
  - wearable
  - cgm
  - genetic
  - nhis
- baseline PRO:
  - aggregate z
  - domain z by goal
- regimen structure:
  - ingredient keys
  - per-ingredient daily dose
  - schedule slots
  - regimen status counts

## Metrics

- split sizes:
  - train = `270`
  - val = `105`
  - test = `105`
- selected alpha: `0.01`
- test metrics:
  - `mean_domain_mae = 0.025335`
  - `mean_domain_rmse = 0.040893`
  - `aggregate_mae = 0.021604`
  - `aggregate_rmse = 0.03396`
  - `aggregate_r2 = 0.812435`
  - `zero_baseline_mean_domain_mae = 0.0572`
  - `zero_baseline_aggregate_mae = 0.0572`

## Interpretation

- `effect_model_v1` materially outperforms a zero-delta baseline on both domain and aggregate targets
- this is a more meaningful learned efficacy artifact than `v0` because it learns explicit domain shifts, not only an abstract effect proxy
- the artifact remains offline only in this loop and does not bypass deterministic safety or frozen-eval behavior

## Next recommended work

1. add guarded `policy_model_v1` plus `effect_model_v1` into batch replay for learned-vs-deterministic comparison
2. slice replay by `cgm`, `genetic`, `low-risk/high-risk`, and `single-goal/multi-goal`
3. improve synthetic richness for underrepresented response patterns, especially stronger `re_optimize` and adverse-tolerability trajectories

## Current replay integration status

- `effect_model_v1` is now wired into guarded batch replay only:
  - `artifacts/reports/closed_loop_batch_simulation_v1_compare.json`
- Guard boundary remained narrow by design:
  - only after deterministic candidate filtering
  - only on `low_risk`
  - never for pregnancy / medications / conditions / explicit avoid
  - only inside a near-tied deterministic candidate window
- Full replay snapshot:
  - `raw_ranking_disagreement_count = 32`
  - `effect_guard_applied_count = 32`
  - `differing_final_policy_user_ids = 0`
  - `differing_final_state_user_ids = 0`
- Interpretation:
  - the model can disagree with deterministic ranking on guarded low-risk steps
  - current synthetic signal plus clamp policy is still too conservative to create final replay divergence
  - the next improvement target is richer synthetic effect separation, not weaker guards
