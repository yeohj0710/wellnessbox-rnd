# Plan Lifecycle and Order Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-079 plan lifecycle transitions end to end and prove OP-080 keeps those transitions separate from actual WellnessBox order state.

**Architecture:** Add a focused lifecycle service over the existing `executions` and append-only `execution_events` ledger. Each transition reconstructs current plan state, validates one deterministic action, stores one idempotent event, and performs only existing follow-up/job cleanup required by terminal plan actions. The API forbids order fields and returns a fixed no-order-mutation boundary; service-source evidence verifies that lifecycle code does not call cart, order, or payment mutations.

**Tech Stack:** Python 3.11+, Pydantic v2, SQLite, FastAPI, pytest, Ruff, deterministic JSON/SHA-256 evidence.

---

### Task 1: Define the lifecycle contract and reconstruction rules

**Files:**
- Create: `src/wellnessbox_rnd/interim/plan_lifecycle.py`
- Test: `tests/test_plan_lifecycle.py`

- [ ] **Step 1: Write failing contract tests**

```python
def test_plan_lifecycle_contract_covers_all_required_actions() -> None:
    assert {item.value for item in PlanLifecycleAction} == {
        "maintain", "adjust", "replace", "stop", "monitor"
    }

def test_replace_requires_distinct_replacement_plan() -> None:
    with pytest.raises(ValueError, match="replacement_plan_id_required"):
        PlanLifecycleTransitionRequestV1(
            execution_id="execution_1", profile_id="usr_1", plan_id="plan_1",
            action="replace", reason_code="PRO_WORSENED",
            idempotency_key="replace-1", occurred_at=NOW,
        )
```

- [ ] **Step 2: Run the tests and confirm module-not-found failure**

Run: `.\.venv-interim\Scripts\python.exe -m pytest tests/test_plan_lifecycle.py -q`

- [ ] **Step 3: Implement strict enums and models**

Define `PlanLifecycleState` values `ACTIVE`, `MAINTAINED`, `ADJUSTED`, `MONITORING`, `REPLACED`, and `STOPPED`. Define `PlanLifecycleAction` values `maintain`, `adjust`, `replace`, `stop`, and `monitor`. The request uses `extra="forbid"`, requires timezone-aware `occurred_at`, requires a distinct `replacement_plan_id` only for `replace`, and therefore rejects every order/cart/payment field. The result validates literal `order_state_effect="NONE"` and `order_state_mutation_allowed=False`.

- [ ] **Step 4: Implement reconstruction from active execution events**

Start a recommendation-linked plan at `ACTIVE`. Replay only `plan_lifecycle_transition_v1` follow-up events in event-index order. Validate stored state continuity. Treat `REPLACED` and `STOPPED` as terminal for the old plan and create `ACTIVE` state for the replacement plan from the same lineage event.

- [ ] **Step 5: Run tests and commit**

Run the focused test, then stage only the new module and test. Commit `feat: define plan lifecycle transitions`.

### Task 2: Persist transitions in the existing execution ledger

**Files:**
- Modify: `src/wellnessbox_rnd/interim/plan_lifecycle.py`
- Modify: `src/wellnessbox_rnd/interim/jobs.py`
- Test: `tests/test_plan_lifecycle.py`
- Test: `tests/test_interim_jobs.py`

- [ ] **Step 1: Write failing persistence tests**

Cover exact retry deduplication, changed-payload conflict, stale `state_before`, missing consent, wrong profile/execution/plan linkage, terminal-state rejection, concurrent attempts, and ordered event indexes. Assert transition rows use `execution_events`, not a new lifecycle table.

- [ ] **Step 2: Run focused tests and confirm the intended failures**

Run: `.\.venv-interim\Scripts\python.exe -m pytest tests/test_plan_lifecycle.py tests/test_interim_jobs.py -q`

- [ ] **Step 3: Implement `PlanLifecycleService.transition` with `BEGIN IMMEDIATE`**

Within one transaction, load execution and active consent, reconstruct state, resolve an existing idempotency row, validate the transition, append a `followup_evaluation/system` event with deterministic payload/hash, and return the stored event. Exact retries return the same event; different payloads raise `plan_lifecycle_idempotency_conflict`.

