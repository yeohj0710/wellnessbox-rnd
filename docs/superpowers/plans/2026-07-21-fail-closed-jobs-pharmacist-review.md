# Fail-Closed Jobs and Pharmacist Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-077 and OP-078 by preventing duplicate execution, cancelling stale, timed-out, or consent-invalid workflow jobs, and persisting immutable pharmacist-review completion postconditions in the existing review table.

**Architecture:** Extend the existing SQLite `workflow_jobs`, `review_tasks`, execution ledger, and FastAPI admin routes. Job creation pins the current execution evidence and consent snapshot; claim and acknowledgement revalidate those identities inside `BEGIN IMMEDIATE`. Fail-closed cancellations create deterministic rows in the existing `review_tasks` table, and the existing review decision route delegates to a typed service that records and hashes verified completion postconditions.

**Tech Stack:** Python 3.11, SQLite, Pydantic v2, FastAPI, pytest, Ruff, deterministic JSON/SHA-256 evidence.

---

### Task 1: Persist review provenance and immutable completion postconditions

**Files:**
- Modify: `src/wellnessbox_rnd/interim/store.py`
- Create: `src/wellnessbox_rnd/interim/reviews.py`
- Test: `tests/test_interim_reviews.py`

- [ ] **Step 1: Write migration and service tests that initially fail**

Add tests that require `review_tasks` columns `source_job_id`, `completion_postcondition_json`, and `completion_postcondition_sha256`; deterministic creation for the same source/reason; atomic first-pharmacy assignment; rejection of a second decision; and a completion postcondition proving a source job remains `CANCELLED`.

```python
completed = service.complete_review(
    review_id=review["review_id"],
    pharmacy_id=7,
    decision={"decision": "ACKNOWLEDGED", "note": "Reviewed failure."},
    completed_at=NOW,
)
assert completed["postconditions"]["source_job_status"] == "CANCELLED"
assert store.scalar("select completion_postcondition_sha256 from review_tasks")
```

- [ ] **Step 2: Run the new tests and confirm the missing schema/service failure**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_reviews.py -q`

Expected: FAIL because the new columns and `PharmacistReviewService` do not exist.

- [ ] **Step 3: Add schema v11 migration and the review service**

Add nullable provenance/postcondition columns without replacing `review_tasks`. Implement deterministic review identity from profile, reason codes, and optional source job. Completion must run in `BEGIN IMMEDIATE`, assign an unassigned task to the first supplied pharmacy, require `OPEN`, validate the source job is still `CANCELLED` when present, store canonical decision/postcondition JSON, store SHA-256, and reject later mutation.

```python
postconditions = {
    "schema_version": "pharmacist_review_completion_postcondition_v1",
    "review_status": "COMPLETED",
    "source_job_id": source_job_id,
    "source_job_status": "CANCELLED" if source_job_id else None,
    "decision_recorded": True,
}
```

- [ ] **Step 4: Run the review tests and Ruff**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_reviews.py -q`

Run: `.venv-interim\Scripts\python.exe -m ruff check src/wellnessbox_rnd/interim/reviews.py src/wellnessbox_rnd/interim/store.py tests/test_interim_reviews.py`

Expected: PASS.

- [ ] **Step 5: Commit the schema and service**

```powershell
git add -- src/wellnessbox_rnd/interim/store.py src/wellnessbox_rnd/interim/reviews.py tests/test_interim_reviews.py
git commit -m "feat: persist pharmacist review postconditions"
```

### Task 2: Pin job evidence and consent at creation

**Files:**
- Modify: `src/wellnessbox_rnd/interim/jobs.py`
- Modify: `tests/test_interim_jobs.py`

- [ ] **Step 1: Add failing creation-identity tests**

Require every job payload to contain the active execution consent snapshot and a deterministic digest of active execution-event IDs plus effective payload hashes. Exact enqueue retries must return the existing job; the same idempotency key with another payload or evidence digest must raise `workflow_job_idempotency_payload_conflict`.

```python
payload = result["reminder_job"]["payload"]
assert payload["consent_snapshot_id"] == "consent_jobs"
assert len(payload["execution_evidence_sha256"]) == 64
```

