# PROGRESS

## Current loop

- Chosen stage: `P1`
- Chosen task: `adopt structured current-supplement dose in the maintained synthetic_longitudinal_v3 source`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/frozen_eval/frozen_eval_v1.jsonl`
  - `case_count = 256`

## What changed

- Adopted structured supplement dose in one more maintained synthetic-generation path:
  - `src/wellnessbox_rnd/synthetic/rich_longitudinal_v3.py`
  - `data/synthetic/synthetic_longitudinal_v3.jsonl`
- Added deterministic normalization for emitted `current_supplements` in v3:
  - fills `dose` from `DOSE_TEMPLATES` when ingredient mapping is unambiguous
  - uses ingredient list first, then low-ambiguity name canonicalization
  - leaves fallback untouched when mapping is ambiguous or no template exists
- Added measurable reporting:
  - `scripts/generate_synthetic_longitudinal_v3.py`
  - `artifacts/reports/synthetic_longitudinal_v3_summary.json`
  - `artifacts/reports/synthetic_longitudinal_v3_summary.md`
  - v3 cohort summary now includes `structured_current_supplement_dose_record_count`
- Expanded focused regression coverage:
  - `tests/test_rich_synthetic_longitudinal_v3.py`
  - summary count now must match the generated record count with populated structured doses

## Why this loop was chosen

- The highest-priority unfinished item after the mineral `dose_limits` loop was one more bounded maintained input/source-path adoption.
- `synthetic_longitudinal_v3` is a maintained upstream source for training and replay artifacts, so it has better leverage than another API-only tweak.
- The existing v4 helper pattern could be reused with a small local change set and produce a measurable artifact delta without touching frozen eval.

## Safety coverage delta

- rule count stayed flat:
  - `dose_limits = 5`
- dataset/input adoption delta:
  - before: maintained v3 synthetic source did not emit structured supplement doses
  - after: `synthetic_longitudinal_v3` emits structured supplement doses on `270 / 480` records
- measurable artifact:
  - `C:/dev/wellnessbox-rnd/artifacts/reports/synthetic_longitudinal_v3_summary.json`
  - `structured_current_supplement_dose_record_count = 270`
  - `record_count = 480`

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

- `dose_limits` still cover only five ingredients
- structured supplement dose now exists in the API and both maintained `synthetic_longitudinal_v3` / `v4`, but not yet broadly across other maintained input paths
- `cgm` remains the weakest official eval modality at `72.0%`
- low-risk `re_optimize` richness in replay remains thin
- learned artifacts remain replay-only and not runtime-eligible

## Validation

- `python -m ruff check src/wellnessbox_rnd/synthetic/rich_longitudinal_v3.py scripts/generate_synthetic_longitudinal_v3.py tests/test_rich_synthetic_longitudinal_v3.py`
- `python -m pytest tests/test_rich_synthetic_longitudinal_v3.py -q`
- `python scripts/generate_synthetic_longitudinal_v3.py`
- `python scripts/manage_eval_dataset.py validate`
- `python scripts/manage_eval_dataset.py summary`
- `python -m ruff check .`
- `python -m pytest`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_eval`
- `python scripts/run_eval.py --dataset data/frozen_eval/frozen_eval_v1.jsonl --output-dir artifacts/reports/current_loop_final_eval`
