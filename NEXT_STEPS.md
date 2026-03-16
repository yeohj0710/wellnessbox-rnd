# NEXT_STEPS

## Current priority

The repo is directionally aligned with the intended architecture, but the strongest remaining KPI gaps are still in score semantics and weakest-slice measurement, not in chat or API polish.

Current state in one line:

- deterministic safety is strong
- deterministic recommendation and eval harness exist
- synthetic Dataset F and parser contracts exist
- but PRO scoring semantics and weakest-slice linkage are still the highest-ROI missing pieces

## Recommended next five loops

1. `P2/P4`: implement the smallest deterministic `PRO z-score transform` on top of the shared baseline/follow-up PRO event contract.
2. `P2/P4`: link sensor/genetic parser outputs, file schema validation, and `CGMNormalizedEventV1` to a frozen-eval-compatible weakest-slice audit.
3. `P2/P4`: revisit `cgm` only with a final-step `continue_plan` versus `re_optimize` score-geometry loop, not another threshold-edge widening loop.
4. `P3/P4`: run a bounded Dataset F effect-improvement audit or deliberately changed candidate training loop only if it introduces a non-baseline learned signal.
5. `P2/P4`: tighten the distributed normalized contracts into a clearer reusable structured hub layer only if loops 1-3 expose repeated schema friction.

## Area status snapshot

- normalized data contracts / data hub: `partial`
- safety rules / reference linkage: `done`
- recommendation + optimization: `partial`
- PRO scoring: `partial`
- sensor/genetic parser: `partial`
- `cgm` weakest slice / replay: `partial`
- synthetic pre/post dataset: `partial`
- lightweight training / replay eval: `partial`
- chat retrieval / verifier / OpenAI adapter: `partial`
- inference API: `partial`
- full evaluation harness: `partial`

## Manual backlog priority

- must-do: none
- optional:
  - rerun enriched OpenAI live smoke from the shell/session that actually has `OPENAI_API_KEY`
- keep the OpenAI rerun below the core KPI path

## Guardrails

- Keep work inside `C:/dev/wellnessbox-rnd`
- Preserve deterministic baseline, frozen-eval comparability, safety precedence, bounded chat, and replay-only learned artifacts
- Do not use `original_plan.pdf` beyond KPI ambiguity or page-level audit needs
- Prefer the smallest measurable subtask over broader rewrites
