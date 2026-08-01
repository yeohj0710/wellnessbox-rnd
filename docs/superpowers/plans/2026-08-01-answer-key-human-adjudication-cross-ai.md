# Answer-Key Human Adjudication and Cross-AI Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep KPI-1·3·4·5 answer keys independent from the system under test while letting AI prepare and cross-check every case so the named human only makes the final case-level decision.

**Architecture:** The primary drafter remains bound to an engine-input registry audit. A second AI can receive a packet that omits the primary answer, rationale, engine logic and engine output, then return an independently derived opinion tied to the packet digest. Provider-family separation is recorded as optional defense-in-depth; hard validity comes from distinct actor identity, audited information boundaries, pre-output human adjudication and sealing.

**Tech Stack:** Python 3.11+, dataclasses, JSON, argparse, pytest, Ruff.

---

### Task 1: Make the information boundary the hard invariant

**Files:**
- Modify: `src/wellnessbox_rnd/evals/answer_key_integrity.py`
- Modify: `src/wellnessbox_rnd/evals/answer_key_workbench.py`
- Modify: `tests/test_answer_key_integrity.py`
- Modify: `tests/test_answer_key_workbench.py`

- [ ] **Step 1: Write failing tests for declared blinding and actor identity**

```python
def test_missing_engine_logic_path_fails_declared_blinding():
    result = audit_declared_blinding(workbench, registry)
    assert result["verdict"] == "FAIL"

def test_same_provider_different_actor_is_not_a_hard_failure():
    provenance = build_provenance(
        workbench,
        summary,
        system_under_test_id="openai-counseling-engine-v1",
    )
    assert provenance["role_separation"]["exact_identity_separated"] is True
```

- [ ] **Step 2: Run the focused tests and confirm the new assertions fail**

Run: `python -m pytest tests/test_answer_key_integrity.py tests/test_answer_key_workbench.py -q`

Expected: FAIL because `audit_declared_blinding` and the information-boundary provenance do not exist.

- [ ] **Step 3: Implement the hard boundary**

```python
def audit_declared_blinding(workbench, registry):
    required = {item["path"] for item in registry["entries"] if item["role"] == "engine_logic"}
    declared = {tuple(sorted(item.get("blinded_from", []))) for item in workbench["drafts"]}
    missing = sorted(required - set(next(iter(declared), ())))
    return {"missing_engine_logic": missing, "verdict": "FAIL" if missing else "PASS"}
```

Replace the KPI-4 provider-family block with an all-KPI exact actor check. Require `system_under_test_id`, reject only an exact drafting-actor match, and record that provider separation is advisory rather than proof of independence.

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_answer_key_integrity.py tests/test_answer_key_workbench.py -q`

Expected: PASS.

### Task 2: Preserve fast human inputs and audit the recorded effort

**Files:**
- Modify: `src/wellnessbox_rnd/evals/answer_key_workbench.py`
- Modify: `src/wellnessbox_rnd/evals/answer_key_integrity.py`
- Modify: `scripts/run_answer_key_workbench.py`
- Modify: `tests/test_answer_key_workbench.py`
- Modify: `tests/test_answer_key_integrity.py`

- [ ] **Step 1: Write failing tests for per-case duration**

```python
def test_fast_decision_is_saved_with_duration():
    decision = decide(
        draft=draft,
        final_answer=draft.draft_answer,
        decided_by="검토자",
        review_duration_seconds=0.4,
    )
    assert decision.review_duration_seconds == 0.4

def test_audit_fails_when_recorded_average_is_below_floor():
    assert audit_review_effort(workbench)["verdict"] == "FAIL"
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python -m pytest tests/test_answer_key_integrity.py tests/test_answer_key_workbench.py -q`

Expected: FAIL because decisions do not persist review duration.

- [ ] **Step 3: Store duration without discarding the input**

Add `review_duration_seconds` to `Decision`. Save every valid human choice. Show an immediate warning for a sub-second decision, but leave the seal audit responsible for blocking an implausibly fast review. Include rejected cases in review-effort calculations.

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest tests/test_answer_key_integrity.py tests/test_answer_key_workbench.py -q`

Expected: PASS.

### Task 3: Add blinded cross-AI packets and responses

