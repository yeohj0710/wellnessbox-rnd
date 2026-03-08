# Frozen Eval Growth Log

## 2026-03-08 loop 1

- Selected task: `frozen eval expansion`
- Reason: primary validated frozen eval size was `16`, below the forced P0 threshold of `100`

### Case count

- before: `16`
- after: `40`
- delta: `+24`

### New case mix

- `13` hard / negative / ambiguous cases
- `10` regression-style cases

### Metric delta

| metric | before | after |
| --- | --- | --- |
| `recommendation_coverage_pct` | `100.0` | `100.0` |
| `efficacy_improvement_pp` | `13.070858781952536` | `12.162726622990466` |
| `next_action_accuracy_pct` | `100.0` | `100.0` |
| `explanation_quality_accuracy_pct` | `100.0` | `100.0` |
| `safety_reference_accuracy_pct` | `100.0` | `100.0` |
| `adverse_event_count_yearly` | `0.0` | `0.0` |
| `sensor_genetic_integration_rate_pct` | `75.0` | `58.53658536585366` |

## 2026-03-08 loop 2

- Selected task: `frozen eval expansion`
- Reason: primary validated frozen eval size was still `40`, below the forced P0 threshold of `100`

### Case count

- before: `40`
- after: `64`
- delta: `+24`

### New case mix

- `20` hard / negative / ambiguous cases
- `15` regression-style cases

### Metric delta

| metric | before | after |
| --- | --- | --- |
| `recommendation_coverage_pct` | `100.0` | `100.0` |
| `efficacy_improvement_pp` | `12.162726622990466` | `11.195266390106452` |
| `next_action_accuracy_pct` | `100.0` | `100.0` |
| `explanation_quality_accuracy_pct` | `100.0` | `100.0` |
| `safety_reference_accuracy_pct` | `100.0` | `100.0` |
| `adverse_event_count_yearly` | `0.0` | `0.0` |
| `sensor_genetic_integration_rate_pct` | `58.53658536585366` | `44.57831325301205` |

## 2026-03-08 loop 3

- Selected task: `frozen eval expansion`
- Reason: primary validated frozen eval size was still `64`, below the forced P0 threshold of `100`

### Case count

- before: `64`
- after: `88`
- delta: `+24`

### New case mix

- `20` hard / negative / ambiguous cases
- `16` regression-style cases
- added explicit coverage for:
  - parser-limit / long-title parser miss
  - review with no candidates across more goals
  - blocked vs review boundary cases
  - more CGM / genetic attempted failure density

### Metric delta

| metric | before | after |
| --- | --- | --- |
| `recommendation_coverage_pct` | `100.0` | `100.0` |
| `efficacy_improvement_pp` | `11.195266390106452` | `10.27822332512464` |
| `next_action_accuracy_pct` | `100.0` | `100.0` |
| `explanation_quality_accuracy_pct` | `100.0` | `100.0` |
| `safety_reference_accuracy_pct` | `100.0` | `100.0` |
| `adverse_event_count_yearly` | `0.0` | `0.0` |
| `sensor_genetic_integration_rate_pct` | `44.57831325301205` | `38.01652892561984` |

### Bottleneck shift

- before bottleneck: `genetic = 14.705882352941176%`
- after bottleneck: `genetic = 10.0%`
- remaining weak modality: `cgm = 20.0%`

## 2026-03-08 loop 4

- Selected task: `frozen eval expansion`
- Reason: primary validated frozen eval size was still `88`, below the forced P0 threshold of `100`

### Case count

- before: `88`
- after: `112`
- delta: `+24`

### New case mix

- `20` hard / negative / ambiguous cases
- `16` regression-style cases
- added explicit coverage for:
  - long-title parser-limit misses on avoid / duplicate filtering
  - no-candidate review paths across more goals
  - survey-missing blocked cases with pregnancy / anticoagulant / renal risk
  - more missing-context multi-goal follow-up gates
  - additional CGM / genetic attempted failures

### Metric delta

| metric | before | after |
| --- | --- | --- |
| `recommendation_coverage_pct` | `100.0` | `100.0` |
| `efficacy_improvement_pp` | `10.27822332512464` | `9.94784689765133` |
| `next_action_accuracy_pct` | `100.0` | `100.0` |
| `explanation_quality_accuracy_pct` | `100.0` | `100.0` |
| `safety_reference_accuracy_pct` | `100.0` | `100.0` |
| `adverse_event_count_yearly` | `0.0` | `0.0` |
| `sensor_genetic_integration_rate_pct` | `38.01652892561984` | `32.903225806451616` |

### Bottleneck shift

