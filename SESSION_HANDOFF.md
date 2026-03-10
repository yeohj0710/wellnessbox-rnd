# SESSION_HANDOFF

## Scope guardrails

- Work only inside `C:/dev/wellnessbox-rnd`
- Do not read or reference:
  - `wellnessbox/`
  - `docs/03_integration/`
  - `docs/00_discovery/`
  - `docs/00_migration/`
  - `docs/legacy_from_wellnessbox/`

## Source of truth

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## What this loop did

- Chosen stage: `P2`
- Chosen task: `learned efficacy gated integration into optimizer`
- Why:
  - source-of-truth requires quantified effect and optimization to work together
  - the repo already had a learned efficacy artifact
  - the safest next increment was a narrow opt-in reranker behind deterministic
    safety and filtering
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## Integration pipeline added

- New runtime feature builder for learned scoring:
  - `build_runtime_efficacy_feature_dict(...)`
- New feature-row prediction helper:
  - `predict_effect_proxy_from_feature_dict(...)`
- New optimizer gate:
  - `enable_learned_reranking=True`
  - `learned_efficacy_artifact_path=...`
- The gate only applies when:
  - safety status is `ok`
  - no pregnancy / condition / medication risk is present
  - goal set is exactly `general_wellness`
  - deterministic candidate totals are within a `1.0` point margin
- New tests:
  - `C:/dev/wellnessbox-rnd/tests/test_learned_optimizer_integration.py`
  - `C:/dev/wellnessbox-rnd/tests/test_closed_loop_simulation.py`
- New artifacts:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.md`

## Integration result snapshot

- scenario: `syn-user-009`
- deterministic baseline top recommendation:
  - `vitamin_d3`
- learned gated rerank top recommendation:
  - `vitamin_c`
- selected candidate learned bonus:
  - `3.619935`
- simulation trace still ends on a conservative continuation path:
  - `recommendation_ready -> intake_active -> intake_active`
- regression also covers:
  - missing-artifact fallback
  - high-risk anticoagulant no-op path
  - rerank-enabled closed-loop trace

## Safety and baseline status

- Training data comes only from repo-generated synthetic data.
- Safety rules remain outside and ahead of the learned model.
- The learned model is now wired into runtime ranking only through an explicit
  opt-in gate.
- Missing artifact or ineligible risk profile falls back to deterministic ranking.
- Frozen eval metrics stayed unchanged:
  - `recommendation_coverage_pct = 100.0`
  - `efficacy_improvement_pp = 9.90291632090153`
  - `next_action_accuracy_pct = 99.21875`
  - `explanation_quality_accuracy_pct = 99.47916666666667`
  - `safety_reference_accuracy_pct = 99.86979166666667`
  - `adverse_event_count_yearly = 0.0`
  - `sensor_genetic_integration_rate_pct = 90.40247678018576`

## Commands run

- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop`
- `python scripts/run_closed_loop_simulation.py --user-id syn-user-009 --enable-learned-reranking --report-json artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.json --report-md artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.md`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final`

## Files changed this loop

- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/models/__init__.py`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/models/efficacy_model_v0.py`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/optimizer/service.py`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/orchestration/recommendation_service.py`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/schemas/recommendation.py`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/efficacy/service.py`
- `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/simulation/closed_loop_v0.py`
- `C:/dev/wellnessbox-rnd/scripts/run_closed_loop_simulation.py`
- `C:/dev/wellnessbox-rnd/tests/test_learned_optimizer_integration.py`
- `C:/dev/wellnessbox-rnd/tests/test_closed_loop_simulation.py`
- `C:/dev/wellnessbox-rnd/docs/03_models/03_learned_efficacy_gated_integration.md`
- `C:/dev/wellnessbox-rnd/docs/04_simulation/01_closed_loop_simulation_harness.md`
- `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.json`
- `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_simulation_v0_syn_user_009_learned_rerank.md`
- `C:/dev/wellnessbox-rnd/PROGRESS.md`
- `C:/dev/wellnessbox-rnd/NEXT_STEPS.md`
- `C:/dev/wellnessbox-rnd/SESSION_HANDOFF.md`

## Recommended next loop

1. Train a next-action / policy model v0 from synthetic closed-loop traces.
2. Extend learned reranking to the next safe low-risk subset with new regression
   coverage.
3. Add batch simulation metrics over multiple synthetic users.
