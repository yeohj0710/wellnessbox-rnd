# PROGRESS

## Current loop

- Chosen stage: `P2`
- Chosen task: `learned efficacy gated integration into optimizer`
- Reason:
  - source-of-truth requires quantified effect and optimization to be combined
  - a learned efficacy artifact already exists but was not wired into recommendation ranking
  - the safest next step is gated reranking behind deterministic safety and candidate filtering
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## What changed

- Added reusable runtime efficacy feature builder:
  - `build_runtime_efficacy_feature_dict(...)`
- Added feature-row prediction helper:
  - `predict_effect_proxy_from_feature_dict(...)`
- Extended candidate score breakdown with `learned_effect_bonus`.
- Added gated optimizer reranking:
  - default `off`
  - only applies after deterministic safety filtering
  - only applies on low-risk `general_wellness` cases
  - only applies when top deterministic candidates are within a `1.0` point margin
- Extended `recommend(...)` with opt-in learned reranking arguments while keeping the
  default deterministic path unchanged.
- Extended closed-loop simulation runner with `--enable-learned-reranking`.
- Added integration regression tests:
  - near-tied single-product rerank case
  - high-risk no-op case
  - missing-artifact fallback case
- Generated integration artifact:
  - `artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.json`
  - `artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.md`

## Integration summary

- scenario: `syn-user-009`
- dataset: `data/synthetic/synthetic_longitudinal_v1.jsonl`
- learned model artifact: `artifacts/models/efficacy_model_v0.json`
- deterministic baseline recommendation:
  - `vitamin_d3`
- learned reranking recommendation:
  - `vitamin_c`
- learned tie-break bonus on the selected candidate:
  - `3.619935`
- end-to-end simulation still stayed on the conservative path:
  - cycle `0`: `recommendation_ready`
  - cycle `1`: `continue_plan -> intake_active`
  - cycle `2`: `continue_plan -> intake_active`

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

- synthetic pipeline exists
- first trainable model artifact exists
- closed-loop simulation harness now exists
- learned efficacy model is now gated into optimizer ranking for a narrow low-risk subset
- default runtime remains deterministic when reranking is not enabled
- deterministic safety and fallback still lead

## Validation

- `python scripts/run_closed_loop_simulation.py --user-id syn-user-009 --enable-learned-reranking --report-json artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.json --report-md artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.md`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final`
