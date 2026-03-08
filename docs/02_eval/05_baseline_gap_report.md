# Baseline Gap Report

## Scope

- primary dataset: `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
- dataset size: `118`
- eval source:
  - `python scripts/manage_eval_dataset.py summary`
  - `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl`

## Assumptions

- Official recommendation, next-action, explanation, and safety metrics are all
  `100.0` because the current frozen eval is aligned to the deterministic
  baseline's present behavior.
- This document therefore treats `failure bucket` as current baseline weakness
  observed through category coverage, `next_action_rationale.reason_code`,
  parser-limit case behavior, and modality attempted/success diagnostics.
- `sensor_genetic_integration_rate_pct` is still a dataset-observation proxy,
  not a live parser runtime KPI.

## Status Update After Genetic Fix

- parser-limit buckets remain resolved:
  - `parser_miss_current_supplement_long_title = 0`
  - `parser_miss_avoid_long_title = 0`
- new genetic regression coverage added:
  - `eval-117`
  - `eval-118`
- genetic-aware deterministic ranking now changes recommendation order in:
  - `general_wellness`
  - `heart_health`
  - selected mixed-goal cases with `general_wellness` or `immunity_support`
- remaining top buckets are still modality-driven:
  - `genetic_attempted_but_not_integrated`
  - `wearable_attempted_but_not_integrated`
  - `cgm_attempted_but_not_integrated`

## Official metric status

| metric | score | target | passed |
| --- | --- | --- | --- |
| `recommendation_coverage_pct` | `100.0` | `80.0` | `True` |
| `efficacy_improvement_pp` | `9.94784689765133` | `> 0.0` | `True` |
| `next_action_accuracy_pct` | `100.0` | `80.0` | `True` |
| `explanation_quality_accuracy_pct` | `100.0` | `91.0` | `True` |
| `safety_reference_accuracy_pct` | `100.0` | `95.0` | `True` |
| `adverse_event_count_yearly` | `0.0` | `<= 5.0` | `True` |
| `sensor_genetic_integration_rate_pct` | `32.48407643312102` | `90.0` | `False` |

## Category distribution

Summary output snapshot:

| category | count |
| --- | --- |
| `parser_limit` | `16` |
| `genetic_supported` | `2` |
| `review_no_candidates` | `15` |
| `missing_context` | `14` |
| `safety_blocked` | `14` |
| `safety_warning` | `9` |
| `complex_multi_goal` | `6` |
| `edge_case` | `5` |
| `normal_recommendation` | `5` |
| `chronic_condition` | `4` |
| `explanation_quality` | `4` |
| `collect_more_input` | `3` |
| `free_text_alias` | `3` |
| `catalog_alias` | `2` |
| `duplicate_overlap` | `2` |
| `integration_mixed` | `2` |
| `pregnancy_review` | `2` |
| remaining singleton categories | `7` total |

Observation:

- The heaviest categories are no longer easy recommendation paths.
- `parser_limit`, `review_no_candidates`, `missing_context`, and
  `safety_blocked` now dominate the dataset, which is consistent with the
  current known bottlenecks.
- `genetic_supported` is still small, which means runtime improvement landed
  before broad modality-coverage expansion.

## Next-action distribution

| expected next action | count |
| --- | --- |
| `start_plan` | `48` |
| `collect_more_input` | `36` |
| `needs_human_review` | `34` |

Observed next-action rationale counts from current baseline:

| reason code | count |
| --- | --- |
| `start_plan_ready` | `48` |
| `needs_review_due_to_safety` | `19` |
| `blocked_minimum_input` | `16` |
| `collect_more_input_high_priority_missing_info` | `15` |
| `needs_review_no_candidates` | `15` |
| `collect_more_input_multiple_missing_items` | `5` |

Observation:

- Conservative gating is not a corner case anymore.
- `needs_review_due_to_safety`, `blocked_minimum_input`, and
  `needs_review_no_candidates` together account for `50` cases.

## Modality attempted / success / bottleneck

From current summary + eval:

| modality | attempted cases | attempted total | success total | success rate |
| --- | --- | --- | --- | --- |
| `wearable` | `63` | `63` | `42` | `66.66666666666667%` |
| `cgm` | `24` | `24` | `4` | `16.666666666666668%` |
| `genetic` | `70` | `70` | `5` | `7.142857142857143%` |

Bottleneck:

- `genetic` is the worst modality.
- `cgm` is the second worst modality.
- Both are materially below the official target and below `wearable`.

## Failure bucket top 10

| rank | bucket | type | count | examples | next code file(s) |
| --- | --- | --- | --- | --- | --- |
| 1 | `genetic_attempted_but_not_integrated` | sensor/genetic parser gap | `65` | `eval-021`, `eval-110`, `eval-118` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/service.py` |
| 2 | `wearable_attempted_but_not_integrated` | sensor parser gap | `21` | `eval-024`, `eval-095`, `eval-110` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/service.py` |
| 3 | `cgm_attempted_but_not_integrated` | sensor parser gap | `20` | `eval-022`, `eval-090`, `eval-110` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/service.py` |
| 4 | `needs_review_due_to_safety` | conservative gating | `19` | `eval-006`, `eval-073`, `eval-110` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/service.py` |
| 5 | `blocked_minimum_input` | conservative gating | `16` | `eval-003`, `eval-094`, `eval-097` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py` |
| 6 | `collect_more_input_high_priority_missing_info` | missing-info gate | `15` | `eval-004`, `eval-090`, `eval-113` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py` |
| 7 | `needs_review_no_candidates` | conservative gating / no-candidate path | `15` | `eval-053`, `eval-099`, `eval-104` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/service.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/safety/service.py` |
| 8 | `collect_more_input_multiple_missing_items` | missing-info gate | `5` | `eval-014`, `eval-059`, `eval-107` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py` |
| 9 | `genetic_context_ranking_shift` | deterministic ranking change under genetic context | `5` | `eval-034`, `eval-109`, `eval-117` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/service.py` |
| 10 | `parser_miss_resolved_but_watchlisted` | resolved regression watchlist | `0` | `eval-113`, `eval-114`, `eval-116` | `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/catalog.py`, `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/domain/intake.py` |

