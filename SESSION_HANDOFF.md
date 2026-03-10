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

- Chosen stage: `P4`
- Chosen task: `multi-user batch replay simulation plus guarded learned-policy comparison`
- Why:
  - single-scenario simulation already existed
  - learned policy artifact already existed
  - the next missing piece was batch replay with aggregate metrics, not another single-user trace
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## Batch simulation result

- Extended simulation module:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/simulation/closed_loop_v0.py`
- Added batch runner:
  - `C:/dev/wellnessbox-rnd/scripts/run_closed_loop_batch_simulation.py`
- Added artifacts:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/closed_loop_batch_simulation_v0_policy_compare.md`

Batch snapshot:

- users replayed: `48`
- total trace steps per mode: `84`
- final states:
  - `baseline_questionnaire_due = 24`
  - `intake_active = 12`
  - `stop_or_escalate = 12`
- final policy actions:
  - `ask_targeted_followup = 24`
  - `continue_plan = 12`
  - `reduce_or_stop = 12`
- policy comparison:
  - `differing_final_state_user_ids = 0`
  - `differing_final_policy_user_ids = 0`
  - `differing_policy_path_user_ids = 0`

## GPT / learned / deterministic boundary

- GPT wrapper was not used in this loop.
- Learned policy integration exists only in simulation replay.
- Runtime recommendation logic did not change.
- Safety hard rules remain upstream of learned efficacy and learned policy.
- Deterministic policy remains the ceiling: more-permissive learned actions are clamped back.
- Current batch replay shows `policy_guard_applied_count = 0` because the synthetic policy labels are still generator-derived and matched exactly by the current model.

## Validation snapshot

- `python scripts/run_closed_loop_batch_simulation.py --dataset data/synthetic/synthetic_longitudinal_v1.jsonl --max-cycles 3 --max-users 48 --model-artifact artifacts/models/efficacy_model_v0.json --policy-model-artifact artifacts/models/policy_model_v0.json`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final`

## Result snapshot

- deterministic-only and learned-policy-guarded batch replay currently produce the same final states and final policy actions
- this is expected on the current dataset because policy labels come from deterministic generation
- batch replay and aggregate state metrics now exist, so future learned-policy differences can be measured when synthetic label diversity grows

## Recommended next loop

1. Wire `reference_knowledge_base_v1.json` into deterministic safety/rule loading behind strict validation.
2. Expand synthetic policy labels beyond the current 3-action distribution.
3. Add batch replay slices by modality and risk cohort once richer policy labels exist.
