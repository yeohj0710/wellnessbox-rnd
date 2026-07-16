# Event Idempotency and Data Mutation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete OP-027 and OP-028 at the implementation-evidence stage by proving event-write idempotency across both log classes and by processing correction and deletion requests without breaking event lineage or immutable audit history.

**Architecture:** Reuse `execution_events`, `behavior_events`, `execution_knowledge_lineage`, and `audit_events`. Add one `event_mutations` hash-chain table plus an effective `payload_state` and effective-payload hash on both event tables. Keep the ingestion fingerprint immutable. Corrections replace only the effective payload; deletions write a tombstone, securely overwrite released SQLite pages, and truncate the WAL. Event identity, knowledge lineage, and trigger-protected append-only mutation/audit rows remain intact.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLite, pytest, Ruff.

---

### Task 1: Schema version 8 and migration safety

**Files:**
- Modify: `src/wellnessbox_rnd/interim/store.py`
- Test: `tests/test_interim_store.py`

- [x] **Step 1: Write the failing clean-schema and v7 migration tests**

```python
def test_schema_version_7_gains_event_mutation_history(tmp_path) -> None:
    store = build_version_7_database_with_one_execution_event(tmp_path)
    store.migrate()
    assert store.scalar("select max(version) from schema_migrations") == 8
    assert store.scalar(
        "select payload_state from execution_events where event_id='event_1'"
    ) == "ACTIVE"
    assert "event_mutations" in store.table_names()
```

- [x] **Step 2: Run the migration test and verify the missing schema fails**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_interim_store.py -q`

Expected: FAIL because schema version 8, `payload_state`, and `event_mutations` do not exist.

- [x] **Step 3: Add the schema and idempotency invariant**

```sql
CREATE TABLE IF NOT EXISTS event_mutations (
  mutation_id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL,
  target_type TEXT NOT NULL CHECK(target_type IN ('execution_event', 'behavior_event')),
  target_event_id TEXT NOT NULL,
  operation TEXT NOT NULL CHECK(operation IN ('correction', 'deletion')),
  idempotency_key TEXT NOT NULL,
  request_sha256 TEXT NOT NULL,
  prior_payload_sha256 TEXT NOT NULL,
  result_payload_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(profile_id, target_type, target_event_id, idempotency_key)
);
```

Add `payload_state TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(payload_state IN ('ACTIVE', 'CORRECTED', 'DELETED'))` to fresh event tables and idempotently add it to v7 tables during migration.

- [x] **Step 4: Run migration and store tests**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_interim_store.py -q`

Expected: PASS with existing rows preserved and repeated migration unchanged.

### Task 2: Automatic correction and deletion ledger

**Files:**
- Create: `src/wellnessbox_rnd/interim/data_mutation.py`
- Modify: `src/wellnessbox_rnd/interim/data_lake.py`
- Modify: `src/wellnessbox_rnd/interim/behavior_log.py`
- Test: `tests/test_event_idempotency_data_mutation.py`

- [x] **Step 1: Write failing correction, deletion, replay, and conflict tests**

```python
first = ledger.apply(
    profile_id=profile_id,
    target_type="execution_event",
    target_event_id=event_id,
    operation="correction",
    idempotency_key="correct-1",
    replacement_payload={"status": "corrected"},
)
replay = ledger.apply(...same arguments...)
assert replay.deduplicated is True
assert store.scalar("select count(*) from event_mutations") == 1
assert store.scalar("select count(*) from audit_events") == 1
assert store.scalar("select count(*) from execution_knowledge_lineage") == lineage_before
```

Also assert that changed payload under `correct-1` raises `IdempotencyConflictError`, deletion writes a tombstone, and a correction after deletion raises a state conflict.

- [x] **Step 2: Run the focused test and verify it fails**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_event_idempotency_data_mutation.py -q`

Expected: FAIL because `DataMutationLedger` is absent.

- [x] **Step 3: Implement the ledger with one immediate transaction**

```python
class DataMutationLedger:
    def apply(
        self,
        *,
        profile_id: str,
        target_type: str,
        target_event_id: str,
        operation: str,
        idempotency_key: str,
        replacement_payload: dict[str, Any] | None = None,
    ) -> EventMutationResult:
        """Apply one idempotent correction or deletion and append its audit hash chain."""
```

Resolve ownership before mutation, check an existing idempotency record before target state, update the effective event payload and state, insert one mutation row, then insert one `audit_events` row in the same transaction. Store only hashes in mutation/audit history so deletion does not copy removed payload elsewhere.

- [x] **Step 4: Expose effective payload state in existing record models**

```python
class ExecutionEventRecord(_StrictModel):
    payload_state: Literal["ACTIVE", "CORRECTED", "DELETED"]
```

Apply the same field to `BehaviorEventRecord` and row mappers.

- [x] **Step 5: Run focused ledger and existing Data Lake tests**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_event_idempotency_data_mutation.py tests/test_data_lake_lineage.py tests/test_log_separation_execution_identity.py -q`