## Bucket distinctions checked

Observed non-zero buckets:

- `conservative_gating`: `needs_review_due_to_safety`, `blocked_minimum_input`,
  `needs_review_no_candidates`, `collect_more_input_*`
- `genetic_ranking_shift`: ranking now changes under explicit genetic context
- `sensor/genetic bottleneck`: genetic and CGM attempted-success gaps dominate

Checked zero-count buckets on the current primary dataset:

| bucket | count | note |
| --- | --- | --- |
| `false_positive_status` | `0` | no status mismatch against current frozen eval |
| `false_negative_status` | `0` | no status miss against current frozen eval |
| `alias_miss` | `0` | current `catalog_alias` and `free_text_alias` cases still hit |
| `missing_info_miss` | `0` | current next-action expectations still match |
| `parser_miss_current_supplement_long_title` | `0` | resolved in loop 6 and still holding |
| `parser_miss_avoid_long_title` | `0` | resolved in loop 6 and still holding |

## Regression cases added in this loop

- `eval-117`: general wellness with genetic context should prioritize
  `vitamin_d3`.
- `eval-118`: heart-health context with genetic availability and atorvastatin
  should prioritize `omega3`.

These two cases intentionally increase regression coverage for deterministic
genetic handling without gaming the official coverage, explanation, or safety
metrics.

## Recommended next code change

Single highest-value next fix:

1. Improve deterministic `cgm` normalization so CGM availability affects
   ranking and follow-up readiness more directly than the current boolean proxy.

Why this comes first:

- `genetic` remains the worst modality, but this loop already landed the first
  direct ranking responses for that bucket.
- The parser-limit runtime bucket is still `0`.
- The next untouched deterministic bottleneck is `cgm`.
