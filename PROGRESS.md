# PROGRESS

## Current loop

- Chosen stage: `P4`
- Chosen task: `multi-user batch replay simulation with aggregate transition metrics and guarded learned-policy comparison`
- Why:
  - the no-human action space, ingestion pipeline, synthetic longitudinal dataset, learned efficacy artifact, and policy artifact now exist
  - the next missing execution layer was batch replay over many users instead of single-scenario traces
  - the narrowest next step was to compare deterministic-only replay against learned-policy-guarded replay without touching runtime recommendation logic
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## What changed

- Extended simulation harness:
  - `src/wellnessbox_rnd/simulation/closed_loop_v0.py`
  - `src/wellnessbox_rnd/simulation/__init__.py`
- Single-scenario simulation now accepts:
  - learned policy artifact path
  - `--enable-learned-policy`
- Added batch replay runner:
  - `scripts/run_closed_loop_batch_simulation.py`
- Added batch simulation regression coverage:
  - `tests/test_closed_loop_simulation.py`
- Generated batch comparison artifacts:
  - `artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.json`
  - `artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.md`
- Updated simulation documentation:
  - `docs/04_simulation/01_closed_loop_simulation_harness.md`

## Batch replay snapshot

- compared modes:
  - `deterministic_only`
  - `learned_policy_guarded`
- replay scope:
  - `48 users`
  - `84 total trace steps per mode`
  - `average_trace_length = 1.75`
- aggregate final states:
  - `baseline_questionnaire_due = 24`
  - `intake_active = 12`
  - `stop_or_escalate = 12`
- aggregate final policy actions:
  - `ask_targeted_followup = 24`
  - `continue_plan = 12`
  - `reduce_or_stop = 12`
- adverse events:
  - `12`
- average predicted effect proxy:
  - `0.154855`
- comparison deltas:
  - `differing_final_state_user_ids = 0`
  - `differing_final_policy_user_ids = 0`
  - `differing_policy_path_user_ids = 0`

## Deterministic boundary

- GPT wrapper was not used in this loop.
- Learned policy integration exists only inside simulation replay.
- Runtime recommendation logic did not change.
- Guarded policy replay still clamps any more-permissive learned action back to the deterministic policy action.
- Current `policy_guard_applied_count = 0` because the synthetic policy labels are still generator-derived and the learned policy reproduces them exactly on this dataset version.

## Deterministic baseline status

Frozen eval remained unchanged:

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.90291632090153`
- `next_action_accuracy_pct = 99.21875`
- `explanation_quality_accuracy_pct = 99.47916666666667`
- `safety_reference_accuracy_pct = 99.86979166666667`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 90.40247678018576`

## Current bottlenecks

Runtime next-action reason buckets:

1. `blocked_minimum_input = 5`
2. `collect_more_input_multiple_missing_items = 4`
3. `needs_review_no_candidates = 4`
4. `needs_review_due_to_safety = 3`
5. `collect_more_input_high_priority_missing_info = 3`

Closed-loop roadmap status:

- no-human runtime action space exists
- citation-backed ingestion pipeline exists
- synthetic longitudinal dataset exists
- learned efficacy model exists
- learned policy model exists
- multi-user batch replay and aggregate state metrics now exist
- next major missing execution layer is wiring structured knowledge into deterministic safety loading and broadening synthetic policy diversity

## Validation

- `python scripts/run_closed_loop_batch_simulation.py --dataset data/synthetic/synthetic_longitudinal_v1.jsonl --max-cycles 3 --max-users 48 --model-artifact artifacts/models/efficacy_model_v0.json --policy-model-artifact artifacts/models/policy_model_v0.json`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final`
