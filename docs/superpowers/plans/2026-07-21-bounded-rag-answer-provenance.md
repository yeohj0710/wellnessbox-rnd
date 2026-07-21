# Bounded RAG Answer Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing counseling retrieval path search only a repository-approved knowledge scope and make every supported answer expose evidence identity, answer-time validity, and reconciled uncertainty.

**Architecture:** Extend the existing immutable retrieval contracts with a versioned `BoundedKnowledgeScope`; do not add a second corpus or retriever. Pass one timezone-aware `as_of` value through retrieval, deterministic answering, and the OpenAI adapter. Extend citations and answers with validity and uncertainty fields, and verify those fields against the exact selected chunks.

**Tech Stack:** Python 3.11+, Pydantic v2, deterministic lexical retrieval, pytest, Ruff, JSON smoke evidence.

---

### Task 1: Pin the allowed counseling knowledge scope

**Files:**
- Modify: `src/wellnessbox_rnd/chat/retrieval.py`
- Modify: `src/wellnessbox_rnd/chat/__init__.py`
- Test: `tests/test_chat_retrieval.py`

- [ ] **Step 1: Write failing policy tests**

Add tests that construct a scope with explicit allowed source types, claim types, and reference IDs; confirm retrieval excludes a disallowed chunk, rejects a timezone-naive `as_of`, rejects an empty allowlist, and returns only active passages.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python -m pytest tests/test_chat_retrieval.py -q`

Expected: FAIL because `BoundedKnowledgeScope` and `retrieve_bounded_chunks` do not exist.

- [ ] **Step 3: Implement the immutable scope and bounded retriever**

Add `BoundedKnowledgeScope` with `scope_id`, `allowed_source_types`, `allowed_claim_types`, `allowed_reference_ids`, and `max_results`. Reconcile non-empty unique sorted allowlists. Add `retrieve_bounded_chunks(manifest, scope, query, as_of, top_k)` that requires a timezone-aware answer time, rejects `top_k` above the scope limit, filters by all three allowlists and passage validity, and delegates scoring to the current deterministic scorer.

- [ ] **Step 4: Run focused tests and lint**

Run: `python -m pytest tests/test_chat_retrieval.py -q`

Run: `python -m ruff check src/wellnessbox_rnd/chat tests/test_chat_retrieval.py`

Expected: PASS.

- [ ] **Step 5: Commit the policy contract**

Stage only the three listed files and commit `feat: bound counseling retrieval scope`.

### Task 2: Carry evidence validity and uncertainty into answers

**Files:**
- Modify: `src/wellnessbox_rnd/chat/answering.py`
- Modify: `src/wellnessbox_rnd/chat/openai_adapter.py`
- Test: `tests/test_chat_retrieval.py`
- Test: `tests/test_chat_openai_adapter.py`

- [ ] **Step 1: Write failing answer-contract tests**

Add tests requiring supported answers to include the answer time, scope ID, citation effective/retired dates, active-at-answer flag, an uncertainty level, and concrete uncertainty reasons. Add tampering tests for a forged active flag, mismatched scope ID, omitted uncertainty, and a retired passage selected after retirement.

- [ ] **Step 2: Run tests and confirm the contract is absent**

Run: `python -m pytest tests/test_chat_retrieval.py tests/test_chat_openai_adapter.py -q`

Expected: FAIL on the missing fields and parameters.

- [ ] **Step 3: Extend deterministic and provider-backed answers**

Add an immutable `AnswerUncertainty` contract. Require `scope` and timezone-aware `as_of` in bounded answer generation. Build citations from selected chunks with their exact IDs and validity dates. Derive uncertainty conservatively from claim type: mixed, limited, inconclusive, null-without-deficiency, and policy claims must state their limitation; other claims still state that the answer is bounded to the cited passage and is not individualized clinical certainty. Make the OpenAI adapter use the same bounded selection and reconstruct provider citations only from selected chunks.

- [ ] **Step 4: Strengthen verification without claiming OP-085**

Allow `verify_bounded_template_answer` to receive the manifest, scope, and answer time. Recompute selected-chunk identity, citation dates, active state, scope membership, and uncertainty reconciliation. This verifies OP-084 fields but does not yet implement the full unsupported-claim/risk/forbidden-expression verifier owned by OP-085.

- [ ] **Step 5: Run focused and downstream tests**

Run: `python -m pytest tests/test_chat_retrieval.py tests/test_chat_openai_adapter.py tests/test_learned_runtime_boundary_audit.py -q`

Expected: PASS.

- [ ] **Step 6: Commit answer provenance**

Stage only the four listed files and commit `feat: expose answer validity and uncertainty`.

### Task 3: Produce deterministic OP-083/084 evidence and reports

**Files:**
- Create: `scripts/run_bounded_rag_answer_provenance_smoke.py`
- Create: `data/original_plan/evidence/op083_op084_bounded_rag_answer_provenance_smoke_v1.json`
- Create: `docs/original_plan/research_reports/OP-083.md`
- Create: `docs/original_plan/research_reports/OP-084.md`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`

- [ ] **Step 1: Write the smoke before claiming evidence**

Build the current 24-passage corpus, use one explicit repository-approved scope, test supported/unsupported/out-of-scope/retired/disallowed-source cases, and prove citation and uncertainty reconciliation. Record source/data hashes and explicit false values for service integration, deployment, operation, external validation, and live LLM inference.

- [ ] **Step 2: Run the smoke twice**

Run the smoke twice to separate temporary files and compare bytes. Expected: byte-identical JSON and matching source/data identities.

- [ ] **Step 3: Write full prose research reports**

Write separate Korean prose reports for OP-083 and OP-084. Explain the original requirement, reused code path, threat boundary, implementation, test cases, failures found, evidence, limitations, and stage decision in complete sentences rather than compressed bullets.

- [ ] **Step 4: Update manifest and generated completion reports**

Claim only `IMPLEMENTED` for OP-083/084 after smoke and focused tests pass. Regenerate completion outputs with `scripts/build_original_plan_completion_report.py`; do not hardcode counts.

- [ ] **Step 5: Add the smoke to CI and commit evidence**

Add exact script/test/lint paths to `Original plan evidence`, stage only loop-owned files, and commit.

### Task 4: Verify, review, publish, and hand off

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] **Step 1: Run focused, workflow-equivalent, and full regression**

Run focused tests, every workflow smoke, the exact workflow pytest selection, full Ruff, and full pytest. Confirm any red tests remain only the established absent-report and CGM geometry groups.

- [ ] **Step 2: Run frozen evaluation comparison**

Run all 256 frozen cases against the OP-035/036 report. Confirm seven metric deltas and every weakest-slice category delta.

- [ ] **Step 3: Request independent review**

Use a sub-agent to inspect the latest tree for scope bypass, stale evidence selection, citation tampering, false certainty, and duplicated systems. Fix every Critical or Important finding and restart verification after source changes.

- [ ] **Step 4: Run final audit and publish**

Run manifest audit, completion check, all smokes, source hashes, Ruff, `git diff --check`, and `git diff --cached --check`. Push the loop-owned commits and wait for `Original plan evidence` to succeed.

- [ ] **Step 5: Record exact final results**

Update the three handoff documents with actual hashes, test counts, CI run ID, report coverage `6/120`, explicit stage boundaries, five bottlenecks, and the next three loops.
