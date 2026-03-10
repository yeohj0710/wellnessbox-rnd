# NEXT_STEPS

## Current priority

Priority is now split between `P1` deterministic knowledge wiring and `P4` simulation richness.

What now exists:

- no-human runtime action space:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py`
- citation-backed ingestion pipeline:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/ingestion/reference_ingestion.py`
  - `C:/dev/wellnessbox-rnd/data/knowledge/reference_knowledge_base_v1.json`
- synthetic longitudinal dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v1.jsonl`
- policy training dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/policy_training_v0.jsonl`
- learned efficacy artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/efficacy_model_v0.json`
- learned policy artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/policy_model_v0.json`
- batch closed-loop replay:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.json`

Still missing for the no-human closed-loop target:

- runtime wiring from ingested knowledge artifact into deterministic rule loading
- broader synthetic policy labels beyond the current 3-action distribution
- simulation slices by modality and risk cohort
- a batch replay path that shows non-trivial learned-policy differences after richer synthetic labels exist

Conservative floors already accepted:

- `collect_more_input_high_priority_missing_info = 3`
- `needs_review_due_to_safety = 3`
- remaining explicit-avoid `needs_review_no_candidates = 4`

Active unresolved buckets:

1. `blocked_minimum_input = 5`
2. `collect_more_input_multiple_missing_items = 4`
3. `needs_review_no_candidates = 4`
4. `needs_review_due_to_safety = 3`

Rate-based weakest modality:

- `cgm = 36 / 50 = 72.0%`

## Recommended next loop

1. Wire `reference_knowledge_base_v1.json` into deterministic safety/rule loading behind strict validation only.
2. Broaden synthetic policy trajectories so `continue_plan`, `re_optimize`, `reduce_or_stop`, and `monitor_only` become learnable next-action labels, not just simulation outputs.
3. Extend batch replay with modality/risk cohort slices and compare learned-policy-on vs deterministic-only once richer labels exist.

## Guardrails

- Keep work inside `C:/dev/wellnessbox-rnd`
- Do not read or reference:
  - `wellnessbox/`
  - `docs/03_integration/`
  - `docs/00_discovery/`
  - `docs/00_migration/`
  - `docs/legacy_from_wellnessbox/`
- Use:
  - `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
  - `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`
- Preserve:
  - deterministic baseline
  - frozen eval
  - safety rule precedence
  - deterministic fallback when learned output is missing or suspicious
  - system-owned action space only at runtime
  - structured citation validation before knowledge artifacts are used
