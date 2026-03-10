---
reference_id: REF-KNOWLEDGE-ANTICOAG-001
source_title: Supplement Interaction Notes
source_type: interaction_reference
page_or_section: glucosamine chondroitin and anticoagulants
reference_uri: data/knowledge/supplements/supplement_overdose_and_drug_interactions_expert.md
---

This sample reference captures the anticoagulant interaction note already present in the local supplement knowledge files.
Glucosamine and chondroitin should be treated as a bleeding-risk interaction when warfarin or Coumadin is present.

```json
{
  "claim_id": "CLM-KNOWLEDGE-ANTICOAG-001",
  "claim_text": "Glucosamine or chondroitin used with warfarin or Coumadin can increase anticoagulant effect and bleeding risk.",
  "normalized_claim_type": "drug_interaction",
  "ingredient_keys": ["glucosamine", "chondroitin"],
  "medication_keys": ["warfarin", "Coumadin"],
  "domain_keys": ["drug_interaction", "bleeding_risk"],
  "rule_candidate": {
    "rule_id": "KB-SAFETY-ANTICOAG-001",
    "rule_type": "block_anticoagulant_interaction",
    "severity": "blocker",
    "if": {
      "any_medications": ["warfarin", "Coumadin"],
      "any_ingredients": ["glucosamine", "chondroitin"]
    },
    "then": {
      "next_action": "blocked",
      "reason_code": "anticoagulant_interaction"
    }
  }
}
```
