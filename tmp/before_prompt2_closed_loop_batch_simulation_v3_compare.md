# closed loop batch simulation v1 compare

- scenario_set_id: `closed_loop_batch_simulation_v3_compare`
- dataset_path: `data\synthetic\synthetic_longitudinal_v4.jsonl`

## Mode Differences

| mode | final_state_diff_users | final_policy_diff_users | ranking_diff_users | trace_diff_users |
| --- | --- | --- | --- | --- |
| learned_effect_guarded | 0 | 0 | 16 | 65 |
| learned_policy_guarded | 0 | 2 | 0 | 11 |
| learned_effect_and_policy_guarded | 0 | 3 | 16 | 65 |

## deterministic_only

- scenario_count: `96`
- total_trace_steps: `356`
- average_trace_length: `3.708333`
- average_predicted_effect_proxy: `0.26325`
- adverse_event_count: `0`
- policy_guard_applied_count: `0`
- effect_guard_applied_count: `0`
- policy_effect_override_applied_count: `0`
- raw_policy_disagreement_count: `0`
- raw_ranking_disagreement_count: `0`
- deterministic_vs_learned_disagreement_count: `0`

### Final States
- `baseline_questionnaire_due`: `21`
- `followup_due`: `65`
- `safety_review`: `10`

### Final Actions
- `ask_targeted_followup`: `21`
- `continue_plan`: `65`
- `trigger_safety_recheck`: `10`

### Cohort Slices

| slice | users | avg_trace_length | avg_effect | adverse_events | disagreement | policy_guard | effect_guard |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cgm_users | 33 | 2.575758 | 0.200212 | 0 | 0 | 0 | 0 |
| genetic_users | 59 | 3.644068 | 0.259028 | 0 | 0 | 0 | 0 |
| low_risk_users | 65 | 5.0 | 0.285498 | 0 | 0 | 0 | 0 |
| high_risk_users | 31 | 1.0 | 0.03 | 0 | 0 | 0 | 0 |
| single_goal_users | 76 | 4.421053 | 0.277134 | 0 | 0 | 0 | 0 |
| multi_goal_users | 20 | 1.0 | 0.03 | 0 | 0 | 0 | 0 |

## learned_effect_guarded

- scenario_count: `96`
- total_trace_steps: `356`
- average_trace_length: `3.708333`
- average_predicted_effect_proxy: `0.245765`
- adverse_event_count: `0`
- policy_guard_applied_count: `0`
- effect_guard_applied_count: `20`
- policy_effect_override_applied_count: `0`
- raw_policy_disagreement_count: `0`
- raw_ranking_disagreement_count: `71`
- deterministic_vs_learned_disagreement_count: `80`
- note: learned effect changed candidate choice on a guarded low-risk subset

### Final States
- `baseline_questionnaire_due`: `21`
- `followup_due`: `65`
- `safety_review`: `10`

### Final Actions
- `ask_targeted_followup`: `21`
- `continue_plan`: `65`
- `trigger_safety_recheck`: `10`

### Cohort Slices

| slice | users | avg_trace_length | avg_effect | adverse_events | disagreement | policy_guard | effect_guard |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cgm_users | 33 | 2.575758 | 0.19905 | 0 | 6 | 0 | 20 |
| genetic_users | 59 | 3.644068 | 0.249028 | 0 | 14 | 0 | 20 |
| low_risk_users | 65 | 5.0 | 0.266346 | 0 | 80 | 0 | 0 |
| high_risk_users | 31 | 1.0 | 0.03 | 0 | 0 | 0 | 20 |
| single_goal_users | 76 | 4.421053 | 0.258608 | 0 | 80 | 0 | 0 |
| multi_goal_users | 20 | 1.0 | 0.03 | 0 | 0 | 0 | 20 |

## learned_policy_guarded

- scenario_count: `96`
- total_trace_steps: `356`
- average_trace_length: `3.708333`
- average_predicted_effect_proxy: `0.26325`
- adverse_event_count: `0`
- policy_guard_applied_count: `125`
- effect_guard_applied_count: `0`
- policy_effect_override_applied_count: `0`
- raw_policy_disagreement_count: `138`
- raw_ranking_disagreement_count: `0`
- deterministic_vs_learned_disagreement_count: `13`
- note: learned policy changed final action on some users without breaking the safety ceiling

### Final States
- `baseline_questionnaire_due`: `21`
- `followup_due`: `65`
- `safety_review`: `10`

### Final Actions
- `ask_targeted_followup`: `21`
- `continue_plan`: `63`
- `monitor_only`: `2`
- `trigger_safety_recheck`: `10`

### Cohort Slices

| slice | users | avg_trace_length | avg_effect | adverse_events | disagreement | policy_guard | effect_guard |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cgm_users | 33 | 2.575758 | 0.200212 | 0 | 0 | 46 | 0 |
| genetic_users | 59 | 3.644068 | 0.259028 | 0 | 9 | 82 | 0 |
| low_risk_users | 65 | 5.0 | 0.285498 | 0 | 13 | 94 | 0 |
| high_risk_users | 31 | 1.0 | 0.03 | 0 | 0 | 31 | 0 |
| single_goal_users | 76 | 4.421053 | 0.277134 | 0 | 13 | 105 | 0 |
| multi_goal_users | 20 | 1.0 | 0.03 | 0 | 0 | 20 | 0 |

## learned_effect_and_policy_guarded

- scenario_count: `96`
- total_trace_steps: `356`
- average_trace_length: `3.708333`
- average_predicted_effect_proxy: `0.245765`
- adverse_event_count: `0`
- policy_guard_applied_count: `127`
- effect_guard_applied_count: `20`
- policy_effect_override_applied_count: `325`
- raw_policy_disagreement_count: `153`
- raw_ranking_disagreement_count: `71`
- deterministic_vs_learned_disagreement_count: `82`
- note: learned effect changed candidate choice on a guarded low-risk subset; learned policy changed final action on some users without breaking the safety ceiling

### Final States
- `baseline_questionnaire_due`: `21`
- `followup_due`: `65`
- `safety_review`: `10`

### Final Actions
- `ask_targeted_followup`: `21`
- `continue_plan`: `62`
- `monitor_only`: `3`
- `trigger_safety_recheck`: `10`

### Cohort Slices

| slice | users | avg_trace_length | avg_effect | adverse_events | disagreement | policy_guard | effect_guard |
| --- | --- | --- | --- | --- | --- | --- | --- |
| cgm_users | 33 | 2.575758 | 0.19905 | 0 | 14 | 46 | 20 |
| genetic_users | 59 | 3.644068 | 0.249028 | 0 | 22 | 82 | 20 |
| low_risk_users | 65 | 5.0 | 0.266346 | 0 | 82 | 96 | 0 |
| high_risk_users | 31 | 1.0 | 0.03 | 0 | 0 | 31 | 20 |
| single_goal_users | 76 | 4.421053 | 0.258608 | 0 | 82 | 107 | 0 |
| multi_goal_users | 20 | 1.0 | 0.03 | 0 | 0 | 20 | 20 |

## Trace Samples
- `learned_effect_guarded` / `syn-v4-user-000`: `5` steps
- `learned_policy_guarded` / `syn-v4-user-002`: `5` steps
- `learned_effect_and_policy_guarded` / `syn-v4-user-000`: `5` steps
