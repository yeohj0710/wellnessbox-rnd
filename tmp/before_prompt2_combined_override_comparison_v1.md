# combined override comparison v1

- dataset_path: `data\synthetic\synthetic_longitudinal_v4.jsonl`
- model_artifact_path: `artifacts/models/effect_model_v3.json`
- policy_model_artifact_path: `artifacts/models/policy_model_v1_uniform.json`

## Deltas
- `policy_effect_override_applied_count_delta`: `-325`
- `low_risk_monitor_only_delta`: `-1`
- `low_risk_re_optimize_delta`: `0`
- `cgm_monitor_only_delta`: `-3`
- `cgm_re_optimize_delta`: `0`
- `low_risk_disagreement_delta`: `-22`
- `cgm_disagreement_delta`: `-14`

## Override On
- final_policy_action_counts: `{'ask_targeted_followup': 21, 'continue_plan': 62, 'monitor_only': 3, 'trigger_safety_recheck': 10}`
- low_risk_final_action_distribution: `{'continue_plan': 62, 'monitor_only': 3}`
- cgm_final_action_distribution: `{'ask_targeted_followup': 10, 'continue_plan': 10, 'monitor_only': 3, 'trigger_safety_recheck': 10}`
- policy_effect_override_applied_count: `325`
- low_risk_disagreement_count: `82`
- cgm_disagreement_count: `14`

## Override Off
- final_policy_action_counts: `{'ask_targeted_followup': 21, 'continue_plan': 63, 'monitor_only': 2, 'trigger_safety_recheck': 10}`
- low_risk_final_action_distribution: `{'continue_plan': 63, 'monitor_only': 2}`
- cgm_final_action_distribution: `{'ask_targeted_followup': 10, 'continue_plan': 13, 'trigger_safety_recheck': 10}`
- policy_effect_override_applied_count: `0`
- low_risk_disagreement_count: `60`
- cgm_disagreement_count: `0`
