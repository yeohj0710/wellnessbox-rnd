# Multi-constraint optimizer and product catalog contract implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement OP-061 as a strict five-dimension optimizer constraint contract and OP-062 as an enriched contract over the existing WellnessBox selling-product catalog.

**Architecture:** Keep R&D ingredient ranking and the WellnessBox Prisma catalog as the existing systems of record. Add a pure R&D feasibility evaluator for explicit efficacy, safety, cost, daily-unit, and formulation constraints. Extend the existing service product-candidate adapter to read `Product.detailFacts` and in-stock `PharmacyProduct` offers, then attach validated catalog facts to the existing `/api/tips` response without creating a route, database, or order.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, TypeScript, Prisma, Node `assert`, deterministic JSON evidence

---

### Task 1: Define and enforce five optimizer constraint dimensions

**Files:**
- Create: `data/contracts/optimization_constraints_v1.json`
- Create: `src/wellnessbox_rnd/optimizer/constraints.py`
- Modify: `src/wellnessbox_rnd/optimizer/__init__.py`
- Test: `tests/test_optimization_constraints.py`

- [ ] **Step 1: Write failing strict-contract tests**

Cover an allowed candidate and one rejection for each of `minimum_effect_score`, safety exclusion, maximum total cost, maximum product/daily-unit count, preferred formulation, derived-output mutation, duplicate identifiers, and non-finite numeric input.

- [ ] **Step 2: Verify the tests fail before implementation**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_optimization_constraints.py -q`

Expected: collection fails because `wellnessbox_rnd.optimizer.constraints` does not exist.

- [ ] **Step 3: Implement the strict versioned evaluator**

Define frozen `OptimizationConstraintsV1`, `OptimizationCandidateFactsV1`, and `OptimizationConstraintEvaluationV1` models. Implement `evaluate_optimization_candidate_v1()` so safety, cost, count, and formulation are hard feasibility constraints while efficacy records an explicit minimum threshold. Recompute every derived violation and reject caller-supplied mutations.

- [ ] **Step 4: Validate the contract and exports**

Run: `.venv-interim\Scripts\python.exe -m pytest tests/test_optimization_constraints.py -q`

Expected: all tests pass.

### Task 2: Enrich the existing service selling-product contract

**Files:**
- Modify: `C:/dev/wellnessbox/lib/product/product.catalog.ts`
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-product-candidates.ts`
- Modify: `C:/dev/wellnessbox/contracts/wb-rnd/product-candidate-catalog-snapshot-v1.json`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-product-candidates.cts`

- [ ] **Step 1: Add failing service QA assertions**

Require every catalog item to expose validated ingredient declarations from categories/detail facts, in-stock offers with integer KRW price and stock, and a non-empty formulation when `detailFacts` supplies one. Require malformed detail facts, offers, prices, stocks, or duplicate product IDs to fail closed.

- [ ] **Step 2: Verify service QA fails**

Run: `npm run qa:tips:rnd-product-candidates`

Expected: assertions fail because the current catalog returns only ID, name, and categories.

- [ ] **Step 3: Extend the existing Prisma selection and adapter**

Select `detailFacts` plus all in-stock `PharmacyProduct` rows with `price`, `stock`, `optionType`, and `capacity`. Normalize them in `listWbRndProductCatalog()`. Attach `ingredient_declarations`, `offers`, and `formulation` to each matched product candidate. Preserve the existing match/status/resolution fields and deterministic ordering.

- [ ] **Step 4: Validate compatibility and fail-closed behavior**

Run: `npm run qa:tips:rnd-product-candidates && npm run qa:tips:rnd-final-safety && npm run typecheck && npm run lint`

Expected: all commands pass without changing the API route or creating an order.

### Task 3: Produce source-bound integration evidence and governance updates

**Files:**
- Create: `scripts/run_optimization_constraints_product_catalog_smoke.py`
- Create: `data/original_plan/evidence/op061_op062_optimization_product_catalog_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: generated completion reports and governance tests

- [ ] **Step 1: Build a deterministic two-repository smoke**

Evaluate one feasible R&D candidate plus all five rejection dimensions, invoke the existing service QA helper against the committed selling-product snapshot, record source paths/commits/SHA-256, and state that production catalog operation, ordering, and deployment are not proven.

- [ ] **Step 2: Commit source before canonical evidence**

Stage only source, tests, contract, plan, and workflow source files by explicit path. Commit the service source first, then R&D source. Regenerate canonical evidence twice and require byte-identical SHA-256.

- [ ] **Step 3: Register exact stages and regenerate reports**

Claim OP-061 `IMPLEMENTED` and OP-062 `INTEGRATED`. Run the audit and report generator instead of editing counts.

- [ ] **Step 4: Run final verification**

Run focused tests, the exact workflow selection, all workflow smokes, full Ruff, service build, full pytest, the 256-case frozen eval comparison, source-hash checks, `git diff --check`, and independent review. Preserve the known 73 absent-report plus 4 CGM-geometry failures unless fresh evidence proves otherwise.

- [ ] **Step 5: Publish and hand off**

Push service first and require Encoding Guard success. Push R&D and require Original plan evidence success. Record exact commits, run IDs, counts, hashes, evidence boundaries, five bottlenecks, and OP-063/064, OP-065/066, OP-067/068 as the next three loops.
