# Data Lake Profile and Execution Lineage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist consent-authorized profile versions and immutable consent snapshots, then connect recommendation, safety, optimization, conversation, and follow-up evaluation events with one execution ID.

**Architecture:** Extend the existing `InterimStore` SQLite database instead of introducing another database. The recommendation route creates one execution, stores consent-authorized profile partitions plus the complete consent decision, records only events that actually ran, and exposes the execution ID in its response; authenticated internal callers may later append conversation and follow-up events after the stored consent is checked.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLite, pytest, TypeScript, Zod

---

### Task 1: Freeze the storage and lineage contract with failing tests

**Files:**
- Modify: `tests/test_interim_store.py`
- Create: `tests/test_data_lake_lineage.py`
- Modify: `tests/test_inference_api.py`

- [x] **Step 1: Write the migration test**

```python
def test_interim_store_migrates_data_lake_lineage_tables(tmp_path) -> None:
    store = InterimStore(tmp_path / "lineage.sqlite3")
    store.migrate()
    assert store.scalar("select max(version) from schema_migrations") == 3
    assert {
        "profile_snapshots",
        "consent_snapshots",
        "executions",
        "execution_events",
    }.issubset(store.table_names())
```

- [x] **Step 2: Write profile and consent version tests**

```python
def test_profile_and_consent_snapshots_are_versioned_and_deduplicated(tmp_path) -> None:
    store = migrated_store(tmp_path)
    ledger = ExecutionLedger(store)
    first = ledger.record_recommendation(request=authorized_request(age=41), response=response())
    duplicate = ledger.record_recommendation(request=authorized_request(age=41), response=response())
    changed = ledger.record_recommendation(request=authorized_request(age=42), response=response())
    assert first.profile_version == duplicate.profile_version == 1
    assert changed.profile_version == 2
    assert store.scalar("select count(*) from profile_snapshots") == 2
    assert store.scalar("select count(*) from consent_snapshots") == 1
```

- [x] **Step 3: Write storage-denial and common-ID tests**

```python
def test_denied_profile_payload_is_not_persisted_but_consent_is_audited(tmp_path) -> None:
    store = migrated_store(tmp_path)
    trace = ExecutionLedger(store).record_recommendation(
        request=denied_request(), response=response()
    )
    assert trace.profile_snapshot_id is None
    assert store.scalar("select count(*) from profile_snapshots") == 0
    assert store.scalar("select count(*) from consent_snapshots") == 1

def test_all_core_events_share_the_response_execution_id(tmp_path) -> None:
    trace = record_authorized_recommendation(tmp_path)
    assert [event.event_type for event in trace.events] == [
        "recommendation",
        "safety",
        "optimization",
    ]
    assert {event.execution_id for event in trace.events} == {trace.execution_id}
```

- [x] **Step 4: Run tests and verify the contract is absent**

Run: `python -m pytest tests/test_interim_store.py tests/test_data_lake_lineage.py -q`

Expected: FAIL because schema version 3, lineage tables, and `ExecutionLedger` do not exist.

### Task 2: Add immutable versioned snapshots and an execution event ledger

**Files:**
- Modify: `src/wellnessbox_rnd/interim/store.py`
- Create: `src/wellnessbox_rnd/interim/data_lake.py`
- Test: `tests/test_interim_store.py`
- Test: `tests/test_data_lake_lineage.py`

- [x] **Step 1: Upgrade the SQLite schema**

Add schema version 3 and the following tables without changing the existing current-state tables:

```sql
CREATE TABLE IF NOT EXISTS profile_snapshots (
  profile_snapshot_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  schema_version TEXT NOT NULL,
  data_class TEXT NOT NULL,
  persisted_sources_json TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(profile_id, version),
  UNIQUE(profile_id, payload_sha256)
);

CREATE TABLE IF NOT EXISTS consent_snapshots (
  consent_snapshot_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  schema_version TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(profile_id, version),
  UNIQUE(profile_id, payload_sha256)
);

CREATE TABLE IF NOT EXISTS executions (
  execution_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  profile_snapshot_id TEXT REFERENCES profile_snapshots(profile_snapshot_id),
  consent_snapshot_id TEXT NOT NULL REFERENCES consent_snapshots(consent_snapshot_id),
  request_sha256 TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_events (
  event_id TEXT PRIMARY KEY,
  execution_id TEXT NOT NULL REFERENCES executions(execution_id),
  event_index INTEGER NOT NULL,
  event_type TEXT NOT NULL CHECK(event_type IN (
    'conversation','recommendation','safety','optimization','followup_evaluation'
  )),
  source TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(execution_id, event_index),
  UNIQUE(execution_id, event_type, idempotency_key)
);
```

- [x] **Step 2: Implement one ledger over the existing store**

Implement `ExecutionLedger.record_recommendation`, `append_event`, and `get_trace`. Canonicalize JSON with sorted keys, reuse an unchanged snapshot by hash, increment the per-profile version only when content changes, and write each recommendation transaction atomically.

- [x] **Step 3: Enforce source-specific persistence consent**

Persist the survey partition only when `survey.allow_persistent_storage` is true. Persist each laboratory observation only under its declared source and only when that source allows storage. Always retain the consent decision snapshot, but do not retain denied raw profile fields in any event payload.

- [x] **Step 4: Run the focused storage tests**

Run: `python -m pytest tests/test_interim_store.py tests/test_data_lake_lineage.py -q`

Expected: PASS.

### Task 3: Connect the real recommendation route and internal delayed events

