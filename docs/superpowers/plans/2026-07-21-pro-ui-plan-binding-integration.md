# OP-057/058 PRO UI and Plan Binding Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the real PRO study UI to the existing R&D recommendation/event ledger so user-entered baseline and follow-up answers are scored, persisted, corrected, and recalculated under the recommendation's immutable plan ID.

**Architecture:** Add one `plan_id` to the existing recommendation request/response contract and persist it in the existing recommendation and optimization events. Add R&D orchestration endpoints that reuse `recommend()`, `ExecutionLedger`, versioned PRO scoring, and `DataMutationLedger` to enroll a plan and create-or-correct a follow-up from raw questionnaire answers. The WellnessBox UI calls thin authenticated service adapters and displays the R&D-returned interpretation; demo-only local calculations remain labeled simulation and cannot masquerade as persisted results.

**Tech Stack:** Python 3.11+, Pydantic v2, FastAPI, SQLite, Next.js 15, React 19, TypeScript, pytest, service QA scripts, Ruff.

---

### Task 1: Make the recommendation plan ID immutable and persisted

**Files:**
- Modify: `src/wellnessbox_rnd/schemas/recommendation.py`
- Modify: `src/wellnessbox_rnd/orchestration/recommendation_service.py`
- Modify: `src/wellnessbox_rnd/interim/data_lake.py`
- Modify: `tests/test_recommendation_contracts.py`
- Modify: `tests/test_data_lake_lineage.py`
- Modify: `tests/test_pro_followup_effects.py`

- [ ] Add failing tests for a caller-supplied `plan_id`, a deterministic request-derived default, response mismatch rejection, and recommendation/optimization events that both retain the same plan ID.
- [ ] Add `plan_id` to `RecommendationRequest` and `RecommendationResponse`. If omitted, derive `plan_<32 lowercase hex>` from the canonical request ID hash. Reject response/request plan mismatch before persistence.
- [ ] Include `plan_id` in both existing core event payloads. When a strict baseline or follow-up is appended, require its plan ID to match the persisted recommendation plan ID.
- [ ] Add rejection tests for an unbound, cross-plan, or corrected-to-another-plan strict PRO event.
- [ ] Run `python -m pytest tests/test_recommendation_contracts.py tests/test_data_lake_lineage.py tests/test_pro_followup_effects.py -q`.

### Task 2: Score raw user answers and enroll the baseline through existing ledgers

**Files:**
- Create: `data/contracts/pro_runtime_reference_baselines_v1.json`
- Create: `src/wellnessbox_rnd/metrics/pro_runtime.py`
- Create: `src/wellnessbox_rnd/orchestration/pro_plan_service.py`
- Modify: `src/wellnessbox_rnd/metrics/__init__.py`
- Modify: `apps/inference_api/routes/interim.py`
- Create: `tests/test_pro_plan_service.py`

- [ ] Add a versioned proxy reference contract for PSQI, ISI, and PSS-10. Each entry contains at least two non-identical baseline raw scores and fixes `SYNTHETIC_OUTCOME_PROXY`; it does not claim a clinical norm.
- [ ] Add failing tests that raw questionnaire item responses are scored only by `score_pro_instrument_response_v1`, standardized only by the existing baseline-distribution builder, and rejected for wrong length/range or contract drift.
- [ ] Implement `enroll_pro_plan_v1`: validate the full existing `RecommendationRequest`, call `recommend()`, persist through `ExecutionLedger.record_recommendation`, build the strict pre-intake event with the response plan ID, and append it to `execution_events`.
- [ ] Add token-protected `POST /v1/interim/pro/plans` accepting `{recommendation_request, baseline, observed_at}` and returning the recommendation, plan ID, execution ID, baseline event ID, and scored baseline.
- [ ] Run `python -m pytest tests/test_pro_plan_service.py tests/test_inference_api.py tests/test_interim_api.py -q`.

### Task 3: Create or correct a follow-up from raw user answers

**Files:**
- Modify: `src/wellnessbox_rnd/orchestration/pro_plan_service.py`
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `tests/test_pro_plan_service.py`
- Modify: `tests/test_pro_followup_effects.py`

