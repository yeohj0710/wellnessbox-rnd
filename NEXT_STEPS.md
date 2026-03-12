# NEXT_STEPS

## Current priority

Priority is now `P2/P4 cohort support + retraining gate`, not another routine input-adoption loop.

What now exists:

- replay parity milestone is complete:
  - combined replay remains slightly closer to effect-only than policy-only on final action
- structured runtime `dose_limits` still exist:
  - `C:/dev/wellnessbox-rnd/data/knowledge/runtime_knowledge_db_v1.json`
  - `dose_limits = 5`
- structured supplement dose is now adopted in:
  - the inference API path
  - the maintained `synthetic_longitudinal_v3` source
  - the maintained `synthetic_longitudinal_v4` source
- learned effect/policy artifacts already exist:
  - they remain guarded and replay-only
  - they are not yet runtime-eligible

## What the latest loops proved

- the maintained `synthetic_longitudinal_v3` source can emit structured current-supplement doses without disturbing frozen eval
- the maintained `synthetic_longitudinal_v4` source can also emit structured current-supplement doses with measurable artifact coverage
- upstream structured-dose adoption is now present in the API and both maintained synthetic sources
- frozen eval stayed unchanged across these adoption loops
- deterministic runtime safety and learned-runtime boundaries stayed unchanged
- additional routine input-adoption loops now have lower marginal value than bounded cohort enrichment

## Recommended next loop

1. `P2/P4`: enrich `cgm` and threshold-edge low-risk trajectories so `continue_plan` vs `monitor_only` vs `re_optimize` boundaries are better represented.
   - Prefer one bounded enrichment loop with measurable deltas in:
     - `cgm` user/record coverage
     - low-risk threshold-edge record counts
     - terminal action richness
     - low-risk `re_optimize` representation
     - replay usefulness on `cgm` and low-risk slices
2. If that enrichment materially changes maintained synthetic cohorts or action richness, retrain the smallest relevant learned artifact(s) and rerun replay in the same loop if feasible, otherwise make that the immediate next loop.
3. `P1`: only if one very tight safety-depth increment clearly has higher leverage than another enrichment loop.
   - Prefer one narrow new `dose_limits` rule family or one equally narrow deterministic safety increment.
   - Do not return to broad input-adoption work by default.
4. `P4`: only after enrichment/retraining, make one final narrow replay-only calibration pass if the effect-only parity margin still needs widening.

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
