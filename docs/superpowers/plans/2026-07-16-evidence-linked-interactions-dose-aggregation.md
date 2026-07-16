# Evidence-Linked Interactions and Dose Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete OP-035 and OP-036 by attaching stable evidence IDs and citations to every active drug-ingredient interaction rule and by returning explicit per-ingredient, cross-product daily-dose aggregates.

**Architecture:** Extend the existing raw-reference ingestion, runtime knowledge database, normalized request, and deterministic safety service. Do not create another interaction engine or dose calculator. The current supplement-dose extraction remains the single calculation path; the safety response exposes its totals, product coverage, and cross-product duplicate state so tests and downstream callers can verify the calculation directly.

**Tech Stack:** Python 3.12, Pydantic 2, FastAPI contracts, JSON rule DSL, pytest, Ruff

---

### Task 1: Lock the interaction evidence contract with failing tests

**Files:**
- Modify: `tests/test_runtime_knowledge_db.py`
- Modify: `tests/test_medication_supplement_input_contracts.py`
- Modify: `tests/test_interim_safety.py`

- [ ] **Step 1: Require every active interaction rule to carry valid evidence IDs**

```python
def test_every_interaction_rule_is_evidence_linked() -> None:
    runtime_db = build_runtime_knowledge_db()
    assert all(rule.reference_ids for rule in runtime_db.interaction_rules)
    assert all(rule.claim_ids for rule in runtime_db.interaction_rules)
    assert validate_runtime_knowledge_db(runtime_db) == []
```

- [ ] **Step 2: Require the warfarin-omega3 decision to return its exact citation**

```python
summary = assess_safety(normalize_request(warfarin_request))
rule = next(item for item in summary.rule_refs if item.rule_id == "SAFETY-ANTICOAG-001")
assert rule.reference_ids == ["REF-NIH-ODS-OMEGA3-001"]
assert rule.claim_ids == ["CLM-NIH-ODS-OMEGA3-WARFARIN-001"]
assert rule.citations[0].reference_id == "REF-NIH-ODS-OMEGA3-001"
```

- [ ] **Step 3: Require the replay safety finding to preserve the same IDs**

```python
decision = evaluate_safety({"medications": ["warfarin"], "ingredients": ["omega3"]})
finding = next(item for item in decision.findings if item.rule_id == "SAFE-DDI-001")
assert finding.reference_ids == ("REF-NIH-ODS-OMEGA3-001",)
assert finding.claim_ids == ("CLM-NIH-ODS-OMEGA3-WARFARIN-001",)
```

- [ ] **Step 4: Run the focused tests and confirm that the new assertions fail**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_runtime_knowledge_db.py tests/test_medication_supplement_input_contracts.py tests/test_interim_safety.py -q`

Expected: FAIL because the deterministic interaction rule and replay finding do not yet expose reference and claim IDs.

### Task 2: Ingest the authoritative omega-3/warfarin source and link the rule

**Files:**
- Create: `data/raw_references/nih_ods_omega3_warfarin.md`
- Modify: `data/rules/safety_rules.json`
- Modify: `src/wellnessbox_rnd/domain/models.py`
- Modify: `src/wellnessbox_rnd/knowledge/runtime_db.py`
- Modify: `src/wellnessbox_rnd/safety/service.py`
- Modify: `src/wellnessbox_rnd/interim/safety.py`
- Regenerate: `data/parsed_references/reference_claims_v1.jsonl`
- Regenerate: `data/knowledge/reference_knowledge_base_v1.json`
- Regenerate: `data/knowledge/runtime_knowledge_db_v1.json`
- Regenerate: `artifacts/reports/reference_ingestion_v1_summary.json`
- Regenerate: `artifacts/reports/reference_ingestion_v1_summary.md`

- [ ] **Step 1: Add the exact NIH ODS source metadata and bounded claim**

```yaml
reference_id: REF-NIH-ODS-OMEGA3-001
source_type: government_health_reference
reference_uri: https://ods.od.nih.gov/factsheets/Omega3FattyAcids-HealthProfessional/
license_status: PUBLIC_GOVERNMENT
```

The parsed claim must state only that fish oil may prolong clotting time with warfarin and that anticoagulated patients should be monitored. The deterministic policy may conservatively exclude omega-3 candidates, but the evidence text must not claim that the source requires universal exclusion.

- [ ] **Step 2: Require stable IDs on data-defined medication rules**

```python
class MedicationInteractionRule(BaseModel):
    medications: list[str] = Field(min_length=1)
    excluded_ingredients: list[str] = Field(min_length=1)
    reference_ids: list[str] = Field(min_length=1)
    claim_ids: list[str] = Field(min_length=1)
    metadata: SafetyRuleMetadata