Expected: PASS.

### Task 3: Authenticated mutation API and full event-idempotency proof

**Files:**
- Modify: `apps/inference_api/routes/interim.py`
- Test: `tests/test_event_idempotency_data_mutation.py`

- [x] **Step 1: Add failing API tests**

```python
response = client.post(
    "/v1/interim/event-mutations",
    headers=internal_headers,
    json={
        "profile_id": profile_id,
        "target_type": "execution_event",
        "target_event_id": event_id,
        "operation": "correction",
        "idempotency_key": "correct-1",
        "replacement_payload": {"status": "corrected"},
    },
)
assert response.status_code == 200
assert response.json()["deduplicated"] is False
```

Test 401 without the internal token, 404 for an unowned target, 409 for idempotency/state conflicts, and 422 for invalid correction/deletion payload combinations. Reuse the existing event and behavior endpoints to prove identical replays deduplicate and changed replays return 409 in both log classes.

- [x] **Step 2: Add strict request models and routes**

```python
@router.post("/event-mutations")
def mutate_event(payload: EventMutationRequest) -> dict[str, Any]:
    return DataMutationLedger(_store()).apply(**payload.model_dump()).model_dump(
        mode="json"
    )
```

Add `GET /event-mutations/{mutation_id}` for durable postcondition re-query.

- [x] **Step 3: Run API and OpenAPI tests**

Run: `.venv-interim/Scripts/python.exe -m pytest tests/test_event_idempotency_data_mutation.py tests/test_interim_api.py -q`

Expected: PASS.

### Task 4: Operational smoke evidence and requirement registry

**Files:**
- Create: `scripts/run_event_idempotency_data_mutation_smoke.py`
- Create: `data/original_plan/evidence/op027_op028_event_idempotency_data_mutation_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `docs/plans/2026-07-15-original-plan-completion-program.md`

- [x] **Step 1: Build an actual-route smoke**

The smoke must create one stored recommendation, replay one execution event and one behavior event, verify changed replays return 409, correct then delete a lineage-linked event, and re-query the mutation, event, lineage, and audit rows from SQLite.

- [x] **Step 2: Run the smoke twice and compare deterministic fields**

Run: `.venv-interim/Scripts/python.exe scripts/run_event_idempotency_data_mutation_smoke.py --output data/original_plan/evidence/op027_op028_event_idempotency_data_mutation_smoke_v1.json`

Expected: all checks true, schema version 8, no duplicate rows, two mutation rows, two audit rows, and unchanged knowledge-lineage row count.

- [x] **Step 3: Register OP-027 and OP-028 as `IMPLEMENTED`**

Add implementation and test evidence to the existing group C entries. Keep both requirements partial because their required stage is `OPERATED` and no production R&D process or durable production DB exists.

- [x] **Step 4: Regenerate and audit completion reports**

Run: `.venv-interim/Scripts/python.exe scripts/build_original_plan_completion_report.py`

Run: `.venv-interim/Scripts/python.exe scripts/audit_original_plan_requirements.py`

Expected: audit PASS with OP-027/028 at implementation evidence only.

### Task 5: Guardrails, documentation, review, and publication

**Files:**
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [x] **Step 1: Run CI-equivalent and frozen-evaluation checks**

Run the exact `Original plan evidence` pytest selection, `python -m ruff check .`, UTF-8/JSON checks, `git diff --check`, the official 256-case frozen evaluation, and the full pytest suite to compare against the documented baseline.

- [x] **Step 2: Record honest scope and deltas**

Document that the workflow is local `IMPLEMENTED`, not production `OPERATED`; event mutation is automatic and does not introduce a human-review action; frozen KPI deltas and replay/slice deltas must be stated from fresh outputs.

- [x] **Step 3: Request independent code review**

Review transaction atomicity, ownership checks, deletion privacy, idempotency scope, lineage preservation, schema migration, and evidence claims. Resolve all actionable findings and rerun focused checks.

Review findings required these completed corrections:

- [x] Require a configured internal token on mutation routes in every environment.
- [x] Preserve immutable ingestion hashes separately from effective payload hashes.
- [x] Add indexed mutation-chain hashes, previous pointers, a chain verifier, and append-only triggers.
- [x] Apply `secure_delete`, WAL truncation, and database compaction before deletion success returns.
- [x] Persist cleanup state and recover interrupted deletion cleanup on retry or store startup.
- [x] Snapshot pending mutation IDs so concurrent deletions cannot be marked clean prematurely.
- [x] Make the v7-to-v8 mutation-schema change atomic and preserve existing v7 event rows.
- [x] Add raw-file erasure, post-mutation replay, tamper, audit-hash, and concurrent replay tests.

- [x] **Step 4: Commit, push, and verify CI**

Stage only OP-027/028 files, keep user-owned untracked plans untouched, push `main`, and verify the `Original plan evidence` workflow succeeds.
