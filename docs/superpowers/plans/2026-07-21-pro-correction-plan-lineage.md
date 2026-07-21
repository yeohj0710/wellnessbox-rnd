# OP-057/058 PRO Correction and Plan Lineage Implementation Plan

> **For agentic workers:** Execute each checked step in order. Use systematic debugging for failures and verification-before-completion before any completion claim.

**Goal:** Recalculate an observed PRO effect immediately after a real service-side user correction, and link the recommendation ingredients and observed PRO effects through one immutable plan ID without creating a second event store.

**Architecture:** Extend the existing R&D `ExecutionLedger` and `DataMutationLedger`. A strict plan-link event binds one recommendation execution to one plan ID; baseline and follow-up PRO events must use that plan ID. A correction-and-recalculate service validates the stored lineage, applies the existing correction, reloads effective events, and returns a source-retaining observed-effect interpretation. The Wellnessbox service proxies this endpoint through its existing authenticated R&D client. Local two-process evidence can establish integration, but cannot establish OP-058's required operated stage.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLite, Next.js/TypeScript, Vitest, pytest, Ruff, deterministic JSON evidence.

---

### Task 1: Fix the plan lineage contract with tests

**Files:**
- Modify: `src/wellnessbox_rnd/metrics/pro_followup.py`
- Modify: `src/wellnessbox_rnd/interim/data_lake.py`
- Modify: `tests/test_pro_followup_effects.py`
- Modify: `tests/test_data_lake_lineage.py`

- [ ] Add failing tests proving a recommendation execution can bind exactly one non-empty `plan_id`, selected ingredient keys remain in the recommendation event, and strict PRO events must match the bound plan.
- [ ] Add rejection tests for a conflicting second plan ID, unbound strict PRO input, and forged ingredient or plan lineage.
- [ ] Extend the existing recommendation core event payload and delayed-event validation at the earliest shared invariant. Do not add a table or a parallel event API.
- [ ] Run `python -m pytest tests/test_data_lake_lineage.py tests/test_pro_followup_effects.py -vv`.

### Task 2: Correct and immediately recalculate through the existing mutation ledger

**Files:**
- Create: `src/wellnessbox_rnd/metrics/pro_correction.py`
- Modify: `src/wellnessbox_rnd/metrics/__init__.py`
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `tests/test_pro_followup_effects.py`
- Modify: `tests/test_interim_api.py`

- [ ] Add failing unit tests for correcting a stored week-2 PRO event and returning the recalculated observed effect in the same call.
- [ ] Test idempotent replay, immutable baseline/plan identity, missing baseline, mismatched plan, non-strict target, and response mutation rejection.
- [ ] Implement a source-retaining correction result that calls `DataMutationLedger.apply`, reloads the effective execution trace, selects the bound baseline and corrected follow-up, and calls `interpret_pro_followup_effect_v1` without modifying observed values for adherence or adverse events.
- [ ] Add one token-protected interim endpoint that delegates to this service. Keep existing mutation authentication and error mappings.
- [ ] Run `python -m pytest tests/test_pro_followup_effects.py tests/test_event_idempotency_data_mutation.py tests/test_interim_api.py -vv`.

### Task 3: Connect the existing Wellnessbox service path

**Files:**
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-interim-route.ts`
- Create: `C:/dev/wellnessbox/app/api/tips/pro/effects/route.ts`
- Modify: `C:/dev/wellnessbox/components/tips/ProStudySimulation.tsx`
- Add or modify focused service tests beside the existing server-route tests.

- [ ] Add failing tests proving an authenticated service user is pseudonymized and the correction request is forwarded through `callWbRndInterim`.
- [ ] Add an authenticated route for recording the strict plan-linked PRO sequence and correcting/recalculating a follow-up. Reuse the existing R&D base URL, token, and feature flag.
- [ ] Replace the UI's correction result for the integrated path with the R&D response. Show a precise recovery message when R&D is unavailable; do not silently claim the duplicate TypeScript score is the persisted result.
- [ ] Run the focused Vitest tests plus TypeScript/lint checks selected by the service repository scripts.

### Task 4: Produce reproducible local integration evidence

**Files:**
- Create: `scripts/run_pro_correction_plan_lineage_smoke.py`
- Create after source commits: `data/original_plan/evidence/op057_op058_pro_correction_plan_lineage_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `tests/test_original_plan_audit_cli.py`

- [ ] Start the real local R&D API and exercise the real service adapter or route handler against it with a deterministic user input case.
- [ ] Prove the stored pre-correction event, correction audit record, immediate recalculated effect, common plan ID, selected ingredient lineage, idempotent replay, and explicit non-operation boundary.
- [ ] Run the smoke twice and require byte-identical JSON plus a recomputed source hash covering every directly used R&D and service source file.
- [ ] Run focused Python and service checks, then commit source changes in each repository before generating canonical evidence.

### Task 5: Register honest stages and run the full gate

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md` through its generator
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] Claim OP-057 at `INTEGRATED` only if the real service-to-R&D local path passes. Claim OP-058 at `INTEGRATED`, leaving it partial below required `OPERATED` without production operation evidence.
- [ ] Regenerate the completion report; verify generated counts instead of hardcoding them.
- [ ] Run the workflow-equivalent pytest selection, full pytest, frozen 256-case evaluation, audit/completion checks, full Ruff, deterministic smoke, source-hash verification, `git diff --check`, and `git diff --cached --check`.
- [ ] Confirm the full-suite failures contain only the known 73 absent-report cases and 4 CGM geometry cases; investigate every new failure from first cause.
- [ ] Request an independent sub-agent review of the final tree. Require Critical 0 and Important 0, or fix and rerun the full gate.
- [ ] Stage only explicit loop-owned files, commit and push each repository, then verify the triggered `Original plan evidence` GitHub Actions run succeeds.
- [ ] Record only final hashes, counts, commits, and CI run IDs in the three handoff documents.

### Placeholder scan

- [ ] Run `rg -n "TODO|TBD|FIXME|placeholder|pass$|NotImplemented"` on every new or modified source, test, evidence, and governance file. Resolve intentional matches before staging.
