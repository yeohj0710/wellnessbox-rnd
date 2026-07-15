# Knowledge Evidence Lineage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist the existing reference artifact as source, parsed span, normalized claim, rule, and recommendation-result lineage while retaining source type, license, effective date, and retirement date.

**Architecture:** Reuse `reference_knowledge_base_v1.json`, `runtime_knowledge_db_v1.json`, `EvidenceRegistry`, and the OP-021/022 `InterimStore`; do not create a second knowledge system. Schema version 5 adds normalized claim/rule/link tables and execution-result lineage. The actual `/v1/recommend` route synchronizes the versioned local knowledge artifact before it atomically records its execution, and the internal trace endpoint returns only the structured lineage needed for audit.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLite, pytest

---

### Task 1: Freeze source metadata and migration behavior

**Files:**
- Modify: `src/wellnessbox_rnd/ingestion/reference_ingestion.py`
- Modify: `src/wellnessbox_rnd/knowledge/runtime_db.py`
- Modify: `src/wellnessbox_rnd/interim/store.py`
- Modify: `data/raw_references/master_context_action_space.md`
- Modify: `data/raw_references/master_context_citation_structure.md`
- Modify: `data/raw_references/supplement_warfarin_interaction.md`
- Modify: `data/knowledge/reference_knowledge_base_v1.json`
- Modify: `data/knowledge/runtime_knowledge_db_v1.json`
- Modify: `tests/test_reference_ingestion.py`
- Modify: `tests/test_runtime_knowledge_db.py`
- Modify: `tests/test_interim_store.py`

- [x] **Step 1: Write failing metadata and schema migration tests**

Assert that every canonical reference has `source_type`, `license_status`, `effective_at`, and optional `retired_at`. Build a schema-v4 fixture with one source and passage, migrate it, and assert schema version 5, preserved rows, parsed-span columns, and the four new lineage tables.

- [x] **Step 2: Run the tests and confirm the missing metadata/schema failures**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_reference_ingestion.py tests/test_runtime_knowledge_db.py tests/test_interim_store.py -q`

Expected: FAIL because reference metadata and schema-v5 lineage tables do not exist.

- [x] **Step 3: Extend the canonical reference envelope**

Add these required fields to `ReferenceMetadata` and `KnowledgeReferenceRecord`:

```python
license_status: str
effective_at: str
retired_at: str | None = None
```

The three local raw references use `APPROVED_INTERNAL` and `2026-03-10T00:00:00Z`; this is the local artifact effective date, not an external publication date. Update both tracked knowledge JSON artifacts with the same fields.

- [x] **Step 4: Add schema-v5 lineage tables and passage span columns**

Add `page_or_section`, `line_start`, `line_end`, and `metadata_json` to `evidence_passages`. Add:

```sql
knowledge_claims(claim_id, evidence_id, normalized_claim_type, claim_text,
                 ingredient_keys_json, medication_keys_json, domain_keys_json,
                 checksum, effective_at, retired_at, data_class)
knowledge_rules(rule_id, rule_type, severity, source_kind, predicate_json,
                action_json, checksum, valid_from, valid_to, status, data_class)
claim_rule_links(claim_id, rule_id)
execution_knowledge_lineage(lineage_id, execution_id, event_id, output_type,
                            output_key, rule_id, claim_id, evidence_id,
                            source_id, created_at)
```

Migrate existing schema-v4 passages in place and retain their payloads.

- [x] **Step 5: Run the metadata and migration tests**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_reference_ingestion.py tests/test_runtime_knowledge_db.py tests/test_interim_store.py -q`

Expected: PASS.

### Task 2: Synchronize the existing knowledge artifact into the Data Lake

**Files:**
- Create: `src/wellnessbox_rnd/interim/knowledge_lineage.py`
- Modify: `src/wellnessbox_rnd/interim/evidence.py`
- Create: `tests/test_knowledge_lineage.py`

- [x] **Step 1: Write the failing synchronization test**

Synchronize the real `reference_knowledge_base_v1.json` twice and assert idempotent counts of three sources, five parsed passages, five claims, five rules, and five claim-rule links. Query `KB-SAFETY-ANTICOAG-001` and prove this chain:

```text
REF-KNOWLEDGE-ANTICOAG-001
  -> parsed line span 13..33
  -> CLM-KNOWLEDGE-ANTICOAG-001
  -> KB-SAFETY-ANTICOAG-001
```

Assert the source type, `APPROVED_INTERNAL` license, effective date, null retirement date, and source-content checksum.

- [x] **Step 2: Run the test and confirm the synchronizer is absent**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_knowledge_lineage.py -q`

Expected: FAIL because `KnowledgeLineageRegistry` is not defined.

- [x] **Step 3: Preserve parsed-span identity in EvidenceRegistry**

Extend `add_passage` with optional `evidence_id`, `page_or_section`, `line_start`, `line_end`, and metadata fields. Include `source_tier`, license, lifecycle dates, and raw-content checksum metadata in source change detection. Existing callers remain source-compatible.

- [x] **Step 4: Implement one idempotent artifact synchronizer**

`KnowledgeLineageRegistry.sync_reference_artifact()` validates the canonical artifact, registers each parsed local source with its raw-file hash, retains the upstream reference URI separately, persists one parsed span per claim, upserts claims and rules, and writes direct claim-rule links. A changed source remains quarantined through the existing EvidenceRegistry rule.

- [x] **Step 5: Run the synchronization tests**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_evidence.py tests/test_knowledge_lineage.py -q`

