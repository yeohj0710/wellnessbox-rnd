# Follow-up Job Queue and Due-plan Cron Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-073/074 by storing follow-up reminders in one durable SQLite workflow queue and having a deterministic cron runner enqueue one reevaluation job for each due follow-up.

**Architecture:** Extend the existing interim SQLite schema rather than adding a second service or event store. `BoundedAgent.create_followup` writes the existing follow-up and its reminder job atomically; a queue service claims due follow-ups and inserts idempotent reevaluation jobs under `BEGIN IMMEDIATE`. A FastAPI internal endpoint and CLI runner expose the same cron function without claiming deployment or production operation.

**Tech Stack:** Python 3.11, SQLite, Pydantic v2, FastAPI, pytest, Ruff.

---

### Task 1: Durable workflow-job contract and schema

**Files:**
- Create: `src/wellnessbox_rnd/interim/jobs.py`
- Modify: `src/wellnessbox_rnd/interim/store.py`
- Test: `tests/test_interim_jobs.py`

- [ ] Write failing tests proving exact job types/statuses, payload-hash conflict rejection, idempotent enqueue, and atomic follow-up-plus-reminder creation.
- [ ] Run `python -m pytest -q tests/test_interim_jobs.py` and confirm the missing module/schema failures.
- [ ] Add `workflow_jobs` with unique idempotency keys, inspectable payload JSON/SHA-256, scheduled/claimed/completed timestamps, and follow-up/plan/profile linkage. Add `plan_id` to `followups` through an idempotent migration.
- [ ] Implement one queue service that inserts the existing follow-up and `FOLLOWUP_REMINDER` job in the same `BEGIN IMMEDIATE` transaction.
- [ ] Run the focused tests and Ruff, then commit only Task 1 files.

### Task 2: Due-plan cron and existing Agent/API integration

**Files:**
- Modify: `src/wellnessbox_rnd/interim/jobs.py`
- Modify: `src/wellnessbox_rnd/interim/agent.py`
- Modify: `apps/inference_api/routes/interim.py`
- Create: `scripts/run_due_plan_reevaluation_cron.py`
- Test: `tests/test_interim_jobs.py`
- Test: `tests/test_interim_agent.py`
- Test: `tests/test_interim_api.py`

- [ ] Write failing tests for before-due/no-op, at-due enqueue, repeated cron idempotency, two due plans, non-open exclusion, and API/CLI use of the same function.
- [ ] Implement `enqueue_due_plan_reevaluations(as_of)` with a single immediate transaction, one `PLAN_REEVALUATION` job per follow-up, deterministic ordering, and no duplicate after retry.
- [ ] Route `create_followup` through the queue service and require a concrete `plan_id`; expose an authenticated internal cron endpoint and a CLI that points at the configured interim database.
- [ ] Run focused tests, Ruff, and commit only Task 2 files.

### Task 3: Canonical evidence and governance

**Files:**
- Create: `scripts/run_followup_job_queue_cron_smoke.py`
- Create: `data/original_plan/evidence/op073_op074_followup_job_queue_cron_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Regenerate: `docs/original_plan/COMPLETION_STATUS.md`
- Regenerate: `docs/original_plan/completion_status_v1.json`

- [ ] Create a deterministic smoke with future reminder, due-plan cron, duplicate cron, two-plan ordering, queue payload/source identity, and explicit non-operation boundary.
- [ ] Run it twice and require byte-identical output, then commit source before generating canonical evidence.
- [ ] Claim only `IMPLEMENTED` for OP-073/074; both remain PARTIAL below required `OPERATED`.
- [ ] Regenerate and test the manifest/report, add the smoke to the existing evidence workflow, and commit explicit evidence/governance paths.

### Task 4: Final verification and handoff

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] Run workflow-equivalent tests, full Ruff, all affected canonical smokes, full pytest with JUnit counts, and the 256-case frozen eval comparison.
- [ ] Run audit/report checks, source-hash checks, `git diff --check`, and `git diff --cached --check` after the last change.
- [ ] Obtain independent review with Critical 0 / Important 0, fix any finding, and repeat verification.
- [ ] Push explicit commits, require `Original plan evidence` success, then record exact hashes, counts, stage boundaries, CI run, five bottlenecks, and next loops OP-075/076, OP-077/078, OP-079/080.
