# OP-049/050 learned replay and service product-candidate plan

> Execute this bounded loop without replacing the existing recommendation, ingredient mapping, `/api/tips`, or product-catalog paths.

**Goal:** Compare the optional learned reranker with the deterministic baseline on identical replay requests, then prove that an R&D recommendation is converted through the existing WellnessBox ingredient mapping into candidates from the real service product catalog path.

**Evidence stages:** OP-049 `IMPLEMENTED`; OP-050 `INTEGRATED`. This loop does not claim deployment or production operation.

## Task 1: Lock paired replay contracts with failing tests

- Add a strict case-level comparison schema for baseline and learned selections, ranks, scores, safety/status changes, learned decision, and aggregate counts.
- Replay the exact same frozen-eval request through both modes.
- Reject case loss, duplicate IDs, inconsistent deltas, unvalidated learned application, or any safety/status drift.

## Task 2: Implement the reusable replay comparator

- Reuse `recommend()` twice per request; do not add a second scorer.
- Use a committed, explicitly labeled replay-only efficacy artifact fixture.
- Preserve every case result and report applied, deterministic-baseline, true fallback, ineligible, changed-selection, rank-change, and safety/status-change counts separately.

## Task 3: Lock service product-candidate conversion with failing QA

- Extend the existing `/api/tips` route dependency seam with a product-catalog loader.
- Verify mapped service ingredient IDs resolve only to supplied in-stock product rows by versioned match terms.
- Require explicit `MATCHED` or `NO_MATCH`; never invent a product ID.
- Fail closed if the service product catalog cannot be read or the product-candidate contract is invalid.

## Task 4: Connect the existing WellnessBox catalog path

- Add a versioned service contract for ingredient-to-product match terms.
- Query the existing Prisma `Product`/`PharmacyProduct` catalog with the existing in-stock predicate and order.
- Attach bounded, deterministic product candidates after the existing R&D safety authority and ingredient mapping succeed.
- Preserve blocked and unmapped behavior unchanged.

## Task 5: Prove the two-repository boundary

- Start the actual R&D FastAPI process locally.
- Invoke the exported WellnessBox `POST /api/tips` handler with its test-only dependency hook and a catalog fixture shaped exactly like the live Prisma query.
- Observe the actual R&D HTTP process on the safety-blocked boundary. Verify READY ingredient/product conversion and no-match behavior separately through the test-only route dependency seam and the captured live-catalog snapshot in the same report.

## Task 6: Close evidence and publish

- Run focused R&D and service QA, both repository checks, paired replay smoke twice, the affected two-process smoke, original-plan audit/report, full Ruff, frozen eval, and the full-suite baseline.
- Obtain independent review with zero Critical/Important findings.
- Commit and push each repository explicitly without staging user-owned UI or plan files.
- Require the service Encoding Guard and R&D Original plan evidence workflows to pass.
