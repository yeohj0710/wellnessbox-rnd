# OP-055/056 Personal and Group PRO Effect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate plan-linked personal observed PRO changes from a cohort mean and return deterministic sample-size, confidence-interval, and uncertainty metadata without making a causal-effect claim.

**Architecture:** Extend the existing `metrics/pro_followup.py` output through one new group-summary module. Each group summary retains the validated personal interpretations as its source, derives one arithmetic cohort mean, and reuses the interim KPI bootstrap algorithm through a shared statistics helper. The summary rejects mixed or duplicate cohort members and remains explicitly observational and data-class scoped.

**Tech Stack:** Python 3.11+, Pydantic v2, deterministic `random.Random`, pytest, Ruff, JSON evidence contracts, existing original-plan audit/report workflow.

---

### Task 1: Promote the existing deterministic bootstrap helper

**Files:**
- Create: `src/wellnessbox_rnd/metrics/statistics.py`
- Modify: `src/wellnessbox_rnd/interim/kpi.py`
- Test: `tests/test_pro_group_effects.py`
- Test: `tests/test_interim_kpi.py`

- [ ] **Step 1: Write failing helper tests**

```python
def test_deterministic_bootstrap_mean_ci_replays_exactly() -> None:
    values = [-0.2, 0.1, 0.4, 0.8]
    first = deterministic_bootstrap_mean_ci(values)
    second = deterministic_bootstrap_mean_ci(values)
    assert first == second
    assert first[0] <= statistics.mean(values) <= first[1]


def test_deterministic_bootstrap_mean_ci_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="values_required"):
        deterministic_bootstrap_mean_ci([])
    with pytest.raises(ValueError, match="finite"):
        deterministic_bootstrap_mean_ci([0.0, float("nan")])
```

- [ ] **Step 2: Run the tests and confirm the helper is absent**

Run: `python -m pytest tests/test_pro_group_effects.py -k bootstrap -vv`

Expected: collection/import failure because `wellnessbox_rnd.metrics.statistics` does not exist.

- [ ] **Step 3: Move the existing algorithm into the shared metrics module**

```python
def deterministic_bootstrap_mean_ci(
    values: Sequence[float],
    *,
    confidence_level: float = 0.95,
    iterations: int = 3_000,
    seed: int = 20_260_710,
) -> tuple[float, float]:
    checked = [float(value) for value in values]
    if not checked:
        raise ValueError("bootstrap_values_required")
    if not all(math.isfinite(value) for value in checked):
        raise ValueError("bootstrap_values_must_be_finite")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("bootstrap_confidence_level_must_be_between_zero_and_one")
    if iterations < 1:
        raise ValueError("bootstrap_iterations_must_be_positive")
    rng = random.Random(seed)
    estimates = [statistics.mean(rng.choice(checked) for _ in checked) for _ in range(iterations)]
    alpha = (1.0 - confidence_level) / 2.0
    return linear_percentile(estimates, alpha), linear_percentile(estimates, 1.0 - alpha)
```

Update `interim/kpi.py` to import this function and remove its private `_percentile` and `_bootstrap_ci` copies. Keep the current argument order, seed, and iteration count so existing KPI output remains unchanged.

- [ ] **Step 4: Run helper and interim KPI regression tests**

Run: `python -m pytest tests/test_pro_group_effects.py -k bootstrap tests/test_interim_kpi.py -vv`

Expected: all selected tests pass and the seven proxy KPI behavior is unchanged.

### Task 2: Fix the OP-055/056 contract

**Files:**
- Create: `data/contracts/pro_group_effect_summary_v1.json`
- Create: `src/wellnessbox_rnd/metrics/pro_group_effects.py`
- Modify: `src/wellnessbox_rnd/metrics/__init__.py`
- Test: `tests/test_pro_group_effects.py`

- [ ] **Step 1: Write failing contract and separation tests**

```python
def test_group_summary_separates_personal_effects_from_group_estimate() -> None:
    personal = [_personal_effect(index, raw_score) for index, raw_score in enumerate((9, 8, 7))]
    summary = build_pro_group_effect_summary_v1(
        cohort_id="cohort_sleep_week_2",
        personal_effects=personal,
    )
    assert summary.personal_effects == personal
    assert summary.group_estimate.sample_size == 3
    assert summary.group_estimate.mean_health_z_change == round(
        statistics.mean(item.mean_health_z_change for item in personal), 6
    )
    assert summary.causal_effect_claim_allowed is False
    assert summary.effect_claim_scope == "group_observed_association_not_causal"
```

- [ ] **Step 2: Run the test and confirm the builder is absent**

Run: `python -m pytest tests/test_pro_group_effects.py -k group_summary_separates -vv`

Expected: import failure for `build_pro_group_effect_summary_v1`.

- [ ] **Step 3: Implement strict source-retaining summary models**

Define:

```python
class PROConfidenceIntervalV1(_StrictModel):
    confidence_level: Literal[0.95]
    lower: float = Field(allow_inf_nan=False)
    upper: float = Field(allow_inf_nan=False)
    method: Literal["deterministic_percentile_bootstrap_mean"]
    iterations: Literal[3000]
    seed: Literal[20260710]


class PROGroupObservedEffectEstimateV1(_StrictModel):
    sample_size: StrictInt = Field(ge=2)
    fully_interpretable_sample_size: StrictInt = Field(ge=0)
    interpretation_status_counts: dict[PROInterpretationStatusV1, StrictInt]
    mean_health_z_change: float = Field(allow_inf_nan=False)
    mean_health_z_change_ci95: PROConfidenceIntervalV1
    mean_health_percentile_change: float = Field(allow_inf_nan=False)
    mean_health_percentile_change_ci95: PROConfidenceIntervalV1
    observed_change_status: Literal["improved", "worsened", "no_material_change"]


class PROGroupEffectSummaryV1(_StrictModel):
    schema_version: Literal["pro_group_effect_summary_v1"]
    contract_version: Literal["2026-07-21.1"]
    cohort_id: str
    data_class: DataClass
    follow_up_timepoint: Literal["week_2", "week_4", "discontinuation"]
    personal_effects: list[PROFollowUpEffectInterpretationV1] = Field(min_length=2)
    group_estimate: PROGroupObservedEffectEstimateV1
    uncertainty_reason_codes: list[str]
    causal_effect_claim_allowed: Literal[False]
    effect_claim_scope: Literal["group_observed_association_not_causal"]
```

