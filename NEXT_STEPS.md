# NEXT_STEPS

## Current priority

Stage is now `P2`.

Available trainable artifact:

- model artifact: `C:/dev/wellnessbox-rnd/artifacts/models/efficacy_model_v0.json`
- eval report:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/efficacy_model_v0_eval.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/efficacy_model_v0_eval.md`
- split artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/efficacy_model_v0_splits.json`
- simulation harness:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/simulation/closed_loop_v0.py`
- gated optimizer integration:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/service.py`
- sample trace artifacts:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_simulation_v0_syn_user_001.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_simulation_v0_syn_user_001.md`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.md`

Conservative floor already accepted:

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

1. Train a `P1` next-action / policy model v0 on synthetic longitudinal traces and
   explicit simulation actions.
2. Extend the current learned reranking from narrow `general_wellness` gating to a
   broader but still low-risk subset with explicit regression coverage.
3. Extend the simulation harness with multi-scenario batch replay and aggregate
   transition metrics.

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
  - explicit state machine semantics for closed-loop steps
