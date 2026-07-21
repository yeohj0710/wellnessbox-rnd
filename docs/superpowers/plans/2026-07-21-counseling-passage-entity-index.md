# Counseling Passage and Entity Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-081 and OP-082 by enriching the existing counseling retrieval corpus with source/effective-date lineage and extracting bounded question entities from the existing runtime knowledge database.

**Architecture:** Extend `wellnessbox_rnd.chat.retrieval` instead of adding another knowledge store. Retrieval chunks remain claim/passage records but gain validated source metadata copied from `reference_knowledge_base_v1`; deterministic question extraction uses the aliases, medications, conditions, and fixed health-goal vocabulary already present in `runtime_knowledge_db_v1`. A smoke builds both outputs from committed artifacts and proves deterministic identity without claiming deployment or production use.

**Tech Stack:** Python 3.11, Pydantic v2, committed JSON/JSONL knowledge artifacts, pytest, Ruff.

---

### Task 1: Lock the passage-lineage and entity contracts

**Files:**
- Modify: `src/wellnessbox_rnd/chat/retrieval.py`
- Modify: `tests/test_chat_retrieval.py`

- [ ] Add failing tests that reject passage chunks without timezone-aware `effective_at`, preserve reference URI/license/line span, reject retired passages at the query time, and reject manifest count mismatches.
- [ ] Add failing tests that extract one or more health goals, canonical ingredient IDs, medication IDs, condition/risk keys, urgent symptom signals, and matched spans without substring false positives.
- [ ] Run `python -m pytest tests/test_chat_retrieval.py -q` and require failures at the missing contracts.
- [ ] Implement frozen Pydantic contracts, deterministic longest-alias matching, Unicode-aware normalization, explicit Korean/English goal aliases, and a small fixed urgent-signal vocabulary. Do not infer diagnoses or use an LLM.
- [ ] Run the focused test again and require PASS.

### Task 2: Reuse the existing reference and runtime knowledge artifacts

**Files:**
- Modify: `scripts/build_chat_retrieval_assets.py`
- Modify: `tests/test_chat_retrieval.py`

- [ ] Add a failing test that builds chunks from parsed claims plus `reference_knowledge_base_v1` and requires the exact source title, URI, license, effective date, retirement date, section, and line range.
- [ ] Change `_build_chunk_from_claim` to require the matching committed reference metadata. Fail closed on missing references, duplicate reference IDs, invalid dates, or claims whose source fields disagree with the reference registry.
- [ ] Keep `chunk::<claim_id>` identity and the existing retrieval score behavior so OP-083 can later add an allow-list without replacing this corpus.
- [ ] Run `python -m pytest tests/test_chat_retrieval.py tests/test_runtime_knowledge_db.py -q` and require PASS.
- [ ] Commit the source and focused tests before generating canonical evidence.

### Task 3: Generate deterministic OP-081/082 evidence

**Files:**
- Create: `scripts/run_counseling_passage_entity_smoke.py`
- Create: `data/original_plan/evidence/op081_op082_counseling_passage_entity_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`

- [ ] Build the complete passage corpus from committed claims and reference metadata. Record passage count, unique source count, date/lineage completeness, retirement filtering, and source hashes.
- [ ] Run representative Korean and English questions that cover multiple goals, ingredient aliases, warfarin/Coumadin, kidney conditions, urgent bleeding/chest-pain signals, and a safe no-entity question. Record canonical entities and matched text.
- [ ] Run the smoke twice to separate files and require byte-identical SHA-256 values before writing the canonical evidence path.
- [ ] Add the smoke, focused tests, and Ruff targets to the existing `Original plan evidence` workflow.
- [ ] Commit canonical evidence only after source identity points to the source-first commit.

### Task 4: Record honest stages and full prose reports

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Create: `docs/original_plan/research_reports/OP-081.md`
- Create: `docs/original_plan/research_reports/OP-082.md`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`

- [ ] Claim OP-081 and OP-082 only at `IMPLEMENTED`, their required stage, when canonical evidence and tests pass.
- [ ] Write one long Korean prose report per OP. Explain the existing artifact reuse, lineage fields, extraction boundaries, failed approaches, deterministic cases, evidence limitations, and absence of service/operation claims.
- [ ] Run the manifest audit and completion-report generator. Use generated counts rather than editing expected totals by hand.
- [ ] Update manifest/completion regression expectations to include OP-081 and OP-082.

### Task 5: Run completion gates and publish

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] Run focused tests, exact workflow selection, every workflow smoke, full Ruff, and full pytest. Require no failure group beyond the known 73 absent-report and four CGM-geometry failures.
- [ ] Run the 256-case frozen eval against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`; require seven zero metric deltas and unchanged overall and metric-specific weakest categories.
- [ ] Request an independent review and require Critical 0 / Important 0 before final claims.
- [ ] Update handoff documents with actual counts, hashes, report coverage `4/120`, commits, and CI run.
- [ ] Stage only loop-owned files, push, and require the GitHub Actions `Original plan evidence` run to pass.
