---
reference_id: REF-MC-CANDIDATE-SIGNAL-001
source_title: Master context candidate signal scoring policy
source_type: master_context
page_or_section: Sections 6.9, 13.3, and 18.2
reference_uri: docs/context/master_context.md
license_status: APPROVED_INTERNAL
effective_at: 2026-07-16T00:00:00Z
parsed_source_uri: data/raw_references/master_context_candidate_signal_scoring.md
---
The master context requires candidate generation to use symptoms, lifestyle, dietary and laboratory context after safety filtering. It also lists bounded genetic adjustment directions. Candidate points are deterministic ordering policy, not a diagnosis, treatment target, dose recommendation, or efficacy probability.
```json
{
  "claim_id": "CLM-MC-CANDIDATE-SIGNAL-POLICY-001",
  "claim_text": "Candidate scoring may use normalized symptom, laboratory, lifestyle, dietary, wearable, CGM, and genetic context after safety filtering; the resulting points are ordering policy rather than clinical efficacy probabilities.",
  "normalized_claim_type": "candidate_signal_policy",
  "ingredient_keys": [],
  "domain_keys": ["candidate_signal_policy"]
}
```
```json
{
  "claim_id": "CLM-MC-CANDIDATE-SIGNAL-CYP1A2-001",
  "claim_text": "The master-context prototype increases L-theanine priority for a declared CYP1A2 slow-metabolizer tag, without treating the tag as a diagnosis or efficacy guarantee.",
  "normalized_claim_type": "genetic_candidate_signal_policy",
  "ingredient_keys": ["l_theanine"],
  "domain_keys": ["sleep_support", "stress_support"]
}
```
```json
{
  "claim_id": "CLM-MC-CANDIDATE-SIGNAL-LPL-001",
  "claim_text": "The master-context prototype increases omega-3 priority for a declared adverse LPL triglyceride-risk tag, without treating the tag as a diagnosis or efficacy guarantee.",
  "normalized_claim_type": "genetic_candidate_signal_policy",
  "ingredient_keys": ["omega3"],
  "domain_keys": ["heart_health"]
}
```
