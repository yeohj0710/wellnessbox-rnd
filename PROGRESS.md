# PROGRESS

## Current loop

- Chosen task: `blocked_minimum_input reduction`
- Reason: live eval showed the main actionable mismatch cluster in survey-missing
  heart-health blocked cases (`eval-191`, `eval-192`, `eval-195`, `eval-196`)
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 246`

## What changed

- `_can_clear_heart_survey_only_block(...)` now accepts the same narrow
  missing-code envelope as the existing heart survey fallback:
  - `missing_survey`
  - `missing_heart_context`
  - optional `missing_primary_symptom`
  - optional `missing_current_supplements`
- The helper still stays conservative:
  - non-pregnant only
  - no medications / no conditions / no avoid list
  - `heart_health` only
  - wearable low-activity context required
  - rule ids limited to `INTAKE-SURVEY-001` and optional `SAFETY-DUP-001`
  - survivors limited to `omega3 + coq10` or `coq10`
- New frozen regressions added:
  - `eval-245`
  - `eval-246`
- Existing frozen regressions now pass at runtime:
  - `eval-191`
  - `eval-192`
  - `eval-195`
  - `eval-196`

## Metric delta

Baseline before this loop:

- `recommendation_coverage_pct = 98.05825242718447`
- `efficacy_improvement_pp = 9.90291632090153`
- `next_action_accuracy_pct = 97.54098360655738`
- `explanation_quality_accuracy_pct = 98.63387978142076`
- `safety_reference_accuracy_pct = 99.31693989071039`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 90.03215434083602`

After this loop:

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.90291632090153`
- `next_action_accuracy_pct = 99.1869918699187`
- `explanation_quality_accuracy_pct = 99.4579945799458`
- `safety_reference_accuracy_pct = 99.86449864498645`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 90.09584664536742`

## Current bottlenecks

Runtime next-action reason buckets:

1. `collect_more_input_high_priority_missing_info = 10`
2. `needs_review_due_to_safety = 7`
3. `needs_review_no_candidates = 6`
4. `blocked_minimum_input = 5`

Modality bottleneck:

- `cgm = 34 / 48 = 70.83333333333333%`

## Validation

- `python -m ruff check .`
- `python -m pytest`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/final_loop60`
