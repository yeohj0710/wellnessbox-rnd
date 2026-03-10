---
reference_id: REF-MC-CITATION-001
source_title: WellnessBox R&D Master Context
source_type: master_context
page_or_section: 17.4 citation structure
reference_uri: docs/context/master_context.md
---

This sample reference normalizes citation requirements from the master context into a deterministic raw document.
Structured citations need stable identifiers and typed fields so downstream safety and explanation modules can validate them.

```json
{
  "claim_id": "CLM-MC-CITATION-001",
  "claim_text": "Safety engine outputs must always carry reference_ids so the closed-loop agent stays citation-backed.",
  "normalized_claim_type": "citation_requirement",
  "domain_keys": ["safety_engine", "citations"],
  "rule_candidate": {
    "rule_id": "KB-CITE-001",
    "rule_type": "require_reference_ids",
    "severity": "warning",
    "if": {
      "component": ["safety_engine"]
    },
    "then": {
      "require_fields": ["reference_ids"]
    }
  }
}
```

The canonical citation payload also needs a stable structure instead of free-text retrieval output.
That structure is what lets rule ids, claim ids, and references stay connected across ingestion and runtime explanation.

```json
{
  "claim_id": "CLM-MC-CITATION-002",
  "claim_text": "Structured citations should include ref_id, source_title, source_type, page_or_section, claim_text, and normalized_claim_type.",
  "normalized_claim_type": "citation_schema",
  "domain_keys": ["citations", "knowledge_base"],
  "rule_candidate": {
    "rule_id": "KB-CITE-002",
    "rule_type": "enforce_citation_schema",
    "severity": "warning",
    "if": {
      "component": ["reference_ingestion"]
    },
    "then": {
      "require_fields": [
        "ref_id",
        "source_title",
        "source_type",
        "page_or_section",
        "claim_text",
        "normalized_claim_type"
      ]
    }
  }
}
```
