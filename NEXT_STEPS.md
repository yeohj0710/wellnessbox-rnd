# NEXT_STEPS

## Current priority

The latest prioritization loop re-ranked the next work by ROI against current KPI bottlenecks and implementation gaps.

What the current repo state now suggests:

- `cgm` replay is still partially blocked by final-step score geometry, so more threshold-edge tweaking is lower ROI right now
- `OpenAI` live smoke is still env-blocked, so more local adapter prep is also lower ROI until a real key exists
- the most KPI-aligned unblocked gap is now `PRO scoring`
- the most leverage-heavy infra gap after that is eval report comparison
- the clearest weakest-slice follow-up after that is sensor/genetic parser linkage into frozen-eval evidence

## Recommended next loop

1. `P2/P4`: implement the smallest deterministic `PRO scoring` contract: baseline/follow-up form schema plus improvement metric summary artifact for a tiny sample set.
2. `P2/P4`: add a version-to-version eval comparison helper that reads two eval report JSON files and emits metric deltas plus weakest-slice movement.
3. `P2/P4`: link normalized sensor/genetic parser outputs to a frozen-eval-compatible slice audit focused on the current weakest integration category.

## Deferred until higher ROI or user env is ready

- `P3/P4`: rerun the live OpenAI smoke after `OPENAI_API_KEY` injection and confirm whether `provider = openai_responses_api` or a verifier fallback still occurs.
- `P3/P4`: if live smoke succeeds later, expand `QA dataset D` so the live path is tested beyond the current seed case.
- `P2/P4`: revisit `cgm` only if the loop explicitly targets final-step `continue_plan` vs `re_optimize` score geometry rather than more threshold-edge widening.

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
  - frozen eval comparability
  - safety hard-rule precedence
  - deterministic fallback when learned output is missing, suspicious, or out of scope
  - system-owned action space only
  - bounded evidence-grounded chat path with verifier
  - no recommendation/safety/optimizer runtime coupling to the OpenAI adapter
  - replay-only boundaries for learned artifacts unless explicitly widened by a later documented decision
  - repo-local backlog discipline through `PENDING_USER_ACTIONS.md` and `scripts/manual_backlog.ps1`
