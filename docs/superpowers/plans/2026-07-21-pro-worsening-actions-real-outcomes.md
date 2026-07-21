# PRO Worsening Actions and Real Outcomes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-059 deterministic PRO worsening actions and OP-060 same-API real-world outcome handling through the existing plan, event, service, and TIPS UI paths.

**Architecture:** Add a strict PRO-specific action decision derived from the existing `PROFollowUpEffectInterpretationV1`, then map the exact maintain/reduce/stop/re-optimize decisions onto the existing `NextAction` and workflow states. Parameterize the existing enrollment baseline `data_class`, preserve that class for every follow-up, and pass the field through the current WellnessBox route and browser client without creating a second API or store.

**Tech Stack:** Python 3.11, Pydantic, FastAPI, SQLite execution ledger, pytest, TypeScript, Next.js route helpers, Node QA scripts.

---

### Task 1: Lock the PRO action decision contract

**Files:**
- Create: `src/wellnessbox_rnd/metrics/pro_actions.py`
- Modify: `src/wellnessbox_rnd/metrics/__init__.py`
- Test: `tests/test_pro_actions.py`

- [ ] **Step 1: Write failing decision tests**

Create interpretations for worsened outcomes with serious adverse events, non-serious adverse events, low adherence, missed doses, and fully adherent/no-adverse-event inputs. Assert exact decisions `stop`, `reduce`, `maintain`, and `re_optimize`; assert their mappings to existing `NextAction.REDUCE_OR_STOP`, `NextAction.CONTINUE_PLAN`, and `NextAction.RE_OPTIMIZE` plus projected workflow states.

- [ ] **Step 2: Verify the contract is absent**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_pro_actions.py -q`
Expected: collection failure because `wellnessbox_rnd.metrics.pro_actions` does not exist.

- [ ] **Step 3: Implement the strict derived model**

Implement `PROPlanActionDecisionV1` and `decide_pro_plan_action_v1(interpretation)` with this priority: serious adverse event → `stop`; any other adverse event → `reduce`; worsened but adherence-limited or missed-dose-limited → `maintain`; interpretable worsening → `re_optimize`; non-worsening → `maintain`. Revalidate all derived fields from the source interpretation and prohibit causal claims.

- [ ] **Step 4: Verify all decision branches**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_pro_actions.py -q`
Expected: all tests pass.

### Task 2: Parameterize the existing PRO API by data class

**Files:**
- Modify: `src/wellnessbox_rnd/orchestration/pro_plan_service.py`
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `tests/test_pro_plan_service.py`
- Modify: `tests/test_interim_api.py`

- [ ] **Step 1: Write failing API tests**

Enroll identical request shapes with `SYNTHETIC_OUTCOME_PROXY` and `REAL_WORLD_OUTCOME`. Assert the baseline and later follow-up retain the selected class, the returned action decision exists, and an unsupported class returns HTTP 422. Assert a retry with the same request ID but a different class returns HTTP 409.

- [ ] **Step 2: Run focused failures**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_pro_plan_service.py tests/test_interim_api.py -q`
Expected: failures because enrollment does not accept `data_class` and follow-up responses do not contain `action_decision`.

- [ ] **Step 3: Extend the existing service and endpoint**

Add an allowed outcome class type containing only `SYNTHETIC_OUTCOME_PROXY` and `REAL_WORLD_OUTCOME`. Pass it into `enroll_pro_plan_v1`, assign it to the baseline event, retain baseline class in follow-ups, derive `action_decision` after every create/correction, and return the decision beside interpretation and lineage. Do not change the SQLite schema or create a parallel endpoint.

- [ ] **Step 4: Verify persistence, correction, and conflicts**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_pro_actions.py tests/test_pro_plan_service.py tests/test_interim_api.py -q`
Expected: all tests pass.

### Task 3: Pass data class through the existing WellnessBox integration

**Files:**
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-interim-route.ts`
- Modify: `C:/dev/wellnessbox/lib/tips/pro-study-rnd-client.ts`
- Modify: `C:/dev/wellnessbox/components/tips/ProStudySimulation.tsx`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-tips-pro-study-rnd-client.cts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-tips-pro-correction-route.cts`

- [ ] **Step 1: Add failing route/client assertions**

Assert the browser client sends `dataClass`, the authenticated route maps it to `data_class`, unsupported values fail before upstream access, and the UI stores the returned action decision. Keep the default UI choice synthetic and label real-world outcome mode explicitly.

- [ ] **Step 2: Run QA to see the missing bindings**

Run: `npm run qa:tips:pro-study-rnd && npm run qa:tips:pro-correction`
Expected: assertions fail until the new field and response are wired.

- [ ] **Step 3: Implement the pass-through and rendered result**

Add the two-value `ProOutcomeDataClass` type, send `dataClass` from the UI, validate it in the service route, forward `data_class` to R&D, parse `action_decision`, and show the exact next action only for live R&D results. Do not let the browser set profile identity, plan identity, or consent claims.

- [ ] **Step 4: Verify service code**

Run: `npm run qa:tips:pro-study-rnd && npm run qa:tips:pro-correction && npm run typecheck && npm run lint && npm run build`
Expected: all commands exit 0.

### Task 4: Generate evidence and update the manifest

**Files:**
- Create: `scripts/run_pro_worsening_action_real_outcome_smoke.py`
- Create: `data/original_plan/evidence/op059_op060_pro_action_real_outcome_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`

- [ ] **Step 1: Build a two-process deterministic smoke**

Exercise all four worsening decisions and run a `REAL_WORLD_OUTCOME` enrollment/follow-up through the authenticated WellnessBox helper and localhost R&D API. Record source paths, last-touch commits, normalized hashes, explicit non-production/non-causal boundaries, and no synthetic/real class mixing.

- [ ] **Step 2: Commit sources before evidence**

Stage only loop-owned source and test paths and commit them. Regenerate the smoke twice and require byte-identical SHA-256 output.

- [ ] **Step 3: Claim only proven stages**

Set OP-059 and OP-060 to `INTEGRATED` only if the two-process smoke passes. Regenerate completion reports with `scripts/build_original_plan_completion_report.py`; never hardcode disposition counts.

- [ ] **Step 4: Add CI replay**

Add the smoke, canonical diff check, focused tests, and Ruff paths to `Original plan evidence`.

### Task 5: Complete regression, review, publication, and handoff

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] **Step 1: Run final validation**

Run focused tests, exact workflow pytest selection, full Ruff, all canonical smokes affected by shared paths, full pytest, frozen eval 256 comparison, audit, report check, source hashes, and both Git diff checks. Require no failures beyond the known 73 absent-report and 4 CGM-geometry groups.

- [ ] **Step 2: Obtain independent review**

Review the final tree for Critical/Important findings. Fix findings through systematic debugging and restart final validation.

- [ ] **Step 3: Publish and observe CI**

Push the WellnessBox commit, pin it in the R&D workflow, push R&D, and require service Encoding Guard plus R&D Original plan evidence success. Do not deploy or change production configuration.

- [ ] **Step 4: Record exact handoff evidence**

Update the three handoff documents with actual hashes, case counts, test totals, CI run IDs, stage boundaries, five bottlenecks, and the next three loops. Stage these files explicitly and push.
