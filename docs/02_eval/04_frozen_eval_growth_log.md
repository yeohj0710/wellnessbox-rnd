# Frozen Eval Growth Log

## Loop 65

- Selected task: `needs_review_due_to_safety reduction`
- Reason: the active priority stayed on safety-review over-conservatism, and
  the remaining anticoagulant `heart_health + energy_support` subset admitted
  one more narrow deterministic release when `vitamin_b_complex` avoidance left
  `coq10` as the only survivor
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count: 254 -> 256`

## New coverage

- Added regressions:
  - `eval-255`
  - `eval-256`
- Existing regressions now pass at runtime:
  - `eval-252`

## Metric delta

- `recommendation_coverage_pct: 100.0 -> 100.0`
- `efficacy_improvement_pp: 9.90291632090153 -> 9.90291632090153`
- `next_action_accuracy_pct: 99.21259842519684 -> 99.21875`
- `explanation_quality_accuracy_pct: 99.4750656167979 -> 99.47916666666667`
- `safety_reference_accuracy_pct: 99.86876640419948 -> 99.86979166666667`
- `adverse_event_count_yearly: 0.0 -> 0.0`
- `sensor_genetic_integration_rate_pct: 90.34267912772586 -> 90.40247678018576`

## Current bottlenecks

- `needs_review_no_candidates = 6`
- `collect_more_input_multiple_missing_items = 5`
- `blocked_minimum_input = 5`
- `needs_review_due_to_safety = 3`
- `collect_more_input_high_priority_missing_info = 3`
- modality bottleneck: `cgm = 36 / 50 = 72.0%`

## Loop 64

- Selected task: `needs_review_due_to_safety reduction`
- Reason: the active priority stayed on safety-review over-conservatism, and
  the remaining anticoagulant `heart_health + blood_glucose` subset admitted one
  more narrow deterministic release
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count: 252 -> 254`

## New coverage

- Added regressions:
  - `eval-253`
  - `eval-254`
- Existing regressions now pass at runtime:
  - `eval-050`
  - `eval-087`
  - `eval-132`

## Metric delta

- `recommendation_coverage_pct: 100.0 -> 100.0`
- `efficacy_improvement_pp: 9.90291632090153 -> 9.90291632090153`
- `next_action_accuracy_pct: 99.2063492063492 -> 99.21259842519684`
- `explanation_quality_accuracy_pct: 99.47089947089947 -> 99.4750656167979`
- `safety_reference_accuracy_pct: 99.86772486772487 -> 99.86876640419948`
- `adverse_event_count_yearly: 0.0 -> 0.0`
- `sensor_genetic_integration_rate_pct: 90.22082018927445 -> 90.34267912772586`

## Current bottlenecks

- `needs_review_no_candidates = 6`
- `collect_more_input_multiple_missing_items = 5`
- `blocked_minimum_input = 5`
- `needs_review_due_to_safety = 4`
- `collect_more_input_high_priority_missing_info = 3`
- modality bottleneck: `cgm = 36 / 50 = 72.0%`

## Loop 63

- Selected task: `needs_review_due_to_safety reduction`
- Reason: `collect_more_input_high_priority_missing_info = 3` is now treated as
  a conservative floor, so the active priority moved to safety-review
  over-conservatism
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count: 250 -> 252`

## New coverage

- Added regressions:
  - `eval-251`
  - `eval-252`
- Existing regressions now pass at runtime:
  - `eval-026`
  - `eval-102`

## Metric delta

- `recommendation_coverage_pct: 100.0 -> 100.0`
- `efficacy_improvement_pp: 9.90291632090153 -> 9.90291632090153`
- `next_action_accuracy_pct: 99.2 -> 99.2063492063492`
- `explanation_quality_accuracy_pct: 99.46666666666667 -> 99.47089947089947`
- `safety_reference_accuracy_pct: 99.86666666666666 -> 99.86772486772487`
- `adverse_event_count_yearly: 0.0 -> 0.0`
- `sensor_genetic_integration_rate_pct: 90.15873015873017 -> 90.22082018927445`

## Current bottlenecks

- `needs_review_due_to_safety = 6`
- `needs_review_no_candidates = 6`
- `collect_more_input_multiple_missing_items = 5`
- `blocked_minimum_input = 5`
- `collect_more_input_high_priority_missing_info = 3`
- modality bottleneck: `cgm = 34 / 48 = 70.83333333333333%`

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
