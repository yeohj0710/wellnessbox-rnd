# Large-Drop Replay Prerequisite Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the next replay loop's ambiguous missing-file crash with a reproducible prerequisite audit that preserves the strict no-training gate.

**Architecture:** Add one small eval module that records required input roles, paths, existence, size, and SHA-256. Run it at the start of the existing residual replay script, write a JSON audit in both ready and blocked states, and stop with exit code 2 before loading evidence when prerequisites are absent.

**Tech Stack:** Python 3.11+, pathlib, hashlib, JSON, pytest, Ruff.

---

### Task 1: Define the audit contract

**Files:**
- Create: `tests/test_large_drop_replay_prerequisite_audit.py`
- Create: `src/wellnessbox_rnd/evals/large_drop_replay_prerequisite_audit.py`

- [ ] **Step 1: Write a failing blocked-state test**

Assert that one present and one absent required input produce `blocked_missing_prerequisites`, identify the missing role, and preserve `training_allowed = false`.

- [ ] **Step 2: Run the focused test and confirm import failure**

Run: `python -m pytest tests/test_large_drop_replay_prerequisite_audit.py -q`

Expected: collection fails because the audit module does not exist.

- [ ] **Step 3: Implement the smallest audit module**

Add deterministic file metadata, SHA-256, status, blocker roles, and atomic JSON writing. Do not regenerate or train any model.

- [ ] **Step 4: Add ready-state and writer tests**

Assert all-present inputs become `ready`, hashes are stable, and the written JSON round-trips exactly.

### Task 2: Put preflight before evidence loading

**Files:**
- Modify: `scripts/build_non_cgm_residual_threshold_cross_attribution.py`
- Test: `tests/test_large_drop_replay_prerequisite_audit.py`

- [ ] **Step 1: Add the audit output argument and required-role mapping**

The required roles are dataset, policy artifact, reference artifact, held candidate artifact, family diagnostic, subgroup diagnostic, mid-margin diagnostic, and prior small-drop attribution.

- [ ] **Step 2: Write the audit before calling `load_json_artifact`**

Return exit code 2 with a concise missing-role message when blocked. Continue unchanged when ready.

- [ ] **Step 3: Run the real command**

Run: `python scripts/build_non_cgm_residual_threshold_cross_attribution.py`

Expected now: exit 2, a valid prerequisite audit, no training, and no fabricated attribution output.

### Task 3: Handoff and validation

**Files:**
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [ ] **Step 1: Record the measured blocked state**

Record exact missing roles and keep `large_drop` as the next replay target after evidence restoration.

- [ ] **Step 2: Run focused tests and Ruff**

Run: `python -m pytest tests/test_large_drop_replay_prerequisite_audit.py -q`

Run: `python -m ruff check src/wellnessbox_rnd/evals/large_drop_replay_prerequisite_audit.py scripts/build_non_cgm_residual_threshold_cross_attribution.py tests/test_large_drop_replay_prerequisite_audit.py`

- [ ] **Step 3: Verify boundaries**

Confirm no candidate model was created, frozen-eval metrics remain unchanged, and only the prerequisite audit was written under `artifacts/reports/`.
