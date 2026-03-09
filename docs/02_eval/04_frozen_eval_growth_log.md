# Frozen Eval Growth Log

## Loop 60

- Selected task: `blocked_minimum_input reduction`
- Reason: live eval showed the largest actionable mismatch cluster in
  survey-missing heart-health blocked cases
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count: 244 -> 246`

## New coverage

- Added regressions:
  - `eval-245`
  - `eval-246`
- Existing regressions now pass at runtime:
  - `eval-191`
  - `eval-192`
  - `eval-195`
  - `eval-196`

## Metric delta

- `recommendation_coverage_pct: 98.05825242718447 -> 100.0`
- `efficacy_improvement_pp: 9.90291632090153 -> 9.90291632090153`
- `next_action_accuracy_pct: 97.54098360655738 -> 99.1869918699187`
- `explanation_quality_accuracy_pct: 98.63387978142076 -> 99.4579945799458`
- `safety_reference_accuracy_pct: 99.31693989071039 -> 99.86449864498645`
- `adverse_event_count_yearly: 0.0 -> 0.0`
- `sensor_genetic_integration_rate_pct: 90.03215434083602 -> 90.09584664536742`

## Current bottlenecks

- `collect_more_input_high_priority_missing_info = 10`
- `needs_review_due_to_safety = 7`
- `needs_review_no_candidates = 6`
- `blocked_minimum_input = 5`
- modality bottleneck: `cgm = 34 / 48 = 70.83333333333333%`
