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
  - `needs_human_review = 7`
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

 - loop task: `collect_more_input_multiple_missing_items reduction`
- current-loop decision:
  - no new runtime release was introduced
  - added an explicit floor helper for the remaining sleep-related multi-goal
    multiple-missing-items cases
  - preserved pregnancy, medication/condition, and avoid guards
- remaining multiple-missing-items subset:
  - `eval-002`
  - `eval-005`
  - `eval-107`
  - `eval-156`

## False-positive / false-negative notes

- current major unresolved gaps remain conservative gating, not
  over-recommendation
- `collect_more_input_multiple_missing_items` stayed at `4`
- `eval-002` is now an explicit negative boundary because a single `coq10`
  survivor under `SAFETY-ANTICOAG-001` does not replace explicit heart symptom
  detail or survey-backed activity context
- `eval-107` and `eval-156` are now explicit negative boundaries because
  wearable or genetic recovery context does not replace explicit sleep symptom
  detail plus sleep-hours detail for a conservative multi-goal sleep plan
- the only released subset in this bucket remains the multimodal,
  single-goal, low-risk general-wellness case `eval-023`
- the remaining four cases still require conservative intake gating because
  they depend on medication, pregnancy/condition, or multi-goal context that is
  not safely recoverable from the current signals alone
- `collect_more_input_high_priority_missing_info = 3` remains a conservative
  floor and is no longer the active loop target
- `needs_review_due_to_safety = 3` also remains a conservative floor
- `needs_review_no_candidates = 4` remains the explicit-avoid floor
- bottleneck modality remains `cgm`

## Next recommended code target

1. move to `blocked_minimum_input`
2. treat `eval-002`, `eval-005`, `eval-107`, and `eval-156` as the remaining
   `collect_more_input_multiple_missing_items` set unless source-of-truth
   exposes a narrower safe subset
3. keep `needs_review_no_candidates = 4`,
   `needs_review_due_to_safety = 3`, and
   `collect_more_input_high_priority_missing_info = 3` as floors
