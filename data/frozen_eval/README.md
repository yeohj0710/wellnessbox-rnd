# frozen_eval

This directory stores the primary frozen eval dataset for the deterministic
WellnessBox R&D baseline.

## Current dataset

- `frozen_eval_v1.jsonl`: 118 synthetic cases
- `sample_cases.jsonl`: 16-case seed snapshot retained for reference

## Coverage

- normal recommendation
- safety warning
- blocked minimum-input case
- missing-context follow-up cases
- explanation quality proxy
- conservative edge case
- duplicate overlap safety case
- catalog alias normalization cases
- gut health baseline
- energy support baseline
- mixed wearable/CGM/genetic integration observations
- genetic-supported ranking regressions
- long-title parser-limit failures
- review paths with no remaining safe candidates
- stacked survey-missing safety blocks

## Authoring workflow

Use the dataset helper before editing JSONL by hand:

```bash
python scripts/manage_eval_dataset.py summary
python scripts/manage_eval_dataset.py validate
python scripts/manage_eval_dataset.py scaffold --case-id eval-100 --category normal_recommendation --description "new case" --goal sleep_support
```

To append a scaffolded case directly into a dataset:

```bash
python scripts/manage_eval_dataset.py scaffold ^
  --case-id eval-100 ^
  --category normal_recommendation ^
  --description "new case" ^
  --goal sleep_support ^
  --append
```

## Validation invariants

- `case_id` values must be unique.
- JSONL rows are kept in lexicographic `case_id` order.
- `request.request_id` must match `case_id` for deterministic tracing.
- `minimum_explanation_term_coverage` must stay within `0..100`.
- `required_explanation_terms` cannot be empty when coverage is above `0`.
- `integration.<modality>.success` cannot exceed `attempted`.

## Working assumptions

- The dataset is still synthetic and is used as a deterministic regression set.
- `sensor_genetic_integration_rate_pct` is still a proxy metric based on the
  `integration.attempted` and `integration.success` observations embedded in the
  dataset.
- The eval report includes modality-level integration diagnostics for
  `wearable`, `cgm`, and `genetic` so the bottleneck is visible without changing
  the official KPI score.
- The current dataset is broader than the original 5-case seed, but it is not a
  production acceptance set yet.

## Update rule

When the baseline behavior changes intentionally, update the dataset and the
expected outputs together, then rerun:

```bash
python -m ruff check .
python -m pytest
python scripts/run_eval.py
```
