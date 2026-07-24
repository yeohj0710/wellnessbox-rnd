# eval report comparison

- baseline_report_path: etc/final_cycle/pre_eval/eval_report.json
- candidate_report_path: artifacts\reports\eval_report.json
- baseline_case_count: 256
- candidate_case_count: 256
- case_count_delta: 0.0
- metric_count: 7
- nonzero_metric_delta_count: 0
- pass_changed_count: 0

## metric deltas

| metric | baseline | candidate | delta | baseline_passed | candidate_passed |
| --- | --- | --- | --- | --- | --- |
| adverse_event_count_yearly | 0.0 | 0.0 | 0.0 | True | True |
| efficacy_improvement_pp | 9.90291632090153 | 9.90291632090153 | 0.0 | True | True |
| explanation_quality_accuracy_pct | 99.47916666666667 | 99.47916666666667 | 0.0 | True | True |
| next_action_accuracy_pct | 99.21875 | 99.21875 | 0.0 | True | True |
| recommendation_coverage_pct | 100.0 | 100.0 | 0.0 | True | True |
| safety_reference_accuracy_pct | 99.86979166666667 | 99.86979166666667 | 0.0 | True | True |
| sensor_genetic_integration_rate_pct | 90.40247678018576 | 90.40247678018576 | 0.0 | True | True |

## weakest slice delta

- both_available: True
- baseline_overall_category: safety_blocked
- candidate_overall_category: safety_blocked
- overall_category_changed: False

| metric | baseline_category | candidate_category | changed |
| --- | --- | --- | --- |
| adverse_event_count_yearly | bone_joint | bone_joint | False |
| efficacy_improvement_pp | safety_warning | safety_warning | False |
| explanation_quality_accuracy_pct | safety_blocked | safety_blocked | False |
| next_action_accuracy_pct | safety_blocked | safety_blocked | False |
| recommendation_coverage_pct | bone_joint | bone_joint | False |
| safety_reference_accuracy_pct | safety_blocked | safety_blocked | False |
| sensor_genetic_integration_rate_pct | free_text_alias | free_text_alias | False |
