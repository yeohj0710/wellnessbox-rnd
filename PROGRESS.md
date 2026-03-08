# PROGRESS

## Current status

`wellnessbox-rnd` remains a pure R&D repo.

Source of truth:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

This loop selected `genetic deterministic handling improvement` because the
primary frozen eval case count was `116 >= 100`, a formal gap report existed,
and the chosen runtime bucket from that report was `genetic` deterministic
handling.

## What changed in this loop

- Added deterministic genetic signal flags in
  `src/wellnessbox_rnd/domain/intake.py` so baseline ranking can distinguish
  micronutrient, cardiometabolic, and recovery contexts.
- Added deterministic genetic evidence bonuses in
  `src/wellnessbox_rnd/efficacy/service.py` for:
  - `vitamin_d3` in micronutrient context
  - `omega3` in cardiometabolic context
  - `magnesium_glycinate` in recovery context
- Expanded the primary frozen eval from `116 -> 118` validated cases (`+2`) to
  add genetic ranking regressions tied directly to the chosen bucket.
- Added two genetic regression cases:
  - `eval-117`: general wellness with genetic context should prioritize `vitamin_d3`
  - `eval-118`: heart health with genetic context should prioritize `omega3`
- Aligned pre-existing genetic cases `eval-034`, `eval-049`, and `eval-109`
  with the new deterministic behavior so the frozen eval reflects the intended
  ranking change rather than the old non-genetic baseline.
- Added direct regression tests for:
  - general wellness genetic uplift
  - heart-health genetic uplift
  - multi-goal heart/immunity genetic backfill behavior

## Validation results

- `python -m ruff check .`: passed
- `python -m pytest`: `34 passed`
- `python scripts/manage_eval_dataset.py validate`: passed
- `python scripts/manage_eval_dataset.py summary`: passed
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/final_loop7`: passed

## Official metric snapshot

Before (`frozen_eval_v1.jsonl`, 116 cases):

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.94784689765133`
- `next_action_accuracy_pct = 100.0`
- `explanation_quality_accuracy_pct = 100.0`
- `safety_reference_accuracy_pct = 100.0`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 32.903225806451616`

After (`frozen_eval_v1.jsonl`, 118 cases):

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.94784689765133`
- `next_action_accuracy_pct = 100.0`
- `explanation_quality_accuracy_pct = 100.0`
- `safety_reference_accuracy_pct = 100.0`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 32.48407643312102`

## New case mix

- `2` hard / negative / ambiguous cases
- `2` regression-style cases

## Current bottlenecks

1. `genetic = 7.142857142857143%` remains the clearest bottleneck.
2. `cgm = 16.666666666666668%` remains weak.
3. Conservative review / no-candidate gating is still dense after the genetic ranking fix.

## Assumptions

- `sensor_genetic_integration_rate_pct` is still a dataset-observation proxy, not
  a runtime parser KPI.
- The frozen eval remains synthetic and is still not a production acceptance gate.

## Recommended next loop

1. Improve deterministic `cgm` handling in `src/wellnessbox_rnd/domain/intake.py`
   and `src/wellnessbox_rnd/efficacy/service.py`.
2. Add regression cases where CGM availability should change ranking or
   follow-up readiness in a measurable way.
3. After CGM work, revisit `genetic_attempted_but_not_integrated` with richer
   normalization than the current boolean proxy.
