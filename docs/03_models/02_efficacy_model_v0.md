# Efficacy Model v0

## Scope

This loop adds the first trainable efficacy quantification model on top of the
synthetic longitudinal cohort.

- stage: `P1`
- task: `efficacy quantification model v0`
- target:
  - predict `expected_effect_proxy`
  - remain lightweight and CPU-friendly
  - preserve deterministic safety and frozen-eval baseline as guardrails

## Design

- model family: ridge-style linear regression implemented with `numpy`
- no external training dependency is required
- user-level deterministic split:
  - train / val / test are separated by `user_id`
- features:
  - demographics and lifestyle
  - goals, symptoms, conditions, medications
  - input availability
  - current supplement state
  - follow-up step
  - baseline recommendation count and baseline candidate identities

## Artifacts

- model artifact: [efficacy_model_v0.json](/c:/dev/wellnessbox-rnd/artifacts/models/efficacy_model_v0.json)
- evaluation JSON: [efficacy_model_v0_eval.json](/c:/dev/wellnessbox-rnd/artifacts/reports/efficacy_model_v0_eval.json)
- evaluation Markdown: [efficacy_model_v0_eval.md](/c:/dev/wellnessbox-rnd/artifacts/reports/efficacy_model_v0_eval.md)
- split artifact: [efficacy_model_v0_splits.json](/c:/dev/wellnessbox-rnd/artifacts/reports/efficacy_model_v0_splits.json)

## Guardrails

- training data comes only from
  [synthetic_longitudinal_v1.jsonl](/c:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v1.jsonl)
- deterministic baseline remains unchanged
- no safety logic is bypassed
- model is trained offline only and is not yet integrated into runtime

## Training result

- seed: `20260310`
- feature_count: `61`
- split sizes:
  - `train = 99`
  - `val = 30`
  - `test = 15`
- selected alpha: `0.01`
- held-out test:
  - `mae = 0.026791`
  - `rmse = 0.040277`
  - `r2 = 0.963691`
  - baseline `mae = 0.182578`
  - baseline `rmse = 0.211372`

## Interpretation

- this is a trainable minimum model, not a runtime replacement
- it demonstrates that the synthetic cohort carries enough signal for a first
  learned efficacy predictor
- deterministic safety and frozen-eval behavior remain unchanged
