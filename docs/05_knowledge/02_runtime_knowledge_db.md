# Runtime Knowledge DB Wiring

## Loop choice

- chosen stage: `P1`
- chosen task: `validated runtime knowledge DB wiring into deterministic safety`

## What changed

- added runtime knowledge DB schema and loader:
  - `C:/dev/wellnessbox-rnd/src/wellnessbox_rnd/knowledge/runtime_db.py`
- added runtime DB build script:
  - `C:/dev/wellnessbox-rnd/scripts/build_runtime_knowledge_db.py`
- added sample query script:
  - `C:/dev/wellnessbox-rnd/scripts/query_runtime_knowledge.py`
- added runtime knowledge coverage tests:
  - `C:/dev/wellnessbox-rnd/tests/test_runtime_knowledge_db.py`

## Runtime DB tables

- `ingredients`
- `ingredient_aliases`
- `medications`
- `conditions`
- `interaction_rules`
- `contraindication_rules`
- `dose_limits`
- `ingredient_domain_scores`
- `references`
- `reference_spans`
- `workflow_policies`

## Deterministic safety boundary

- runtime does not read `data/raw_references/`
- runtime reads only structured artifacts:
  - `C:/dev/wellnessbox-rnd/data/knowledge/reference_knowledge_base_v1.json`
  - `C:/dev/wellnessbox-rnd/data/knowledge/runtime_knowledge_db_v1.json`
- `reference_knowledge_base_v1.json` is schema-validated before runtime DB build or load
- structured knowledge rules add citation-backed `rule_refs` without weakening legacy deterministic guards

## Current runtime usage

- knowledge-derived interaction rules are now available in deterministic safety
- current runtime match path:
  - medication set intersects a structured interaction rule
  - current supplement ingredients intersect the same structured rule
  - safety returns blocker/warning plus linked `reference_ids`, `claim_ids`, and citation excerpts

## Sample query

```bash
python scripts/query_runtime_knowledge.py --medication warfarin --current-ingredient glucosamine
```

Expected result:

- `KB-SAFETY-ANTICOAG-001` appears in `rule_refs`
- `REF-KNOWLEDGE-ANTICOAG-001` appears in `reference_ids`
- `CLM-KNOWLEDGE-ANTICOAG-001` appears in `claim_ids`
- runtime safety status becomes `blocked`
- next action becomes `trigger_safety_recheck`
