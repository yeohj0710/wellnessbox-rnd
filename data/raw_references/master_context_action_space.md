---
reference_id: REF-MC-ACTION-001
source_title: WellnessBox R&D Master Context
source_type: master_context
page_or_section: autonomous closed-loop action policy
reference_uri: docs/context/master_context.md
---

This sample reference captures the no-human action space required for the autonomous closed-loop agent.
Runtime actions must remain system-owned so the state machine can continue without manual review or handoff semantics.

```json
{
  "claim_id": "CLM-MC-ACTION-001",
  "claim_text": "Runtime next_action must stay inside the system-owned action space and must not expose manual review or handoff actions.",
  "normalized_claim_type": "action_space_constraint",
  "domain_keys": ["policy", "action_space"],
  "rule_candidate": {
    "rule_id": "KB-ACTION-001",
    "rule_type": "enforce_system_owned_actions",
    "severity": "warning",
    "if": {
      "component": ["policy_engine"]
    },
    "then": {
      "allowed_actions": [
        "blocked",
        "collect_more_input",
        "start_plan",
        "continue_plan",
        "re_optimize",
        "reduce_or_stop",
        "monitor_only",
        "ask_targeted_followup",
        "trigger_safety_recheck"
      ]
    }
  }
}
```

When safety risk rises, the system still owns the control flow and should move into a safety recheck path rather than a human-review action.

```json
{
  "claim_id": "CLM-MC-ACTION-002",
  "claim_text": "High-risk safety paths should route to trigger_safety_recheck as a system action instead of a human-handoff action.",
  "normalized_claim_type": "safety_recheck_policy",
  "domain_keys": ["policy", "safety_recheck"],
  "rule_candidate": {
    "rule_id": "KB-ACTION-002",
    "rule_type": "map_high_risk_to_safety_recheck",
    "severity": "warning",
    "if": {
      "safety_status": ["needs_review"]
    },
    "then": {
      "next_action": "trigger_safety_recheck"
    }
  }
}
```
