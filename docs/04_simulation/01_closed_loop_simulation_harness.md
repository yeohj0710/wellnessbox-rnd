# Closed-Loop Simulation Harness v0

## Stage and purpose

- Stage: `P2`
- Task: `closed-loop simulation harness`
- Why this work fits the source-of-truth:
  - `master_context` prioritizes a testable state machine over a large agent graph.
  - The plan requires end-to-end traces such as intake -> recommendation -> follow-up
    -> state update -> next action.
  - The learned efficacy model must stay behind deterministic safety and fallback
    behavior.

## What this harness does

- Replays a synthetic user from the step-0 request stored in
  `data/synthetic/synthetic_longitudinal_v1.jsonl`.
- Calls the deterministic recommendation engine at each cycle.
- Uses the learned efficacy artifact when available to estimate follow-up effect.
- Falls back to deterministic synthetic effect proxy if the model artifact is
  missing or unusable.
- Applies an explicit policy transition layer:
  - baseline intake -> `present_recommendation` / `request_baseline_questionnaire` /
    `request_safety_review`
  - follow-up received + positive learned effect -> `continue_plan`
  - follow-up received + weak effect -> `re_optimize_combination`
  - adverse event or review path -> `stop_and_escalate` or `request_safety_review`

## Main files

- `src/wellnessbox_rnd/simulation/closed_loop_v0.py`
- `scripts/run_closed_loop_simulation.py`
- `tests/test_closed_loop_simulation.py`

## Example command

```bash
python scripts/run_closed_loop_simulation.py --user-id syn-user-001
python scripts/run_closed_loop_simulation.py --user-id syn-user-009 --enable-learned-reranking
```

## Current run snapshot

- output JSON:
  - `artifacts/reports/closed_loop_simulation_v0_syn_user_001.json`
- output Markdown:
  - `artifacts/reports/closed_loop_simulation_v0_syn_user_001.md`
- scenario result:
  - cycle `0`: `baseline_intake -> present_recommendation -> recommendation_ready`
    with learned effect `0.276794`
  - cycle `1`: `followup_received -> continue_plan -> intake_active`
    with learned effect `0.344644`
  - cycle `2`: `followup_received -> continue_plan -> intake_active`
    with learned effect `0.46764`
- final state:
  - `intake_active`
- final policy action:
  - `continue_plan`
- negative regression path:
  - `syn-user-002` stops at follow-up with `stop_and_escalate`

## Learned reranking integration

- The simulation runner can now exercise the gated optimizer reranker with
  `--enable-learned-reranking`.
- Current narrow gate:
  - safety status `ok`
  - no pregnancy / condition / medication risk
  - goal set exactly `general_wellness`
  - near-tied deterministic candidates only
- Example integrated run:
  - artifact:
    - `artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.md`
  - baseline top recommendation:
    - `vitamin_d3`
  - reranked top recommendation:
    - `vitamin_c`

## Current scope limits

- This is a simulation harness, not runtime integration into recommendation ranking.
- State transitions are explicit and deterministic.
- Safety still comes entirely from the deterministic baseline and hard rules.
- The learned efficacy model only informs simulated follow-up effect estimation.
