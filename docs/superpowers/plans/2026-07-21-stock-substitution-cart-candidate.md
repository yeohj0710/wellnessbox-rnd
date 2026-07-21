# OP-069/070 Stock Substitution and Cart Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recompute a safety-preserving product combination when previously selected inventory disappears, then expose the selected combination as an existing WellnessBox cart-compatible candidate without creating an order before explicit approval.

**Architecture:** Extend the existing `/api/tips` route and `wb-rnd-product-candidates` adapter. The request may contain a strict service-only previous-combination context; the route removes that context before calling R&D, reruns the existing constrained combination search against the current catalog, and reports whether an in-stock substitute replaced the previous combination. The current top-ranked combination is converted to the existing `ClientCartItem` field shape as a non-mutating candidate with `approval_required=true` and `order_created=false`; no cart storage, `Order`, or `OrderItem` write occurs.

**Tech Stack:** Next.js route functions, TypeScript, existing Prisma catalog reader, existing deterministic combination search, existing client cart contract, Python/Pydantic independent evidence validation, pytest, Ruff.

---

### Task 1: Lock the service-only request and substitution contracts

**Files:**
- Modify: `C:/dev/wellnessbox/contracts/wb-rnd/product-candidate-match-v1.json`
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-interim-route.ts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-product-candidates.cts`

- [ ] Add contract versions `product_combination_inventory_context_v1`, `product_combination_stock_substitution_v1`, and `product_combination_cart_candidate_v1`.
- [ ] Write a failing QA case that submits `product_combination_context` containing the prior catalog version, combination ID, and sorted pharmacy-product IDs, and verifies that this service-only object is absent from the body sent to `/v1/interim/recommendations`.
- [ ] Reject extra fields, unsorted or duplicate offer IDs, invalid combination IDs, and invalid catalog versions before catalog evaluation.
- [ ] Run `npm run qa:rnd:product-candidates` and confirm the new assertions fail before implementation.

### Task 2: Recompute a globally ranked substitute after stock changes

**Files:**
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-product-candidates.ts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-product-candidates.cts`

- [ ] Reuse `validateCatalog`, `buildProductCombinations`, constraint filters, and `rankProductCombinations`; do not add a second catalog or optimizer.
- [ ] Determine whether any prior pharmacy-product ID is absent from the current validated in-stock catalog.
- [ ] If inventory is unchanged, return `UNCHANGED` only when the same top combination remains selected.
- [ ] If prior inventory is missing and the complete search has a current top result, return `SUBSTITUTED` with previous/current combination IDs, missing offer IDs, current catalog version, and `safety_constraints_preserved=true`.
- [ ] If search is truncated or no eligible replacement exists, return `SEARCH_TRUNCATED` or `UNAVAILABLE` without claiming a substitute.
- [ ] Add a regression fixture with one selected offer removed, an in-stock alternative, and active budget/product/safety constraints. Assert the replacement differs, contains no missing offer, and remains within every constraint.
- [ ] Run service QA, typecheck, and focused lint.

### Task 3: Produce a cart-compatible candidate without order creation

**Files:**
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-product-candidates.ts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-product-candidates.cts`
- Reuse: `C:/dev/wellnessbox/lib/client/cart-storage.ts`

- [ ] Convert the current rank-1 combination to `{productId, productName, optionType, quantity}` items accepted byte-for-field by `parseClientCartItems`.
- [ ] Return `READY` only when every selected offer has a non-empty option type; otherwise return `UNAVAILABLE` with an explicit reason.
- [ ] Include `approval_required=true`, `approval_status=NOT_APPROVED`, `cart_storage_written=false`, `order_created=false`, and no order/order-item identifier.
- [ ] Assert the route dependency set contains no order writer and that QA invokes no order API or Prisma order mutation.
- [ ] Assert parsing the candidate with `parseClientCartItems` preserves every item exactly while local storage remains untouched.

### Task 4: Independently validate substitution and cart evidence in R&D

**Files:**
- Modify: `src/wellnessbox_rnd/optimizer/product_combinations.py`
- Modify: `src/wellnessbox_rnd/optimizer/__init__.py`
- Modify: `tests/test_product_combinations.py`
- Create: `scripts/run_product_combination_stock_cart_smoke.py`

- [ ] Add frozen Pydantic models for inventory context, substitution result, and cart candidate with `extra=forbid`.
- [ ] Recompute the previous combination ID from sorted pharmacy-product IDs and verify missing IDs against the canonical current catalog.
- [ ] Reuse `ProductCombinationRankingEvidenceV1` to prove the substitute is the current rank-1 safe combination; reject forged safety flags, replacement IDs, missing IDs, cart items, approval state, and order-creation state.
- [ ] Run the service QA twice from the smoke: baseline catalog, then stock-changed catalog with the baseline context.
- [ ] Write deterministic canonical evidence to `data/original_plan/evidence/op069_op070_product_combination_stock_cart_smoke_v1.json` and verify two runs are byte-identical.

### Task 5: Register evidence, run regressions, review, and publish

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

- [ ] Commit service and R&D source before generating canonical evidence.
- [ ] Claim OP-069 and OP-070 at `INTEGRATED` only after the service route, current catalog, existing constrained search, and cart contract are connected by reproducible evidence.
- [ ] Regenerate every service-dependent canonical smoke from a clean service worktree pinned to the final service commit.
- [ ] Run audit, report generation/check, workflow-equivalent pytest, full pytest, full Ruff, service QA/typecheck/lint, frozen eval comparison, source hashes, and both Git diff checks.
- [ ] Obtain independent review with Critical `0` and Important `0`; fix findings and restart validation if needed.
- [ ] Explicitly stage loop-owned paths, push both repositories, and require GitHub Actions `Original plan evidence` success.
- [ ] Record exact commits, evidence hashes, counts, regression groups, frozen deltas, and CI run. Do not claim Prisma execution, production operation, cart mutation, approval, order creation, or payment.
