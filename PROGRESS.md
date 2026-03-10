# PROGRESS

## Current loop

- Chosen stage: `P3`
- Chosen task: `train effect_model_v1 on richer synthetic longitudinal trajectories`
- Why:
  - runtime knowledge DB wiring exists
  - rich synthetic longitudinal and policy datasets exist
  - learned policy v1 now exists, but learned efficacy was still `v0` and too shallow for domain-level effect reasoning
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## What changed

- Added effect model v1 artifact schema:
  - `src/wellnessbox_rnd/models/effect_model_v1.py`
- Added effect model v1 training/eval module:
  - `src/wellnessbox_rnd/training/effect_model_v1.py`
- Extended exports:
  - `src/wellnessbox_rnd/models/__init__.py`
  - `src/wellnessbox_rnd/training/__init__.py`
- Added v1 training script:
  - `scripts/train_effect_model_v1.py`
- Added regression coverage:
  - `tests/test_effect_model_v1.py`
- Generated new learned artifacts:
  - `artifacts/models/effect_model_v1.json`
  - `artifacts/reports/effect_model_v1_eval.json`
  - `artifacts/reports/effect_model_v1_eval.md`
  - `artifacts/reports/effect_model_v1_splits.json`
  - `artifacts/reports/effect_model_v1_feature_schema.json`
  - `artifacts/reports/effect_model_v1_feature_schema.md`
- Added model documentation:
  - `docs/03_models/07_effect_model_v1.md`

## Effect model v1 snapshot

- `model_name = effect_model_v1`
- `cohort_version = synthetic_longitudinal_v2`
- `seed = 20260310`
- `alpha = 0.01`
- `output_count = 9`
- `feature_count = 70`
- split sizes:
  - `train = 270`
  - `val = 105`
  - `test = 105`
- output names:
  - `blood_glucose`
  - `bone_joint`
  - `energy_support`
  - `general_wellness`
  - `gut_health`
  - `heart_health`
  - `immunity_support`
  - `sleep_support`
  - `stress_support`

## Effect model v1 metrics

- train:
  - `mean_domain_mae = 0.019431`
  - `aggregate_mae = 0.015845`
  - `aggregate_rmse = 0.023304`
  - `aggregate_r2 = 0.909172`
- val:
  - `mean_domain_mae = 0.018197`
  - `aggregate_mae = 0.013834`
  - `aggregate_rmse = 0.018891`
  - `aggregate_r2 = 0.94572`
- test:
  - `mean_domain_mae = 0.025335`
  - `mean_domain_rmse = 0.040893`
  - `aggregate_mae = 0.021604`
  - `aggregate_rmse = 0.03396`
  - `aggregate_r2 = 0.812435`
  - `zero_baseline_aggregate_mae = 0.0572`

## Deterministic boundary

- GPT wrapper was not used in this loop.
- synthetic data uses no actual user data and no external APIs.
- deterministic safety remains upstream of learned artifacts.
- `effect_model_v1` is offline only in this loop and does not alter runtime policy selection.
- frozen eval behavior did not change in this loop.

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

Closed-loop roadmap status:

- no-human runtime action space exists
- citation-backed ingestion pipeline exists
- runtime structured knowledge DB wiring exists
- rich synthetic longitudinal dataset exists
- rich synthetic policy dataset exists
- learned effect model v1 now exists
- learned policy model v1 exists
- multi-user batch replay exists
- next major missing layers are cohort-sliced replay and learned-vs-deterministic batch comparison

## Validation

- `python scripts/train_effect_model_v1.py`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final`
