# Product Combination Top-k and Reproducibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing product-combination path so it returns deterministic top-k choices, explicit non-selection reasons, and replay identities bound to the normalized input and catalog version.

**Architecture:** Keep combination generation, filtering, and catalog access in the existing WellnessBox `/api/tips` adapter. Canonicalize validated catalog facts and recommendation constraints before hashing; rank eligible combinations by an explicit immutable cost/product-burden tuple; return every evaluated non-top-k combination with deterministic reason codes. Add an independent R&D contract that recomputes ranking, reasons, and result identity from service evidence.

**Tech Stack:** TypeScript, Node `crypto`, existing Next.js route adapter, Python 3.11, Pydantic v2, pytest, Ruff.

---

### Task 1: Freeze the response contract with failing service QA

**Files:**
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-product-candidates.cts`
- Modify: `C:/dev/wellnessbox/contracts/wb-rnd/product-candidate-match-v1.json`

- [ ] **Step 1: Add assertions for top-k, reasons, and replay identity**

```ts
assert.deepEqual(result.product_combination_top_k.map((item) => item.rank), [1, 2, 3]);
assert.ok(result.product_combination_non_selection.every((item) => item.reason_codes.length > 0));
assert.match(result.product_combination_replay.catalog_version, /^catalog_[a-f0-9]{64}$/);
assert.match(result.product_combination_replay.result_sha256, /^[a-f0-9]{64}$/);
```

- [ ] **Step 2: Add reordered-catalog and repeated-request cases**

```ts
assert.deepEqual(repeated.product_combination_top_k, first.product_combination_top_k);
assert.equal(reordered.product_combination_replay.catalog_version, first.product_combination_replay.catalog_version);
assert.equal(reordered.product_combination_replay.result_sha256, first.product_combination_replay.result_sha256);
```

- [ ] **Step 3: Run the QA and confirm the new assertions fail**

Run: `node --conditions=react-server --import tsx scripts/qa/check-rnd-product-candidates.cts`

Expected: FAIL because the top-k and replay fields do not exist.

### Task 2: Implement deterministic service ranking and identities

**Files:**
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-product-candidates.ts`
- Modify: `C:/dev/wellnessbox/contracts/wb-rnd/product-candidate-match-v1.json`
- Test: `C:/dev/wellnessbox/scripts/qa/check-rnd-product-candidates.cts`

- [ ] **Step 1: Add contract versions and bounds**

```json
"combination_ranking_contract_version": "product_combination_ranking_v1",
"catalog_version_contract_version": "product_catalog_content_sha256_v1",
"max_ranked_product_combinations": 3
```

- [ ] **Step 2: Canonicalize catalog and request data**

```ts
function canonicalSha256(value: unknown) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}
```

Sort products, offers, categories, declarations, ingredient amounts, recommendations, and constraint arrays before hashing. Do not hash request IDs, timestamps, or response run IDs.

- [ ] **Step 3: Preserve evaluated combinations and derive reason codes**

```ts
const reasonCodes = [
  overBudget && "OVER_BUDGET",
  overProductCount && "OVER_MAX_PRODUCTS",
  safetyExcluded && "SAFETY_EXCLUDED_INGREDIENT",
  eligibleButBelowTopK && "LOWER_RANKED",
].filter(Boolean).sort();
```

- [ ] **Step 4: Rank eligible combinations**

```ts
eligible.sort((left, right) =>
  left.total_cost_krw - right.total_cost_krw ||
  left.product_count - right.product_count ||
  left.combination_id.localeCompare(right.combination_id)
);
```

Return ranks `1..k`, the exact ranking tuple, every evaluated non-selection identity with reason codes, `input_sha256`, `catalog_version`, and `result_sha256`.

- [ ] **Step 5: Run service checks**

Run: `node --conditions=react-server --import tsx scripts/qa/check-rnd-product-candidates.cts`

Expected: PASS with identical repeated and reordered-catalog results.

- [ ] **Step 6: Commit the service source change**

```powershell
git add -- contracts/wb-rnd/product-candidate-match-v1.json lib/server/wb-rnd-product-candidates.ts scripts/qa/check-rnd-product-candidates.cts
git commit -m "feat: rank reproducible product combinations"
```

### Task 3: Add independent R&D verification

