# Counseling Verifier and Urgent Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-085 and OP-086 by making every counseling response pass a repository-owned verifier and by returning deterministic emergency guidance before retrieval or recommendation for a positively detected urgent-risk question.

**Architecture:** Extend the existing question-entity, bounded retrieval, template answer, and OpenAI adapter path instead of adding a second counseling system. Put the versioned verification policy in the current knowledge-data tree, keep final answer construction server-owned, and make one verifier recompute grounding, risk coverage, forbidden-language checks, and emergency precedence from the original question and approved evidence.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, JSON knowledge registries, existing deterministic smoke/audit tooling, Ruff, GitHub Actions.

---

### Task 1: Lock the verifier and emergency contracts with failing tests

**Files:**
- Modify: `tests/test_chat_retrieval.py`
- Modify: `tests/test_chat_openai_adapter.py`

- [ ] **Step 1: Add verifier rejection tests**

Add cases that start from a valid supported answer and separately alter the answer text to add an uncited clinical claim, remove a cited interaction risk, insert repository-forbidden diagnosis or guaranteed-outcome language, and add recommendation language to an emergency response. Assert exact verifier issue codes for each mutation.

- [ ] **Step 2: Add urgent-precedence tests**

Add positive, explicit-negation, and contrast-clause questions. Assert that a positive urgent signal returns `safety_escalation`, begins with the repository emergency instruction, contains no supplement recommendation, has no evidence citations, and never invokes the provider. Assert that negated urgent wording continues through the ordinary bounded path.

- [ ] **Step 3: Run the new tests and record the expected failure**

Run `python -m pytest tests/test_chat_retrieval.py tests/test_chat_openai_adapter.py -q`. Expect failures because the policy registry, verifier fields, safety-escalation status, and emergency short circuit do not exist yet.

### Task 2: Add one repository-owned counseling verification policy

**Files:**
- Create: `data/knowledge/counseling_answer_verifier_policy_v1.json`
- Create: `src/wellnessbox_rnd/chat/verifier.py`
- Modify: `src/wellnessbox_rnd/chat/__init__.py`

- [ ] **Step 1: Define the policy data**

Create a versioned, fail-closed JSON policy containing the allowed answer statuses and templates, forbidden claim categories and expressions, urgent-risk keys already produced by question extraction, the exact emergency guidance sequence, and phrases that count as recommendation language. Keep medical diagnosis, guaranteed safety/effect, dosage direction, and delayed-emergency language forbidden.

- [ ] **Step 2: Validate repository identity**

Implement immutable Pydantic models and `load_counseling_answer_verifier_policy()`. Reject unknown fields, duplicate or unsorted values, missing urgent keys, empty guidance, and a caller-supplied policy that is not exactly equal to the repository file.

- [ ] **Step 3: Implement recomputed verification**

Implement a verifier result with separate booleans for evidence grounding, unsupported-claim suppression, required-risk coverage, forbidden-expression absence, emergency precedence, and policy identity. Recompute question entities from the runtime knowledge database, rebuild the expected server template from selected chunks, and return stable issue codes instead of trusting answer metadata.

- [ ] **Step 4: Run focused verifier tests**

Run `python -m pytest tests/test_chat_retrieval.py -q`. Expect all retrieval, answer, verifier, and urgent-safety tests to pass.

- [ ] **Step 5: Commit the policy and verifier**

Stage only the policy, verifier, exports, and focused test file. Commit with `feat: add counseling answer safety verifier`.

### Task 3: Make emergency guidance precede retrieval and provider generation

**Files:**
- Modify: `src/wellnessbox_rnd/chat/answering.py`
- Modify: `src/wellnessbox_rnd/chat/openai_adapter.py`
- Modify: `tests/test_chat_openai_adapter.py`

- [ ] **Step 1: Build the emergency answer before retrieval**

Pass the existing runtime knowledge database into answer generation. Run `extract_question_entities()` first. When a non-negated urgent key exists, return a deterministic `safety_escalation` answer whose first sentence directs immediate emergency help, whose later sentences stop supplement use and prohibit waiting for chat advice, and whose structured safety trace lists the exact detected keys.

- [ ] **Step 2: Keep final prose server-owned**

Change the live provider schema so the provider may choose only status and approved chunk identifiers. Ignore provider-authored prose and render the final supported, unsupported, or out-of-scope response from repository templates. Reject status/chunk combinations that do not reconcile.

- [ ] **Step 3: Short-circuit the adapter**

