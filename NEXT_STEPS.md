# NEXT_STEPS

## Current priority

Primary frozen eval is validated at `250` cases, so P1 work continues.

Forced-priority unresolved buckets:

1. `collect_more_input_high_priority_missing_info = 3`
2. `needs_review_due_to_safety = 7`
3. `needs_review_no_candidates = 6`
4. `blocked_minimum_input = 5`

Rate-based weakest modality:

- `cgm = 34 / 48 = 70.83333333333333%`

## Recommended next loop

1. Treat the remaining `collect_more_input_high_priority_missing_info = 3` as a
   conservative floor unless new source-of-truth evidence appears.
2. Move to `needs_review_due_to_safety`.
3. Revisit this bucket only if `docs/context/master_context.md` or
   `docs/context/original_plan.pdf` provide explicit support for survey-missing
   general-wellness or wearable-only heart-plus-glucose plan start.

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
