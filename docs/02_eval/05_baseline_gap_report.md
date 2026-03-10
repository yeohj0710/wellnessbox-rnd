# Baseline Gap Report

Updated against:

- dataset: `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
- report: `C:/dev/wellnessbox-rnd/artifacts/reports/current_loop_final/eval_report.json`

## Official metrics

| metric | score | target | note |
| --- | ---: | ---: | --- |
| `recommendation_coverage_pct` | `100.0` | `80.0` | pass |
| `efficacy_improvement_pp` | `9.90291632090153` | `> 0` | pass |
| `next_action_accuracy_pct` | `99.21875` | `80.0` | pass |
| `explanation_quality_accuracy_pct` | `99.47916666666667` | `91.0` | pass |
| `safety_reference_accuracy_pct` | `99.86979166666667` | `95.0` | pass |
| `adverse_event_count_yearly` | `0.0` | `<= 5.0` | pass |
| `sensor_genetic_integration_rate_pct` | `90.40247678018576` | `90.0` | pass |

## Distribution snapshot

- `case_count = 256`
- expected next action:
  - `start_plan = 235`
  - `collect_more_input = 14`
  - `trigger_safety_recheck = 7`
- modality attempted/success:
  - `wearable = 135 / 126 = 93.33333333333333%`
  - `cgm = 50 / 36 = 72.0%`
  - `genetic = 138 / 130 = 94.20289855072464%`
- bottleneck modality: `cgm`

## Runtime failure buckets

Current runtime next-action reason buckets:

| rank | bucket | count | class | next code path |
| --- | --- | ---: | --- | --- |
| 1 | `blocked_minimum_input` | `5` | conservative gating | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 2 | `collect_more_input_multiple_missing_items` | `4` | missing-info gate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 3 | `needs_review_no_candidates` | `4` | conservative gating / no-candidate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 4 | `needs_review_due_to_safety` | `3` | conservative gating | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 5 | `collect_more_input_high_priority_missing_info` | `3` | missing-info gate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |

## Current loop impact

 - loop task: `P4 batch closed-loop replay`
- current-loop decision:
  - added multi-user replay and aggregate transition metrics
  - compared deterministic-only vs learned-policy-guarded replay
  - kept runtime next-action semantics, frozen eval expectations, and conservative buckets unchanged
  - preserved pregnancy, medication/condition, and avoid guards
  - kept deterministic policy as the guard ceiling for learned outputs

## False-positive / false-negative notes

- current major unresolved gaps remain conservative gating, not
  over-recommendation
- `trigger_safety_recheck = 7` is now the autonomous replacement for the old
  review action bucket
- the underlying conservative reasons did not change:
  - `needs_review_no_candidates = 4`
  - `needs_review_due_to_safety = 3`
- review-floor examples remain:
  - `eval-027`, `eval-059`, `eval-060`, `eval-061`
  - `eval-063`, `eval-110`, `eval-254`
- `collect_more_input_high_priority_missing_info = 3` remains a conservative
  floor and is no longer the active loop target
- `needs_review_due_to_safety = 3` also remains a conservative floor
- `needs_review_no_candidates = 4` remains the explicit-avoid floor
- bottleneck modality remains `cgm`

## Next recommended code target

1. wire citation-backed knowledge artifacts into deterministic safety/rule loading
2. broaden synthetic policy labels so learned-policy replay can diverge meaningfully from deterministic replay
3. keep `needs_review_no_candidates = 4`,
   `needs_review_due_to_safety = 3`, and
   `collect_more_input_high_priority_missing_info = 3` as floors