- before bottleneck: `genetic = 10.0%`
- after bottleneck: `genetic = 7.352941176470588%`
- remaining weak modality: `cgm = 16.666666666666668%`

## 2026-03-08 loop 5

- Selected task: `baseline failure analysis documentation`
- Reason: primary validated frozen eval size had crossed `100`, and a formal gap report did not exist yet

### Case count

- before: `112`
- after: `114`
- delta: `+2`

### New case mix

- `2` hard / negative / ambiguous cases
- `2` regression-style cases
- added explicit regression coverage for:
  - parser-limit current-supplement duplicate miss
  - parser-limit avoid-title over-recommendation

### Metric delta

| metric | before | after |
| --- | --- | --- |
| `recommendation_coverage_pct` | `100.0` | `100.0` |
| `efficacy_improvement_pp` | `9.94784689765133` | `9.94784689765133` |
| `next_action_accuracy_pct` | `100.0` | `100.0` |
| `explanation_quality_accuracy_pct` | `100.0` | `100.0` |
| `safety_reference_accuracy_pct` | `100.0` | `100.0` |
| `adverse_event_count_yearly` | `0.0` | `0.0` |
| `sensor_genetic_integration_rate_pct` | `32.903225806451616` | `32.903225806451616` |

### Main output

- added `docs/02_eval/05_baseline_gap_report.md`
- documented category distribution, next-action distribution, modality bottlenecks,
  top-10 failure buckets, and zero-count checked buckets
- tied the report to new regression cases `eval-113` and `eval-114`

## 2026-03-08 loop 6

- Selected task: `free-text product title parser improvement`
- Reason: `case_count >= 100`, gap report existed, and the chosen runtime bucket was
  long-title parser miss on current-supplement / avoid canonicalization

### Case count

- before: `114`
- after: `116`
- delta: `+2`

### New case mix

- `2` hard / negative / ambiguous cases
- `2` regression-style cases
- added explicit regression coverage for:
  - long CoQ10 current-supplement title canonicalization
  - long magnesium avoid-title canonicalization

### Metric delta

| metric | before | after |
| --- | --- | --- |
| `recommendation_coverage_pct` | `100.0` | `100.0` |
| `efficacy_improvement_pp` | `9.94784689765133` | `9.94784689765133` |
| `next_action_accuracy_pct` | `100.0` | `100.0` |
| `explanation_quality_accuracy_pct` | `100.0` | `100.0` |
| `safety_reference_accuracy_pct` | `100.0` | `100.0` |
| `adverse_event_count_yearly` | `0.0` | `0.0` |
| `sensor_genetic_integration_rate_pct` | `32.903225806451616` | `32.903225806451616` |

### Bucket impact

- `parser_miss_current_supplement_long_title`: `8 -> 0`
- `parser_miss_avoid_long_title`: `7 -> 0`
- remaining bottleneck modality: `genetic = 7.352941176470588%`
- second bottleneck modality: `cgm = 16.666666666666668%`

## 2026-03-08 loop 7

- Selected task: `genetic deterministic handling improvement`
- Reason: `case_count >= 100`, gap report existed, and the chosen runtime bucket was
  `genetic`

### Case count

- before: `116`
- after: `118`
- delta: `+2`

### New case mix

- `2` hard / negative / ambiguous cases
- `2` regression-style cases
- added explicit regression coverage for:
  - general wellness genetic uplift (`eval-117`)
  - heart-health genetic uplift (`eval-118`)

### Metric delta

| metric | before | after |
| --- | --- | --- |
| `recommendation_coverage_pct` | `100.0` | `100.0` |
| `efficacy_improvement_pp` | `9.94784689765133` | `9.94784689765133` |
| `next_action_accuracy_pct` | `100.0` | `100.0` |
| `explanation_quality_accuracy_pct` | `100.0` | `100.0` |
| `safety_reference_accuracy_pct` | `100.0` | `100.0` |
| `adverse_event_count_yearly` | `0.0` | `0.0` |
| `sensor_genetic_integration_rate_pct` | `32.903225806451616` | `32.48407643312102` |

### Bucket impact

- deterministic ranking now changes under genetic context for:
  - `general_wellness -> vitamin_d3`
  - `heart_health -> omega3`
- aligned older genetic-context cases `eval-034`, `eval-049`, `eval-109`
- remaining bottleneck modality: `genetic = 7.142857142857143%`
- second bottleneck modality: `cgm = 16.666666666666668%`

## Assumptions

- `sensor_genetic_integration_rate_pct` is still a dataset-observation proxy.
- The primary frozen eval is larger and harder, but it is still not a production KPI gate.
