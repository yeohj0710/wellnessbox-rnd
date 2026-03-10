# Policy Model v0

## Loop choice

- chosen stage: `P3`
- chosen task: `train next-action / policy model v0 on synthetic longitudinal records`

## Why this connects to the autonomous agent target

- the no-human action space already exists
- citation-backed ingestion now exists
- the next missing learned module is a policy model that can score system-owned next actions without human handoff semantics
- this model is trained only on repo-local synthetic data and remains downstream of deterministic safety guards

## Scope

- dataset source:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v1.jsonl`
- derived policy dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/policy_training_v0.jsonl`
- model artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/policy_model_v0.json`
- evaluation artifacts:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/policy_model_v0_eval.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/policy_model_v0_eval.md`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/policy_model_v0_splits.json`

## Model design

- lightweight deterministic training:
  - multiclass ridge classifier implemented with `numpy`
- target classes:
  - `start_plan`
  - `collect_more_input`
  - `trigger_safety_recheck`
- features include:
  - profile and lifestyle
  - goal / symptom / condition / medication context
  - modality availability
  - current supplements and baseline candidate keys
  - `follow_up_step`
  - `expected_effect_proxy`
  - `adherence_proxy`
  - `risk_tier`
  - `adverse_event`
  - `closed_loop_state`
  - `safety_status`

## Deterministic guard boundary

- GPT wrapper was not used
- safety hard rules still stay outside the learned model
- evaluation reports both:
  - raw learned prediction
  - guard-adjusted prediction
  - deterministic policy replay
- guard rule:
  - if learned output is more permissive than deterministic policy, clamp back to deterministic action

## Interpretation

- because synthetic labels come from deterministic policy generation, deterministic replay remains the ceiling baseline
- the purpose of v0 is not to replace that baseline immediately
- the purpose is to establish:
  - policy dataset
  - trainable model artifact
  - comparable evaluation loop
  - guarded learned-policy interface

## Next recommended work

1. integrate guarded policy inference into multi-user batch simulation only after aggregate metrics exist
2. expand synthetic policy data beyond the current three-action distribution
3. connect knowledge-base evidence features into future policy or safety models through deterministic validators only
