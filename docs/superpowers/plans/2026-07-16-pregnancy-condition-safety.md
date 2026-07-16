# Pregnancy, Lactation, and Condition Safety Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-033 and OP-034 by separating pregnancy and lactation rules and by expanding condition rules into explicit contraindication and review-required policies.

**Architecture:** Extend the existing strict recommendation input and `SafetyRuleSet`; do not create a second recommendation safety engine. The recommendation path will apply data-defined special-population and condition rules before candidate optimization, while the existing interim replay safety path will expose the same state distinctions with separate deterministic rule IDs. Existing pregnancy behavior remains backward compatible because `pregnant` keeps its current default and rule ID.

**Tech Stack:** Python 3.12, Pydantic v2, JSON rule artifacts, pytest, Ruff

**Status:** Implementation and evidence publication checks complete at the required `IMPLEMENTED` boundary. The WellnessBox combined pregnancy/breastfeeding source field remains an explicit later integration boundary.

---

### Task 1: Lock the special-population input contract

**Files:**
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Test: `tests/test_special_population_condition_safety.py`

- [ ] **Step 1: Write failing schema tests**

```python
def test_user_profile_keeps_pregnancy_and_lactation_independent() -> None:
    pregnant = UserProfile(age=32, biological_sex="female", pregnant=True)
    lactating = UserProfile(age=32, biological_sex="female", lactating=True)
    assert (pregnant.pregnant, pregnant.lactating) == (True, False)
    assert (lactating.pregnant, lactating.lactating) == (False, True)
```

- [ ] **Step 2: Confirm the new contract test fails**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_special_population_condition_safety.py -q`

Expected: FAIL because `UserProfile` does not define `lactating`.

- [ ] **Step 3: Add the independent field**

```python
class UserProfile(_StrictRequestInput):
    age: int = Field(ge=18, le=120)
    biological_sex: BiologicalSex
    pregnant: bool = False
    lactating: bool = False
```

- [ ] **Step 4: Run the focused schema test**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_special_population_condition_safety.py -q`

Expected: schema test PASS.

### Task 2: Apply separate pregnancy and lactation restrictions

**Files:**
- Modify: `src/wellnessbox_rnd/domain/models.py`
- Modify: `data/rules/safety_rules.json`
- Modify: `src/wellnessbox_rnd/safety/service.py`
- Modify: `src/wellnessbox_rnd/knowledge/runtime_db.py`
- Regenerate: `data/knowledge/runtime_knowledge_db_v1.json`
- Regenerate: `artifacts/reports/runtime_knowledge_db_v1_summary.json`
- Regenerate: `artifacts/reports/runtime_knowledge_db_v1_summary.md`
- Test: `tests/test_special_population_condition_safety.py`
- Test: `tests/test_runtime_knowledge_db.py`

- [ ] **Step 1: Add failing pregnancy/lactation behavior tests**

```python
def test_pregnancy_and_lactation_apply_distinct_rules() -> None:
    pregnancy = assess_safety(_intake(pregnant=True))
    lactation = assess_safety(_intake(lactating=True))
    assert [rule.rule_id for rule in pregnancy.rule_refs] == ["SAFETY-PREG-001"]
    assert [rule.rule_id for rule in lactation.rule_refs] == ["SAFETY-LACT-001"]
```

- [ ] **Step 2: Confirm the behavior tests fail**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_special_population_condition_safety.py -q`

Expected: FAIL because one `pregnancy_rule` handles only pregnancy.

- [ ] **Step 3: Replace the singleton with data-defined status rules**

```python
class SpecialPopulationRule(BaseModel):
    statuses: list[Literal["pregnant", "lactating"]]
    excluded_ingredients: list[str] = Field(default_factory=list)
    metadata: SafetyRuleMetadata

class SafetyRuleSet(BaseModel):
    special_population_rules: list[SpecialPopulationRule] = Field(default_factory=list)
```

The JSON artifact must keep `SAFETY-PREG-001` for pregnancy and add `SAFETY-LACT-001` for lactation. Both rules conservatively exclude only explicitly listed ingredients. NCCIH states that ashwagandha should be avoided in pregnancy and should not be used while breastfeeding; retain this source in the implementation evidence notes without claiming OP-035 drug-interaction lineage.

- [ ] **Step 4: Apply every matching status rule in the recommendation engine**

```python
special_population_statuses = {
    status
    for status, active in {
        "pregnant": intake.request.user_profile.pregnant,
        "lactating": intake.request.user_profile.lactating,
    }.items()
    if active
}
for rule in rules.special_population_rules:
    if special_population_statuses.intersection(rule.statuses):
        excluded_ingredients.update(rule.excluded_ingredients)
        _append_unique_text(warnings, rule.metadata.warning_text)
        rule_refs.append(_build_rule_ref(rule.metadata))
```

- [ ] **Step 5: Teach the runtime knowledge builder the new rule shape and regenerate artifacts**

Run: `.venv-interim\Scripts\python.exe scripts/build_runtime_knowledge_db.py`

Expected: the runtime artifact contains separate `pregnancy` and `lactation` condition keys and separate contraindication records.

- [ ] **Step 6: Run focused rule and artifact tests**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_special_population_condition_safety.py tests/test_runtime_knowledge_db.py -q`

Expected: PASS.

### Task 3: Expand condition rules without bypassing the existing engine

**Files:**
- Modify: `src/wellnessbox_rnd/domain/models.py`
- Modify: `data/rules/safety_rules.json`
- Modify: `src/wellnessbox_rnd/safety/service.py`
- Modify: `src/wellnessbox_rnd/knowledge/runtime_db.py`
- Regenerate: `data/knowledge/runtime_knowledge_db_v1.json`
- Test: `tests/test_special_population_condition_safety.py`

