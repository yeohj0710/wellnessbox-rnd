# Baseline Gap Report

Updated against:

- dataset: `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
- report: `C:/dev/wellnessbox-rnd/artifacts/reports/current_loop_final_eval/eval_report.json`

## Latest loop note

- `2026-03-11` calibrated effect-divergence loop kept all frozen official metrics unchanged.
- the meaningful movement in this loop happened in simulation, not frozen eval:
  - `synthetic_longitudinal_v4`
  - `effect_model_v3`
  - `closed_loop_batch_simulation_v3_compare`
- official bottleneck is still `cgm = 72.0%`.

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

- loop task: `P2/P3 calibrated effect richness + retrain`
- current-loop decision:
  - added `synthetic_longitudinal_v4`
  - retrained `effect_model_v3` with policy-proxy calibration
  - reran the same 4-mode replay under guarded near-tie survivor reranking
  - preserved frozen eval expectations and deterministic baseline metrics unchanged

## False-positive / false-negative notes

- current major unresolved gaps remain conservative gating, not over-recommendation
- `trigger_safety_recheck = 7` remains the autonomous replacement for the old review action bucket
- bottleneck modality remains `cgm`
- learned replay is improving, but that signal is still synthetic and simulation-only

## Next recommended code target

1. couple calibrated learned effect more directly into combined replay so `learned_effect_and_policy_guarded` is not almost identical to guarded policy alone
2. expand structured safety coverage, especially `dose_limits`, before widening learned runtime scope
3. enrich low-risk threshold-edge synthetic trajectories again so calibrated learned effect yields more than `1` terminal `monitor_only` case
