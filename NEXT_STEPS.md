# NEXT_STEPS

## Current priority

Priority is now `P4` cohort-sliced replay with learned-vs-deterministic comparison.

What now exists:

- no-human runtime action space:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py`
- citation-backed ingestion pipeline:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/ingestion/reference_ingestion.py`
  - `C:/dev/wellnessbox-rnd/data/knowledge/reference_knowledge_base_v1.json`
- runtime structured knowledge DB wiring:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/knowledge/runtime_db.py`
  - `C:/dev/wellnessbox-rnd/data/knowledge/runtime_knowledge_db_v1.json`
- synthetic longitudinal dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v1.jsonl`
- policy training dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/policy_training_v0.jsonl`
- rich synthetic longitudinal dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v2.jsonl`
- rich policy training dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/policy_training_v1.jsonl`
- learned efficacy artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/efficacy_model_v0.json`
- learned effect artifact v1:
  - `C:/dev/wellnessbox-rnd/artifacts/models/effect_model_v1.json`
- learned policy artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/policy_model_v0.json`
- learned policy artifact v1:
  - `C:/dev/wellnessbox-rnd/artifacts/models/policy_model_v1.json`
- batch closed-loop replay:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.json`

Still missing for the no-human closed-loop target:

- batch replay slices by modality and risk cohort
- learned-vs-deterministic replay comparison using `policy_model_v1` and `effect_model_v1`
- broader structured safety coverage for more interaction, contraindication, and dose-limit rows

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

1. Extend batch replay with guarded `policy_model_v1` plus `effect_model_v1`.
2. Add cohort slices for `cgm`, `genetic`, `low-risk/high-risk`, and `single-goal/multi-goal`, then compare deterministic-only vs learned-on.
3. Expand structured knowledge coverage, especially `dose_limits`, before widening replay scope further.

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
