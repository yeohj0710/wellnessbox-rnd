# NEXT_STEPS

## Current priority

The latest OpenAI live rerun is now classified as an optional chat-only `partial_success_fallback_without_failure_family`. That does not change the KPI-first order: the highest-ROI work remains Dataset F training-view enforcement, direct PRO-event outcome wiring, and a contract-driven weakest-slice audit that combines parser, safety, CGM, and workflow signals.

The current order is:

1. enforce or consume the Dataset F training-view contract in the actual effect-training input path
2. connect the PRO improvement summary to the shared baseline/follow-up PRO event path
3. link parser outputs, file schema validation, supported parser failure types, `CGMNormalizedEventV1`, `cgm_slice_bridge_summary_v1`, the follow-up transition event, the next-action workflow contract, and structured safety evidence linkage to weakest-slice frozen eval
4. revisit `cgm` only with final-step score geometry, not threshold-edge widening
5. rerun training/replay only after the Dataset F boundary and KPI-facing path are tighter

## Recommended next five loops

1. `P3/P4`: add the smallest effect-training input guard that consumes `dataset_f_effect_training_view_v1` and explicitly excludes outcome-side fields from the actual training view.
2. `P2/P4`: add the smallest adapter or validator that computes `PROImprovementSummaryV1` directly from the shared baseline/follow-up PRO event contract.
3. `P2/P4`: link sensor/genetic parser outputs, file schema validation, supported parser failure types, `CGMNormalizedEventV1`, `cgm_slice_bridge_summary_v1`, `FollowUpTransitionEventV1`, `NextActionWorkflowEventV1`, and structured safety evidence linkage to a frozen-eval-compatible weakest-slice audit.
4. `P2/P4`: revisit `cgm` with a final-step `continue_plan` versus `re_optimize` score-geometry loop using the current blocker-family evidence, not another threshold-edge widening loop.
5. `P3/P4`: only after loops 1-3, run a deliberately changed effect-training/replay loop that can plausibly produce non-baseline signal.

## Why this order

- Loop 1 is the clearest highest-ROI item because it directly hardens leakage control on the synthetic pre/post training path.
- Loop 2 is the most direct KPI-semantics loop because PRO outcome meaning should be anchored on one normalized event path.
- Loop 3 is the biggest measurement gap remaining in official-style weakest-slice understanding.
- Loop 4 is still bounded and justified, but only after the upstream audit wiring is tighter.
- Another OpenAI rerun before loops 1-3 would still be lower ROI unless chat-path diagnosis becomes explicitly needed.

## Area status snapshot

- normalized data contracts / data hub: `partial`
- safety rules / reference linkage: `done`
- recommendation + optimization: `partial`, with selected-set contract validation now added
- workflow state machine / next-action contracts: `partial`, with runtime next-action workflow projection now added
- PRO scoring: `partial`, with z-score transform and improvement summary present
- sensor/genetic parser: `partial`, with malformed-input fallback and CGM bridge helpers
- `cgm` weakest slice / replay: `partial`, with blocker-family evidence now clearer
- synthetic pre/post dataset: `partial`, improved with provenance, split hygiene, and response-profile metadata
- lightweight training / replay eval: `partial`, path confirmed runnable but replay signal still baseline-identical
- chat retrieval / verifier / OpenAI adapter: `partial`, but below the KPI path
- inference API: `partial`
- full evaluation harness: `partial`, but usable

## Manual backlog priority

- must-do: none
- optional:
  - rerun the latest OpenAI live smoke only if chat-path diagnosis is still needed, and confirm either `provider = openai_responses_api` or `live_failure` is populated
- explicit priority rule:
  - keep the OpenAI rerun below Dataset F contract enforcement, PRO event integration, weakest-slice audit wiring, and `cgm` score-geometry work

## Guardrails

- Keep work inside `C:/dev/wellnessbox-rnd`
- Preserve deterministic baseline, frozen-eval comparability, safety precedence, bounded chat, and replay-only learned artifacts
- Avoid another training/replay rerun unless the input/output contract changed enough to plausibly create non-baseline signal
- Prefer the smallest measurable subtask over broader redesigns
