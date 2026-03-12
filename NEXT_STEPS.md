# NEXT_STEPS

## Current priority

Priority is now `P4 follow-through on effect-conditioned combined replay + P1 support`.

What now exists:

- calibrated effect-focused synthetic cohort:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
- replay effect artifact with calibrated policy proxy:
  - `C:/dev/wellnessbox-rnd/artifacts/models/effect_model_v3.json`
- guarded 4-mode replay compare on v4:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v3_compare.json`
- combined replay policy now reads the guarded learned effect proxy through policy feature override:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/simulation/closed_loop_v0.py`

## What the latest loop proved

- combined mode had been policy-dominated because raw learned policy inference ignored the learned effect proxy and kept using the original `expected_effect_proxy`
- the new replay-only wiring measurably reduced that collapse:
  - combined vs policy-only final action match: `96 / 96 -> 83 / 96`
  - combined vs policy-only trace action match: `299 / 299 -> 262 / 299`
  - effect-ranking-diff subset combined vs policy-only trace action match: `95 / 95 -> 87 / 95`
- the new path is active on a meaningful portion of replay:
  - `policy_effect_override_applied_count = 257`
- frozen eval stayed unchanged
- deterministic safety guard remained intact

## Recommended next loop

1. `P4`: tune effect-conditioned policy weighting only inside the already-guarded low-risk replay subset so combined mode moves further away from policy-only without turning too many low-risk users into `trigger_safety_recheck`.
2. `P1`: expand structured safety coverage, especially `dose_limits`, before any wider learned usage is considered.
3. `P2/P4`: enrich CGM and threshold-edge low-risk trajectories so `monitor_only` vs `continue_plan` vs `re_optimize` boundaries are better represented.

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
  - deterministic fallback when learned output is missing, suspicious, or out of scope
  - system-owned action space only
