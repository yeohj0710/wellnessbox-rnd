# Dose-Limit Fail-Closed and Rule Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete OP-037 and OP-038 by blocking dose-limit ingredients when the normalized daily dose is incomplete or non-convertible and by returning the applied rule version plus one timezone-aware safety application time.

**Architecture:** Extend the existing `IngredientDoseAggregate`, runtime knowledge records, and deterministic `assess_safety` path. The returned aggregate remains the only dose total used for upper-limit comparison. Capture one UTC application time at the safety-service boundary, inject a fixed time in deterministic smoke tests, and carry explicit integer versions from the existing safety rule data and knowledge artifact into every returned `RuleReference`.

**Tech Stack:** Python 3.12, Pydantic 2, FastAPI response contracts, JSON rule DSL, pytest, Ruff

**Execution outcome:** Implemented with one clarified boundary from PDF page 17 and full-regression evidence: an optional dose that was not supplied does not claim an upper-limit evaluation, while supplied partial, non-convertible, compound, ranged, or schedule-qualified evidence excludes the affected ingredient without inventing a total. Only a complete measured upper-limit violation blocks the whole recommendation.

---

### Task 1: Lock fail-closed and temporal response behavior with failing tests

**Files:**
- Modify: `tests/test_medication_supplement_input_contracts.py`
- Modify: `tests/test_runtime_knowledge_db.py`
- Modify: `tests/test_inference_api.py`

- [ ] **Step 1: Require supplied but incomplete dose evidence to apply the ingredient's existing dose-limit rule**

Add focused cases for an optional undosed vitamin-D control, a partially dosed cross-product vitamin-D regimen, and vitamin C expressed in incompatible `IU`. The undosed control must report `dose_input_count=0` without claiming an upper-limit rule. Each supplied-but-incomplete case must return `dose_complete=false`, exclude the ingredient, preserve the global recommendation status, and include the corresponding dose-limit rule with `application_reason="dose_evidence_incomplete"`.

```python
summary = assess_safety(normalize_request(request), applied_at=FIXED_APPLIED_AT)
rule = next(item for item in summary.rule_refs if item.rule_id == "SAFETY-DOSE-VITD3-001")
assert summary.status == RecommendationStatus.OK
assert "vitamin_d3" in summary.excluded_ingredients
assert rule.application_reason == "dose_evidence_incomplete"
```

- [ ] **Step 2: Preserve normalized upper-limit comparison for complete doses**

Add one `1 g + 1.2 g` vitamin-C case. The aggregate must be `2200 mg`, `dose_complete=true`, and the existing rule must use `application_reason="upper_limit_exceeded"`. Add a complete `1500 mg` control that does not return the dose-limit rule.

- [ ] **Step 3: Require explicit rule versions and one injected application time**

Call `assess_safety` with `datetime(2026, 7, 16, tzinfo=UTC)`. Assert `SafetySummary.applied_at` equals the injected value and every returned `RuleReference.rule_version` is a positive integer. Assert a naive datetime is rejected.

```python
fixed = datetime(2026, 7, 16, tzinfo=UTC)
summary = assess_safety(normalize_request(request), applied_at=fixed)
assert summary.applied_at == fixed
assert all(item.rule_version >= 1 for item in summary.rule_refs)
with pytest.raises(ValueError, match="timezone-aware"):
    assess_safety(normalize_request(request), applied_at=datetime(2026, 7, 16))
```

- [ ] **Step 4: Require runtime records and API output to preserve version metadata**

Assert every interaction, contraindication, and dose-limit runtime record has `rule_version >= 1`. Through the real recommendation endpoint, assert the safety response contains a parseable timezone-aware `applied_at` and positive versions on every returned rule.

- [ ] **Step 5: Run the focused tests and confirm the new assertions fail**

Run:

```powershell
.venv-interim\Scripts\python.exe -m pytest tests/test_medication_supplement_input_contracts.py tests/test_runtime_knowledge_db.py tests/test_inference_api.py -q
```

Expected: FAIL because incomplete dose evidence is not yet blocked and response/runtime version and application-time fields do not exist.

### Task 2: Version existing safety rules and runtime records

