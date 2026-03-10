# Closed-Loop Simulation Harness v0

## Stage and purpose

- Stage: `P4`
- Task: `closed-loop batch replay + guarded learned-policy comparison`
- Why this work fits the source-of-truth:
  - `master_context` prioritizes a testable state machine over a large agent graph.
  - The plan requires end-to-end traces such as intake -> recommendation -> follow-up
    -> state update -> next action.
  - The learned efficacy model must stay behind deterministic safety and fallback
    behavior.

## What this harness does

- Replays a synthetic user or a batch of synthetic users from the step-0
  requests stored in `data/synthetic/synthetic_longitudinal_v1.jsonl`.
- Calls the deterministic recommendation engine at each cycle.
- Uses the learned efficacy artifact when available to estimate follow-up
  effect.
- Falls back to deterministic synthetic effect proxy if the efficacy artifact
  is missing or unusable.
- Can apply a guarded learned policy artifact inside simulation only.
- Applies an explicit system-owned policy transition layer:
  - baseline intake -> `start_plan` / `ask_targeted_followup` /
    `trigger_safety_recheck`
  - follow-up received + positive learned effect -> `continue_plan`
  - follow-up received + weak effect -> `re_optimize`
  - adverse event path -> `reduce_or_stop`

## Main files

- `src/wellnessbox_rnd/simulation/closed_loop_v0.py`
- `scripts/run_closed_loop_simulation.py`
- `scripts/run_closed_loop_batch_simulation.py`
- `tests/test_closed_loop_simulation.py`

## Example command

```bash
python scripts/run_closed_loop_simulation.py --user-id syn-user-001
python scripts/run_closed_loop_simulation.py --user-id syn-user-009 --enable-learned-reranking
python scripts/run_closed_loop_simulation.py --user-id syn-user-001 --enable-learned-policy
python scripts/run_closed_loop_batch_simulation.py --max-users 48
```

## Current run snapshot

- output JSON:
  - `artifacts/reports/closed_loop_simulation_v0_syn_user_002_system_actions.json`
- output Markdown:
  - `artifacts/reports/closed_loop_simulation_v0_syn_user_002_system_actions.md`
- scenario result:
  - cycle `0`: `baseline_intake -> start_plan -> recommendation_ready`
    with learned effect `0.263242`
  - cycle `1`: engine `trigger_safety_recheck`,
    policy `reduce_or_stop -> stop_or_escalate`
    with learned effect `-0.019236`
- final state:
  - `stop_or_escalate`
- final policy action:
  - `reduce_or_stop`
- positive regression path:
  - `syn-user-001` continues with `continue_plan`

## Batch replay snapshot

- output JSON:
  - `artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.json`
- output Markdown:
  - `artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.md`
- compared modes:
  - `deterministic_only`
  - `learned_policy_guarded`
- replay scale:
  - `48 users`
  - `84 total trace steps per mode`
- aggregate final states:
  - `baseline_questionnaire_due = 24`
  - `intake_active = 12`
  - `stop_or_escalate = 12`
- aggregate final policy actions:
  - `ask_targeted_followup = 24`
  - `continue_plan = 12`
  - `reduce_or_stop = 12`
- comparison result:
  - no user-level final-state or final-policy divergence yet
  - current learned policy reproduces deterministic replay on this dataset version

## Learned policy and reranking integration

- The single-user simulation runner can exercise the gated optimizer reranker
  with `--enable-learned-reranking`.
- The simulation runners can exercise the guarded learned policy path with
  `--enable-learned-policy` or via the batch comparison runner.
- Current narrow gate:
  - learned efficacy reranking:
    - safety status `ok`
    - no pregnancy / condition / medication risk
    - goal set exactly `general_wellness`
    - near-tied deterministic candidates only
  - learned policy:
    - simulation-only
    - deterministic action ceiling via guard
    - no runtime action-space changes
- Example integrated runs:
  - reranking artifact:
    - `artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.md`
  - batch comparison artifact:
    - `artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.md`

## Current scope limits

- This is a simulation harness, not runtime integration into recommendation ranking or runtime next-action selection.
- State transitions are explicit and deterministic.
- Safety still comes entirely from the deterministic baseline and hard rules.
- The learned efficacy model only informs simulated follow-up effect estimation.
- The learned policy model only informs simulation replay and is still guarded by deterministic policy.
- Human handoff semantics were removed from runtime and simulation action vocabularies.
