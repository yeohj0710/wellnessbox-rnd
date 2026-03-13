# NEXT_STEPS

## Current priority

The bounded combined-replay override diagnostic loop is now complete.

What the latest loop proved:

- disabling effect-conditioned override in combined replay removes all override applications:
  - `policy_effect_override_applied_count: 325 -> 0`
- that restores a small amount of low-risk richness:
  - combined low-risk final actions: `continue_plan: 65 -> 63`, `monitor_only: 0 -> 2`
- disagreement counts also improve:
  - low-risk disagreement count: `65 -> 60`
  - `cgm` disagreement count: `3 -> 0`
- but the real target still does not move:
  - combined `cgm` final actions stay `ask_targeted_followup: 10`, `continue_plan: 13`, `trigger_safety_recheck: 10`
  - no combined `cgm monitor_only` or `cgm re_optimize` final actions appear

## Recommended next loop

1. `P2/P4`: keep the fixed v4 cohort, current effect artifact, and restored uniform policy artifact, and make one minimal replay-only change to the combined override gate or effect-conditioned policy priors for the `cgm` threshold-edge region, then rerun combined replay only.
2. `P2/P4`: if that still does not move the `cgm` terminal-action slice, add one more bounded diagnostic that reports the exact records/users where override-off still falls back to `continue_plan`.
3. `P1`: only if replay/training work is blocked, take one very tight deterministic safety increment.

## Guardrails

- Keep work inside `C:/dev/wellnessbox-rnd`
- Do not read or reference:
  - `wellnessbox/`
  - `docs/03_integration/`
  - `docs/00_discovery/`
  - `docs/00_migration/`
  - `docs/legacy_from_wellnessbox/`
- Use source hierarchy from `AGENTS.md`
- Do NOT routinely parse or summarize `docs/context/original_plan.pdf`
- Consult `original_plan.pdf` only for KPI ambiguity, measurement audits, or explicit page-level checks
- Preserve:
  - deterministic baseline
  - frozen eval
  - safety hard-rule precedence
  - deterministic fallback when learned output is missing, suspicious, or out of scope
  - system-owned action space only
  - replay-only boundaries for learned artifacts unless explicitly widened by a later documented decision
