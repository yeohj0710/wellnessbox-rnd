# NEXT_STEPS

## Current priority

Primary frozen eval is validated at `246` cases, so P1 work continues.

Current strongest unresolved buckets:

1. `collect_more_input_high_priority_missing_info = 10`
2. `needs_review_due_to_safety = 7`
3. `needs_review_no_candidates = 6`
4. `blocked_minimum_input = 5`

Rate-based weakest modality:

- `cgm = 34 / 48 = 70.83333333333333%`

## Recommended next loop

1. Reduce `collect_more_input_high_priority_missing_info`.
2. Add at least `2` harder regression cases where modality context exists but
   high-priority intake context is still insufficient.
3. After that pass, choose exactly one of:
   - another missing-info / follow-up reduction
   - `cgm` deterministic follow-through improvement

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