- [ ] **Step 4: Apply lifecycle postconditions without order mutations**

For `stop` and the old side of `replace`, close matching open follow-ups and cancel READY/CLAIMED jobs. For `maintain`, `adjust`, and `monitor`, preserve open work. Do not create, update, or delete service cart/order/payment rows.

- [ ] **Step 5: Update active-plan checks**

Make `_execution_plan_is_active` consume lifecycle events so `STOPPED` and `REPLACED` deactivate the old plan, while a replacement plan becomes active from the same recorded lineage. Preserve serious-AE discontinuation behavior.

- [ ] **Step 6: Run focused tests and commit**

Stage only the lifecycle/jobs source and focused tests. Commit `feat: persist plan lifecycle transitions`.

### Task 3: Expose the API and generate deterministic boundary evidence

**Files:**
- Modify: `apps/inference_api/routes/interim.py`
- Test: `tests/test_interim_api.py`
- Create: `scripts/run_plan_lifecycle_order_boundary_smoke.py`
- Create: `data/original_plan/evidence/op079_op080_plan_lifecycle_order_boundary_smoke_v1.json`

- [ ] **Step 1: Write failing API tests**

Test `POST /v1/interim/plan-lifecycle/transitions` for all five actions on isolated plan lineages. Extra `order_status`, `order_id`, and `payment_status` fields must receive HTTP 422 and write no event.

- [ ] **Step 2: Add the mutation-token-protected route**

```python
@router.post(
    "/plan-lifecycle/transitions",
    dependencies=[Depends(require_event_mutation_token)],
)
def transition_plan(payload: PlanLifecycleTransitionRequestV1) -> dict[str, Any]:
    return PlanLifecycleService(_store()).transition(payload).model_dump(mode="json")
```

Map unknown execution/plan to 404, idempotency/stale-state conflicts to 409, permission errors to 403, and invalid transitions to 422.

- [ ] **Step 3: Build the five-case E2E smoke**

Create five independent active plans and execute `maintain`, `adjust`, `replace`, `stop`, and `monitor` through the real FastAPI route. Verify stored event identity, terminal cleanup, replacement activation, exact retry, forbidden order fields, no R&D order mutation capability, and a read-only WellnessBox source scan for order/cart/payment mutation symbols. Pin both repository source identities without modifying WellnessBox.

- [ ] **Step 4: Run twice and compare bytes**

Use a clean service worktree under `etc/service-clean-op079`. Generate `etc/op079_op080_run1.json` and `run2.json`; require identical SHA-256 values before copying the canonical file.

- [ ] **Step 5: Commit source before evidence**

Commit API, tests, smoke, and workflow source first. Regenerate canonical evidence against that commit and commit the evidence separately.

### Task 4: Claim only the proven stage and run all gates

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] **Step 1: Add manifest and workflow evidence**

Claim OP-079 and OP-080 only at `IMPLEMENTED`. Their required stage is `OPERATED`, so both remain PARTIAL. Do not claim actual order mutation, service integration, deployment, or production operation.

- [ ] **Step 2: Regenerate and check reports**

Run the requirement audit, completion-report generator, and completion `--check`. Expected audit status is PASS with no source-hash issue.

- [ ] **Step 3: Run all validation gates**

Run focused tests, the exact workflow pytest selection, all workflow smokes, full Ruff, full pytest, and the 256-case frozen eval. Require no failure group beyond the known 73 absent-report plus 4 CGM-geometry failures. Compare all seven metrics and the full weakest-slice structure with `artifacts/reports/op035_op036_frozen_eval/eval_report.json`; every delta must be zero.

- [ ] **Step 4: Request independent final review**

Require Critical 0 and Important 0. Fix any defect with systematic debugging and restart verification.

- [ ] **Step 5: Update handoff, push, and monitor CI**

Record actual counts, hashes, commits, and successful `Original plan evidence` run. Keep the overall OP-001~120 goal active and identify OP-081/082 as the next loop.
