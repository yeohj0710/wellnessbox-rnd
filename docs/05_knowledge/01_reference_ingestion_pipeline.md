# Reference Ingestion Pipeline

## Loop choice

- chosen stage: `P1`
- chosen task: `raw docs folder -> parsed claims/rules/citations ingestion pipeline`

## Why this connects to the autonomous agent target

- the no-human closed-loop agent still needs citation-backed safety and policy evidence
- `master_context` requires structured citations, linked `rule_id` / `claim_id` / `reference_id`, and safety outputs that carry `reference_ids`
- a deterministic ingestion layer is the narrowest step that turns static notes into machine-validated knowledge artifacts

## What was added

- raw markdown reference folder:
  - `C:/dev/wellnessbox-rnd/data/raw_references`
- deterministic ingestion module:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/ingestion/reference_ingestion.py`
- ingestion script:
  - `C:/dev/wellnessbox-rnd/scripts/ingest_raw_references.py`
- structured outputs:
  - `C:/dev/wellnessbox-rnd/data/parsed_references/reference_claims_v1.jsonl`
  - `C:/dev/wellnessbox-rnd/data/knowledge/reference_knowledge_base_v1.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/reference_ingestion_v1_summary.json`
  - `C:/dev/wellnessbox-rnd/artifacts/reports/reference_ingestion_v1_summary.md`

## Raw doc format

- markdown frontmatter provides:
  - `reference_id`
  - `source_title`
  - `source_type`
  - `page_or_section`
  - `reference_uri`
- each raw claim is a fenced JSON block
- each claim may include:
  - `claim_id`
  - `claim_text`
  - `normalized_claim_type`
  - `rule_candidate`
  - `ingredient_keys`
  - `medication_keys`
  - `domain_keys`

## Ingestion outputs

- parsed claim with:
  - reference metadata
  - normalized claim type
  - ingredient/domain/medication keys
  - citation span line numbers
  - citation excerpt
- rule candidate with:
  - `rule_id`
  - `rule_type`
  - `severity`
  - normalized `if` / `then` clauses
  - linked `reference_id`
  - linked `claim_id`
- ingredient-domain evidence edges grouped by:
  - `ingredient_key`
  - `domain_key`
  - `claim_ids`
  - `reference_ids`
  - `medication_keys`

## Safety and determinism boundary

- GPT wrapper was not used
- ingestion is deterministic and schema-validated
- this loop did not change runtime recommendation logic
- safety rules remain upstream of learned ranking and simulation policy

## Sample artifact summary

- `reference_count = 3`
- `claim_count = 5`
- `rule_candidate_count = 5`
- `ingredient_domain_evidence_count = 4`
- sample extracted safety rule:
  - `KB-SAFETY-ANTICOAG-001`
- sample extracted ingredient evidence:
  - `glucosamine -> drug_interaction`
  - `chondroitin -> bleeding_risk`

## Next recommended work

1. expand structured reference coverage so more interaction, contraindication, and dose-limit rows enter the runtime knowledge DB
2. train a `P3` policy model on richer synthetic system-owned action labels
3. extend closed-loop simulation to cohort-sliced batch replay with learned-vs-deterministic comparison
