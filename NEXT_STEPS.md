# NEXT_STEPS

## Last completed loop

- Selected task: `genetic deterministic handling improvement`
- Reason: primary validated frozen eval size was `116 >= 100`, a formal gap report existed, and the chosen runtime bucket was `genetic`
- Result:
  - primary dataset stayed `data/frozen_eval/frozen_eval_v1.jsonl`
  - case count increased `116 -> 118`
  - added `2` cases total
  - added `2` hard / negative / ambiguous cases
  - added `2` regression-style cases
  - added direct genetic ranking coverage for `general_wellness` and `heart_health`
  - aligned older genetic-context cases to the new deterministic ranking behavior

## Current primary dataset

- `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
- `case_count = 118`

## Current official metrics

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.94784689765133`
- `next_action_accuracy_pct = 100.0`
- `explanation_quality_accuracy_pct = 100.0`
- `safety_reference_accuracy_pct = 100.0`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 32.48407643312102`

## Current bottlenecks

1. `genetic` is still the worst integration modality at `7.142857142857143%`.
2. `cgm` remains weak at `16.666666666666668%`.
3. `needs_review_due_to_safety` and `needs_review_no_candidates` still dominate conservative gating.
4. Genetic ranking now moves in a few deterministic contexts, but modality success remains mostly unchanged at the dataset-proxy layer.
5. The next code-facing bottleneck after this loop is `cgm`.

## Forced next option at current stage

1. P1 baseline improvement against the largest bucket from the gap report

## Recommended next tasks

1. Improve deterministic `cgm` handling in `src/wellnessbox_rnd/domain/intake.py` and `src/wellnessbox_rnd/efficacy/service.py`.
2. Add regression cases where CGM availability should change ranking or follow-up readiness.
3. After CGM work, revisit `genetic` with richer normalization beyond the current goal-based boolean flags.

## Out of scope

- `wellnessbox/`
- `docs/03_integration/`
- `docs/00_discovery/`
- `docs/00_migration/`
- `docs/legacy_from_wellnessbox/`
- LLM / agent layer / fine-tuning / external integrations
