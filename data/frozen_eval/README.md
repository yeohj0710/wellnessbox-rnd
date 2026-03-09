# frozen_eval

This directory stores the primary frozen eval dataset for the deterministic
WellnessBox R&D baseline.

## Current dataset

- `frozen_eval_v1.jsonl`: 194 synthetic cases
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
- explicit genetic-rationale regressions
- explicit genetic-summary regressions
- genetic glycemic-response regressions
- genetic gut-resilience regressions
- genetic immunity-fallback regressions
- genetic heart/coq10 regressions
- genetic energy-metabolism regressions
- genetic sleep-fallback regressions
- genetic bone-mineral regressions
- cgm-supported ranking regressions
- explicit cgm-observability regressions
- explicit wearable-observability regressions
- renal-only safety review reduction regressions
- pregnancy-only safety review reduction regressions
- survey-missing pregnancy blocked-input reduction regressions
- survey-missing heart blocked-input reduction regressions
- genetic glucose fallback start-plan regressions
- duplicate-only current-regimen continuation regressions
- wearable heart fallback start-plan regressions
- multimodal heart-energy fallback start-plan regressions
- duplicate-only heart-energy fallback start-plan regressions
- multimodal heart-sleep fallback start-plan regressions
- genetic missing-info observability regressions
- pregnancy-plus-renal glucose safety-review reduction regressions
- duplicate-only heart-health fallback regressions
- general-wellness survey-only blocked-input reduction regressions
- heart-only multimodal fallback start-plan regressions
- heart-and-glucose multimodal fallback start-plan regressions
- duplicate-only heart-symptom fallback start-plan regressions
- pregnancy-only sleep review reduction regressions
- survey-missing energy start-plan fallback regressions
- survey-missing energy/bone blocked-input reduction regressions
- survey-missing renal sleep/bone blocked-input reduction regressions
- survey-missing bone-support start-plan regressions
- survey-missing general-wellness start-plan regressions
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
- Assumption: `integration.<modality>.success = 1` means the modality changed
  ranking or is explicitly pinned in the frozen eval explanation contract.
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