**Files:**
- Modify: `data/rules/safety_rules.json`
- Modify: `src/wellnessbox_rnd/domain/models.py`
- Modify: `src/wellnessbox_rnd/knowledge/runtime_db.py`
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Regenerate: `data/knowledge/runtime_knowledge_db_v1.json`

- [ ] **Step 1: Add an explicit positive version to every structured safety rule**

Add `"version": 1` to every `metadata` object in `safety_rules.json`. Make the field required in `SafetyRuleMetadata`.

```python
class SafetyRuleMetadata(BaseModel):
    rule_id: str
    version: int = Field(ge=1)
    message: str
    severity: Severity
    warning_text: str
```

- [ ] **Step 2: Carry versions into runtime safety records**

Add `rule_version: int = Field(ge=1)` to `InteractionRuleRecord`, `ContraindicationRuleRecord`, and `DoseLimitRecord`. Deterministic records use `metadata["version"]`. Knowledge-artifact rules use the positive integer suffix parsed fail-closed from `artifact.artifact_version`, currently `reference_knowledge_base_v1`.

```python
match = re.fullmatch(r".*_v(?P<version>[1-9]\d*)", artifact.artifact_version)
if match is None:
    raise ValueError("knowledge artifact version must end in _v<positive integer>")
knowledge_rule_version = int(match.group("version"))
```

- [ ] **Step 3: Add version and reason fields to the response contract**

Add a required positive `rule_version` and optional bounded `application_reason` to `RuleReference`. Add required `AwareDatetime applied_at` to `SafetySummary`.

```python
class RuleReference(BaseModel):
    rule_id: str
    rule_version: int = Field(ge=1)
    application_reason: Literal[
        "dose_evidence_incomplete",
        "upper_limit_exceeded",
    ] | None = None
    ...

class SafetySummary(BaseModel):
    applied_at: AwareDatetime
    ...
```

- [ ] **Step 4: Regenerate and validate the runtime artifact**

Run:

```powershell
.venv-interim\Scripts\python.exe -c "from pathlib import Path; from wellnessbox_rnd.knowledge.runtime_db import build_runtime_knowledge_db; Path('data/knowledge/runtime_knowledge_db_v1.json').write_text(build_runtime_knowledge_db().model_dump_json(indent=2), encoding='utf-8')"
```

Expected: stored artifact equals a fresh build and runtime validation returns no issues.

### Task 3: Apply dose-limit rules fail-closed through the existing aggregate path

**Files:**
- Modify: `src/wellnessbox_rnd/safety/service.py`
- Modify: `tests/test_medication_supplement_input_contracts.py`

- [ ] **Step 1: Capture one timezone-aware application time**

Change `assess_safety` to accept `applied_at: datetime | None = None`. Reject naive values, otherwise normalize to UTC. When omitted, capture `datetime.now(UTC)` exactly once and place it on the returned `SafetySummary`.

```python
def assess_safety(
    intake: NormalizedIntake,
    *,
    applied_at: datetime | None = None,
) -> SafetySummary:
    effective_applied_at = applied_at or datetime.now(UTC)
    if effective_applied_at.tzinfo is None:
        raise ValueError("applied_at must be timezone-aware")
    effective_applied_at = effective_applied_at.astimezone(UTC)
```

- [ ] **Step 2: Return structured dose-limit applications**

Replace the tuple returned by `_find_triggered_dose_limits` with a private frozen record containing the dose-limit rule, optional observed amount, and reason. For any aggregate with a configured limit and `dose_input_count > 0`, return `dose_evidence_incomplete` before comparing amounts when `dose_complete` is false, the total is missing, or the normalized unit differs from the rule unit. An optional absent dose is not evaluated. Only complete compatible aggregates can produce `upper_limit_exceeded`.

```python
@dataclass(frozen=True)
class _DoseLimitApplication:
    rule: DoseLimitRecord
    observed_amount: float | None
    reason: Literal["dose_evidence_incomplete", "upper_limit_exceeded"]
```

- [ ] **Step 3: Block incomplete applications without inventing a numeric comparison**

