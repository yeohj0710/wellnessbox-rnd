# Frozen Eval Growth Log

## Loop 62

- Selected task: `collect_more_input_high_priority_missing_info reduction`
- Reason: live eval still had the forced-priority missing-info bucket in pure
  blood-glucose cases with explicit post-meal spike detail
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count: 248 -> 250`

## New coverage

- Added regressions:
  - `eval-249`
  - `eval-250`
- Existing regressions now pass at runtime:
  - `eval-007`
  - `eval-014`

## Metric delta

- `recommendation_coverage_pct: 100.0 -> 100.0`
- `efficacy_improvement_pp: 9.90291632090153 -> 9.90291632090153`
- `next_action_accuracy_pct: 99.19354838709677 -> 99.2`
- `explanation_quality_accuracy_pct: 99.46236559139786 -> 99.46666666666667`
- `safety_reference_accuracy_pct: 99.86559139784946 -> 99.86666666666666`
- `adverse_event_count_yearly: 0.0 -> 0.0`
- `sensor_genetic_integration_rate_pct: 90.15873015873017 -> 90.15873015873017`

## Current bottlenecks

- `needs_review_due_to_safety = 7`
- `needs_review_no_candidates = 6`
- `collect_more_input_multiple_missing_items = 5`
- `blocked_minimum_input = 5`
- `collect_more_input_high_priority_missing_info = 3`
- modality bottleneck: `cgm = 34 / 48 = 70.83333333333333%`

## Loop 61

- Selected task: `collect_more_input_high_priority_missing_info reduction`
- Reason: live eval still had the forced-priority missing-info bucket in
  survey-missing anticoagulant heart-health cases
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count: 246 -> 248`

## New coverage

- Added regressions:
  - `eval-247`
  - `eval-248`
- Existing regressions now pass at runtime:
  - `eval-070`
  - `eval-095`
  - `eval-142`
  - `eval-243`
  - `eval-244`

## Metric delta

- `recommendation_coverage_pct: 100.0 -> 100.0`
- `efficacy_improvement_pp: 9.90291632090153 -> 9.90291632090153`
- `next_action_accuracy_pct: 99.1869918699187 -> 99.19354838709677`
- `explanation_quality_accuracy_pct: 99.4579945799458 -> 99.46236559139786`
- `safety_reference_accuracy_pct: 99.86449864498645 -> 99.86559139784946`
- `adverse_event_count_yearly: 0.0 -> 0.0`
- `sensor_genetic_integration_rate_pct: 90.09584664536742 -> 90.15873015873017`

## Current bottlenecks

- `needs_review_due_to_safety = 7`
- `needs_review_no_candidates = 6`
- `collect_more_input_high_priority_missing_info = 5`
- `collect_more_input_multiple_missing_items = 5`
- `blocked_minimum_input = 5`
- modality bottleneck: `cgm = 34 / 48 = 70.83333333333333%`

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
