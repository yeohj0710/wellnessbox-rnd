# WellnessBox TIPS Interim End-to-End Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the verified 150,000-record `PROXY_GOLD_SIMULATION` package into the R&D runtime and WellnessBox service, execute every proxy KPI path end to end, and generate truthful interim evidence while preserving all real-world replacement gates.

**Architecture:** `wellnessbox-rnd` owns research data, SQLite persistence, evidence/safety/Agent logic, evaluation, reports, and the FastAPI contract. `wellnessbox` owns only authenticated feature-flagged thin proxy routes and Korean user/pharmacist/admin UI. Large frozen datasets remain external artifacts addressed by URI and SHA-256, while the import database stores row lineage and normalized operational records.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLite, scikit-learn/joblib, pytest/ruff; Next.js App Router, TypeScript, React, Tailwind, existing WellnessBox auth and QA scripts.

---

## File map

### `C:/dev/wellnessbox-rnd`

- `src/wellnessbox_rnd/interim/contracts.py`: data classes, replacement states, API payloads.
- `src/wellnessbox_rnd/interim/manifest.py`: package path resolution, SHA-256 and split validation.
- `src/wellnessbox_rnd/interim/store.py`: SQLite migrations, transactions, views, lineage and audit.
- `src/wellnessbox_rnd/interim/importer.py`: streaming import of 150k proxy rows and outcome/ADR/W-C-G records.
- `src/wellnessbox_rnd/interim/kpi.py`: plan-compatible seven-KPI evaluator with bootstrap confidence intervals.
- `src/wellnessbox_rnd/interim/safety.py`: versioned deterministic rules and replay.
- `src/wellnessbox_rnd/interim/agent.py`: bounded state machine and ten typed tools.
- `src/wellnessbox_rnd/interim/connectors.py`: official-source and device adapter contracts with environment/license gates.
- `src/wellnessbox_rnd/interim/reports.py`: required Markdown/JSON/report/manifest generation.
- `apps/inference_api/routes/interim.py`: operational and admin FastAPI routes.
- `scripts/run_interim_pipeline.py`: verify, import, retrain, evaluate, report and all commands.
- `tests/test_interim_*.py`: unit, migration, contract, API, replay, security and report tests.
- `docs/tips/**`, `artifacts/tips/interim/**`: generated evidence and reports.

### `C:/dev/wellnessbox`

- `lib/server/wb-rnd-interim-client.ts`: fixed-origin authenticated R&D client and pseudonymization.
- `lib/server/wb-rnd-interim-route.ts`: role-aware route handlers.
- `app/api/tips/**`, `app/api/admin/tips/**`, `app/api/pharm/tips/**`: thin routes using `route-auth.ts`.
- `app/(features)/tips/**`: user recommendation, chat, follow-up, PRO and AE interface.
- `app/(admin)/admin/tips/**`: source/rule/dataset/model/KPI dashboard.
- `app/(pharm)/pharm/tips/**`: simulation-badged review queue.
- `scripts/qa/check-tips-interim-modules.cts`: static contract/auth/flag guard.

## Task 1: Freeze source evidence and audit baseline

- [ ] Verify all 19 bundled manifest entries, four split counts, model hash, and 7/7 proxy KPI result.
- [ ] Record source package path, package manifest hash, model hash and PDF p.25-26 audit in `docs/tips/CURRENT_REPO_AUDIT.md`.
- [ ] Mark every capability with `IMPLEMENTED_AND_VERIFIED`, `IMPLEMENTED_UNVERIFIED`, `PARTIAL`, `MISSING`, `BLOCKED_EXTERNAL`, or `NOT_APPLICABLE`.
- [ ] Add regression tests that fail on any manifest hash/count drift.

Run:

```powershell
python scripts/run_interim_pipeline.py verify-package
python -m pytest tests/test_interim_manifest.py -q
```

Expected: 19/19 hashes, 150000 rows, model hash `41786a4d...a0a1aa4`, proxy KPI 7/7.

## Task 2: Add durable research store and streaming imports

- [ ] Write failing migration tests for clean DB, idempotent rerun, and upgrade from schema version 1.
- [ ] Implement SQLite tables for source/evidence/rules/datasets/models/cases/recommendations/Agent/PRO/ADR/connectors/KPI/audit/notebooks.
- [ ] Stream all 150,000 gzip rows in bounded batches; retain `PROXY_GOLD_SIMULATION`, split, session, line number, row hash and payload.
- [ ] Import 240 outcome proxy rows, 3 ADR rows and 180 linkage rows into the same operational tables used by later real data.
- [ ] Build materialized-query views for KPI and admin status.

Required invariant:

```python
assert store.scalar("select count(*) from proxy_cases") == 150_000
assert store.scalar("select count(*) from pro_observations") == 240
assert store.scalar("select count(*) from adverse_events") == 3
assert store.scalar("select count(*) from connector_sessions") == 180
```

Run:

```powershell
python scripts/run_interim_pipeline.py migrate --clean
python scripts/run_interim_pipeline.py import
python -m pytest tests/test_interim_store.py tests/test_interim_importer.py -q
```

## Task 3: Correct KPI semantics and register retrained model

- [ ] Test recommendation KPI against original p.26 denominator `|R_i|` (pharmacist/proxy reference set), not predicted-set precision.
- [ ] Test KPI-7 as mean of W/C/G source rates with per-source counts, not pooled success.
- [ ] Preserve proxy pass and real replacement state as separate fields for every KPI.
- [ ] Execute the package training pipeline into a new R&D run directory; never overwrite the frozen source.
- [ ] Register artifact URI/hash, dataset hash, feature schema, config, code commit, metrics and rollback pointer.

