# Adaptive Answer-Key Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep every 100-case KPI answer key while reducing detailed human review to AI disagreements, risk flags, and a deterministic five-case agreement sample; a named human still makes the final batch approval.

**Architecture:** One agent drafts all answers and a different provider-family agent independently proposes answers from a blind export. The workbench compares both sets, requires detailed human review for disagreements and a deterministic adaptive sample, then records one explicit human batch approval for untouched agreements. Any sampled error expands the sample from 5 to 20, and two sampled errors require detailed review of every agreement.

**Tech Stack:** Python dataclasses, JSON workbench artifacts, argparse CLI, SHA-256 deterministic sampling, pytest, Ruff.

---

### Task 1: Lock the adaptive review policy with tests

**Files:**
- Create: `src/wellnessbox_rnd/evals/adaptive_answer_key_review.py`
- Create: `tests/test_adaptive_answer_key_review.py`

- [ ] **Step 1: Write failing policy tests**

Cover these exact rules:

```python
def test_all_agreements_require_only_five_detailed_reviews(): ...
def test_every_disagreement_and_flag_is_required(): ...
def test_one_sample_correction_expands_to_twenty(): ...
def test_two_sample_corrections_require_every_case(): ...
def test_same_provider_family_cannot_review_its_own_draft(): ...
```

- [ ] **Step 2: Run the tests and confirm the module is missing**

Run: `python -m pytest tests/test_adaptive_answer_key_review.py -q`

Expected: collection failure because `adaptive_answer_key_review` does not exist.

- [ ] **Step 3: Implement deterministic planning**

Define:

```python
INITIAL_AGREEMENT_SAMPLE = 5
EXPANDED_AGREEMENT_SAMPLE = 20

def build_adaptive_review_plan(workbench: Workbench) -> dict[str, Any]:
    """Return disagreements, flags, sampled agreements, escalation, and pending IDs."""

def register_independent_ai_review(
    workbench: Workbench,
    *,
    reviewing_agent: str,
    blinded_from: list[str],
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate a complete blind second opinion from another provider family."""
```

Choose agreement samples by ascending SHA-256 of `indicator_id + ':' + case_id`, never by mutable list order. Reject missing, extra, duplicated, empty-answer, and same-provider-family records.

- [ ] **Step 4: Run policy tests**

Run: `python -m pytest tests/test_adaptive_answer_key_review.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/wellnessbox_rnd/evals/adaptive_answer_key_review.py tests/test_adaptive_answer_key_review.py
git commit -m "feat: plan adaptive answer key review"
```

### Task 2: Persist AI review and honest human decision modes

**Files:**
- Modify: `src/wellnessbox_rnd/evals/answer_key_workbench.py`
- Modify: `tests/test_answer_key_workbench.py`

- [ ] **Step 1: Write failing persistence tests**

Add tests proving legacy workbenches still load and new workbenches round-trip:

```python
assert restored.ai_review == workbench.ai_review
assert restored.batch_approval == workbench.batch_approval
assert restored.decisions[case_id].decision_mode == "ai_consensus_batch_approval"
assert restored.decisions[case_id].reviewed_in_detail is False
```

- [ ] **Step 2: Add optional schema fields**

Extend `Decision` with defaulted `decision_mode="detailed_review"` and `reviewed_in_detail=True`. Extend `Workbench` with defaulted `ai_review={}` and `batch_approval=None`. Include both fields in `load_workbench` and `save_workbench` without breaking old JSON.

- [ ] **Step 3: Make summaries distinguish review from approval**

Add `detailed_review_count`, `batch_approved_count`, and `detailed_edit_rate_pct`. Keep the existing total counts and reviewers for compatibility. Never describe batch-approved cases as individually reviewed.

- [ ] **Step 4: Run persistence tests**

Run: `python -m pytest tests/test_answer_key_workbench.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/wellnessbox_rnd/evals/answer_key_workbench.py tests/test_answer_key_workbench.py
git commit -m "feat: persist adaptive answer key decisions"
```

### Task 3: Add the blind AI-review and minimal-human-review commands

**Files:**
- Modify: `scripts/run_answer_key_workbench.py`
- Modify: `tests/test_adaptive_answer_key_review.py`

- [ ] **Step 1: Write failing CLI tests**

Test these commands and failure modes:

```text
export-ai-review --indicator KPI-1 --agent claude --output <path>
import-ai-review --indicator KPI-1 --file <path>
minimal-status --indicator KPI-1
review-minimal --indicator KPI-1 --by <name>
approve-consensus --indicator KPI-1 --by <name>
```

The export must omit `draft_answer`. Import must require complete cases and different provider families. Approval must fail until required detailed reviews are complete, fail if any case is rejected, and require the exact typed confirmation `<KPI> AI 합의안 일괄 승인`.

- [ ] **Step 2: Implement blind export and import**

Export only `case_id`, `prompt`, an aggregate answer vocabulary, and instructions to return `proposed_answer`, `confidence`, and `flags`. Import provenance must record `reviewing_agent`, `blinded_from`, source SHA-256, and case reviews.

- [ ] **Step 3: Implement minimal detailed review**

Reuse the existing review display and one-second save floor, but show only the plan's `pending_required_detail_ids`. Enter accepts the draft; `e` edits; `r` rejects. Recompute the adaptive plan after every saved decision so escalation happens immediately.

- [ ] **Step 4: Implement explicit batch approval**

