# Follow-up Input Decision and Serious Adverse-Event Stop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make accepted PRO/device inputs enqueue an immediate plan-reevaluation job and make a serious adverse event atomically stop the linked plan, queued work, active agent runs, and further recommendations.

**Architecture:** Extend the existing SQLite execution ledger and `workflow_jobs` queue instead of adding a scheduler or event store. Input receipts create deterministic follow-up work linked to an active execution/plan. Serious adverse events append a discontinuation event to the same execution, close linked follow-ups, cancel READY/CLAIMED jobs, stop current recommendation/agent runs, create one urgent review, and leave an unresolved adverse-event hold that recommendation entry points check before model execution.

**Tech Stack:** Python 3.11+, SQLite, FastAPI, Pydantic, pytest, Ruff.

---

### Task 1: Specify input-to-next-job behavior

**Files:**
- Modify: `tests/test_interim_jobs.py`
- Modify: `src/wellnessbox_rnd/interim/jobs.py`

- [ ] **Step 1: Write failing queue tests**

Add cases proving that a PRO or device receipt linked to an active execution creates one immediate `PLAN_REEVALUATION` job, an identical receipt is idempotent, a changed receipt conflicts, and a stopped plan cannot enqueue work.

- [ ] **Step 2: Run the focused tests and observe failure**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_interim_jobs.py -q`

Expected: FAIL because `enqueue_input_reevaluation` does not exist.

- [ ] **Step 3: Extend the shared queue**

Implement `WorkflowJobQueue.enqueue_input_reevaluation(...)`. Validate the execution/profile/plan linkage in the same immediate transaction, create or reuse a deterministic follow-up row, and enqueue a `PLAN_REEVALUATION` job with the input kind, input ID, received time, and bounded reason code in its hashed payload.

- [ ] **Step 4: Run the queue tests**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_interim_jobs.py -q`

Expected: PASS.

### Task 2: Connect actual PRO and device receipt paths

**Files:**
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `src/wellnessbox_rnd/interim/agent.py`
- Modify: `tests/test_pro_plan_service.py`
- Modify: `tests/test_interim_agent.py`
- Modify: `tests/test_interim_api.py`

- [ ] **Step 1: Write failing route and agent tests**

Prove that `/pro/followups`, the device connector with explicit plan context, `ingest_pro`, and `ingest_wearable` return a persisted `next_job` only after successful storage. Invalid device input must not enqueue work.

- [ ] **Step 2: Run the focused tests and observe failure**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_pro_plan_service.py tests/test_interim_agent.py tests/test_interim_api.py -q`

Expected: FAIL because no input receipt currently schedules the next job.

- [ ] **Step 3: Add the integration calls**

After successful PRO/device persistence, call `enqueue_input_reevaluation` with the exact execution, plan, profile, source input ID, and observed timestamp. Require all plan-context fields together for connector requests and fail closed on incomplete context.

- [ ] **Step 4: Run the focused tests**

Run the command from Step 2.

Expected: PASS.

### Task 3: Stop a plan and further recommendations on serious adverse events

**Files:**
- Modify: `src/wellnessbox_rnd/interim/agent.py`
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `tests/test_interim_agent.py`
- Modify: `tests/test_interim_api.py`

- [ ] **Step 1: Write failing serious-event tests**

Cover exact execution/plan ownership, canonical discontinuation event append, linked follow-up/job cancellation, all active profile runs stopped, recommendation rows stopped, one urgent review created, exact retry idempotency, changed retry conflict, and rejection of subsequent recommendation and ordered-workflow requests before model execution.

- [ ] **Step 2: Run the tests and observe failure**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_interim_agent.py tests/test_interim_api.py -q`

Expected: FAIL because the existing private helper neither links the plan nor blocks later recommendations.

- [ ] **Step 3: Implement the atomic stop**

Expose an authenticated adverse-event route and a public agent service method. In one immediate transaction, validate the run and execution-plan ownership, insert the serious event, append one `followup_evaluation` discontinuation event, stop active agent and recommendation runs, close the plan's follow-ups, cancel READY/CLAIMED jobs, and insert one urgent review. Treat unresolved `adverse_events.status='ESCALATED'` as a recommendation hold at every interim recommendation entry point.

- [ ] **Step 4: Run the serious-event tests**

Run the command from Step 2.

Expected: PASS.

### Task 4: Produce deterministic evidence and register honest stages

**Files:**
- Create: `scripts/run_followup_input_serious_ae_smoke.py`
- Create: `data/original_plan/evidence/op075_op076_followup_input_serious_ae_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`

- [ ] **Step 1: Build the smoke**

Exercise PRO and device next-job decisions plus serious-event cancellation and recommendation hold twice from fixed inputs. Record source paths/hashes and explicit false production-operation claims.

- [ ] **Step 2: Commit source before evidence generation**

Stage only loop-owned source/tests and commit them. Generate the canonical smoke only from that committed source identity.

- [ ] **Step 3: Register evidence**

Claim OP-075 and OP-076 only at `IMPLEMENTED`; both remain PARTIAL because required stage is `OPERATED`. Add the smoke and focused tests to the manifest and CI workflow.

- [ ] **Step 4: Regenerate reports and validate determinism**

Run the smoke twice and compare bytes, run the audit, and run the completion report generator in check mode.

### Task 5: Regression, independent review, and publication

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] **Step 1: Run local verification**

Run focused tests, the exact workflow pytest selection, all canonical smokes using a clean service worktree, full Ruff, full pytest with JUnit, frozen eval 256 comparison, audit, completion check, and both Git diff checks.

- [ ] **Step 2: Obtain independent review**

Request review of the final source tree. Require Critical 0 / Important 0; fix findings using systematic debugging and repeat verification.

- [ ] **Step 3: Publish and verify CI**

Explicitly stage loop-owned files, push `main`, and verify GitHub Actions `Original plan evidence` succeeds. Do not deploy or change production configuration.

- [ ] **Step 4: Record handoff**

Record actual counts, hashes, commits, CI run, frozen deltas, operational boundary, five blockers, and OP-077/078 as the next loop.