Run:

```powershell
python scripts/run_interim_pipeline.py retrain
python scripts/run_interim_pipeline.py evaluate
python -m pytest tests/test_interim_kpi.py tests/test_interim_model_registry.py -q
```

Gate: recommendation >=88% and CI lower >=84%; effect CI lower >0; action >=90%; answer >=96%; safety >=99% with hard FN 0; ADR <=5; W/C/G >=97%.

## Task 4: Implement evidence, safety and connector vertical slices

- [ ] Add source registry/evidence passage ingestion with license, freshness, hash, quarantine, content-diff and lineage gates.
- [ ] Add deterministic safety categories: emergency, pregnancy/lactation, age, kidney/liver, allergy, surgery, drug interaction, condition caution, duplicate, UL, test-before-recommend, timing, label constraint and stale source.
- [ ] Reject active critical rules without approved evidence and make `BLOCK`/`STOP_AND_ESCALATE` non-overridable.
- [ ] Add temporal replay and 300+ data-driven safety scenarios from the proxy evaluation.
- [ ] Implement PubMed, ClinicalTrials.gov, DailyMed, openFDA, RxNorm, ODS, DSLD and MFDS contract adapters; keep unavailable licensed/provider paths explicit.
- [ ] Implement W/C/G replay with consent, schema/unit/timezone/dedup/provenance postconditions.

Run:

```powershell
python -m pytest tests/test_interim_evidence.py tests/test_interim_safety.py tests/test_interim_connectors.py -q
```

## Task 5: Implement bounded Agent and operational API

- [ ] Encode the 12 allowed states and transition table; reject unknown transitions.
- [ ] Implement typed tools: `get_user_profile`, `retrieve_evidence`, `check_safety`, `rank_ingredients`, `optimize_regimen`, `create_followup`, `ingest_pro`, `ingest_wearable`, `escalate_pharmacist`, `log_adverse_event`.
- [ ] Enforce consent, pseudonymization, idempotency, timeout, audit and durable postconditions.
- [ ] Make serious AE atomically stop the plan and create an escalation record.
- [ ] Expose status/KPI/chat/recommendation/follow-up/PRO/AE/connector/admin/review routes.
- [ ] Add prompt-injection, timeout, stale evidence, duplicate action, missing consent and postcondition-failure tests.

Run:

```powershell
python -m pytest tests/test_interim_agent.py tests/test_interim_api.py tests/test_interim_security.py -q
```

## Task 6: Integrate authenticated feature-flagged WellnessBox UI

- [ ] Add `WB_RND_INTERIM_ENABLED`, fixed base URL, timeout, token and pseudonym salt settings.
- [ ] Require user, pharmacist or admin auth at each service-owned route; never expose raw app user IDs.
- [ ] Build user flow for recommendation/chat/follow-up/PRO/AE with evidence date, uncertainty and simulation status.
- [ ] Build pharmacist queue with a visible `PROXY_GOLD_SIMULATION` badge and immutable submit semantics.
- [ ] Build admin source/rule/dataset/model/KPI/connector dashboard.
- [ ] Follow Toss reference hierarchy: Pretendard-compatible typography, calm section rhythm, Korean-first direct copy, `#191f28` text, `#3182f6` action, restrained white/soft-gray bands.
- [ ] Preserve the existing nine user-modified service files and all checkout/subscription/fulfillment flows.

Run:

```powershell
npm run qa:tips:interim
npm run audit:encoding
npm run lint
npm run build
```

## Task 7: Generate interim reports and immutable evidence

- [ ] Generate every required `docs/tips/interim/*.md` file from DB and evaluation data.
- [ ] Generate `artifacts/tips/interim/kpi_report.json` and `evidence_manifest.json` after all other artifacts.
- [ ] Generate `IMPLEMENTATION_STATUS.md`, `BLOCKERS.md`, KPI traceability, security/privacy, ADR, connector and external-test documents.
- [ ] Use readable Korean problem-to-result flow based on Toss Feed references; remove generic report filler.
- [ ] Include proxy 7/7 in the first results table and separate real replacement status in its own column.
- [ ] Validate every manifest hash after generation.

Run:

```powershell
python scripts/run_interim_pipeline.py report
python scripts/run_interim_pipeline.py verify-release
```

## Task 8: Full verification and completion audit

- [ ] Run clean install, clean/upgrade migration, full pytest, ruff, API E2E, deterministic replay, PII/secret scan, dependency audit and research-note generation.
- [ ] Run WellnessBox lint/build/QA and browser E2E at desktop and mobile widths.
- [ ] Compare every requirement and named artifact to direct evidence; do not infer completion from absence of errors.
- [ ] Record external-only gates: pharmacist labels, real outcomes, 12-month operation, production devices, external test/certification and legal review.
- [ ] Update `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md` and commit only task-owned files.

Final command:

```powershell
python scripts/run_interim_pipeline.py all --verify
```

Expected: all automated gates green, critical safety/security failures 0, proxy KPI 7/7, and no unsupported real-world claim.

## Self-review

- Spec coverage: package requirements 1-13, vertical slices 1-12, ten Agent tools, ten reports, all completion gates and final replacement states are assigned above.
- Placeholder scan: no implementation step relies on a blank adapter, TODO, mock UI or hardcoded KPI result.
- Type consistency: data classes use exact labels `PROXY_GOLD_SIMULATION`, `SYNTHETIC_OUTCOME_PROXY`, `SYNTHETIC_SAFETY_PROXY`, `SIMULATED_INTEGRATION_PROXY`; replacement states remain separate.
- Execution choice: inline execution in this active goal, as required by the user-provided override.
