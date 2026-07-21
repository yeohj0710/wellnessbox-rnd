# Product Combination Constraint and Safety Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Exclude selling-product combinations above the trusted budget or maximum product count and prove that deterministic safety exclusions cannot re-enter product optimization for OP-065/066.

**Architecture:** Extend the existing R&D interim recommendation response with a strict `product_optimization_constraints_v1` object. R&D validates request limits and derives excluded ingredient keys from its final deterministic safety decision; the service consumes only this upstream contract, never raw client limits. The existing `/api/tips` product-combination adapter filters materialized combinations by cost and product count, rejects any recommendation or product combination containing a safety-excluded ingredient, and reports deterministic filter counts and reasons.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, TypeScript, existing Next.js route-function adapter, pytest, existing smoke/audit workflow.

---

### Task 1: Lock the R&D response contract with failing tests

**Files:**
- Modify: `apps/inference_api/routes/interim.py`
- Modify: `tests/test_interim_api.py`

- [ ] Add request tests for exact nonnegative integer `max_total_cost_krw` and `max_products` between 1 and 20, including rejection of booleans, floats, unknown fields, and out-of-range values.
- [ ] Add response assertions for `schema_version`, `max_total_cost_krw`, `max_products`, sorted unique `excluded_ingredient_keys`, and deterministic safety rule IDs.
- [ ] Add a hard-safety case proving requested ingredients are included in `excluded_ingredient_keys` and recommendations remain empty.
- [ ] Run `.venv-interim/Scripts/python.exe -m pytest tests/test_interim_api.py -q` and confirm the new assertions fail before implementation.

### Task 2: Emit trusted product constraints from the existing R&D route

**Files:**
- Modify: `apps/inference_api/routes/interim.py`

- [ ] Define frozen, extra-forbid request/response Pydantic models for `product_optimization_constraints_v1`.
- [ ] Default absent limits to `100000` KRW and `5` products for backward compatibility; accept explicit limits only through the validated R&D request model.
- [ ] Derive excluded ingredient keys from the final deterministic safety decision. When the final decision blocks, include every normalized requested ingredient; otherwise emit an empty tuple under the current all-or-nothing interim safety policy.
- [ ] Emit sorted unique safety rule IDs with the limits and exclusions in the persisted response.
- [ ] Run the focused interim tests and require PASS.

### Task 3: Filter existing service product combinations and fail closed on safety re-entry

**Files:**
- Modify: `contracts/wb-rnd/product-candidate-match-v1.json`
- Modify: `lib/server/wb-rnd-product-candidates.ts`
- Modify: `scripts/qa/check-rnd-product-candidates.cts`

- [ ] Add `product_optimization_constraints_v1` and `product_combination_filter_v1` versions to the existing product contract.
- [ ] Add QA cases with feasible, over-budget, and over-product-count combinations; assert only feasible combinations remain and exact exclusion counts are reported.
- [ ] Add contradictory upstream cases where an excluded R&D ingredient is recommended or appears in a selected product. Require the existing recommendation route to return the service fail-closed response and no combinations.
- [ ] Validate the upstream constraints strictly before candidate generation. Reject missing, malformed, unsorted, duplicate, or unknown safety exclusions rather than falling back to client input.
- [ ] Filter after combination materialization and before deterministic sorting/capping. Record pre-filter count, eligible count, budget-excluded count, product-count-excluded count, and safety-excluded count.
- [ ] Keep search truncation separate from constraint exclusions and preserve existing combination IDs.
- [ ] Run `npm run qa:rnd:product-candidates`, `npm run typecheck`, and `npm run lint`; require PASS.

### Task 4: Independently validate filtering in R&D and generate canonical evidence

**Files:**
- Modify: `src/wellnessbox_rnd/optimizer/product_combinations.py`
- Modify: `src/wellnessbox_rnd/optimizer/__init__.py`
- Modify: `tests/test_product_combinations.py`
- Create: `scripts/run_product_combination_constraint_safety_smoke.py`
- Create: `data/original_plan/evidence/op065_op066_product_combination_filter_smoke_v1.json`

- [ ] Add frozen, extra-forbid models for trusted limits, filter counts, exclusion reasons, and eligible combinations.
- [ ] Recompute every combination's cost, product count, ingredient membership, and eligibility; reject forged counts, reasons, or any excluded ingredient in output.
- [ ] Run the existing service QA with full evidence enabled, validate feasible and excluded cases independently, and bind both repository source paths, commits, and normalized SHA-256 identities.
- [ ] Record that route-function integration is proven while actual Prisma execution, production freshness, deployment, ordering, payment, and operation remain unproven.
- [ ] Run the smoke twice and require byte-identical output.

### Task 5: Govern, regress, review, publish, and hand off

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] Commit source and tests before canonical evidence. Stage every loop-owned path explicitly and never stage `etc/` or protected plans.
- [ ] Claim OP-065/066 only at `INTEGRATED`, regenerate the completion report, and require audit PASS.
- [ ] Run focused tests, exact workflow pytest selection, every workflow smoke twice, full Ruff, service QA/typecheck/lint/build, full pytest, and the official 256-case frozen evaluation.
- [ ] Obtain independent review and resolve every Critical or Important finding before publication.
- [ ] Push service first, require Encoding Guard success, push R&D next, require Original plan evidence success, then record exact hashes, totals, run IDs, five bottlenecks, and the next three loops.

