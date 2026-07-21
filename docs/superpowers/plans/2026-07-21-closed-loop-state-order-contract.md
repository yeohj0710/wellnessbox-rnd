# Closed-loop State and Order Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-071/072 by making one strict R&D contract authoritative for closed-loop states, allowed operations, forbidden transitions, and the safety-to-plan execution order.

**Architecture:** Extend the existing `interim.agent.BoundedAgent` instead of adding a second workflow engine. Move its state/transition definitions into a focused immutable contract, add an ordered recommendation workflow method that reuses the existing safety, ranking, evidence, and optimization tools, and persist the existing `agent_steps` audit records. Local SQLite and localhost API evidence prove implementation only; they do not prove the required `OPERATED` stage.

**Tech Stack:** Python 3.11, Pydantic v2, FastAPI, SQLite, pytest, Ruff.

---

### Task 1: Define the authoritative state and operation contract

**Files:**
- Create: `src/wellnessbox_rnd/interim/workflow_contract.py`
- Modify: `src/wellnessbox_rnd/interim/agent.py`
- Test: `tests/test_interim_workflow_contract.py`

- [ ] **Step 1: Write failing contract tests**

Test the complete state list, sorted allowed operations, exact allowed transitions, terminal states, and rejection of forbidden transitions. Verify that no manual-review or human-handoff operation appears in the contract.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `.venv-interim\Scripts\python.exe -m pytest -q tests/test_interim_workflow_contract.py`

Expected: collection failure because `workflow_contract.py` does not exist.

- [ ] **Step 3: Implement the immutable contract**

Define `ClosedLoopState`, `ClosedLoopOperation`, `ClosedLoopTransitionV1`, a canonical allowed-operation map, and `apply_closed_loop_transition_v1`. Keep `STOPPED` and `COMPLETED` terminal and reject every undeclared transition.

- [ ] **Step 4: Make `BoundedAgent` import the contract**

Replace the duplicated local `AgentState`, `TRANSITIONS`, and `transition` definitions with compatibility aliases to the new contract. Preserve existing public imports while making the new module authoritative.

- [ ] **Step 5: Run tests and commit**

Run the new contract tests plus `tests/test_interim_agent.py`, then commit only the contract, agent, and focused tests.

### Task 2: Enforce the recommendation execution order

**Files:**
- Modify: `src/wellnessbox_rnd/interim/agent.py`
- Modify: `apps/inference_api/routes/interim.py`
- Test: `tests/test_interim_workflow_contract.py`
- Test: `tests/test_interim_api.py`

- [ ] **Step 1: Add failing ordered-workflow tests**

Cover the exact successful sequence `check_safety -> rank_ingredients -> retrieve_evidence -> optimize_regimen -> start_plan`, a blocked safety result that stops before candidate generation, missing evidence that stops before optimization, and attempts to optimize or start a plan out of order.

- [ ] **Step 2: Run the tests and confirm the order assertions fail**

Run: `.venv-interim\Scripts\python.exe -m pytest -q tests/test_interim_workflow_contract.py tests/test_interim_api.py`

- [ ] **Step 3: Implement `BoundedAgent.execute_recommendation_workflow`**

Reuse `execute_tool` for safety, ranking, evidence, and optimization so hashes and `agent_steps` remain in the existing audit tables. Require evidence-backed candidates before optimization. Record `start_plan` as a system-owned workflow step only after optimization succeeds, and return a strict trace with before/after states and operation order.

- [ ] **Step 4: Expose the existing agent route**

Add one request model and `/v1/interim/agent/workflow` handler beside the current agent endpoints. Do not create another route family, database, event store, or service-side workflow.

- [ ] **Step 5: Run API and agent regressions and commit**

Run focused agent/API tests, Ruff on changed paths, and commit the implementation before generating evidence.

### Task 3: Generate deterministic evidence and register honest stages

**Files:**
- Create: `scripts/run_closed_loop_state_order_smoke.py`
- Create: `data/original_plan/evidence/op071_op072_closed_loop_state_order_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: governance tests under `tests/test_original_plan_*.py`

- [ ] **Step 1: Build a deterministic local SQLite smoke**

Seed one approved evidence passage, execute one successful workflow, one safety-blocked workflow, one evidence-empty workflow, and forbidden-order cases. Normalize generated identities and timestamps before hashing so two runs are byte-identical.

- [ ] **Step 2: Run the smoke twice**

Compare SHA-256 and bytes. The evidence must say `IMPLEMENTED`, `required_stage=OPERATED`, `production_operation_proven=false`, and must not claim deployment or service integration.

- [ ] **Step 3: Update manifest and generated reports**

Claim OP-071 and OP-072 only at `IMPLEMENTED`, leaving both PARTIAL. Generate the completion report rather than editing counts manually.

- [ ] **Step 4: Update CI and governance tests**

Add the smoke, focused tests, and reproducibility check to `Original plan evidence`.

### Task 4: Verify, review, and publish

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] **Step 1: Run full validation**

Run focused tests, workflow-equivalent tests, all canonical smokes, full Ruff, audit/report check, full pytest, frozen eval comparison, source-hash checks, and both Git diff checks.

- [ ] **Step 2: Obtain independent review**

Require Critical `0` and Important `0`; fix defects with systematic debugging and restart verification when source changes.

- [ ] **Step 3: Commit and push explicit paths**

Never use `git add .`. Push source before evidence/governance and require the `Original plan evidence` workflow to succeed.

- [ ] **Step 4: Record the handoff**

Record exact counts, hashes, commits, CI run, evidence boundary, five bottlenecks, and next loops OP-073/074, OP-075/076, and OP-077/078.