- [ ] **Step 2: Run the creation tests and confirm failure**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_jobs.py -q`

Expected: FAIL because current payloads do not pin consent or evidence.

- [ ] **Step 3: Add canonical execution identity helpers and use them in all enqueue paths**

Compute identities inside each existing enqueue transaction. Hash only active execution-event identity fields, and include the execution's consent snapshot. Do not add a new event store or scheduler.

```python
identity = {
    "consent_snapshot_id": execution["consent_snapshot_id"],
    "events": [
        {"event_id": row["event_id"], "effective_payload_sha256": row["effective_payload_sha256"]}
        for row in rows
    ],
}
```

- [ ] **Step 4: Run jobs tests and Ruff**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_jobs.py -q`

Run: `.venv-interim\Scripts\python.exe -m ruff check src/wellnessbox_rnd/interim/jobs.py tests/test_interim_jobs.py`

Expected: PASS.

- [ ] **Step 5: Commit pinned job identities**

```powershell
git add -- src/wellnessbox_rnd/interim/jobs.py tests/test_interim_jobs.py
git commit -m "feat: pin workflow jobs to consent and evidence"
```

### Task 3: Fail closed at claim and acknowledgement

**Files:**
- Modify: `src/wellnessbox_rnd/interim/jobs.py`
- Modify: `tests/test_interim_jobs.py`
- Test: `tests/test_interim_reviews.py`

- [ ] **Step 1: Add failing duplicate, stale-evidence, timeout, and consent-loss tests**

Cover these distinct cases: exact duplicate enqueue produces one executable row; payload conflict creates no second row; evidence mutation before claim cancels the job; a changed/absent active consent snapshot cancels the job; expired claim lease cancels instead of requeueing; evidence/consent mutation after claim makes acknowledgement cancel rather than complete. Each cancellation must have an exact reason and one deterministic open review.

```python
assert queue.claim_ready_jobs(worker_id="worker", as_of=NOW) == []
assert store.scalar("select status from workflow_jobs") == "CANCELLED"
assert store.scalar("select last_error from workflow_jobs") == "STALE_EXECUTION_EVIDENCE"
assert store.scalar("select count(*) from review_tasks") == 1
```

- [ ] **Step 2: Run the tests and confirm current recovery/ack behavior fails the contract**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_jobs.py tests/test_interim_reviews.py -q`

Expected: FAIL because expired jobs currently return to `READY`, consent/evidence are not revalidated, and no review is created.

- [ ] **Step 3: Implement one fail-closed validation path**

Inside the existing immediate claim/ack transactions, validate in this order: active plan, active consent identity, current execution-evidence identity, then claim token/lease. Convert invalid jobs to `CANCELLED`, clear lease/token, store one of `DUPLICATE_EXECUTION`, `STALE_EXECUTION_EVIDENCE`, `WORKFLOW_JOB_TIMEOUT`, or `CONSENT_NOT_ACTIVE`, and call the review service's in-transaction creation helper. Exact idempotent enqueue remains one row and therefore cannot execute twice.

- [ ] **Step 4: Run focused tests and Ruff**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_jobs.py tests/test_interim_reviews.py tests/test_interim_agent.py -q`

Run: `.venv-interim\Scripts\python.exe -m ruff check src/wellnessbox_rnd/interim/jobs.py src/wellnessbox_rnd/interim/reviews.py tests/test_interim_jobs.py tests/test_interim_reviews.py`

Expected: PASS.

- [ ] **Step 5: Commit fail-closed execution**

```powershell
git add -- src/wellnessbox_rnd/interim/jobs.py src/wellnessbox_rnd/interim/reviews.py tests/test_interim_jobs.py tests/test_interim_reviews.py tests/test_interim_agent.py
git commit -m "feat: fail closed unsafe workflow jobs"
```

### Task 4: Route serious-AE and admin decisions through the typed review service

**Files:**
- Modify: `src/wellnessbox_rnd/interim/agent.py`
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `tests/test_interim_agent.py`
- Modify: `tests/test_interim_api.py`

- [ ] **Step 1: Add failing API and serious-AE review tests**

