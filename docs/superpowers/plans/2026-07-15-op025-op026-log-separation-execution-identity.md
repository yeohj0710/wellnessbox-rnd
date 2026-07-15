# Log Separation and Execution Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store user-behavior logs and research-evaluation logs in structurally separate stores (OP-025), and record model ID, dataset IDs, code commit, and configuration hash on every persistent recommendation execution (OP-026).

**Architecture:** Reuse the OP-021/022 `InterimStore` and `ExecutionLedger`; do not create a second event system. Schema version 6 adds a `behavior_events` table whose bounded event vocabulary is disjoint from the research `execution_events` vocabulary, plus an `execution_identities` table keyed by execution ID. The actual `/v1/recommend` route records its execution identity inside the existing persistence transaction, and the authenticated trace endpoint returns the structured identity. A new authenticated behavior-event endpoint writes only to the behavior store and fails closed on missing storage consent.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, SQLite, pytest

---

### Task 1: Schema v6 with disjoint log stores and execution identity

**Files:**
- Modify: `src/wellnessbox_rnd/interim/store.py`
- Modify: `tests/test_interim_store.py`

- [x] **Step 1: Write failing schema tests**

Assert schema version 6, the new `behavior_events` and `execution_identities` tables, and a v5-fixture migration that preserves existing execution and event rows. Assert the behavior event-name CHECK vocabulary is disjoint from the research event-type CHECK vocabulary at the SQL level.

- [x] **Step 2: Add the v6 tables and bump the schema version**

`behavior_events` carries profile ID, authorizing consent snapshot, constant `log_class='user_behavior'`, a bounded behavior event-name vocabulary, occurred-at, idempotency key, payload JSON and SHA-256, data class, and created-at with a `(profile_id, event_name, idempotency_key)` uniqueness rule. `execution_identities` carries model ID, engine version, code commit with its resolution source, dataset identity JSON, config JSON, config SHA-256, and created-at, keyed by execution ID.

- [x] **Step 3: Run the store tests**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_interim_store.py -q`

Expected: PASS.

### Task 2: Execution identity recording on the actual recommendation route

**Files:**
- Create: `src/wellnessbox_rnd/interim/execution_identity.py`
- Modify: `src/wellnessbox_rnd/interim/data_lake.py`
- Create: `tests/test_log_separation_execution_identity.py`

- [x] **Step 1: Write the failing identity tests**

Post a storage-consented request to `/v1/recommend` and assert the stored identity: `model_id='deterministic_baseline_v1'`, the engine version from response metadata, four versioned runtime dataset identities (runtime knowledge DB, reference knowledge base, safety rules, ingredient catalog) each with a 64-hex SHA-256, a code commit resolved from the `WB_RND_CODE_COMMIT` environment override, and a config SHA-256 that is identical for two identical runs. The trace endpoint must return the same structured identity.

- [x] **Step 2: Implement the identity builder**

`build_execution_identity(response)` hashes the tracked runtime dataset artifacts, resolves the code commit from the environment first and the local `.git` HEAD second with an explicit `unresolved` fallback, and produces a canonical config JSON plus SHA-256. `ExecutionLedger.record_recommendation` inserts the identity row in the same transaction as the execution row, and `ExecutionTrace` exposes it as `execution_identity`.

- [x] **Step 3: Run the identity tests**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_log_separation_execution_identity.py tests/test_data_lake_lineage.py -q`

Expected: PASS.

### Task 3: Behavior log store with fail-closed separation

**Files:**
- Create: `src/wellnessbox_rnd/interim/behavior_log.py`
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `tests/test_log_separation_execution_identity.py`
- Modify: `tests/test_interim_api.py`

- [x] **Step 1: Write the failing separation tests**

Assert: a behavior event appends only to `behavior_events`; a research event type posted to the behavior endpoint returns 422; a behavior event name posted to the research execution-event endpoint returns 422; identical replays deduplicate; a same-key different-payload replay returns 409; a profile whose active consent denies survey persistent storage returns 403; the execution trace never contains behavior events; and the log-class summary reports zero cross-contamination.

- [x] **Step 2: Implement the behavior recorder and routes**

`BehaviorLogRecorder.append_event` validates the bounded behavior vocabulary, requires a timezone-aware occurred-at, checks the profile's active consent snapshot for survey persistent storage, and enforces idempotency. Add `POST /v1/interim/behavior-events` and `GET /v1/interim/log-classes`, and include the two new tables in the status counts.

- [x] **Step 3: Run the separation and API tests**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_log_separation_execution_identity.py tests/test_interim_api.py tests/test_inference_api.py -q`

Expected: PASS.

### Task 4: Produce local evidence and register honest completion stages

**Files:**
- Create: `scripts/run_log_separation_identity_smoke.py`
- Create: `data/original_plan/evidence/op025_op026_log_separation_identity_smoke_v1.json`
- Modify: `scripts/run_data_lake_lineage_smoke.py`
- Modify: `scripts/run_knowledge_lineage_smoke.py`
- Modify: `data/original_plan/evidence/op021_op022_data_lake_lineage_smoke_v1.json`
- Modify: `data/original_plan/evidence/op023_op024_knowledge_lineage_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/plans/2026-07-15-original-plan-completion-program.md`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`

- [x] **Step 1: Add a deterministic smoke and refresh the schema-6 evidence**

The new smoke uses a temporary SQLite database, a fixed `WB_RND_CODE_COMMIT` override, and the actual FastAPI routes; its aggregate output contains no timestamps or commit SHAs from the live checkout. Update the two prior lineage smokes from schema check 5 to 6 and regenerate their committed evidence.

- [x] **Step 2: Claim only IMPLEMENTED**

OP-025 and OP-026 require `OPERATED`. Register both as `IMPLEMENTED` because a local `TestClient` plus temporary SQLite proves neither a production round trip nor a production re-query. Expected regenerated status: complete 22, partial 6, pending 91, external 1.

- [x] **Step 3: Regenerate and audit**

Run: `.venv-interim\Scripts\python.exe scripts/build_original_plan_completion_report.py`

Run: `.venv-interim\Scripts\python.exe scripts/audit_original_plan_requirements.py`

Expected: audit PASS with 28 valid claims.

### Task 5: Run guardrails and publish exact files

**Files:**
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [x] **Step 1: Extend CI selection with CI-safe tests only**

Add the new test file, smoke, and modules to the workflow path filters and test selection. The new tests must not depend on ignored local artifacts.

- [x] **Step 2: Run focused and broad checks plus frozen-eval parity**

Run Ruff, the focused selection, the full suite against the known 74+4 failure baseline, and the official 256-case frozen evaluation with all seven metric deltas equal to zero.

- [x] **Step 3: Update handoff documents, commit, push, and watch CI**

Record the loop in the three handoff documents, commit only owned files to `main`, push, and confirm the Original plan evidence workflow passes.
