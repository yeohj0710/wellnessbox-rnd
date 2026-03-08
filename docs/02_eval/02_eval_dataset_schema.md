# Eval Dataset Schema

Source of truth:

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf`

## Purpose

The frozen eval dataset is the deterministic regression contract for the current
baseline. Each line is one JSON object in JSONL format.

Primary dataset:

- `C:/dev/wellnessbox-rnd/data/frozen_eval/sample_cases.jsonl`

Current size:

- 16 synthetic cases

## Top-level fields

| Field | Type | Notes |
| --- | --- | --- |
| `case_id` | string | Stable case identifier |
| `synthetic` | boolean | All current cases are synthetic |
| `category` | string | Scenario bucket for coverage tracking |
| `description` | string | Human-readable case summary |
| `request` | object | `RecommendationRequest` payload |
| `expected` | object | Expected deterministic outcome contract |
| `follow_up` | object or null | Synthetic pre/post observation for efficacy proxy |
| `integration` | object | Wearable, CGM, genetic attempt/success observations |
| `adverse_event_reported` | boolean | Annual adverse-event proxy flag |

## `expected` object

| Field | Type | Notes |
| --- | --- | --- |
| `recommendation_reference.required_ingredients` | string[] | Required ingredient coverage set |
| `expected_status` | string | `ok`, `needs_review`, `blocked` |
| `expected_next_action` | string | Deterministic next action |
| `required_rule_ids` | string[] | Safety rule IDs that must appear |
| `required_excluded_ingredients` | string[] | Ingredients that must be excluded |
| `required_explanation_terms` | string[] | Explanation proxy terms |
| `minimum_explanation_term_coverage` | float | Minimum required proxy coverage |

## `integration` object

Example:

```json
{
  "wearable": { "attempted": 1, "success": 1 },
  "cgm": { "attempted": 1, "success": 0 },
  "genetic": { "attempted": 1, "success": 1 }
}
```

## Deterministic authoring workflow

Use the helper script before manual JSONL edits:

```bash
python scripts/manage_eval_dataset.py summary
python scripts/manage_eval_dataset.py validate
python scripts/manage_eval_dataset.py scaffold --case-id eval-100 --category normal_recommendation --description "new case" --goal sleep_support
```

`scaffold` prints a minimal valid case skeleton. Add `--append` to merge the new
case into the dataset and rewrite the JSONL in sorted `case_id` order.

## Validation invariants

The dataset helper currently enforces the following invariants:

- `case_id` values are unique.
- JSONL rows stay sorted by `case_id`.
- `request.request_id` matches `case_id`.
- `minimum_explanation_term_coverage` stays within `0..100`.
- `required_explanation_terms` is non-empty when coverage is above `0`.
- `integration.<modality>.success <= attempted`.
- integration modalities are limited to `wearable`, `cgm`, and `genetic`.

## Current coverage goals

- normal recommendation
- safety warning with medication interaction
- blocked minimum-input contract
- missing-context follow-up cases
- explanation quality proxy
- conservative edge case
- duplicate overlap safety signal
- catalog alias normalization
- modality integration mix

## Assumptions

- `sensor_genetic_integration_rate_pct` is still a proxy derived from
  case-level observations, not from real parser execution.
- The eval runner emits modality-level integration diagnostics in addition to
  the pooled KPI score so the bottleneck modality is visible in the report.
- The current dataset is larger and more representative than the original
  5-case seed, but still too small to be treated as a production KPI gate.
