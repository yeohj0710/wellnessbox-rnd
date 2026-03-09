# Baseline Gap Report

Updated against:

- dataset: `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
- report: `C:/dev/wellnessbox-rnd/artifacts/reports/current_loop_final/eval_report.json`

## Official metrics

| metric | score | target | note |
| --- | ---: | ---: | --- |
| `recommendation_coverage_pct` | `100.0` | `80.0` | pass |
| `efficacy_improvement_pp` | `9.90291632090153` | `> 0` | pass |
| `next_action_accuracy_pct` | `99.2` | `80.0` | pass |
| `explanation_quality_accuracy_pct` | `99.46666666666667` | `91.0` | pass |
| `safety_reference_accuracy_pct` | `99.86666666666666` | `95.0` | pass |
| `adverse_event_count_yearly` | `0.0` | `<= 5.0` | pass |
| `sensor_genetic_integration_rate_pct` | `90.15873015873017` | `90.0` | pass |

## Distribution snapshot

- `case_count = 250`
- expected next action:
  - `start_plan = 222`
  - `collect_more_input = 15`
  - `needs_human_review = 13`
- modality attempted/success:
  - `wearable = 129 / 120 = 93.02325581395348%`
  - `cgm = 48 / 34 = 70.83333333333333%`
  - `genetic = 138 / 130 = 94.20289855072464%`
- bottleneck modality: `cgm`

## Runtime failure buckets

Current runtime next-action reason buckets:

| rank | bucket | count | class | next code path |
| --- | --- | ---: | --- | --- |
| 1 | `needs_review_due_to_safety` | `7` | conservative gating | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 2 | `needs_review_no_candidates` | `6` | conservative gating / no-candidate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 3 | `collect_more_input_multiple_missing_items` | `5` | missing-info gate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 4 | `blocked_minimum_input` | `5` | conservative gating | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |
| 5 | `collect_more_input_high_priority_missing_info` | `3` | missing-info gate | [recommendation_service.py](/c:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py) |

## Current loop impact

- loop task: `collect_more_input_high_priority_missing_info reduction`
- current-loop decision:
  - no additional code change was made
  - source-of-truth recheck kept the remaining `3` cases on
    `collect_more_input`
- conservative-floor cases:
  - `eval-003`: survey-missing `general_wellness` with no symptom or modality
    anchor
  - `eval-081`: wearable-only `heart_health + blood_glucose` with no symptom
    detail and dual high-priority context gaps
  - `eval-106`: wearable-only `blood_glucose + heart_health` with no symptom
    detail and dual high-priority context gaps

## False-positive / false-negative notes

- current major unresolved gaps remain conservative gating, not
  over-recommendation
- `collect_more_input_high_priority_missing_info` was reduced from `5` to `3`
  without weakening pregnancy, medication, renal, or multimodal safety gates
- `master_context.md` still treats survey/symptoms as core intake and
  wearable/CGM/genetic as optional data, so no further safe fallback was
  introduced for the remaining `3`
- bottleneck modality remains `cgm`, but runtime priority is still dictated by
  the remaining forced-priority missing-info bucket

## Next recommended code target

1. treat `collect_more_input_high_priority_missing_info = 3` as a conservative
   floor unless new source-of-truth evidence appears
2. move to `needs_review_due_to_safety`
3. revisit this bucket only if source-of-truth explicitly supports survey-missing
   general-wellness or wearable-only heart-plus-glucose start conditions