**Files:**
- Create: `src/wellnessbox_rnd/evals/answer_key_peer_review.py`
- Create: `tests/test_answer_key_peer_review.py`
- Modify: `src/wellnessbox_rnd/evals/answer_key_workbench.py`
- Modify: `scripts/run_answer_key_workbench.py`
- Modify: `scripts/seal_reference_standard.py`

- [ ] **Step 1: Write packet and response validation tests**

```python
def test_packet_omits_primary_answer_and_rationale():
    packet = build_blinded_peer_packet(workbench, engine_logic_paths)
    assert set(packet["cases"][0]) == {"case_id", "prompt"}

def test_response_requires_packet_digest_and_complete_case_ids():
    with pytest.raises(ValueError, match="peer_review_case_ids_mismatch"):
        validate_peer_response(response, packet, workbench, engine_logic_paths)
```

Also test that engine-output consultation, missing blinded paths and the same exact actor are rejected, while a different actor from the same provider is allowed.

- [ ] **Step 2: Run the peer-review tests and confirm failure**

Run: `python -m pytest tests/test_answer_key_peer_review.py -q`

Expected: FAIL because the peer-review module does not exist.

- [ ] **Step 3: Implement packet export, response import and persistence**

The packet contains only `case_id`, `prompt`, answer-format guidance, required blindness paths and a deterministic SHA-256 digest. The response contains a different `review_agent_id`, its independent source, the packet digest, complete case opinions, and an explicit `engine_output_consulted: false` claim. Persist only validated responses in `Workbench.peer_review`.

- [ ] **Step 4: Show both opinions to the human**

Add CLI commands:

```text
export-peer-packet --indicator KPI-4 --output <path>
import-peer-review --indicator KPI-4 --response <path>
```

During `review`, show agreement or disagreement and allow `p` to choose the peer opinion. `Enter`, `p`, `e`, and `r` remain explicit human decisions; no AI response creates a final decision automatically.

- [ ] **Step 5: Run focused CLI and persistence tests**

Run: `python -m pytest tests/test_answer_key_peer_review.py tests/test_answer_key_workbench.py -q`

Expected: PASS.

### Task 4: Align the measurement contract and handoff

**Files:**
- Modify: `data/original_plan/contracts/kpi_measurement_contract_v1.json`
- Modify: `docs/original_plan/KPI_COMPLIANCE_STRATEGY.md`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

- [ ] **Step 1: Document the decision boundary**

State that provider diversity reduces correlated model bias but is not proof of independence. The mandatory conditions are audited source separation, complete engine-input blinding, a distinct system-under-test identity, human case-level adjudication, and sealing before engine output.

- [ ] **Step 2: Record the reduced human role**

State that AI prepares two opinions and evidence while the person only accepts the primary opinion, accepts the peer opinion, edits, or rejects. Do not use agreement, approval rate, rejection rate or provider diversity as a seal gate.

- [ ] **Step 3: Update loop records**

Record the exact changed files, validation results, unchanged frozen metrics, remaining 400 human decisions, and the next three loops.

### Task 5: Verify and commit the bounded loop

**Files:**
- Verify all files above.

- [ ] **Step 1: Run the registry and integrity audits**

Run:

```text
python scripts/build_engine_input_registry.py
git diff --exit-code -- data/original_plan/contracts/engine_input_registry_v1.json
python scripts/audit_answer_key_integrity.py --json
```

Expected: registry READY; source and declared-blinding audits PASS for four indicators; completion remains BLOCKED because human decisions and active seals do not exist.

- [ ] **Step 2: Run focused tests and Ruff**

Run:

```text
python -m pytest tests/test_answer_key_integrity.py tests/test_answer_key_peer_review.py tests/test_answer_key_workbench.py tests/test_completion_wizard.py -q
python -m ruff check scripts/run_answer_key_workbench.py scripts/seal_reference_standard.py src/wellnessbox_rnd/evals/ tests/test_answer_key_integrity.py tests/test_answer_key_peer_review.py tests/test_answer_key_workbench.py
```

Expected: PASS.

- [ ] **Step 3: Run the broader guardrails**

Run:

```text
python -m pytest -q --tb=no
python -m ruff check scripts/ src/wellnessbox_rnd/evals/
```

Expected: no new failures beyond the recorded repository baseline.

- [ ] **Step 4: Commit only task files**

Stage the exact files listed above. Preserve unrelated receipts, uploads and handoff artifacts.
