# Counseling session and service adapter implementation plan

> **For Codex:** Execute this plan task by task with test-first changes. Preserve all pre-existing service worktree changes and stage only loop-owned paths.

**Goal:** Store the verified R&D counseling answer and its recommendation execution identity in the existing WellnessBox chat session, and make the existing service chat route call the R&D counseling API through a thin adapter.

**Architecture:** Add one authenticated R&D counseling endpoint that composes the existing bounded answer generator and existing recommendation execution path. Return a versioned response containing the answer, verification trace, and execution identity. Extend the existing service-side R&D client with a contract validator, invoke it from the existing `/api/chat` route when a real `sessionId` is present, and persist the answer plus execution metadata through the existing `ChatSession` and `ChatMessage` models. Do not add a second chat or event store.

**Tech stack:** FastAPI, Pydantic, SQLite execution ledger, Next.js App Router, TypeScript, Prisma, Vitest/Node QA, pytest.

---

### Task 1: Freeze the cross-repository contract with failing tests

- Add R&D API tests covering authentication, verified answer output, recommendation execution identity, idempotency, and urgent-safety suppression.
- Add service tests covering environment gating, pseudonymous subject identity, strict response validation, timeout/error behavior, and use of the supplied chat session ID.
- Run only the new tests and retain the expected initial failures.

### Task 2: Implement the R&D counseling composition endpoint

- Reuse `generate_chat_answer_with_openai_fallback` and the approved counseling scope.
- Reuse `ExecutionLedger.record_recommendation`; do not create a parallel recommendation table.
- Bind one immutable counseling request identity to the caller's chat session ID and return the existing execution ID.
- Require the existing internal token header and reject malformed or conflicting idempotent requests.
- Run focused R&D tests and Ruff on changed Python files.

### Task 3: Implement the thin service adapter

- Extend `lib/server/wb-rnd-interim-client.ts` or a narrowly adjacent module instead of creating another generic HTTP client.
- Invoke the R&D counseling endpoint from the existing chat route only when the feature flag and required session/profile inputs are present.
- Persist the returned assistant answer and recommendation execution identity through existing `persistChatSession` and Prisma `meta` fields.
- Preserve the existing model-backed chat path as the disabled/unavailable fallback until OP-089 defines the deterministic provider-failure policy.
- Run focused service tests, encoding audit, lint, and build.

### Task 4: Prove actual local integration

- Start the real FastAPI application on localhost with an isolated SQLite database.
- Execute the real service route/adapter against that process.
- Read back the existing service chat session and R&D execution ledger to prove that the same session identity connects the stored answer and recommendation execution.
- Run the smoke twice and require byte-identical canonical payloads after removing runtime-only process data.

### Task 5: Record evidence without overstating stages

- Commit source first in each repository.
- Generate canonical evidence from committed source identities.
- Claim OP-088 `INTEGRATED` only after the two-process proof succeeds.
- Keep OP-087 below required `OPERATED` unless production operation evidence exists.
- Write long-form Korean prose research reports for OP-087 and OP-088. Explain the requirement, reused paths, design decisions, failures, corrections, tests, limitations, and stage decision in full sentences.
- Regenerate the manifest-derived completion report.

### Task 6: Complete regression and independent review

- Run focused tests, workflow-equivalent tests, all deterministic smokes, Ruff, full pytest, frozen evaluation, source hashes, audit, completion check, and both diff checks.
- Request an independent sub-agent review of the final cross-repository tree and resolve every Critical or Important finding.
- Stage explicit loop-owned paths only, commit, push, and verify the triggered GitHub Actions evidence workflow.
- Record only final verified counts, hashes, commits, and CI run IDs in handoff documents.