For `dose_evidence_incomplete`, exclude the ingredient and add an informational application record that states the supplied dose was partial, ambiguous, or non-convertible and therefore could not be compared safely. Do not format a fake observed total, claim that the upper limit was exceeded, or stop unrelated safe alternatives. Return the existing rule ID with the structured application reason. Complete upper-limit violations retain blocker severity.

- [ ] **Step 4: Preserve complete normalized comparisons**

For `upper_limit_exceeded`, keep using the aggregate's normalized amount and the existing formatted comparison warning. Both branches consume the same aggregate returned to callers.

- [ ] **Step 5: Attach versions to every rule reference**

Pass `metadata.version` or `record.rule_version` in `_build_rule_ref`, `_build_interaction_rule_ref`, and dose-limit rule construction. No rule reference may be returned without a positive version.

- [ ] **Step 6: Run focused safety tests**

Run:

```powershell
.venv-interim\Scripts\python.exe -m pytest tests/test_medication_supplement_input_contracts.py tests/test_runtime_knowledge_db.py tests/test_inference_api.py tests/test_special_population_condition_safety.py -q
```

Expected: PASS.

### Task 4: Produce deterministic OP-037/038 evidence and completion claims

**Files:**
- Create: `scripts/run_dose_limit_fail_closed_rule_metadata_smoke.py`
- Create: `data/original_plan/evidence/op037_op038_dose_limit_rule_metadata_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Regenerate: `docs/original_plan/completion_status_v1.json`
- Regenerate: `docs/original_plan/COMPLETION_STATUS.md`

- [ ] **Step 1: Build deterministic evidence with an injected time**

Use `2026-07-16T00:00:00Z` for every smoke safety call. Include complete-above-limit unit conversion, complete-below-limit control, missing dose, partial dose, incompatible unit, positive rule versions, and `contains_health_identifiers=false`. Run twice and require byte-identical output.

- [ ] **Step 2: Claim only `IMPLEMENTED`**

Register OP-037 and OP-038 with exact implementation, test, smoke script, and evidence paths. Do not claim deployed service integration or production operation.

- [ ] **Step 3: Regenerate reports and extend CI**

Run the new smoke before the exact requirement contract test selection. Add the new smoke script, evidence artifact, and focused tests to workflow path filters and lint coverage.

Expected generated counts: claimed requirements `38`; complete `28`; partial `10`; pending `81`; external `1`; contradicted `0`.

### Task 5: Verify, review, publish, and hand off

**Files:**
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [ ] **Step 1: Run focused and CI-equivalent tests**

Run the Task 3 focused selection, then the exact `Original plan evidence` pytest selection.

- [ ] **Step 2: Run deterministic and repository guardrails**

Run:

```powershell
.venv-interim\Scripts\python.exe -m ruff check .
.venv-interim\Scripts\python.exe scripts/audit_original_plan_requirements.py
.venv-interim\Scripts\python.exe scripts/build_original_plan_completion_report.py --check
.venv-interim\Scripts\python.exe scripts/run_dose_limit_fail_closed_rule_metadata_smoke.py
git diff --check
git diff --cached --check
```

- [ ] **Step 3: Run the full suite and classify only known baseline failures**

Expected baseline before this loop: `635 passed`, `77 failed`; the failures are `73` absent ignored-report artifacts and `4` CGM geometry assertions. Any new failure requires systematic debugging.

- [ ] **Step 4: Verify frozen evaluation compatibility**

Run the official 256-case frozen evaluation against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`. Require zero delta for all seven metrics and no weakest-slice category changes.

- [ ] **Step 5: Request independent review**

Review fail-closed semantics, no invented totals, unit normalization, timezone handling, version provenance, deterministic smoke behavior, response compatibility, and manifest claim strength. Resolve every Critical and Important finding.

- [ ] **Step 6: Commit only loop-owned files and push `main`**

Use explicit paths, never `git add .`. Keep the two user-owned untracked planning documents untouched. Suggested commit message:

```text
feat: fail closed on uncertain supplement doses
```

- [ ] **Step 7: Verify push-triggered CI**

Wait for `Original plan evidence` to succeed. Do not deploy WellnessBox or claim two-process production integration in this R&D-only loop.
