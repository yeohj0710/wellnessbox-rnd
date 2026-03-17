# PROGRESS

## Current loop

- Chosen stage: `P2/P4`
- Chosen task: `implement PROImprovementSummaryV1 directly from the shared baseline/follow-up PRO event contract`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
  - `case_count = 480`

## What changed

- Added one bounded shared-contract implementation/report pair:
  - `artifacts/reports/pro_improvement_summary_contract_v1.json`
  - `artifacts/reports/pro_improvement_summary_contract_v1.md`
- Added minimal implementation only on the PRO normalized path:
  - `src/wellnessbox_rnd/schemas/pro_events.py`
  - `src/wellnessbox_rnd/metrics/pro_scoring.py`
  - `scripts/build_pro_improvement_summary_contract.py`
  - `tests/test_pro_improvement_summary_contract.py`
  - updated `tests/test_pro_events.py`
- Updated:
  - `PROGRESS.md`
  - `NEXT_STEPS.md`
  - `SESSION_HANDOFF.md`

## Why this loop was chosen

- The repo already had a shared baseline/follow-up PRO event path, but the strongest remaining gap was:
  - making `PROImprovementSummaryV1` read directly from that normalized event contract
  - proving `z-score`, `percentile`, and `delta_pp` stay on one testable path
- This loop was the smallest implementation step that tightened KPI-path semantics without reopening training or runtime scope.

## Result in this loop

- The shared baseline/follow-up PRO event now carries one normalized snapshot shape for both timepoints:
  - `timepoint`
  - `aggregate_z`
  - `aggregate_percentile`
  - `domain_z`
  - `domain_percentile`
- `PROImprovementSummaryV1` is now computed directly from that shared contract and exposes:
  - `baseline_aggregate_z`
  - `follow_up_aggregate_z`
  - `baseline_aggregate_percentile`
  - `follow_up_aggregate_percentile`
  - `aggregate_delta_z`
  - `aggregate_delta_pp`
- The new contract artifact fixes the end-to-end read as:
  - `derived_directly_from_shared_event_contract = true`
  - `baseline_follow_up_same_normalized_structure_case_count = 480`
  - `event_to_summary_valid_case_count = 480`
  - `event_to_summary_invalid_case_count = 0`
  - `delta_pp_matches_percentile_diff_all_valid_cases = true`
  - `frozen_eval_compatible = true`

## Interpretation

- PRO outcome meaning now sits on one normalized baseline/follow-up event path in real code, not just in docs.
- The shared PRO contract is stronger than before, but this does not reopen training:
  - the training-readiness gate remains `NO-GO`
  - replay and synthetic-validity blockers still dominate overall priority

## Behavior boundary

- No runtime recommendation change
- No safety logic change
- No optimizer change
- No inference API change
- No effect-model training
- No chat/OpenAI change
- Learned artifacts remain replay-only

## Deterministic baseline status

Official frozen eval baseline remains unchanged:

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.90291632090153`
- `next_action_accuracy_pct = 99.21875`
- `explanation_quality_accuracy_pct = 99.47916666666667`
- `safety_reference_accuracy_pct = 99.86979166666667`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 90.40247678018576`

## Validation

- `python scripts/build_pro_improvement_summary_contract.py --report-json artifacts/reports/pro_improvement_summary_contract_v1.json --report-md artifacts/reports/pro_improvement_summary_contract_v1.md`
- `python -m pytest tests/test_pro_events.py tests/test_pro_scoring.py tests/test_pro_improvement_summary_contract.py -q`
- `python -m ruff check src/wellnessbox_rnd/schemas/pro_events.py src/wellnessbox_rnd/metrics/pro_scoring.py scripts/build_pro_improvement_summary_contract.py tests/test_pro_events.py tests/test_pro_scoring.py tests/test_pro_improvement_summary_contract.py`
- `git diff --check -- src/wellnessbox_rnd/schemas/pro_events.py src/wellnessbox_rnd/metrics/pro_scoring.py scripts/build_pro_improvement_summary_contract.py tests/test_pro_events.py tests/test_pro_improvement_summary_contract.py artifacts/reports/pro_improvement_summary_contract_v1.json artifacts/reports/pro_improvement_summary_contract_v1.md PROGRESS.md NEXT_STEPS.md SESSION_HANDOFF.md`