Before config loading, bounded retrieval, or any HTTP request, build and verify the emergency answer. Return it with `attempted_live_call=false`, no model, no evidence chunks, and an explicit `urgent_safety_precedence` reason.

- [ ] **Step 4: Run adapter and downstream tests**

Run `python -m pytest tests/test_chat_openai_adapter.py tests/test_chat_retrieval.py tests/test_interim_api.py -q`. Expect all selected tests to pass.

- [ ] **Step 5: Commit emergency precedence**

Stage only the answer, adapter, and test files. Commit with `feat: prioritize urgent counseling safety guidance`.

### Task 4: Create deterministic OP-085/086 evidence

**Files:**
- Create: `scripts/run_counseling_verifier_urgent_safety_smoke.py`
- Create: `data/original_plan/evidence/op085_op086_counseling_verifier_urgent_safety_smoke_v1.json`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `.github/workflows/original-plan-evidence.yml`

- [ ] **Step 1: Implement the smoke**

Run supported, unsupported, out-of-scope, positive urgent, negated urgent, and contrast-clause cases through the existing counseling path. Add independent tamper probes for an unsupported claim, omitted interaction risk, forbidden diagnosis, guaranteed outcome, delayed emergency advice, forged policy, and provider-call attempt. Record source and data hashes plus explicit statements that deployment, production operation, external validation, and live provider use were not proven.

- [ ] **Step 2: Prove determinism**

Run the smoke twice to two temporary paths under `etc/`, compare bytes, then generate the canonical evidence file. Verify the stored source identity against the committed source tree.

- [ ] **Step 3: Add CI selection**

Add the registry, verifier, smoke, and focused tests to the existing `Original plan evidence` workflow and its audit source-path expectations. Run the exact workflow pytest selection locally.

- [ ] **Step 4: Commit source-first evidence support**

If source changed after the previous source commit, commit it first. Regenerate canonical evidence against that commit, stage explicit paths, and commit with `evidence: prove OP-085 and OP-086 counseling safety`.

### Task 5: Write the two full research reports and update canonical status

**Files:**
- Create: `docs/original_plan/research_reports/OP-085.md`
- Create: `docs/original_plan/research_reports/OP-086.md`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`

- [ ] **Step 1: Write OP-085 as explanatory prose**

Explain the unsupported-claim, omitted-risk, and forbidden-expression threat model; why server-owned rendering was chosen; every tamper probe; the remaining limitations; and the precise `IMPLEMENTED` evidence boundary. Do not substitute bullets or raw test output for the narrative.

- [ ] **Step 2: Write OP-086 as explanatory prose**

Explain urgent signal detection, negation and clause boundaries, why emergency guidance bypasses retrieval and provider generation, the exact user-visible ordering, false-positive/false-negative limitations, and why local verification does not prove operation. Expand Retrieval-Augmented Generation and other unfamiliar abbreviations on first use.

- [ ] **Step 3: Update manifest and generated report**

Claim only `IMPLEMENTED` for both requirements, register canonical source/test/data evidence, regenerate `COMPLETION_STATUS.md`, and verify counts from the generator instead of writing expected totals by hand.

- [ ] **Step 4: Commit reports and manifest evidence**

Stage only both reports, the manifest, and generated status. Commit with `evidence: claim OP-085 and OP-086 implemented`.

### Task 6: Regress, independently review, publish, and hand off

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] **Step 1: Run all verification layers**

Run syntax checks, focused tests, the exact workflow selection, every canonical smoke, full Ruff, full pytest, frozen evaluation comparison, manifest audit, completion stale check, source-hash verification, `git diff --check`, and `git diff --cached --check`. Classify the full-suite failures against the established 77-case baseline.

- [ ] **Step 2: Request independent review**

Use a sub-agent to inspect the latest committed tree for unsupported-claim bypass, risk omission, forbidden-expression evasion, emergency-precedence bypass, source-identity gaps, and overclaimed evidence stage. Fix every Critical or Important finding and restart verification from the focused tests.

- [ ] **Step 3: Publish and observe CI**

Push the explicit source/evidence commits. Wait for the triggered `Original plan evidence` run to succeed. Do not deploy or change production configuration.

- [ ] **Step 4: Record the final facts**

Update the three handoff files with actual hashes, counts, test results, report coverage `8/120`, independent-review result, CI run, five bottlenecks, and next loops OP-087/088, OP-089/090, and OP-091/092. Commit and push those files only.
