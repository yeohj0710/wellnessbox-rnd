# Policy Model v1

## Loop choice

- chosen stage: `P3`
- chosen task: `train policy_model_v1 on synthetic_longitudinal_v2`

## Why this loop

- `policy_training_v1` now contains the richer no-human action space
- `policy_model_v0` still only reflected the earlier 3-action synthetic dataset
- the highest-leverage single next step was to learn next-action selection from the richer synthetic state while keeping deterministic safety upstream

## Artifacts

- training dataset:
  - [synthetic_longitudinal_v2.jsonl](/c:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v2.jsonl)
- flattened policy dataset:
  - [policy_training_v1.jsonl](/c:/dev/wellnessbox-rnd/data/synthetic/policy_training_v1.jsonl)
- model artifact:
  - [policy_model_v1.json](/c:/dev/wellnessbox-rnd/artifacts/models/policy_model_v1.json)
- evaluation reports:
  - [policy_model_v1_eval.json](/c:/dev/wellnessbox-rnd/artifacts/reports/policy_model_v1_eval.json)
  - [policy_model_v1_eval.md](/c:/dev/wellnessbox-rnd/artifacts/reports/policy_model_v1_eval.md)
- feature schema:
  - [policy_model_v1_feature_schema.json](/c:/dev/wellnessbox-rnd/artifacts/reports/policy_model_v1_feature_schema.json)
  - [policy_model_v1_feature_schema.md](/c:/dev/wellnessbox-rnd/artifacts/reports/policy_model_v1_feature_schema.md)
- split artifact:
  - [policy_model_v1_splits.json](/c:/dev/wellnessbox-rnd/artifacts/reports/policy_model_v1_splits.json)

## Model design

- lightweight multiclass ridge classifier implemented with `numpy`
- target classes:
  - `ask_targeted_followup`
  - `continue_plan`
  - `monitor_only`
  - `re_optimize`
  - `reduce_or_stop`
  - `trigger_safety_recheck`
- feature count: `66`
- feature groups:
  - scalar = `30`
  - goal = `9`
  - baseline = `9`
  - follow_up = `9`
  - delta = `9`

## Metrics

- split sizes:
  - train = `270`
  - val = `105`
  - test = `105`
- test metrics:
  - raw_accuracy = `0.904762`
  - guarded_accuracy = `0.8`
  - deterministic_accuracy = `0.2`
  - majority_baseline_accuracy = `0.32381`

## Deterministic guard boundary

- raw learned prediction is never the final safety authority
- guard path still compares learned output against deterministic `recommend()` output
- if learned output is more permissive than deterministic policy, it is clamped back by the guard
- structured safety remains upstream and unchanged

## Interpretation

- raw learned performance is high because the richer synthetic trajectories are internally coherent
- guarded accuracy drops relative to raw accuracy because deterministic clamping still overrides more permissive learned predictions
- guarded accuracy remains far above both deterministic replay and majority baseline on this dataset

## Next recommended work

1. train `effect_model_v1` on the same `synthetic_longitudinal_v2` dataset so closed-loop replay can compare learned policy and learned efficacy together
2. wire `policy_model_v1` into batch replay only behind the same deterministic safety guard
3. add cohort-sliced replay for `cgm`, `genetic`, `low-risk/high-risk`, and `single-goal/multi-goal`