```

- [ ] **Step 3: Materialize deterministic rules as `evidence_linked_policy` records**

```python
InteractionRuleRecord(
    source_kind="evidence_linked_policy",
    reference_ids=raw_rule["reference_ids"],
    claim_ids=raw_rule["claim_ids"],
    ...,
)
```

`validate_runtime_knowledge_db` must reject both `knowledge_artifact` and `evidence_linked_policy` interaction records when either ID collection is empty or points outside the runtime reference tables.

- [ ] **Step 4: Build `RuleReference` from the runtime record**

```python
RuleReference(
    rule_id=interaction_rule.rule_id,
    source=interaction_rule.source_kind,
    reference_ids=interaction_rule.reference_ids,
    claim_ids=interaction_rule.claim_ids,
    citations=build_citations_for_rule(...),
)
```

- [ ] **Step 5: Preserve the IDs in the interim replay finding**

```python
SafetyFinding(
    rule_id="SAFE-DDI-001",
    category="drug_interaction",
    action="BLOCK",
    reason="anticoagulant_interaction",
    reference_ids=("REF-NIH-ODS-OMEGA3-001",),
    claim_ids=("CLM-NIH-ODS-OMEGA3-WARFARIN-001",),
)
```

- [ ] **Step 6: Regenerate reference and runtime artifacts**

Run: `.venv-interim/Scripts/python.exe scripts/ingest_raw_references.py`

Run: `.venv-interim/Scripts/python.exe -c "from pathlib import Path; from wellnessbox_rnd.knowledge.runtime_db import build_runtime_knowledge_db; Path('data/knowledge/runtime_knowledge_db_v1.json').write_text(build_runtime_knowledge_db().model_dump_json(indent=2), encoding='utf-8')"`

Expected: the new reference and claim IDs appear in both knowledge artifacts, and runtime validation returns no issues.

### Task 3: Expose cross-product ingredient and dose aggregation

**Files:**
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Modify: `src/wellnessbox_rnd/safety/service.py`
- Modify: `tests/test_medication_supplement_input_contracts.py`

- [ ] **Step 1: Add an explicit safety response record**

```python
class IngredientDoseAggregate(BaseModel):
    ingredient_key: str
    product_count: int = Field(ge=1)
    product_names: list[str] = Field(min_length=1)
    duplicate_across_products: bool
    total_daily_amount: float | None = Field(default=None, ge=0)
    unit: str | None = None
    dose_observation_count: int = Field(ge=0)
    dose_complete: bool
```

Add `duplicate_ingredient_keys` and `ingredient_dose_aggregates` to `SafetySummary` with empty-list defaults.

- [ ] **Step 2: Reuse the existing dose extraction for one aggregation pass**

For each normalized supplement occurrence, collect its canonical ingredient keys and its existing normalized dose observations. Aggregate totals by ingredient, count distinct product occurrences, retain sorted product names, and set `dose_complete` only when every contributing product occurrence has an observed dose for that ingredient.

- [ ] **Step 3: Make dose-limit checks consume the same aggregate records**

```python
aggregates = _build_ingredient_dose_aggregates(intake, runtime_knowledge_db)
for dose_limit, observed_amount in _find_triggered_dose_limits(
    aggregates, runtime_knowledge_db
):
    ...
```

This removes the second independent summation pass and guarantees that the returned total equals the amount compared with the structured limit.

- [ ] **Step 4: Prove complete, incomplete, duplicate, and single-product cases**

Tests must assert:

- two vitamin-D products produce `4400 IU`, `product_count=2`, and `duplicate_across_products=true`;
- two probiotic products with no dose still appear as a duplicate with `total_daily_amount=null`;
- one dosed and one undosed vitamin-D product produce a partial total with `dose_complete=false`;
- two ingredient lines inside one product do not set `duplicate_across_products=true`.

- [ ] **Step 5: Run the focused tests**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_runtime_knowledge_db.py tests/test_medication_supplement_input_contracts.py tests/test_interim_safety.py -q`

Expected: PASS.

### Task 4: Produce deterministic OP-035/036 evidence and completion claims

**Files:**
- Create: `scripts/run_interaction_dose_aggregation_smoke.py`
- Create: `data/original_plan/evidence/op035_op036_interaction_dose_aggregation_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Regenerate: `docs/original_plan/completion_status_v1.json`
- Regenerate: `docs/original_plan/COMPLETION_STATUS.md`

- [ ] **Step 1: Build a deterministic smoke with actual engine results**

The artifact must contain:

- warfarin plus omega-3 reference ID, claim ID, and citation;
- warfarin plus glucosamine knowledge-artifact reference and claim IDs;
- two-product `4400 IU` vitamin-D aggregate and triggered dose rule;
- duplicate probiotics with an unknown total;
- a partial vitamin-D aggregate marked `dose_complete=false`;
- `contains_health_identifiers=false`.

- [ ] **Step 2: Claim OP-035 and OP-036 only at `IMPLEMENTED`**

List exact implementation and test/evidence paths in the manifest. Do not claim service integration or production operation.

- [ ] **Step 3: Regenerate completion reports and enforce CI selection**

Run: `.venv-interim/Scripts/python.exe scripts/build_original_plan_completion_report.py`

Expected counts: claimed requirements `36`; complete `26`; partial `10`; pending `83`; external `1`; contradicted `0`.

### Task 5: Verify, review, publish, and hand off

**Files:**
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [ ] **Step 1: Run focused and CI-equivalent tests**

Run the three focused files from Task 3, then the exact `Original plan evidence` workflow pytest selection.

- [ ] **Step 2: Run deterministic and repository guardrails**

Run:

```powershell
.venv-interim\Scripts\python.exe -m ruff check .
.venv-interim\Scripts\python.exe scripts/audit_original_plan_requirements.py
.venv-interim\Scripts\python.exe scripts/build_original_plan_completion_report.py --check
.venv-interim\Scripts\python.exe scripts/run_interaction_dose_aggregation_smoke.py
git diff --check
```

- [ ] **Step 3: Verify frozen evaluation compatibility**

Run the official 256-case frozen evaluation and compare all seven current metrics with the previously committed report. Expected delta for every metric: `0`.

- [ ] **Step 4: Request an independent code review and resolve all Critical/Important findings**

Review scope: evidence accuracy, fail-closed validation, no double-counting, incomplete-dose semantics, backward-compatible response defaults, and manifest claim strength.

- [ ] **Step 5: Commit only loop-owned files and push `main`**

Commit message: `feat: link interactions and aggregate supplement doses`

- [ ] **Step 6: Verify the push-triggered `Original plan evidence` workflow succeeds**

Do not deploy WellnessBox or claim two-process production integration; this bounded loop changes only the R&D repository.