**Files:**
- Modify: `src/wellnessbox_rnd/optimizer/product_combinations.py`
- Modify: `src/wellnessbox_rnd/optimizer/__init__.py`
- Modify: `tests/test_product_combinations.py`

- [ ] **Step 1: Add strict Pydantic ranking and explanation models**

```python
class ProductCombinationRankingV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["product_combination_ranking_v1"]
    max_ranked_combinations: StrictInt = Field(ge=1, le=10)
    combinations: tuple[ProductCombinationV1, ...]
    top_k: tuple[RankedProductCombinationV1, ...]
    non_selection: tuple[ProductCombinationNonSelectionV1, ...]
```

- [ ] **Step 2: Recompute rank order and all reasons in the model validator**

The validator must reject forged rank, missing filtered reasons, a selected combination in non-selection output, duplicate identities, non-canonical reason ordering, and a forged result hash.

- [ ] **Step 3: Add deterministic and forged-output tests**

```python
assert first.model_dump(mode="json") == second.model_dump(mode="json")
with pytest.raises(ValidationError):
    ProductCombinationRankingV1.model_validate(forged_rank)
```

- [ ] **Step 4: Run focused tests**

Run: `.\.venv-interim\Scripts\python.exe -m pytest tests/test_product_combinations.py -q`

Expected: PASS.

- [ ] **Step 5: Commit R&D source**

```powershell
git add -- src/wellnessbox_rnd/optimizer/product_combinations.py src/wellnessbox_rnd/optimizer/__init__.py tests/test_product_combinations.py
git commit -m "feat: verify deterministic product ranking"
```

### Task 4: Generate canonical integration evidence

**Files:**
- Create: `scripts/run_product_combination_top_k_reproducibility_smoke.py`
- Create: `data/original_plan/evidence/op067_op068_product_combination_top_k_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`

- [ ] **Step 1: Run the service QA from the canonical smoke**

Use `WELLNESSBOX_EVIDENCE_ROOT`, capture the service report, validate combinations with the R&D model, and independently recompute top-k, reasons, input/catalog/result hashes.

- [ ] **Step 2: Bind both repositories' relevant source paths**

Include the service catalog adapter, contract, QA, catalog reader, and R&D ranking validator, tests, and smoke script. Normalize CRLF to LF in the combined source hash.

- [ ] **Step 3: Generate twice and compare exact bytes**

Run the smoke twice to `etc/op067_op068_a.json` and `etc/op067_op068_b.json`; require equal SHA-256 before copying the first file to the canonical evidence path.

- [ ] **Step 4: Add the smoke to GitHub Actions**

Pin the committed service source SHA and compare the regenerated canonical file with `git diff --exit-code`.

### Task 5: Claim only proven stages and verify the loop

**Files:**
- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `docs/original_plan/completion_status_v1.json`
- Modify: `tests/test_original_plan_manifest.py`
- Modify: `tests/test_original_plan_audit.py`
- Modify: `tests/test_original_plan_audit_cli.py`
- Modify: `tests/test_original_plan_completion_report.py`
- Modify: `PROGRESS.md`
- Modify: `SESSION_HANDOFF.md`
- Modify: `NEXT_STEPS.md`

- [ ] **Step 1: Register OP-067/068 as `INTEGRATED` only after canonical evidence passes**

- [ ] **Step 2: Regenerate and check completion reports**

Run the report builder, audit, and workflow-equivalent tests. Do not hardcode report totals outside governance regression assertions.

- [ ] **Step 3: Run full validation**

Run service QA/typecheck/lint, full Ruff, all workflow smokes, full pytest, and the 256-case frozen evaluation. Require no new failure group and zero frozen metric/weakest-slice deltas.

- [ ] **Step 4: Perform independent review**

Require Critical `0` and Important `0`; fix and restart verification if either count is nonzero.

- [ ] **Step 5: Commit, push, and verify CI**

Stage only loop-owned files. Push the service commit before the R&D evidence commit. Verify `Original plan evidence` succeeds, then record exact hashes, counts, commits, and run IDs in the three handoff files.

---

Self-review: OP-067 is covered by deterministic ranking plus complete reason codes for every evaluated non-top-k combination. OP-068 is covered by canonical input/catalog/result identities and repeated/reordered-catalog evidence. The plan does not claim live Prisma execution, catalog freshness, deployment, production operation, order creation, or payment. No placeholders remain, and field names are consistent across service, R&D, smoke, and governance tasks.