- [ ] Add failing tests for first week-2/week-4 creation, same-timepoint user correction, immediate recalculation, idempotent replay, and cross-plan/cross-instrument rejection.
- [ ] Implement `record_or_correct_pro_followup_v1`. Build the strict event from raw answers, adherence, adverse-event context, and the persisted plan ID. Append a new timepoint through `ExecutionLedger`; correct an existing assessment through the atomic correction service.
- [ ] Return one strict result shape containing operation `created|corrected`, event ID, raw score, interpretation, and recommendation-effect lineage.
- [ ] Add token-protected `POST /v1/interim/pro/followups` and preserve precise 404/409/422 mappings.
- [ ] Run focused service and mutation tests.

### Task 4: Connect the authenticated WellnessBox route and actual UI

**Files:**
- Create: `C:/dev/wellnessbox/lib/tips/pro-study-rnd-client.ts`
- Modify: `C:/dev/wellnessbox/lib/tips/pro-study-engine.ts`
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-interim-route.ts`
- Create: `C:/dev/wellnessbox/app/api/tips/pro/plans/route.ts`
- Modify: `C:/dev/wellnessbox/app/api/tips/pro/effects/route.ts`
- Modify: `C:/dev/wellnessbox/components/tips/ProStudySimulation.tsx`
- Create: `C:/dev/wellnessbox/scripts/qa/check-tips-pro-study-rnd-client.cts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-tips-pro-correction-route.cts`
- Modify: `C:/dev/wellnessbox/package.json`

- [ ] Add a browser-client contract with `enrollProPlan` and `saveProFollowup`; both call the two authenticated service routes, reject malformed responses, and never return local calculations as persisted results.
- [ ] Map the compact UI profile through `mapWellnessBoxProfileToWbRndRequest`, inject the authenticated pseudonymous subject ID and survey storage consent, and forward enrollment through the existing interim client.
- [ ] Store `executionId`, `planId`, baseline event ID, follow-up event IDs, and the last R&D interpretation on `StudyParticipant`.
- [ ] Make enrollment and follow-up saving asynchronous. Live participants display only the R&D response. On failure, keep the prior saved record and show `PRO 결과를 저장하지 못했습니다. 잠시 후 다시 시도하세요.` Demo participants stay local and are labeled `simulation`.
- [ ] Add QA assertions that the component imports and calls both client functions and that auth/pseudonymization cannot be overridden by browser payloads.
- [ ] Run `npm run qa:tips:pro-study-rnd`, `npm run qa:tips:pro-correction`, `npm run typecheck`, `npm run lint`, `npm run audit:encoding`, and `npm run build`.

### Task 5: Replace partial evidence with reproducible integration evidence

**Files:**
- Modify: `scripts/run_pro_correction_plan_lineage_smoke.py`
- Modify: `C:/dev/wellnessbox/scripts/qa/run-tips-pro-correction-client.cts`
- Modify after source commits: `data/original_plan/evidence/op057_op058_pro_correction_plan_lineage_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify governance and handoff files generated or listed by the manifest.

- [ ] Exercise enrollment plus first follow-up plus corrected follow-up through the real service route helpers and a real localhost R&D process. Assert persisted recommendation and optimization events carry the same plan ID as baseline/follow-up events.
- [ ] Assert the browser-client QA reaches the service endpoints, correction changes the raw score, recalculation is immediate, failed calls preserve prior UI state, and no production operation is claimed.
- [ ] Run the smoke twice byte-identically and verify both repository source hashes/commits after source-first commits.
- [ ] Claim OP-057 `INTEGRATED` only after the UI path and localhost service-to-R&D path pass. Claim OP-058 `INTEGRATED`, leaving it PARTIAL below required `OPERATED`.
- [ ] Regenerate report counts; run workflow-equivalent tests, full pytest, frozen 256 comparison, full Ruff, audit/report/source-hash/diff checks, and independent review with Critical 0 / Important 0.
- [ ] Stage explicit loop-owned files, push both repositories, require successful service CI and `Original plan evidence`, then update `PROGRESS.md`, `SESSION_HANDOFF.md`, and `NEXT_STEPS.md` with final hashes and runs.

### Placeholder scan

- [ ] Run `rg -n "TODO|TBD|FIXME|placeholder|NotImplemented"` over every modified source, test, evidence, plan, and governance file. Intentional exception `pass` statements are reviewed separately.
