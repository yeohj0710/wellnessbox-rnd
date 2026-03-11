# Closed-Loop Simulation Harness v1

## Stage and purpose

- Stage: `P4`
- Current focus: `guarded replay using synthetic_longitudinal_v4 + effect_model_v3 + policy_model_v1`
- Goal:
  - compare deterministic and guarded learned modes without weakening deterministic safety

## Current modes

- `deterministic_only`
- `learned_effect_guarded`
- `learned_policy_guarded`
- `learned_effect_and_policy_guarded`

## Trace fields

Each step records:

- `deterministic_action`
- `raw_learned_policy_action`
- `selected_policy_action`
- `policy_guard_applied`
- `deterministic_top_candidate`
- `raw_learned_top_candidate`
- `selected_candidate`
- `effect_guard_applied`
- `action_source`
- `ranking_source`

## Guard boundary

### Deterministic floor

- frozen eval remains deterministic
- runtime safety remains deterministic
- final action space stays system-owned only

### Learned effect boundary

- `effect_model_v3` is replay-only
- reranking happens only after deterministic candidate filtering
- reranking scores only the deterministic near-tie survivor subset
- reranking is allowed only when:
  - safety status is `ok`
  - risk tier is `low`
  - no pregnancy
  - no medications
  - no conditions
  - no explicit avoid ingredients
  - at least two deterministic candidates remain inside the near-tie window
- replay uses a calibrated policy-facing proxy:
  - `policy_proxy = intercept + slope * predicted_aggregate_delta`
  - current calibration:
    - `slope = 3.11735613`
    - `intercept = 0.09283873`

### Learned policy boundary

- `policy_model_v1` is replay-only
- learned policy cannot override deterministic behavior when:
  - baseline intake step is active
  - safety status is not `ok`
  - pregnancy is present
  - medications are present
  - conditions are present
  - explicit avoid ingredients are present
- more-permissive learned policy outputs are clamped by deterministic guard

## Current commands

```bash
python scripts/run_closed_loop_batch_simulation.py
python scripts/run_closed_loop_batch_simulation.py --dataset data/synthetic/synthetic_longitudinal_v4.jsonl --model-artifact artifacts/models/effect_model_v3.json --policy-model-artifact artifacts/models/policy_model_v1.json
```

## Current artifacts

- JSON full report:
  - `artifacts/reports/closed_loop_batch_simulation_v3_compare.json`
- Markdown summary:
  - `artifacts/reports/closed_loop_batch_simulation_v3_compare.md`
- trace samples:
  - `artifacts/reports/closed_loop_batch_simulation_v3_trace_samples.json`

## Current run snapshot

Replay scale:

- `96 users`
- deterministic mode total trace steps: `356`

Mode comparison:

| mode | final state diff users | final policy diff users | ranking diff users | trace diff users |
| --- | ---: | ---: | ---: | ---: |
| `learned_effect_guarded` | `24` | `25` | `22` | `65` |
| `learned_policy_guarded` | `19` | `34` | `0` | `34` |
| `learned_effect_and_policy_guarded` | `19` | `34` | `22` | `65` |

Key aggregate counters:

- `learned_effect_guarded`
  - `raw_ranking_disagreement_count = 71`
  - `effect_guard_applied_count = 0`
- `learned_policy_guarded`
  - `raw_policy_disagreement_count = 171`
  - `policy_guard_applied_count = 102`
- `learned_effect_and_policy_guarded`
  - `raw_ranking_disagreement_count = 66`
  - `raw_policy_disagreement_count = 218`

## Cohort slice snapshot

| slice | user_count | deterministic disagreement | policy_guard | effect_guard |
| --- | ---: | ---: | ---: | ---: |
| `cgm_users` | `20` | `0` | `18` | `0` |
| `genetic_users` | `53` | `68` | `57` | `0` |
| `low_risk_users` | `65` | `171` | `73` | `0` |
| `high_risk_users` | `31` | `0` | `29` | `0` |
| `single_goal_users` | `76` | `171` | `84` | `0` |
| `multi_goal_users` | `20` | `0` | `18` | `0` |

Interpretation:

- low-risk / single-goal cohorts still show real learned-effect divergence after calibration
- high-risk and `cgm` cohorts remain deterministic at the safety edge
- combined mode is still policy-dominated, so the next replay step is not more wiring but better learned-effect to learned-policy coupling

## Known limits

- replay still follows fixed synthetic trajectories rather than online regenerated state
- learned artifacts are still simulation-only
- structured safety `dose_limits` remain shallow
