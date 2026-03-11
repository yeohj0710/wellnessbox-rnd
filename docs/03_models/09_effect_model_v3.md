# Effect Model v3

## Loop choice

- chosen stage: `P2/P3`
- chosen task: `calibrate learned effect on synthetic_longitudinal_v4 for guarded replay divergence without frozen-eval regression`

## Why v3 exists

- `effect_model_v2` restored learned-effect divergence, but it was too pessimistic at replay time:
  - predicted aggregate deltas were much lower than the policy-facing `expected_effect_proxy`
  - `learned_effect_guarded` could diverge, but the scale mismatch over-pushed low-risk users toward `re_optimize`
- the fix in this loop was twofold:
  - build a threshold-edge low-risk cohort with more modality-available safe users
  - add an explicit policy-proxy calibration layer on top of the domain-delta model

## Inputs and targets

- training dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
- artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/models/effect_model_v3.json`
- target:
  - domain-level `delta_z_by_domain`
- aggregate effect:
  - mean of predicted domain deltas
- policy-facing replay proxy:
  - `policy_proxy = intercept + slope * predicted_aggregate_delta`

## Synthetic v4 changes

- low-risk users remain low-risk across follow-up
- low-risk users now include more `wearable` and `genetic` availability without adding safety risk
- near-tie candidate families are pushed closer to action thresholds
- regimen carries more schedule / duration / dose sensitivity
- adherence-recovery and delayed-flip trajectories are explicit

## Training result

- split sizes:
  - `train = 275`
  - `val = 125`
  - `test = 80`
- selected alpha:
  - `0.01`
- calibration:
  - `policy_proxy_slope = 3.11735613`
  - `policy_proxy_intercept = 0.09283873`
- test metrics:
  - `mean_domain_mae = 0.005517`
  - `aggregate_mae = 0.003698`
  - `aggregate_rmse = 0.004905`
  - `aggregate_r2 = 0.986755`
  - `policy_proxy_mae = 0.040029`
  - `zero_baseline_policy_proxy_mae = 0.1903`

## Replay effect

On `synthetic_longitudinal_v4` replay:

- `learned_effect_guarded`
  - `raw_ranking_disagreement_count = 71`
  - `differing_ranking_user_ids = 22`
  - `differing_final_policy_user_ids = 25`
  - `differing_final_state_user_ids = 24`
- low-risk cohort:
  - deterministic final action: `continue_plan:65`
  - learned-effect final actions: `continue_plan:40, monitor_only:1, re_optimize:24`
- single-goal cohort:
  - learned-effect final actions: `ask_targeted_followup:11, continue_plan:40, monitor_only:1, re_optimize:24`

## Boundary

- `effect_model_v3` is still replay-only
- deterministic safety remains upstream
- reranking still happens only after deterministic candidate filtering
- reranking is now limited to the guarded near-tie survivor set
- pregnancy / medication / condition / explicit avoid still block learned reranking

## Remaining gap

- combined mode is still mostly following guarded policy output
- low-risk terminal `monitor_only` density is still thin
- the model is still not connected to runtime recommendation selection
