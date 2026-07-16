---
reference_id: REF-NIH-ODS-B12-ENERGY-001
source_title: NIH Office of Dietary Supplements - Vitamin B12
source_type: government_health_reference
page_or_section: Energy and endurance
reference_uri: https://ods.od.nih.gov/factsheets/VitaminB12-HealthProfessional/
license_status: PUBLIC_GOVERNMENT
effective_at: 2024-03-26T00:00:00Z
parsed_source_uri: data/raw_references/nih_ods_vitamin_b12_energy.md
---
NIH ODS notes vitamin B12's role in energy metabolism but reports that supplementation does not appear to improve performance or endurance when vitamin B12 status is sufficient. This component-level evidence does not establish efficacy for a whole vitamin-B-complex product.
```json
{
  "claim_id": "CLM-NIH-ODS-B12-ENERGY-001",
  "claim_text": "Vitamin B12 has a role in energy metabolism, but supplementation does not appear to improve performance or endurance without a nutritional deficit; this does not establish whole B-complex efficacy.",
  "normalized_claim_type": "null_goal_evidence_without_deficiency",
  "ingredient_keys": ["vitamin_b_complex"],
  "domain_keys": ["energy_support"]
}
```
NIH ODS also identifies vegetarian and vegan dietary patterns as risk factors for vitamin B12 inadequacy because natural food sources are largely animal foods. This supports a bounded diet-context ordering term, not a diagnosis and not whole B-complex efficacy.
```json
{
  "claim_id": "CLM-NIH-ODS-B12-VEGETARIAN-001",
  "claim_text": "Vegetarian and vegan dietary patterns increase the risk of vitamin B12 inadequacy because natural food sources are largely animal foods; this does not establish whole B-complex efficacy.",
  "normalized_claim_type": "dietary_pattern_candidate_signal",
  "ingredient_keys": ["vitamin_b_complex"],
  "domain_keys": ["energy_support", "general_wellness"]
}
```
