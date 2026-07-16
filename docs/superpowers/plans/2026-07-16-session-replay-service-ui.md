# OP-029/030 Session Replay and Service UI Implementation Plan

> **For Codex:** Execute this plan one task at a time. Preserve the existing KPI replay and Data Lake event paths; this plan adds execution-session replay without creating a parallel recommendation engine.

**Goal:** Persist replayable recommendation-session snapshots, replay them only under the exact stored runtime identity, and let the WellnessBox TIPS evaluator query saved-session counts and inspect replay results.

**Architecture:** Extend the existing R&D `ExecutionLedger` and SQLite store rather than creating another session store. Schema version 9 adds one replay snapshot per execution and an append-only replay-run history. The authenticated interim API lists replayable sessions and performs fail-closed replay after comparing model, engine, code, dataset, and configuration identities. The WellnessBox lab runtime calls those endpoints through the existing authenticated `wb-rnd-interim-client`; the evaluator UI shows connection state, saved counts, and input/version/output checks without exposing raw payloads.

**Status (2026-07-16):** Tasks 1 through 7 are complete at the proven `IMPLEMENTED` boundary. Both repository commits and CI runs passed, the WellnessBox deployment is `Ready` with the `wellnessbox.kr` alias, and a headed Chrome check confirmed the explicit disconnected panel. Production still has no deployed R&D process or `WB_RND_*` settings, so OP-029/030 remain below `OPERATED`. The detailed checklists below preserve the original execution plan; `PROGRESS.md` records the verified results.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLite, pytest; Next.js App Router, React, TypeScript, Prisma-backed TIPS lab state, existing `WB_RND_INTERIM_*` service client.

---

## Task 1: Prove the current gap and lock the replay contract

**Files:**
- Create: `tests/test_session_replay.py`
- Modify: `tests/test_interim_store.py`

- [ ] Assert schema version 9 and the `execution_replay_snapshots` and `execution_replay_runs` tables.
- [ ] Assert a persistently consented `/v1/recommend` execution stores one canonical request snapshot and one stable expected-output snapshot.
- [ ] Assert non-persistable input creates the execution trace but not a replay snapshot.
- [ ] Assert saved-session summary distinguishes total executions from replayable executions and returns bounded newest-first items.
- [ ] Assert replay returns `MATCH` for the same input and identity, even though run IDs and timestamps change.
- [ ] Assert code, dataset, model, engine, or config mismatch returns `VERSION_MISMATCH` without invoking the recommendation engine.
- [ ] Assert a changed stable output returns `MISMATCH`, and every replay attempt appends a queryable result row.
- [ ] Assert all replay routes require the existing internal token and reject invalid execution IDs or missing sessions.

Run: `python -m pytest tests/test_session_replay.py tests/test_interim_store.py -q`
Expected before implementation: FAIL because schema 9 and replay APIs do not exist.

## Task 2: Persist canonical replay snapshots and version identity

**Files:**
- Modify: `src/wellnessbox_rnd/interim/store.py`
- Modify: `src/wellnessbox_rnd/interim/execution_identity.py`
- Modify: `src/wellnessbox_rnd/interim/data_lake.py`

- [ ] Raise `SCHEMA_VERSION` to 9.
- [ ] Add `execution_replay_snapshots` keyed by `execution_id`, with canonical request JSON/hash, stable expected-output JSON/hash, and creation time.
- [ ] Add append-only `execution_replay_runs` with replay status, version/input/output booleans, expected/actual hashes, bounded mismatch fields, and timestamp.
- [ ] Add no-update/no-delete triggers for replay snapshots and replay-run audit rows.
- [ ] Add a reusable current-runtime identity builder so replay can compare the active runtime before recommendation execution.
- [ ] Define the stable response projection by excluding only generated execution ID, decision ID, and metadata timestamp. Keep all recommendation, safety, evidence, action, limitation, and engine fields.
- [ ] Store a replay snapshot in the same transaction as the original execution only when all input used for recommendation permits persistent storage.
- [ ] Preserve all schema 8 rows during migration and make migration idempotent.

## Task 3: Implement deterministic replay and authenticated API routes

**Files:**
- Create: `src/wellnessbox_rnd/interim/session_replay.py`
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `src/wellnessbox_rnd/interim/__init__.py`

- [ ] Add a typed saved-session summary that reports total, replayable, non-replayable, and replay-run counts plus bounded recent sessions.
- [ ] Add `GET /v1/interim/executions?limit=...` under the existing internal-token dependency.
- [ ] Add `POST /v1/interim/executions/{execution_id}/replay` under the same dependency.
- [ ] Load and validate the original canonical request; verify its hash matches the execution and replay snapshot.
- [ ] Compare active model ID, engine version, code commit, dataset hashes, and config hash with the stored execution identity before calling `recommend`.
- [ ] On exact identity, run the existing deterministic `recommend` function and compare the stable response hash with the stored expected hash.
- [ ] Persist and return only bounded replay evidence; never return the raw health-profile request or full stored response from these endpoints.

