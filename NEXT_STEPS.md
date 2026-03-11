# NEXT_STEPS

## Current priority

Priority is now `P4 calibration follow-through + P1 support`.

What now exists:

- calibrated effect-focused synthetic cohort:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
- derived policy rows from the same v4 state space:
  - `C:/dev/wellnessbox-rnd/data/synthetic/policy_training_v1_from_v4.jsonl`
- retrained learned effect artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/effect_model_v3.json`
- guarded 4-mode replay compare on v4:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_compare.json`

What the latest loop proved:

- `learned_effect_guarded` now produces final divergence again after calibration:
  - `71` raw ranking disagreements
  - `22` ranking-diff users
  - `25` final-policy-diff users
  - `24` final-state-diff users
- low-risk and single-goal slices still show non-zero learned-effect divergence:
  - `low_risk deterministic_vs_learned_disagreement_count = 171`
- frozen eval stayed unchanged
- deterministic safety guard remained intact

## Recommended next loop

1. `P4`: analyze why combined mode is still policy-dominated, then route learned effect into guarded policy features or weighting instead of keeping the two paths largely independent.
2. `P1`: expand structured safety coverage, especially `dose_limits`, before any wider learned runtime use.
3. `P2/P4`: enrich threshold-edge low-risk trajectories again so final `monitor_only` cases are not compressed to a single terminal user.

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
  - safety hard-rule precedence
  - deterministic fallback when learned output is missing or suspicious
  - system-owned action space only