Require serious-AE review creation to use the same deterministic service, allow an unassigned review to be completed atomically by the first valid pharmacy decision, persist the completion postcondition hash, reject malformed decisions, and return 409 for an immutable second decision.

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_agent.py tests/test_interim_api.py -q`

Expected: FAIL because the route directly updates rows and the agent directly inserts review tasks.

- [ ] **Step 3: Replace direct writes with `PharmacistReviewService` calls**

Use a strict Pydantic request model with `pharmacy_id >= 1`, a nonempty bounded decision code, and optional bounded notes. Preserve the existing `/admin/reviews` and `/admin/reviews/{review_id}/decision` routes; do not add a new human-review action to the agent state machine.

- [ ] **Step 4: Run API/agent tests and Ruff**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_agent.py tests/test_interim_api.py tests/test_interim_reviews.py -q`

Run: `.venv-interim\Scripts\python.exe -m ruff check apps/inference_api/routes/interim.py src/wellnessbox_rnd/interim/agent.py src/wellnessbox_rnd/interim/reviews.py tests/test_interim_agent.py tests/test_interim_api.py tests/test_interim_reviews.py`

Expected: PASS.

- [ ] **Step 5: Commit the route integration**

```powershell
git add -- apps/inference_api/routes/interim.py src/wellnessbox_rnd/interim/agent.py src/wellnessbox_rnd/interim/reviews.py tests/test_interim_agent.py tests/test_interim_api.py tests/test_interim_reviews.py
git commit -m "feat: enforce pharmacist review completion contract"
```

### Task 5: Build deterministic OP-077/078 evidence and claim only IMPLEMENTED

**Files:**
- Create: `scripts/run_fail_closed_job_pharmacist_review_smoke.py`
- Create: `data/original_plan/evidence/op077_op078_fail_closed_job_review_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`

- [ ] **Step 1: Write a smoke that proves the four fail-closed reasons and review completion**

Use temporary SQLite only. Emit fixed-time, deterministic cases for exact duplicate suppression, stale evidence, timeout, consent loss, and immutable pharmacist-review completion with independently recomputed SHA-256.

- [ ] **Step 2: Run the smoke twice and require byte identity**

Run twice under `etc/`, compare SHA-256, then write the canonical evidence file. Expected: identical hashes and all checks true.

- [ ] **Step 3: Make a source-first commit, regenerate canonical evidence, and update the manifest**

Claim OP-077 and OP-078 at `IMPLEMENTED` only. Both remain PARTIAL because group H requires `OPERATED`. Set deployment, service integration, and production operation flags false.

- [ ] **Step 4: Regenerate reports and update exact audit expectations**

Run: `.venv-interim\Scripts\python.exe scripts/build_original_plan_completion_report.py`

Run: `.venv-interim\Scripts\python.exe scripts/audit_original_plan_requirements.py`

Expected: PASS with generated—not hardcoded—counts.

- [ ] **Step 5: Commit evidence and generated reports with explicit paths**

Use explicit `git add -- <paths>` only; never stage protected plans or `etc/`.

### Task 6: Independent review, full verification, publication, and handoff

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`
- Potentially modify: canonical evidence files whose declared shared source identity changes

- [ ] **Step 1: Run an independent review of the clean source commit**

Require Critical `0` and Important `0`. Fix findings with systematic debugging and restart focused verification if needed.

- [ ] **Step 2: Reproduce every workflow smoke and run the exact workflow pytest selection**

Use a clean WellnessBox worktree pinned to `4d904f43b028a35524a29206aaf7c6b99f58a97b`; preserve all user changes in the service checkout. Refresh only canonical files that actually change source identity.

- [ ] **Step 3: Run full regression and frozen evaluation**

Require no failure group beyond the known 73 absent-report and 4 CGM-geometry failures. Compare all 256 frozen cases against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`; require seven zero metric deltas and unchanged overall/metric weakest categories.

- [ ] **Step 4: Apply verification-before-completion and run final checks**

Run audit, completion `--check`, full Ruff, canonical smoke byte comparison, source-hash validation, `git diff --check`, and `git diff --cached --check` after the final change.

- [ ] **Step 5: Commit, push, verify CI, and update handoff**

Push explicit commits, wait for GitHub Actions `Original plan evidence` success, then record exact counts, hashes, commits, run ID, five bottlenecks, and next loops OP-079/080, OP-081/082, and OP-083/084. Keep the overall OP-001~120 goal active.
