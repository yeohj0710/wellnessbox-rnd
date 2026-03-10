# Learned Efficacy Gated Integration v0

## Stage and purpose

- Stage: `P2`
- Task: `learned efficacy gated integration into optimizer`
- Why this work fits the source-of-truth:
  - quantified effect estimation already exists as a learned artifact
  - the next required step is coupling that signal with optimization
  - safety and deterministic filtering must remain ahead of any learned score

## Integration shape

- Integration point:
  - `src/wellnessbox_rnd/optimizer/service.py`
- Default behavior:
  - unchanged deterministic ranking
- Opt-in behavior:
  - `enable_learned_reranking=True`
  - `learned_efficacy_artifact_path=...`

## Guardrails

- Learned reranking runs only after deterministic blocked/excluded ingredients are
  removed.
- The gate is intentionally narrow in v0:
  - safety status `ok`
  - no pregnancy
  - no condition risk
  - no medication risk
  - goal set is exactly `general_wellness`
  - only candidates within a `1.0` point deterministic margin get a learned bonus
- Missing artifact falls back to deterministic ranking.
- High-risk cases remain deterministic even when reranking is enabled.

## Runtime behavior

- Candidate score breakdown now includes `learned_effect_bonus`.
- When applied, the engine mode becomes:
  - `deterministic_baseline_v1_learned_efficacy_rerank_v0`
- Selected candidates carry:
  - rule ref `OPT-LEARNED-001`

## Current validation snapshot

- synthetic user:
  - `syn-user-009`
- deterministic baseline top recommendation:
  - `vitamin_d3`
- gated learned rerank top recommendation:
  - `vitamin_c`
- selected candidate learned bonus:
  - `3.619935`
- frozen eval:
  - unchanged