Expected: PASS.

### Task 3: Connect actual recommendation results to knowledge lineage

**Files:**
- Modify: `src/wellnessbox_rnd/interim/knowledge_lineage.py`
- Modify: `src/wellnessbox_rnd/interim/data_lake.py`
- Modify: `apps/inference_api/routes/recommend.py`
- Modify: `tests/test_knowledge_lineage.py`
- Modify: `tests/test_inference_api.py`
- Modify: `tests/test_interim_api.py`

- [x] **Step 1: Write a failing actual-route lineage test**

Post a consent-authorized warfarin plus glucosamine request to `/v1/recommend`, retrieve `/v1/interim/executions/{execution_id}`, and assert that the final decision and safety event both link to `KB-SAFETY-ANTICOAG-001`, `CLM-KNOWLEDGE-ANTICOAG-001`, its parsed span, and `REF-KNOWLEDGE-ANTICOAG-001`.

- [x] **Step 2: Run the API test and confirm lineage is missing**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_inference_api.py tests/test_interim_api.py -q`

Expected: FAIL because the route does not synchronize or persist knowledge lineage.

- [x] **Step 3: Synchronize before persistent recommendation execution**

The recommendation route opens one `InterimStore`, synchronizes the versioned local artifact, and passes the same store to `ExecutionLedger`. Do not claim production ingestion or fetch external content.

- [x] **Step 4: Persist lineage in the execution transaction**

Capture the recommendation and safety event IDs. For every structured `RuleReference` with claim IDs, insert one safety-rule lineage row and one final-decision lineage row. Link recommendation items to matching ingredient claims when such claims exist. Skip result lineage when storage consent permits only metadata.

- [x] **Step 5: Expose structured lineage through the existing trace**

Add `knowledge_lineage` to `ExecutionTrace`. Return the source title/type/license/lifecycle, parsed page and line span, claim, rule, event, and output key. Do not return raw source documents by default.

- [x] **Step 6: Run the route and lineage tests**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_knowledge_lineage.py tests/test_data_lake_lineage.py tests/test_inference_api.py tests/test_interim_api.py -q`

Expected: PASS.

### Task 4: Produce local evidence and register honest completion stages

**Files:**
- Create: `scripts/run_knowledge_lineage_smoke.py`
- Create: `data/original_plan/evidence/op023_op024_knowledge_lineage_smoke_v1.json`
- Modify: `scripts/run_data_lake_lineage_smoke.py`
- Modify: `data/original_plan/evidence/op021_op022_data_lake_lineage_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/plans/2026-07-15-original-plan-completion-program.md`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_completion_report.py`

- [x] **Step 1: Add a repeatable local knowledge-lineage smoke**

Use a temporary SQLite database and the actual FastAPI routes. The runner must fail unless the canonical chain, lifecycle metadata, common execution ID, final decision, and safety result are connected after reopening the database.

- [x] **Step 2: Run the smoke and capture deterministic aggregate evidence**

Run: `.venv-interim\Scripts\python.exe scripts/run_knowledge_lineage_smoke.py`

Expected: `status=passed`, `case_count=1`, `source_count=3`, `claim_count=5`, `rule_count=5`, and two execution lineage output types.

- [x] **Step 3: Claim only IMPLEMENTED**

OP-023 and OP-024 require `OPERATED`. Register them as `IMPLEMENTED`, because a local `TestClient` plus temporary SQLite does not prove a real two-process round trip or production re-query. They must therefore appear as partial, not complete.

- [x] **Step 4: Regenerate and audit the completion report**

Run: `.venv-interim\Scripts\python.exe scripts/build_original_plan_completion_report.py`

Run: `.venv-interim\Scripts\python.exe scripts/audit_original_plan_requirements.py`

Expected: audit PASS; valid claims 26; complete 22; partial 4; pending 93; external 1.

### Task 5: Run guardrails and publish exact files

**Files:**
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [x] **Step 1: Run focused and broad R&D checks**

Run: `.venv-interim\Scripts\python.exe -m ruff check .`

Run the focused knowledge, Data Lake, API, and governance tests. Run the full suite and compare failures with the current baseline of 74 missing report artifacts plus four CGM geometry assertions.

- [x] **Step 2: Prove frozen-eval parity**

Run the official 256-case frozen evaluation and compare all seven summary metrics with the pre-loop report. Every delta must be zero.

- [x] **Step 3: Update the required handoff documents**

Record the chosen stage/task, evidence path and case count, exact validation results, frozen deltas, no replay/slice change, five bottlenecks, and three next loops.

- [ ] **Step 4: Review and publish only owned files**

Confirm the two untracked user plan files remain unstaged. Commit the R&D files to `main`, push to `origin/main`, and wait for the Original plan evidence workflow. Do not deploy or claim `INTEGRATED`/`OPERATED`.