**Files:**
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Modify: `src/wellnessbox_rnd/orchestration/recommendation_service.py`
- Modify: `apps/inference_api/routes/recommend.py`
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `tests/test_inference_api.py`
- Modify: `tests/test_interim_api.py`

- [x] **Step 1: Expose the common execution ID**

Add `execution_id: str` to `RecommendationResponse`. Generate one `exec_<uuid>` value at the start of `recommend` and return that same value from blocked and successful branches.

- [x] **Step 2: Persist actual recommendation execution**

After `recommend(payload)` succeeds, call `ExecutionLedger.record_recommendation`. Record exactly the stages that executed: recommendation, safety, and optimization. Do not fabricate a conversation or follow-up event.

- [x] **Step 3: Add authenticated delayed-event endpoints**

Add `POST /v1/interim/executions/{execution_id}/events` for `conversation` and `followup_evaluation`, and `GET /v1/interim/executions/{execution_id}` for trace retrieval. Reject event storage when the event source's saved consent has `allow_persistent_storage=false`; deduplicate matching idempotency keys and reject conflicting replays.

- [x] **Step 4: Prove all five event categories share one ID**

Run the recommendation endpoint, append one conversation event and one follow-up evaluation event, retrieve the trace, and assert that all event rows carry the response's `execution_id`.

- [x] **Step 5: Run the API tests**

Run: `python -m pytest tests/test_inference_api.py tests/test_interim_api.py tests/test_data_lake_lineage.py -q`

Expected: PASS.

### Task 4: Preserve a stable pseudonymous subject across service profile changes

**Files:**
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts`
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-profile-adapter.ts`
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-recommend-preview-payload.ts`
- Modify: `C:/dev/wellnessbox/contracts/wb-rnd/profile-adapter-v1.json`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-profile-adapter.cts`
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Modify: `tests/test_wellnessbox_profile_adapter_contract.py`

- [x] **Step 1: Extend the cross-repository source envelope**

Add optional `subject_id` with the existing `usr_<hex>` pseudonym format to `source_profile`. Add optional `subjectId` to adapter options and forward it without including it in the health payload.

- [x] **Step 2: Freeze the stable-version behavior**

Use one `subject_id` for two requests whose profile ages differ. Assert that R&D stores versions 1 and 2 under the same `profile_id`, while the raw WellnessBox database identifier never appears in the R&D request or database.

- [x] **Step 3: Run both repository contract suites**

Run in `C:/dev/wellnessbox`: `npm run qa:rnd:profile-adapter`

Run in `C:/dev/wellnessbox-rnd`: `python -m pytest tests/test_wellnessbox_profile_adapter_contract.py tests/test_data_lake_lineage.py -q`

Expected: PASS.

### Task 5: Generate operational evidence and update the 120-step ledger

**Files:**
- Create: `scripts/run_data_lake_lineage_smoke.py`
- Create: `data/original_plan/evidence/op021_op022_data_lake_lineage_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `docs/plans/2026-07-15-original-plan-completion-program.md`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [x] **Step 1: Add a repeatable local runtime smoke runner**

The runner must use a temporary SQLite database, call the actual FastAPI recommendation route, append the two delayed event types through the authenticated internal API, reopen the database, and fail unless profile versioning, consent versioning, consent denial, and the five common-ID event types are present.

- [x] **Step 2: Write deterministic local evidence**

Run: `python scripts/run_data_lake_lineage_smoke.py --output data/original_plan/evidence/op021_op022_data_lake_lineage_smoke_v1.json`

Expected: JSON with `status: "passed"`, `profile_version_count: 2`, `denied_profile_payload_count: 0`, and all five event types.

- [x] **Step 3: Claim only proven stages**

Mark OP-021 and OP-022 `IMPLEMENTED`. Register the implementation, contract tests, and local smoke result without presenting a `TestClient` plus temporary SQLite run as two-process integration or production operation evidence.

- [x] **Step 4: Regenerate and validate the completion report**

Run: `python scripts/build_original_plan_completion_report.py`

Run: `python scripts/audit_original_plan_requirements.py`

Expected: both commands exit 0 and the completion report shows OP-021 and OP-022 partial until two-process integration and production re-query evidence exist.

### Task 6: Run guardrails, frozen evaluation, and publish exact commits

**Files:**
- Modify only the files listed in Tasks 1 through 5.

- [x] **Step 1: Run R&D quality gates**

Run: `python -m ruff check .`

Run: `python -m pytest tests/test_interim_store.py tests/test_data_lake_lineage.py tests/test_inference_api.py tests/test_interim_api.py tests/test_wellnessbox_profile_adapter_contract.py tests/test_original_plan_manifest.py tests/test_original_plan_audit.py -q`

Run: `python -m pytest -q`

Expected: focused tests PASS; any full-suite failures must be compared with the frozen legacy baseline instead of hidden.

- [x] **Step 2: Prove frozen-eval parity**

Run the repository's official frozen-eval command recorded in `README.md` or the current evaluation scripts and compare all seven metrics with the pre-loop 256-case baseline. Expected metric delta for every metric: `0`.

- [x] **Step 3: Run WellnessBox gates**

Run in `C:/dev/wellnessbox`: `npm run qa:rnd:profile-adapter`

Run in `C:/dev/wellnessbox`: `npx tsc --noEmit`

Run in `C:/dev/wellnessbox`: `npm run audit:encoding`

Run in both repositories: `git diff --check`

Expected: PASS.

- [x] **Step 4: Commit and push only owned files**

Create one exact WellnessBox contract commit and one exact R&D implementation/evidence commit. Do not stage the ten protected WellnessBox files or `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md`. Push both `main` branches and verify `HEAD == origin/main`.