Run: `python -m pytest tests/test_session_replay.py tests/test_interim_store.py tests/test_data_lake_lineage.py tests/test_inference_api.py tests/test_interim_api.py -q`
Expected: PASS.

## Task 4: Produce deterministic R&D evidence and update the requirement ledger

**Files:**
- Create: `scripts/run_session_replay_service_ui_smoke.py`
- Create: `data/original_plan/evidence/op029_op030_session_replay_service_ui_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md` through its generator
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`

- [ ] Exercise the actual FastAPI recommendation, list, and replay routes against a temporary SQLite database.
- [ ] Prove one `MATCH`, one fail-closed `VERSION_MISMATCH`, saved-session counts, token enforcement, persisted replay-run history, and byte-identical evidence across reruns.
- [ ] Record OP-029 as `IMPLEMENTED` with R&D implementation and test evidence.
- [ ] Do not claim OP-030 above its proven stage until the WellnessBox UI and cross-repository contract checks pass.
- [ ] Regenerate and audit the completion report.

## Task 5: Connect the WellnessBox lab runtime to the replay API

**Files:**
- Create: `C:/dev/wellnessbox/lib/server/tips-lab/rnd-session-replay.ts`
- Modify: `C:/dev/wellnessbox/lib/server/tips-lab/runtime.ts`
- Modify: `C:/dev/wellnessbox/lib/server/tips-lab/state.ts`
- Modify: `C:/dev/wellnessbox/app/api/tips/lab/route.ts` only if response/error mapping requires it
- Create: `C:/dev/wellnessbox/scripts/qa/check-tips-rnd-session-replay.cts`
- Modify: `C:/dev/wellnessbox/package.json`

- [ ] Reuse `callWbRndInterim`; do not create a second HTTP client or accept browser-supplied R&D credentials.
- [ ] Add `list_rnd_sessions` and `replay_rnd_session` lab actions that keep the current state unchanged.
- [ ] Validate execution IDs server-side and map the R&D contract to a bounded Korean-facing view model.
- [ ] Return an explicit `connected=false` state when `WB_RND_INTERIM_*` is disabled or incomplete; never substitute local KPI replay or a fabricated success.
- [ ] Test actual request paths, internal-token forwarding, timeout/error handling, and response validation with a local HTTP test server.

## Task 6: Add the saved-session count and replay-result evaluator UI

**Files:**
- Modify: `C:/dev/wellnessbox/components/tips/InterimUserConsole.tsx`
- Modify: `C:/dev/wellnessbox/components/tips/interim.module.css`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-tips-interim-modules.cts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-tips-web-lab.cts`

- [ ] Show R&D connection state, total saved sessions, replayable sessions, and replay-run count in the “추천 이후 기록” stage.
- [ ] Let the evaluator refresh the session list and replay a selected recent session.
- [ ] Show separate input, runtime-version, and output checks and a Korean result label for `MATCH`, `MISMATCH`, or `VERSION_MISMATCH`.
- [ ] Keep raw request JSON, health data, hashes, and internal status codes out of the default view.
- [ ] Keep the fixed previous/help/next evaluator controls and avoid nested modals or internal scrolling.
- [ ] Add accessible control labels and explicit unavailable/error recovery copy.

## Task 7: Verify, publish, deploy, and inspect the real boundary

**R&D verification:**
- [ ] `python -m pytest <CI-equivalent focused selection> -q`
- [ ] `python -m pytest -q` and classify only pre-existing unrelated failures with exact counts.
- [ ] `python -m ruff check .`
- [ ] Run the replay smoke twice and compare SHA-256.
- [ ] Run manifest audit and completion-report stale check.
- [ ] Run the frozen evaluation and prove all tracked KPI deltas remain zero.
- [ ] `git diff --check` and encoding audit.

**WellnessBox verification:**
- [ ] `npm run qa:tips:rnd-session-replay`
- [ ] `npm run qa:tips:web-lab`
- [ ] `npm run qa:tips:interim`
- [ ] `npm run qa:tips:data-lake` if the local Data Lake path changes.
- [ ] `npx tsc --noEmit`
- [ ] `npm run audit:encoding`
- [ ] `npm run lint`
- [ ] `git diff --check`
- [ ] `npm run build`

**Publication and runtime proof:**
- [ ] Review both diffs and stage only OP-029/030 files; preserve all listed user-owned changes.
- [ ] Commit and push each repository's `main` separately.
- [ ] Confirm the R&D GitHub evidence workflow passes.
- [ ] Deploy WellnessBox production, inspect `Ready`, and confirm the `wellnessbox.kr` alias.
- [ ] In a real browser, sign in to `/tips`, inspect the panel, refresh saved sessions, and attempt replay.
- [ ] State the exact boundary: without a deployed R&D base URL and production `WB_RND_INTERIM_*` variables, the UI must show “R&D 서버 미연결” and OP-029/030 remain below `OPERATED`; do not claim both processes run together until a successful production round trip and postcondition re-query prove it.
