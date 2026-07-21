# Product Combination and Dose Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the existing WellnessBox selling-product candidates into versioned product combinations and calculate duplicate ingredients plus unit-normalized total daily doses for OP-063/064.

**Architecture:** Extend the existing `/api/tips` product-candidate adapter; do not add a route, database, catalog, order flow, or optimizer. The service parses strict amount-bearing product facts into canonical service ingredient amounts, enumerates deterministic combinations from the existing matched candidates, and returns duplicate and total-dose facts. R&D owns a mirrored strict Pydantic contract that independently validates the service-derived output and supplies deterministic canonical evidence.

**Tech Stack:** TypeScript, existing Next.js route-function adapter, Pydantic v2, pytest, existing smoke/audit workflow.

---

### Task 1: Lock the service combination contract with failing QA

**Files:**
- Modify: `C:/dev/wellnessbox/contracts/wb-rnd/product-candidate-match-v1.json`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-product-candidates.cts`

- [ ] Add a versioned `wb_rnd_product_combination_v1` contract version and a bounded maximum combination count.
- [ ] Extend the fixture so one multi-ingredient product covers multiple recommendations and another product creates a cross-product duplicate.
- [ ] Assert canonical ingredient IDs, exact normalized amounts, duplicate flags, distinct product counts, offer identity, deterministic combination IDs, and rejection of unknown units or ambiguous amount text.
- [ ] Run `npm run qa:rnd:product-candidates` and confirm the new assertions fail before implementation.

### Task 2: Parse product declarations and build combinations in the existing adapter

**Files:**
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-product-candidates.ts`

- [ ] Add a strict declaration parser that maps only contract-owned ingredient terms and accepts one numeric amount with `g`, `mg`, `mcg`/`ug`, or `IU`.
- [ ] Normalize mass units to integer micrograms and keep IU as a separate unit; reject ranges, schedules, multiple amounts, nonfinite values, and declarations without one canonical ingredient.
- [ ] Add normalized ingredient amounts to each existing product candidate.
- [ ] Enumerate the Cartesian choice set across matched recommendations, deduplicate the same product ID inside a combination, choose the lowest-price in-stock offer already sorted by the catalog adapter, and cap enumeration at the contract limit.
- [ ] Aggregate amounts by canonical ingredient and normalized unit. Mark an ingredient duplicated only when it occurs in more than one distinct selected product.
- [ ] Sort products, totals, and combinations deterministically and derive the combination ID from their canonical content.
- [ ] Run `npm run qa:rnd:product-candidates`, `npm run typecheck`, and `npm run lint` and require PASS.

### Task 3: Mirror and independently validate the integrated output in R&D

**Files:**
- Create: `src/wellnessbox_rnd/optimizer/product_combinations.py`
- Modify: `src/wellnessbox_rnd/optimizer/__init__.py`
- Create: `tests/test_product_combinations.py`

- [ ] Define frozen, extra-forbid models for product offers, product ingredient amounts, selected products, aggregate doses, and a combination set.
- [ ] Cross-check sorted unique identities, selected-product count, recommendation coverage, aggregate totals, duplicate flags, and content-derived combination IDs in model validators.
- [ ] Add tests for a shared multi-ingredient product, a genuine cross-product duplicate, mixed normalized mass units, IU separation, deterministic ordering, mutations, forged totals, forged duplicate flags, and extra fields.
- [ ] Run `python -m pytest tests/test_product_combinations.py -q` and require PASS.

### Task 4: Produce deterministic integration evidence and governance

**Files:**
- Create: `scripts/run_product_combination_dose_smoke.py`
- Create: `data/original_plan/evidence/op063_op064_product_combination_dose_smoke_v1.json`
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`

- [ ] Invoke the existing service QA helper, validate its returned combination fixture through the R&D contract, and bind evidence to exact source paths and commits in both repositories.
- [ ] Record localhost/route-function integration separately from actual Prisma execution, production freshness, deployment, ordering, payment, and production operation.
- [ ] Run the smoke twice and require byte-identical output.
- [ ] Claim OP-063/064 only at `INTEGRATED`, regenerate the completion report, and require audit PASS.

### Task 5: Verify, review, publish, and hand off

**Files:**
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] Run focused tests, the exact workflow pytest selection, all workflow smokes, full Ruff, service QA/typecheck/lint/build, full pytest, and the 256-case frozen evaluation.
- [ ] Obtain an independent review and resolve every Critical or Important finding before publication.
- [ ] Stage loop-owned files by explicit path, push the service source first, then the R&D source/evidence, and require both GitHub Actions workflows to pass.
- [ ] Record actual hashes, test totals, CI run IDs, evidence boundaries, five bottlenecks, and OP-065/066 as the next loop.
