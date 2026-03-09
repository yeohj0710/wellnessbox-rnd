# Baseline Gap Report

Updated against:

- dataset: `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
- report: `C:/dev/wellnessbox-rnd/artifacts/reports/final_loop60/eval_report.json`

## Official metrics

| metric | score | target | note |
| --- | ---: | ---: | --- |
| `recommendation_coverage_pct` | `100.0` | `80.0` | pass |
| `efficacy_improvement_pp` | `9.90291632090153` | `> 0` | pass |
| `next_action_accuracy_pct` | `99.1869918699187` | `80.0` | pass |
| `explanation_quality_accuracy_pct` | `99.4579945799458` | `91.0` | pass |
| `safety_reference_accuracy_pct` | `99.86449864498645` | `95.0` | pass |
| `adverse_event_count_yearly` | `0.0` | `<= 5.0` | pass |
| `sensor_genetic_integration_rate_pct` | `90.09584664536742` | `90.0` | pass |

가정:

- `efficacy_improvement_pp`는 synthetic follow-up z-score pair 기준이다.
- `sensor_genetic_integration_rate_pct`는 attempted/success pooled proxy다.

## Distribution snapshot

- `case_count = 246`
- expected next action:
  - `start_plan = 211`
  - `collect_more_input = 22`
  - `needs_human_review = 13`
- modality attempted/success:
  - `wearable = 127 / 118 = 92.91338582677166%`
  - `cgm = 48 / 34 = 70.83333333333333%`
  - `genetic = 138 / 130 = 94.20289855072464%`
- bottleneck modality: `cgm`

## Runtime failure buckets

Current runtime next-action reason buckets:

| rank | bucket | count | class | next code path |
| --- | --- | ---: | --- | --- |
| 1 | `collect_more_input_high_priority_missing_info` | `10` | missing-info gate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 2 | `needs_review_due_to_safety` | `7` | conservative gating | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 3 | `needs_review_no_candidates` | `6` | conservative gating / no-candidate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 4 | `collect_more_input_multiple_missing_items` | `5` | missing-info gate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 5 | `blocked_minimum_input` | `5` | conservative gating | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |

## Current loop impact

- loop task: `blocked_minimum_input reduction`
- target fixed by code:
  - survey-missing heart-health blocked cases with wearable low-activity context
- regressions fixed:
  - `eval-191`
  - `eval-192`
  - `eval-195`
  - `eval-196`
- regressions added:
  - `eval-245`
  - `eval-246`

## False-positive / false-negative notes

- current major unresolved gaps are conservative gating, not over-recommendation
- parser/alias miss remains represented in the dataset (`parser_limit = 19`),
  but it is not the top runtime bucket in this loop
- no separate false-positive bucket exceeded the current top-5 runtime gates

## Next recommended code target

1. reduce `collect_more_input_high_priority_missing_info`
2. add at least `2` harder regression cases where modality context exists but
   high-priority intake context is still insufficient
3. then choose exactly one of:
   - another missing-info reduction
   - `cgm` deterministic follow-through improvement