- [ ] **Step 1: Add failing condition-policy tests**

```python
def test_condition_rules_distinguish_contraindication_from_review() -> None:
    renal_review = assess_safety(_intake(conditions=["kidney disease"]))
    hemochromatosis = assess_safety(_intake(conditions=["hemochromatosis"]))
    assert "SAFETY-RENAL-001" in _rule_ids(renal_review)
    assert "SAFETY-HEMO-001" in _rule_ids(hemochromatosis)
    assert "magnesium_glycinate" in renal_review.excluded_ingredients
    assert {"iron", "vitamin_c"}.issubset(hemochromatosis.excluded_ingredients)
```

- [ ] **Step 2: Confirm the expanded cases fail**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_special_population_condition_safety.py -q`

Expected: FAIL because only the current renal rule exists.

- [ ] **Step 3: Add an explicit rule effect and expanded rule data**

```python
class ConditionSafetyRule(BaseModel):
    conditions: list[str] = Field(default_factory=list)
    effect: Literal["contraindication", "review_required"]
    excluded_ingredients: list[str] = Field(default_factory=list)
    metadata: SafetyRuleMetadata
```

Keep the existing chronic-kidney review rule. Add severe renal conditions (`kidney failure`, `dialysis`), hepatic review conditions (`liver failure`, `cirrhosis`), and a hemochromatosis contraindication for iron and vitamin C supplements. NIH ODS notes impaired renal function increases magnesium toxicity risk and cites avoidance of iron and vitamin C supplements for hemochromatosis.

- [ ] **Step 4: Validate rule invariants**

Add a Pydantic validator so `contraindication` rules cannot have an empty `excluded_ingredients` list. Continue deriving recommendation status from the existing metadata severity; `effect` classifies the policy and must not introduce a second status system.

- [ ] **Step 5: Regenerate the runtime knowledge artifact and run focused tests**

Run: `.venv-interim\Scripts\python.exe scripts/build_runtime_knowledge_db.py`

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_special_population_condition_safety.py tests/test_runtime_knowledge_db.py -q`

Expected: PASS and generated artifact equality checks PASS.

### Task 4: Keep interim/replay safety decisions semantically aligned

**Files:**
- Modify: `src/wellnessbox_rnd/interim/safety.py`
- Modify: `tests/test_interim_safety.py`

- [ ] **Step 1: Add failing replay tests for separate states and conditions**

```python
def test_pregnancy_and_lactation_have_separate_replay_rule_ids() -> None:
    assert _rule_ids(evaluate_safety({"pregnant": True})) == {"SAFE-PREG-001"}
    assert _rule_ids(evaluate_safety({"lactating": True})) == {"SAFE-LACT-001"}

def test_condition_replay_separates_renal_hepatic_and_hemochromatosis_rules() -> None:
    result = evaluate_safety({"conditions": ["kidney failure", "cirrhosis", "hemochromatosis"], "ingredients": ["iron"]})
    assert {finding.rule_id for finding in result.findings} == {
        "SAFE-RENAL-001", "SAFE-HEPATIC-001", "SAFE-HEMO-001"
    }
```

- [ ] **Step 2: Replace combined branches with separate deterministic findings**

Pregnancy and lactation get separate findings. Renal and hepatic failure get separate blocker IDs. Hemochromatosis triggers its contraindication only when iron or vitamin C is present.

- [ ] **Step 3: Run interim safety tests twice**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_safety.py -q`

Expected: PASS on both runs with byte-identical deterministic decisions.

### Task 5: Publish requirement evidence and verify the bounded loop

**Files:**
- Create: `scripts/run_special_population_condition_safety_smoke.py`
- Create: `data/original_plan/evidence/op033_op034_special_population_condition_safety_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/plans/2026-07-15-original-plan-completion-program.md`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Regenerate: `docs/original_plan/completion_status_v1.json`
- Regenerate: `docs/original_plan/COMPLETION_STATUS.md`

- [ ] **Step 1: Add a deterministic smoke runner**

The runner must exercise pregnancy, lactation, combined special-population state, kidney review, severe renal restriction, hepatic review, and hemochromatosis contraindication through the real schema, normalization, and `assess_safety` path. It writes sorted JSON and exposes no health identifiers.

- [ ] **Step 2: Run the smoke twice and compare SHA-256**

Run: `.venv-interim\Scripts\python.exe scripts/run_special_population_condition_safety_smoke.py`

Expected: identical artifact bytes and hashes across two runs.

- [ ] **Step 3: Claim OP-033 and OP-034 at IMPLEMENTED with exact evidence**

Add implementation, test, and smoke files to both manifest entries. Mark both completion-program checkboxes only after the manifest audit accepts the claim.

- [ ] **Step 4: Regenerate and audit the completion report**

Run: `.venv-interim\Scripts\python.exe scripts/build_original_plan_completion_report.py`

Run: `.venv-interim\Scripts\python.exe scripts/audit_original_plan_requirements.py`

Expected: PASS, with OP-033 and OP-034 complete at their required `IMPLEMENTED` stage.

- [ ] **Step 5: Run focused, CI-equivalent, frozen-evaluation, Ruff, and full regression checks**

Run the repository's exact Original plan evidence CI pytest selection, full Ruff, the 256-case frozen evaluation with seven tracked deltas, and the full pytest suite. Existing absent-report and CGM failures may be reported only if their identities and counts remain unchanged.

- [ ] **Step 6: Commit and publish only the R&D changes**

```text
git add <only OP-033/034 files>
git commit -m "feat: separate special population safety rules"
git push origin main
```

Verify the pushed `Original plan evidence` workflow succeeds. No WellnessBox deployment is required unless the service repository changes.