The model validator must recompute every group field from `personal_effects` and reject mutations.

- [ ] **Step 4: Enforce cohort identity and uncertainty rules**

`build_pro_group_effect_summary_v1` must reject duplicate plan IDs, duplicate assessment IDs, mixed data classes, mixed follow-up timepoints, mixed instrument/scoring versions, and mixed baseline-distribution hashes. Sort personal numeric values before bootstrap sampling so input order cannot change the deterministic result.

Emit uncertainty reasons in contract order:

```python
[
    "observational_association_not_causal",
    "non_real_world_outcome_data",
    "sample_size_below_100",
    "limited_personal_interpretations_present",
    "confidence_interval_not_entirely_above_zero",
]
```

Include only reasons whose condition applies, except the non-causal reason, which is always present.

- [ ] **Step 5: Run group contract tests**

Run: `python -m pytest tests/test_pro_group_effects.py -vv`

Expected: personal/group separation, deterministic CI, cohort rejection, mutation rejection, and package export tests all pass.

### Task 3: Add deterministic OP-055/056 evidence

**Files:**
- Create: `scripts/run_pro_personal_group_uncertainty_smoke.py`
- Create after source commit: `data/original_plan/evidence/op055_op056_pro_personal_group_uncertainty_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Test: `tests/test_original_plan_audit_cli.py`

- [ ] **Step 1: Add a smoke that builds one 100-person synthetic week-2 cohort**

The smoke must report personal count `100`, a separately named group estimate, both 95% confidence intervals, interpretation-status counts, uncertainty reasons, source paths/hash/commit, and explicit boundaries:

```python
"evidence_boundary": {
    "data_class": "SYNTHETIC_OUTCOME_PROXY",
    "real_world_outcome_used": False,
    "production_operation_proven": False,
    "service_integration_proven": False,
    "causal_effect_claim_allowed": False,
}
```

It must also prove order independence, duplicate-plan rejection, mixed-timepoint rejection, mixed-distribution rejection, output-mutation rejection, and unchanged personal numeric effects.

- [ ] **Step 2: Run the smoke twice before committing source**

Run twice with two `etc/` output paths and compare SHA-256.

Expected: both output files are byte-identical, but their source commit is not canonical until the source-first commit exists.

- [ ] **Step 3: Run focused checks and make the source-first commit**

Run:

```powershell
python -m pytest tests/test_pro_group_effects.py tests/test_pro_followup_effects.py tests/test_interim_kpi.py tests/test_original_plan_audit_cli.py
python -m ruff check src/wellnessbox_rnd/metrics src/wellnessbox_rnd/interim/kpi.py scripts/run_pro_personal_group_uncertainty_smoke.py tests/test_pro_group_effects.py
```

Commit only the contract, source, smoke, tests, and workflow paths.

- [ ] **Step 4: Generate canonical evidence after the source commit**

Run the smoke twice again, once to the canonical path and once to `etc/`. Require byte-identical output and exact source commit/hash recomputation.

### Task 4: Register stages and regenerate governance outputs

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`

- [ ] **Step 1: Register both requirements at `IMPLEMENTED`**

OP-055 and OP-056 both inherit required stage `IMPLEMENTED`. Reference the group contract/module, focused test, smoke, and canonical evidence. Do not register service, operation, or external evidence.

- [ ] **Step 2: Regenerate and verify completion outputs**

Run:

```powershell
python scripts/audit_original_plan_requirements.py
python scripts/build_original_plan_completion_report.py
python scripts/build_original_plan_completion_report.py --check
```

Expected generated counts: derive them from the generator and update exact-count regression tests only to the generated values.

### Task 5: Complete regression, independent review, publication, and handoff

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] **Step 1: Run final local verification**

Run the exact workflow pytest selection, full Ruff, full pytest, official 256-case frozen eval comparison, all canonical smoke checks, source-identity checks, manifest audit, completion report check, `git diff --check`, and `git diff --cached --check`.

Expected: workflow selection passes; no new full-suite failure outside the existing `73` absent-report and `4` CGM-geometry groups; all seven frozen-eval deltas are zero with unchanged weakest slices.

- [ ] **Step 2: Obtain independent review**

Review the latest tree for personal/group identity separation, confidence-interval determinism, cohort duplication/mixing, fail-closed output validation, non-causal boundaries, and evidence completeness. Require Critical `0` and Important `0`.

- [ ] **Step 3: Commit and push loop-owned evidence files explicitly**

Do not use `git add .`. Push only when fresh fetch shows the branch is ahead-only. Require the `Original plan evidence` workflow to pass.

- [ ] **Step 4: Record exact handoff evidence**

Update the three handoff files with actual hashes, commits, CI run, focused/workflow/full-suite counts, frozen-eval deltas, explicit implementation/integration/operation boundaries, five remaining bottlenecks, and OP-057/058 as the next bounded loop.
