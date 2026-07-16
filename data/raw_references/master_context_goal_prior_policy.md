---
reference_id: REF-MC-GOAL-PRIOR-001
source_title: WellnessBox R&D Master Context
source_type: master_context
page_or_section: Sections 13.3 and 18.1 - candidate generation and domain priors
reference_uri: docs/context/master_context.md
license_status: APPROVED_INTERNAL
effective_at: 2026-07-16T00:00:00Z
parsed_source_uri: data/raw_references/master_context_goal_prior_policy.md
---
The master context requires goal-specific candidate tables followed by a base prior score before safety filtering and optimization. The prior is a deterministic candidate-ordering policy, not an efficacy probability or treatment claim. Clinical evidence metadata must therefore qualify the policy without changing its meaning.
```json
{
  "claim_id": "CLM-MC-GOAL-PRIOR-POLICY-001",
  "claim_text": "Each managed catalog ingredient-goal pair receives a versioned candidate-ordering prior before safety filtering; the prior is an internal selection policy and not a clinical efficacy probability.",
  "normalized_claim_type": "candidate_prior_policy",
  "ingredient_keys": [],
  "domain_keys": ["candidate_prior_policy"]
}
```
