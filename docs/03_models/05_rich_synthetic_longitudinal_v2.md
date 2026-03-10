# Rich Synthetic Longitudinal v2

## Loop choice

- chosen stage: `P2`
- chosen task: `expand synthetic longitudinal trajectories and policy labels into synthetic_longitudinal_v2 / policy_training_v1`

## Why this loop

- `policy_training_v0.jsonl` only covered:
  - `start_plan`
  - `collect_more_input`
  - `trigger_safety_recheck`
- the next missing closed-loop layer was richer policy supervision, not another doc-only change
- safety remains deterministic and citation-backed; this loop only broadens synthetic supervision and trajectory coverage

## Artifacts

- rich cohort:
  - [synthetic_longitudinal_v2.jsonl](/c:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v2.jsonl)
- policy dataset:
  - [policy_training_v1.jsonl](/c:/dev/wellnessbox-rnd/data/synthetic/policy_training_v1.jsonl)
- cohort summary:
  - [synthetic_longitudinal_v2_summary.json](/c:/dev/wellnessbox-rnd/artifacts/reports/synthetic_longitudinal_v2_summary.json)
  - [synthetic_longitudinal_v2_summary.md](/c:/dev/wellnessbox-rnd/artifacts/reports/synthetic_longitudinal_v2_summary.md)
- policy summary:
  - [policy_training_v1_summary.json](/c:/dev/wellnessbox-rnd/artifacts/reports/policy_training_v1_summary.json)
  - [policy_training_v1_summary.md](/c:/dev/wellnessbox-rnd/artifacts/reports/policy_training_v1_summary.md)
- sample trace:
  - [synthetic_longitudinal_v2_trace_sample.json](/c:/dev/wellnessbox-rnd/artifacts/reports/synthetic_longitudinal_v2_trace_sample.json)

## Cohort shape

- deterministic seed: `20260310`
- users: `96`
- records: `480`
- steps per user: `5`
- checkpoints:
  - day `0`
  - day `7`
  - day `14`
  - day `30`
  - day `45`

Each cohort record now contains:

- `RecommendationRequest`
- baseline PRO snapshot
- follow-up PRO snapshot
- domain-level `delta_z_by_domain`
- regimen items with dose and schedule
- baseline recommendation keys
- `expected_effect_proxy`
- `adherence_proxy`
- `side_effect_proxy`
- labels:
  - `next_action`
  - `reason_code`
  - `safety_status`
  - `risk_tier`
  - `adverse_event`
  - `closed_loop_state`

## Action coverage

`policy_training_v1` now materially includes all required no-human next actions:

- `continue_plan = 164`
- `re_optimize = 12`
- `reduce_or_stop = 81`
- `monitor_only = 80`
- `ask_targeted_followup = 48`
- `trigger_safety_recheck = 95`

## Generator design

- archetype-driven cohort with modality coverage:
  - wearable
  - cgm
  - genetic
- trajectory modes:
  - `stable_continue`
  - `monitor_plateau`
  - `reoptimize_low_response`
  - `reduce_side_effect`
  - `targeted_followup_low_adherence`
  - `safety_recheck_high_risk`
- policy labels are synthetic gold labels derived from deterministic safety state plus trajectory-specific follow-up logic
- deterministic safety remains upstream:
  - blocked structured safety still maps to `trigger_safety_recheck`
  - safety hard rules are not overridden by synthetic labels

## Feature schema

`policy_training_v1` rows expose `66` numeric features on average, including:

- profile:
  - age
  - pregnancy
- request state:
  - goal count
  - symptom count
  - condition count
  - medication count
  - current supplement count
- modality flags:
  - wearable
  - cgm
  - genetic
- longitudinal signals:
  - trajectory step
  - day index
  - baseline aggregate z
  - follow-up aggregate z
  - delta aggregate z
  - adherence proxy
  - side-effect proxy
  - expected effect proxy
- regimen signals:
  - regimen count
  - reduced count
  - stopped count
- per-goal one-hot and domain z features

## Validation boundary

- data source is synthetic only
- validator enforces:
  - minimum `200` records
  - complete `0..4` step coverage per user
  - non-empty PRO snapshots
  - regimen presence after baseline
  - full required action coverage
- safety hard rules remain deterministic and separate from future learned policy training