After exact human confirmation, create decisions for untouched agreement cases with:

```python
Decision(
    case_id=case_id,
    action="accepted",
    final_answer=draft.draft_answer,
    decided_by=args.by,
    decided_at=approved_at,
    note="AI 합의안 일괄 승인; 개별 상세 검토 아님",
    decision_mode="ai_consensus_batch_approval",
    reviewed_in_detail=False,
)
```

Persist a `batch_approval` record containing the person, time, confirmation, AI review digest, detailed IDs, sampled agreement IDs, correction count, and batch-approved IDs.

- [ ] **Step 5: Run CLI tests**

Run: `python -m pytest tests/test_adaptive_answer_key_review.py tests/test_answer_key_workbench.py -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_answer_key_workbench.py tests/test_adaptive_answer_key_review.py tests/test_answer_key_workbench.py
git commit -m "feat: add minimal human answer key review"
```

### Task 4: Make seal and completion audits understand adaptive approval

**Files:**
- Modify: `src/wellnessbox_rnd/evals/answer_key_integrity.py`
- Modify: `tests/test_answer_key_integrity.py`
- Modify: `tests/test_completion_wizard.py`
- Modify: `tests/test_final_completion_audit.py`

- [ ] **Step 1: Write failing audit tests**

Prove that detailed decisions are pace-checked, batch decisions are excluded from the pace calculation, a valid adaptive plan plus explicit batch approval passes, and a missing or stale approval fails closed.

- [ ] **Step 2: Extend review-effort audit**

`audit_review_effort` must use only `reviewed_in_detail=True` timestamps for seconds-per-decision. It must call the adaptive policy validator when `ai_review` exists and report detailed count, batch-approved count, escalation tier, and batch approval validity.

- [ ] **Step 3: Preserve fail-closed sealing**

`audit_sealing_readiness`, the completion wizard, and the final audit must remain blocked unless every case has a human detailed decision or belongs to a valid explicitly approved AI-consensus batch.

- [ ] **Step 4: Run audit and completion tests**

Run: `python -m pytest tests/test_answer_key_integrity.py tests/test_completion_wizard.py tests/test_final_completion_audit.py -q`

Expected: new tests pass; only the documented existing final-receipt test may fail in the repository-state assertion.

- [ ] **Step 5: Commit**

```bash
git add src/wellnessbox_rnd/evals/answer_key_integrity.py tests/test_answer_key_integrity.py tests/test_completion_wizard.py tests/test_final_completion_audit.py
git commit -m "fix: audit adaptive answer key approval"
```

### Task 5: Update the contract and handoff documents

**Files:**
- Modify: `AGENTS.md`
- Modify: `data/original_plan/contracts/kpi_measurement_contract_v1.json`
- Modify: `docs/original_plan/KPI_COMPLIANCE_STRATEGY.md`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [ ] **Step 1: Replace the obsolete per-case human rule**

State that 100 measured cases remain mandatory. Two different provider-family agents independently propose every answer. A named person reviews every disagreement, every risk flag, and an adaptive agreement sample, then explicitly approves or rejects the remaining agreement batch. Record detailed and batch-approved counts separately.

- [ ] **Step 2: State the limits plainly**

Document that five cases are an operational minimum, not a statistical clinical-validation claim. One sampled correction expands to 20; two require all agreements. Year-2 records remain `pharmacist_candidate_preliminary_safety_review` and never claim licensed-pharmacist review.

- [ ] **Step 3: Validate documents and JSON**

Run: `python -m json.tool data/original_plan/contracts/kpi_measurement_contract_v1.json > NUL`

Expected: exit code 0.

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md data/original_plan/contracts/kpi_measurement_contract_v1.json docs/original_plan/KPI_COMPLIANCE_STRATEGY.md PROGRESS.md NEXT_STEPS.md SESSION_HANDOFF.md
git commit -m "docs: define adaptive answer key review"
```

### Task 6: Final verification and local integration

**Files:**
- No new files.

- [ ] **Step 1: Run focused tests and Ruff**

Run: `python -m pytest tests/test_adaptive_answer_key_review.py tests/test_answer_key_workbench.py tests/test_answer_key_integrity.py tests/test_completion_wizard.py tests/test_final_completion_audit.py -q --tb=short`

Run: `python -m ruff check src/wellnessbox_rnd/evals/adaptive_answer_key_review.py src/wellnessbox_rnd/evals/answer_key_workbench.py src/wellnessbox_rnd/evals/answer_key_integrity.py scripts/run_answer_key_workbench.py tests/test_adaptive_answer_key_review.py tests/test_answer_key_workbench.py tests/test_answer_key_integrity.py`

Expected: feature tests and changed-file Ruff pass, with only the documented repository-state test allowed to fail.

- [ ] **Step 2: Run repository baselines**

Run: `python -m pytest -q --tb=no`

Expected: no failures beyond the recorded baseline set.

Run: `python -m ruff check .`

Expected: no errors beyond the recorded baseline set.

- [ ] **Step 3: Confirm no human action was fabricated**

Run: `python scripts/run_answer_key_workbench.py minimal-status --indicator KPI-1`

Expected: blocked until a real independent AI review is imported; no human decision or batch approval exists.

- [ ] **Step 4: Merge locally**

Commit only named paths, switch to `main`, and run `git merge --ff-only feat/adaptive-answer-key-review`. Do not push.
