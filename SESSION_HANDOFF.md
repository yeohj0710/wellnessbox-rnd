# SESSION_HANDOFF

## 2026-07-22 OP-087/088 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-087 binds counseling answers to one service session, one turn, one verifier decision, and one recommendation run; OP-088 adds the thin WellnessBox-to-R&D adapter inside the existing chat path.
- Primary dataset and cases: `24` passages from `19` sources and frozen evaluation `256` cases. Canonical evidence is `data/original_plan/evidence/op087_op088_counseling_session_service_adapter_smoke_v1.json`, SHA-256 `5941704422859298938a42d55d06c5a4b79d03aa56935cc1cb292a343eff6fce`; R&D source commit `fbebdee389e277642a536281a54800c4637da6e0`; service source commit `f78604c74795c127a004a7be64cb67c7fe112803`.
- Main files: the existing interim route and store, committed counseling corpus, existing chat route and save route, existing R&D client, service QA scripts, focused tests, canonical smoke, manifest, generated completion reports, CI workflow, and two long-form research reports.
- Code/data/training/simulation: a strict counseling turn contract, stable session binding, full semantic replay hash, concurrent recommendation idempotency, pseudonymous profile mapping, and transactional service persistence are implemented. No model training, frozen-data change, deployment, production operation, production database write, external validation, or live language-model inference occurred.
- Stage/result: OP-087 is `IMPLEMENTED` against required `OPERATED`; OP-088 is `IMPLEMENTED` against required `INTEGRATED`. Both are PARTIAL. Completion counts are `62/25/32/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: OP-079 through OP-088 have separate explanatory prose reports. Coverage is `10/120`, not 120/120; `110` remain. Total current report text is `80,291` characters. OP-087 is `11,381` characters and OP-088 is `9,862` characters.
- Independent review: the review sequence found Critical `1`, Important `10`, Minor `0` in total. Fixes cover session-scoped message identity, changed-payload replay rejection, concurrent insertion, privacy allowlists, truthful consent scopes, persisted binding evidence, atomic Prisma writes, stable retries, migration compatibility, and actual `UserProfile` mapping. Final review is Critical `0`, Important `0`, Minor `0`.
- Validation: exact workflow selection `613 passed`; full Ruff PASS; audit PASS (`87` claims, `249` evidence files); completion check PASS; canonical bytes and source hashes verified twice. Full regression is `992 passed`, `77 failed`, with no new failure group. Frozen eval has seven zero metric deltas and unchanged weakest categories.
- Publication: WellnessBox service HEAD `f78604c74795c127a004a7be64cb67c7fe112803` is on `origin/main`. R&D publication and final `Original plan evidence` CI run remain pending.
- Current bottlenecks: `110/120` reports remain; OP-087 lacks production operation; OP-088 lacks `/api/chat` plus isolated Prisma database evidence; no deployed R&D counseling process or production telemetry exists; external counseling validation remains absent.
- Next loops: finish R&D push and CI, then OP-089/090, while reconstructing OP-001 through OP-078 reports only from primary source, Git history, tests, and canonical evidence.

## 2026-07-21 OP-085/086 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-085 blocks unsupported claims, omitted risks, forbidden expressions, and policy/query-evidence mismatch; OP-086 places deterministic emergency guidance before retrieval, recommendation, and provider calls.
- Primary dataset and cases: `24` passages from `19` sources; normal/urgent/negated/contrast answer cases; `5` common urgent phrasing cases; `7` tamper/policy probes; frozen evaluation `256` cases. Canonical evidence is `data/original_plan/evidence/op085_op086_counseling_verifier_urgent_safety_smoke_v1.json`, SHA-256 `e7dcfe8248d7ba73769efd618cd29cb3deb99675df8ee4e5af5aff54280d2a36`; source commit `c6ca444488e7af34b416e3da208016972010315d`; source SHA-256 `14022f4617560b4ae386c047eddb88269903b463fdbd2414edac7f9af9528b9c`; data SHA-256 `11f257c44f05db6d0286de3701cf72c428cbe46991b44f190729371ca167f228`.
- Main files: `src/wellnessbox_rnd/chat/answering.py`, `retrieval.py`, `verifier.py`, the existing OpenAI adapter, `data/knowledge/counseling_answer_verifier_policy_v1.json`, focused tests, canonical smoke, manifest, completion reports, CI workflow, and the two long-form research reports.
- Code/data/training/simulation: final prose is server-owned; verifier decisions are recomputed from repository policy, the original query, current bounded retrieval, and exact selected evidence. No model training, frozen-data change, WellnessBox service code change, deployment, production operation, external validation, or live language-model inference occurred.
- Stage/result: OP-085 and OP-086 are COMPLETE at required stage `IMPLEMENTED`. Completion counts are `62/23/34/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: OP-079 through OP-086 have separate explanatory prose reports. Coverage is `8/120`, not 120/120; `112` remain. Total current report text is `48,961` UTF-8 characters. OP-085 is `6,647` characters and OP-086 is `7,308` characters.
- Independent review: initial Critical `2`, Important `1`, Minor `0`; after the first fixes Critical `0`, Important `0`, Minor `1`; after threshold replay and CI portability fixes final Critical `0`, Important `0`, Minor `0`. Fixed cases are common urgent aliases, query/evidence relevance recomputation, repository-relative policy loading, non-default support-score replay, and CI service-evidence-root resolution.
- Validation: focused `50 passed`; exact workflow selection `609 passed`; all `26` workflow smokes PASS; Ruff PASS; audit PASS (`85` claims, `242` evidence files); completion check PASS; canonical bytes and source/data hashes independently verified.
- Full regression: `1,065` collected, `988 passed`, `77 failed`; known split `73` absent-report + `3` CGM geometry + `1` CGM closed-loop; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: R&D HEAD `bfe7c813c80a29c523a9367b2dc291b1df4d5537` is on `origin/main`. CI run `29841093182` failed only because the smoke assumed a sibling service checkout; commit `c6ca444` fixed it using `WELLNESSBOX_EVIDENCE_ROOT`. Final `Original plan evidence` run `29841384466` passed. The WellnessBox service repository remains at `4d904f43b028a35524a29206aaf7c6b99f58a97b` with preserved user-owned changes.
- Five current bottlenecks: `112/120` reports remain; OP-087/088 session persistence and service adapter are not implemented; no deployed R&D counseling process exists; no authenticated production service-to-R&D counseling call exists; no external counseling validation or production telemetry exists.
- Next three loops: OP-087/088, OP-089/090, and OP-091/092, with one full prose report per newly verified requirement and evidence-grounded backfill for OP-001 through OP-078.

## 2026-07-21 OP-083/084 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-083 repository-bounded retrieval and OP-084 answer provenance, validity dates, and explicit uncertainty.
- Primary dataset and cases: `24` passages from `19` sources, `4` answer cases, `8` rejection probes, and frozen evaluation `256` cases. Canonical evidence is `data/original_plan/evidence/op083_op084_bounded_rag_answer_provenance_smoke_v1.json`, SHA-256 `cfb10b0bdb9d02fbd1851cddde8b32c914a1ac00929b47f60e514c343fffb04d`; source SHA-256 `03c86d65261517c360e4120a9d2f3039cc30fa8db568c9bebe431e558e026f5f`.
- Main files: bounded retrieval and answer contracts, the existing OpenAI adapter, the repository scope registry, focused tests, canonical smoke, manifest, generated completion reports, CI workflow, and `docs/original_plan/research_reports/OP-083.md` plus `OP-084.md`.
- Code/data/training/simulation: retrieval and answer validation now use repository-pinned knowledge identity and reconstruct provenance on the server. No model training, frozen-data change, service code change, deployment, production operation, external validation, or live language-model inference occurred.
- Stage/result: OP-083 and OP-084 are COMPLETE at required stage `IMPLEMENTED`. Completion counts are `60/23/36/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: only OP-079 through OP-084 have individual long-form reports. Coverage is `6/120`, not 120/120; `114` reports remain. The six files total `35,006` UTF-8 characters. Final completion requires 120 separate reports, one for every OP.
- Writing requirement: a research report is a continuous, explanatory human document, not a compact activity log. Every report must spell out the requirement, existing implementation path, evidence examined, reasoning, work performed, failed approaches and corrections, reproducible verification, unresolved limitations, and the distinction among implementation, integration, operation, and external validation. Abbreviations must be expanded on first use, and bullets or machine evidence may support but cannot replace the prose.
- Validation: focused regression `39 passed`; workflow-equivalent `596 passed`; full Ruff PASS; audit PASS (`83` claims, `238` evidence files); completion check PASS; `27` smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `975 passed`, `77 failed`; known split `73` absent-report + `3` CGM geometry + `1` CGM closed-loop; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence HEAD `67d65c3160a004c0ec1f6030a645c3ef9dbda8ee` was pushed; GitHub Actions `Original plan evidence` run `29838281957` passed.
- Five current bottlenecks: `114/120` reports are still missing; OP-085/086 are not implemented; no deployed R&D counseling process exists; no authenticated production service-to-R&D counseling call exists; no external counseling validation or production telemetry exists.
- Next three loops: OP-085/086, OP-087/088, and OP-089/090, with one full prose report per newly verified requirement and evidence-grounded backfill for OP-001 through OP-078.

## 2026-07-21 OP-081/082 handoff

- Chosen stage/tasks: `original plan / counseling RAG`; OP-081 passage-level evidence collection with source/effective dates and OP-082 extraction of health goals, ingredients, drugs, and risk signals.
- Primary dataset and cases: `24` passages from `19` sources and `9` question cases, including `4` urgent cases; frozen eval `256` cases. Canonical evidence is `data/original_plan/evidence/op081_op082_counseling_passage_entity_smoke_v1.json`, SHA-256 `03c0efdc6110208f4e2e185c17524099d5b8fcdc5f27366cf6bd47c5ecb332f4`; source SHA-256 `ab6ffef24a9d936a9374d82a3a385943ad7a8b2600999b909ce7bc413d918d68`.
- Main files: `src/wellnessbox_rnd/chat/retrieval.py`, `scripts/build_chat_retrieval_assets.py`, the existing chat adapter and learned-runtime audit fixture, focused tests, canonical smoke, manifest, generated completion reports, CI workflow, and `docs/original_plan/research_reports/OP-081.md` plus `OP-082.md`.
- Code/data/training/simulation: existing reference and runtime-knowledge data now produce source-span-verified passages and deterministic entity traces. No model training, frozen dataset change, service code change, deployment, production operation, external validation, or LLM inference occurred.
- Stage/result: OP-081 and OP-082 are COMPLETE at required stage `IMPLEMENTED`. Completion counts are `58/23/38/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: separate prose reports now exist for OP-079 through OP-082, so coverage is `4/120`, not 120/120. OP-081 and OP-082 are about 6,500 characters each; all four current reports total `27,023` characters. The remaining 116 reports require evidence-grounded writing and must not be represented by manifest rows alone.
- Validation: focused/downstream regression `51 passed`; workflow-equivalent `584 passed`; full Ruff PASS; audit PASS (`81` claims, `232` evidence files); completion check PASS; `26` smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `968 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence HEAD `fd41644949479fbbc4219eb40fa31d7b4b13a30f` was pushed; GitHub Actions `Original plan evidence` run `29835498939` passed.
- Five current bottlenecks: only `4/120` long-form reports exist; OP-083/084 bounded answer generation is not implemented; no deployed R&D counseling process; no authenticated production service-to-R&D counseling call; no external counseling validation or production telemetry.
- Next three loops: OP-083/084 bounded RAG and evidence validity/uncertainty; OP-085/086; OP-087/088, with one full prose report per newly verified OP and continuing report backfill.

## 2026-07-21 OP-079/080 handoff

- Chosen stage/tasks: `original plan / closed-loop execution`; OP-079 lifecycle transition E2E and OP-080 strict separation between plan state and order state.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `5` authenticated API cases. Evidence SHA-256 is `2d51305ff69306061528a7ac0f6becabb6351d6a7025e439885dc73282246308`; source SHA-256 is `53f79c6cabb636782b9be23b5797ae42861890319a642b9848100096883d5a4f`.
- Main files: `src/wellnessbox_rnd/interim/plan_lifecycle.py`, `jobs.py`, `data_mutation.py`, `store.py`, the existing interim API route, OP-079/080 smoke, focused tests, manifest, completion reports, and both long-form reports.
- Code/data/training/simulation: existing execution lineage now stores and replays guarded transitions and real replacement candidates. No model training, frozen dataset change, service code change, deployment, production operation, or order mutation occurred.
- Stage/result: both requirements are proven only to `IMPLEMENTED` and remain PARTIAL because both require `OPERATED`. Completion counts are `56/23/40/1/0` for complete/partial/pending/external/contradicted.
- Research-report result: two full prose reports exist, so overall coverage is `2/120`, not 120/120. The remaining 118 reports require evidence-by-evidence backfill.
- Validation: focused lifecycle regression `45 passed`; workflow-equivalent `559 passed`; full Ruff PASS; audit PASS (`79` claims, `226` evidence files); completion check PASS; 23 smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `948 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence HEAD `fadf80fc68f6bc93817b8111a8f01cd9d7aa8060` was pushed; GitHub Actions `Original plan evidence` run `29832628539` passed.
- Five current bottlenecks: only `2/120` long-form reports exist; no deployed R&D process; no durable production R&D database/queue; no authenticated production service-to-R&D lifecycle call; no observed production lifecycle or order-boundary telemetry.
- Next three loops: OP-081/082 passage indexing and entity extraction; OP-083/084 bounded RAG with evidence validity and uncertainty; OP-085/086, with report backfill included in each loop.

## 2026-07-21 OP-077/078 handoff

- Chosen stage/tasks: `original plan / closed-loop execution`; OP-077 fail-closed job guards and OP-078 pharmacist-review creation/completion postconditions.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `5` cases. Evidence SHA-256 is `df67af2cf7ecd9f99edc7a98dcf6a607d633983da8a6f9cd65630973b6a0b2d4`; source SHA-256 is `58746132ddc4d840a479a9fe4075423fff45c4cd4cf9c78a10d431ed74fae978`.
- Main files: `src/wellnessbox_rnd/interim/jobs.py`, `reviews.py`, `store.py`, `agent.py`, the existing interim API route, OP-077/078 smoke, focused tests, manifest, completion reports, and affected shared canonical evidence.
- Code/data/training/simulation: existing ledgers, jobs, consent records, and review tasks now enforce pinned guards and immutable review completion. No model training, frozen dataset change, service code change, deployment, or production operation occurred.
- Stage/result: both requirements are proven only to `IMPLEMENTED` and remain PARTIAL because both require `OPERATED`. Completion counts are `56/21/42/1/0` for complete/partial/pending/external/contradicted.
- Validation: focused `59 passed`; workflow-equivalent `541 passed`; full Ruff PASS; audit PASS (`77` claims, `220` evidence files); completion check PASS; 22 smokes regenerated; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `930 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence/docs HEAD `de7f493415618d11a492f782f8bbd20b3939b206` was pushed; GitHub Actions `Original plan evidence` run `29829346647` passed.
- Five current bottlenecks: no deployed R&D process; no durable production R&D database/queue; no production worker timeout/stale-evidence telemetry; no authenticated production service-to-R&D round trip; no observed pharmacist review operation.
- Next three loops: OP-079/080 lifecycle E2E and separate order state; OP-081/082 passage/source indexing and question entity extraction; OP-083/084 bounded RAG and answer evidence/validity/uncertainty.

## 2026-07-21 OP-075/076 handoff

- Chosen stage/tasks: `original plan / closed-loop execution`; OP-075 follow-up input next-job selection and OP-076 serious-adverse-event plan/recommendation stop.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `3` cases. Evidence SHA-256 is `847f861085d44916bfcab9c6a51ed2d9048262023c9c8e4b031b716b8285dd97`; source SHA-256 is `4e33d0f4560699ceb9e06eb894671f4312be9fcfd734a85ce60dbce73b4c7a28`.
- Main files: `src/wellnessbox_rnd/interim/agent.py`, `jobs.py`, `apps/inference_api/routes/interim.py`, the OP-075/076 smoke, focused tests, manifest, completion reports, and affected shared canonical evidence.
- Code/data/training/simulation: existing ledgers and queues now decide revision-bound PRO/device reevaluation work and enforce a fail-closed serious-AE hold. No model training, frozen dataset change, service code change, deployment, or production operation occurred.
- Stage/result: both requirements are proven only to `IMPLEMENTED` and remain PARTIAL because both require `OPERATED`. Completion counts are `56/19/44/1/0` for complete/partial/pending/external/contradicted.
- Validation: focused `30 passed`; workflow-equivalent `532 passed`; full Ruff PASS; audit PASS (`75` claims, `216` evidence files); completion check PASS; 21 smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `921 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: implementation/evidence/docs HEAD `b08cc0744b6f662ac23b5a6bc5fc01d419b2a650` was pushed; GitHub Actions `Original plan evidence` run `29827163566` passed.
- Five current bottlenecks: no deployed R&D process; no durable production R&D database/queue; no production PRO/device ingestion observation; no authenticated production service-to-R&D round trip; no production serious-AE stop/hold telemetry.
- Next three loops: OP-077/078 fail-closed execution and pharmacist-review lifecycle; OP-079/080 lifecycle E2E and separate order state; OP-081/082 consent revocation and minimum-data-state handling.

## 2026-07-21 OP-073/074 handoff

- Chosen stage/tasks: `original plan / closed-loop execution`; OP-073 shared follow-up/reminder queue and OP-074 due-plan reevaluation Cron.
- Primary dataset and cases: `data/original_plan/evidence/op073_op074_followup_job_queue_cron_smoke_v1.json`; two follow-ups and four Cron runs; SHA-256 `5399806ac1e2af79d8390b4456bf54a6bea8de7b5ca8cf7b0b07b2cc099b3ea2`.
- Main files: `src/wellnessbox_rnd/interim/jobs.py`, `store.py`, `agent.py`, `apps/inference_api/routes/interim.py`, both queue/Cron scripts, focused tests, manifest, completion reports, and shared canonical evidence files.
- Code/data/training/simulation: schema v10 links follow-ups/jobs to the existing execution ledger and adds claim/lease/ack/retry state. No model training, frozen dataset change, service code change, deployment, or production operation occurred. Simulation evidence remains explicitly local.
- Stage/result: both requirements are proven only to `IMPLEMENTED` and remain PARTIAL because both require `OPERATED`. Completion counts are `56/17/46/1/0` for complete/partial/pending/external/contradicted.
- Validation: focused `46 passed`; workflow-equivalent `504 passed`; full Ruff PASS; audit PASS (`73` claims, `214` evidence files); completion check PASS; 20 smokes reproduced; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `914 passed`, `77 failed`; known failure split `73` absent-report + `4` CGM geometry; other failures `0`.
- Frozen/replay/slice: `256` cases, seven zero metric deltas, unchanged overall weakest category `safety_blocked`, and no metric-specific weakest-category change.
- Publication: pushed HEAD `97a124b035cda1b525a709b2c2bb0d9a1d8da04a`; GitHub Actions Original plan evidence run `29824602501` succeeded.
- Five current bottlenecks: no deployed R&D process; no durable production R&D database/queue; no deployed CronJob observation; no authenticated production service-to-R&D round trip; no production worker lease/ack/retry telemetry.
- Next three loops: OP-075/076 next-job selection and serious-AE stop; OP-077/078 fail-closed execution and pharmacist-review lifecycle; OP-079/080 lifecycle E2E and separate order state.

Older handoff entries are archived in `docs/archive/SESSION_HANDOFF-archive-1.md`.

## 2026-07-21 closed-loop state and ordered execution handoff

- Chosen stage and tasks: `original plan / closed-loop execution`; OP-071 and OP-072.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke has `5` cases covering success, safety block, missing evidence, direct-move rejection, and idempotent retry.
- Primary evidence: `data/original_plan/evidence/op071_op072_closed_loop_state_order_smoke_v1.json`; SHA-256 `6bb772f0448722ce8efc6f010160f356b9789f026b76be997cd59e3cd0f607e1`; source SHA-256 `021b82bc4ff11faeb23e79b934431d4af2205a42f96070de450c94c27fca8460`.
- Source identity: R&D `26941e94554f21766823c043b635c865257e4646`; no service source is claimed for OP-071/072.
- Main changes: authoritative state/operation contract; strict trace models; exact safety-to-plan order; candidate/safety binding; evidence-constrained optimization; durable steps; direct-state bypass rejection; cross-worker SQLite claims; changed-payload idempotency rejection; existing interim API reuse. No service, training, data-generation, or simulation behavior changed.
- Honest stage: OP-071 and OP-072 are PARTIAL at `IMPLEMENTED`, below required `OPERATED`. Local SQLite behavior and API contract are proven. Service integration, deployment, production operation, and actual plan activation are not.
- Validation: focused/governance `63 passed`; workflow-equivalent `505 passed`, `1 skipped`; full Ruff PASS; `19` workflow smokes PASS; audit PASS with `71` claims and `208` evidence files; independent review Critical `0`, Important `0`.
- Full regression: `902 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: R&D HEAD `61b16929ebd2647438717e450fbceb954e92c140`; Original plan evidence run `29822306554` succeeded. The service repository retained all user changes and received no loop commit.
- Five bottlenecks: production operation evidence for OP-071; production operation evidence for OP-072; actual follow-up job queue for OP-073; due-plan CronJob for OP-074; trusted restoration of `73` absent report artifacts plus separate CGM-geometry investigation.
- Next three loops: OP-073/074, OP-075/076, OP-077/078.

## 2026-07-21 stock substitution and approval-gated cart integration handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-069 and OP-070.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `8` previous combinations, `4` current combinations, `1` missing offer, `3` cart items, `1` active safety rule, and `1` active exclusion.
- Primary evidence: `data/original_plan/evidence/op069_op070_product_combination_stock_cart_smoke_v1.json`; SHA-256 `9b40f6a05e73e82dde8582f7c0e7e043f9e1481214cd3d825c0d19e03a15e139`; combined source SHA-256 `07f8f483bcc013fd51627f27aa58e0e03c6c8cc208dc987abf987600049830ca`.
- Source identity: R&D `a2ae7a289ae3f0923145db707f3c042e868cd059`; WellnessBox `4d904f43b028a35524a29206aaf7c6b99f58a97b`.
- Main changes: strict previous replay context; current-catalog stock loss detection; existing optimizer reuse; independent previous/current ranking validation; exact safety-policy and recommendation-input binding; fail-closed cart suppression on non-stock changes; existing cart-item contract conversion; source scan for cart, order, and payment mutations; manifest, reports, workflow, tests, and canonical evidence. No training or simulation behavior changed.
- Honest stage: OP-069 and OP-070 are COMPLETE at `INTEGRATED`. Existing route-function integration and approval-gated candidate construction are proven. Actual Prisma execution, browser cart mutation, user approval, Order/OrderItem/Payment creation, production deployment, and production operation are not.
- Validation: focused `26 passed`; workflow-equivalent `505 passed`; full Ruff PASS; service QA/typecheck/lint PASS; `18` service-dependent smokes PASS; audit PASS with `69` claims and `203` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `886 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: service commit `4d904f43b028a35524a29206aaf7c6b99f58a97b`; R&D commit `06debd77c39581c6cbe90beefa3be3095336f606`; Original plan evidence run `29819257210` succeeded.
- Five bottlenecks: actual Prisma catalog-query evidence; production catalog freshness; deployed service/R&D operation; OP-071 unified state-transition contract; OP-072 enforced orchestration order.
- Next three loops: OP-071/072, OP-073/074, OP-075/076.

## 2026-07-21 product-combination top-k and reproducibility integration handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-067 and OP-068.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `4` evaluated combinations, top-k `3`, and `1` non-selection reason.
- Primary evidence: `data/original_plan/evidence/op067_op068_product_combination_top_k_smoke_v1.json`; SHA-256 `f510f7c09aea3e23af64275001b53ae6a14b0c45760a3a0a112cb390dd5153ae`; combined source SHA-256 `b78acd6e01dc75eab4dfe18622c975ba810877d6ae3321a5d7847a5452482613`.
- Source identity: R&D `dc8e145b3a62897af6238f2c9b74dd35a75f4714`; WellnessBox `a27de7c0beee507114641e24a058827d46ad2ef0`.
- Main changes: global eligible-combination ranking before response limiting; precise non-selection reasons; fail-closed truncated search; content-addressed optimization and catalog identities; duplicate offer-ID rejection; independent R&D ranking and provenance validation; manifest, reports, workflow, tests, and canonical evidence. No training or simulation behavior changed.
- Honest stage: OP-067 and OP-068 are COMPLETE at `INTEGRATED`. Existing route-function integration is proven, but actual Prisma execution, production data freshness, deployment, production operation, ordering, and payment are not.
- Validation: focused `20 passed`; workflow-equivalent `499 passed`; full Ruff PASS; service QA/typecheck/lint PASS; `17` service-dependent workflow smokes PASS; audit PASS with `67` claims and `200` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `880 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: service commit `a27de7c0beee507114641e24a058827d46ad2ef0`; R&D commit `0635b17c2dd18c9f861c012c5f865fb5f720abf3`; Original plan evidence run `29816477275` succeeded.
- Five bottlenecks: actual Prisma catalog-query evidence; production catalog freshness; deployed service/R&D operation; stock-change substitution evidence for OP-069; approval-gated cart conversion for OP-070.
- Next three loops: OP-069/070, OP-071/072, OP-073/074.

## 2026-07-21 product-combination constraint and safety integration handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-065 and OP-066.
- Primary dataset and cases: frozen eval `256` cases; canonical smoke `4` constraint-filter inputs, `1` product-side safety-filter input, and `1` actual localhost R&D-to-service constraint response.
- Primary evidence: `data/original_plan/evidence/op065_op066_product_combination_filter_smoke_v1.json`; SHA-256 `87c16d1e39d2a7ea9b64f16ba46f0bcb5946da8265aa87c75e40a53611de2a3f`; combined source SHA-256 `ace71663d00cb8999affafc0cd2fad9c24ccc3390264bba0a895fb1703ead1c0`.
- Source identity: R&D `275674c5d667e4a76f42dd6aa62dbcadf5baec50`; WellnessBox `7f248485f522fd85ca09a71a9252cf1ec8dc5896`.
- Main changes: strict R&D product constraints; existing service-route validation before zero-result return; budget and maximum-product filters applied before the eligible cap; product-side ingredient safety exclusion; fail-closed recommendation re-entry protection; independent R&D filter recomputation; manifest, reports, workflow, tests, and canonical evidence. No training or simulation behavior changed.
- Honest stage: OP-065 and OP-066 are COMPLETE at `INTEGRATED`. Actual localhost R&D constraint transport is proven, but the actual READY filter path, Prisma execution, production data freshness, deployment, production operation, ordering, and payment are not.
- Validation: focused `27 passed`; workflow-equivalent `492 passed`; full Ruff PASS; service QA/typecheck/lint PASS; `16` workflow smokes PASS; audit PASS with `65` claims and `198` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `873 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, and unchanged metric-specific weakest categories.
- Publication: service commit `7f248485f522fd85ca09a71a9252cf1ec8dc5896` passed Encoding Guard run `29813747636`. R&D commit `c085d467a6447316fc865b84996e6085fa7b928d` passed Original plan evidence run `29813998092`.
- Five bottlenecks: actual READY R&D filter-path evidence; actual Prisma catalog-query evidence; production catalog freshness; deployed service/R&D operation; OP-067 top-k non-selection reasons.
- Next three loops: OP-067/068, OP-069/070, OP-071/072.

## 2026-07-21 product combination and aggregate-dose integration handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-063 and OP-064.
- Primary dataset and cases: frozen eval `256` cases; service fixture `7` products and `8` recommendations; canonical smoke `4` generated combinations with `2` independently validated representative combinations.
- Primary evidence: `data/original_plan/evidence/op063_op064_product_combination_dose_smoke_v1.json`; SHA-256 `64821bf96e724cfcb21be2b4e0d011dd3c364b072614ca7505dda8659b1e9ea8`; combined source SHA-256 `3c48c1b8fecac69e3b8b088830e0efa7c6bcc4b9784f81af72a0dcc39d69ce05`.
- Source identity: R&D `00fbd06f275e7ba2a486e398fdd56591388df6ad`; WellnessBox `6c599ebeebca73e8d769426b02f12d4e7be19073`.
- Main changes: the existing `/api/tips` adapter converts strict selling-product declarations into deterministic ingredient combinations, reuses the existing in-stock offer selection, deduplicates shared products, normalizes mass to integer nanograms and IU to milli-IU, and reports total declared dose by ingredient and unit. Duplicate ingredients require distinct product IDs. Search is memoized, bounded to `4096` states, and capped at `64` unique combinations. Ambiguous ranges and missing target amounts fail closed. The R&D model independently revalidates identities, costs, totals, duplicates, limits, and source identity. No training or simulation logic changed.
- Honest stage: OP-063 and OP-064 are COMPLETE at `INTEGRATED`. The existing service route and R&D validation contract are connected, but actual Prisma execution, production catalog freshness, deployment, production operation, ordering, and payment are not proven.
- Validation: product-combination tests `10 passed`; exact workflow selection `482 passed`; full Ruff PASS; service QA/typecheck/lint/build PASS; all `15` workflow smokes reproduce byte-identically; audit PASS with `63` claims and `196` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `863 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: service commit `6c599ebeebca73e8d769426b02f12d4e7be19073` passed Encoding Guard run `29811071339`. R&D commit `23d5c43efc8b029f78c2f62c92665bc5960307de` passed Original plan evidence run `29811445770`.
- Five bottlenecks: actual Prisma catalog-query evidence; production catalog freshness; deployed service/R&D operation; OP-065 budget and maximum-product exclusion; OP-066 safety-block preservation.
- Next three loops: OP-065/066, OP-067/068, OP-069/070.

## 2026-07-21 optimization constraints and selling-product contract handoff

- Chosen stage and tasks: `original plan / product optimization`; OP-061 and OP-062.
- Primary dataset and cases: frozen eval `256` cases; canonical constraint smoke `6` cases; service product fixture covers `8` mapped ingredient IDs.
- Primary evidence: `data/original_plan/evidence/op061_op062_optimization_product_catalog_smoke_v1.json`; SHA-256 `aaa917bb4256e648d62fa12564353c26fe01717cb38360aa23e0495e1f22f480`; combined source SHA-256 `83118c67e45f96e6eba41e6ee853977278da8d9a8043239ca35bb3d97da10429`.
- Source identity: R&D `ea3bc72484708002065ee4929dc62ca006ce980c`; WellnessBox `a85767d9dc9418a23a9adeb2372d14a75d10b865`.
- Main changes: immutable R&D constraint contract and evaluator; existing service catalog query extended with detail facts and in-stock offers; existing `/api/tips` adapter extended with normalized amount, price, stock, and formulation facts; strict fail-closed QA; manifest, generated reports, workflow, tests, and canonical evidence.
- Honest stage: OP-061 is COMPLETE at `IMPLEMENTED`. OP-062 is COMPLETE at `INTEGRATED` because the existing service route function consumes the extended adapter contract. Actual Prisma execution, production freshness, deployment, operation, ordering, and payment remain unproven.
- Validation: optimizer `16 passed`; CI-equivalent `472 passed`; full Ruff PASS; service QA/typecheck/lint/build PASS; all `14` workflow smokes byte-identical; audit PASS with `61` claims and `192` evidence files; independent review Critical `0`, Important `0`, Minor `0`.
- Full regression: `853 passed`, `77 failed`, exactly the known `73` absent-report plus `4` CGM-geometry groups. Frozen eval has `256` cases, seven zero metric deltas, unchanged overall `safety_blocked` weakest slice, and unchanged metric-specific weakest categories.
- Publication: service Encoding Guard run `29808830876` and R&D Original plan evidence run `29808907535` passed. Evidence commit is `e50ba258e6b965f3a3af9aa5b078e00e8d690647`.
- Five bottlenecks: actual Prisma catalog query evidence; production catalog freshness; deployed service/R&D operation; product-to-ingredient combination generation; duplicate-ingredient and total-dose enforcement across combinations.
- Next three loops: OP-063/064, OP-065/066, OP-067/068.

## 2026-07-21 PRO worsening actions and outcome-class integration handoff

- Chosen stage and tasks: `original plan / pre-post outcome quantification and PRO`; OP-059 and OP-060.
- Primary dataset/evidence: frozen eval `256` cases; four authenticated real-world-class enrollment/follow-up pairs and one synthetic paired case. Canonical evidence SHA-256 `ec14bf87025c9b1651462a936092cc3e2089956df2a72cfb826fa3594f22318d`; combined source SHA-256 `8e6969aac2e5e4d17bc9dfbb5176207874f697bd111955ea9fca6d06d107f7eb`.
- Source identity: R&D `a580d813abfc1bed0292477c9ba6dc88ec4f8f4f`; WellnessBox `5ec3adf1f3948e910c1f4498083b43c701eaf557`.
- Implementation: `metrics/pro_actions.py` validates the exact four decisions and rejects mutated derived output. The existing plan service, interim route, strict execution events, service proxy/client, TIPS PRO state, and UI carry the decision and selected outcome class. No second recommendation engine, event store, API, or product system was added.
- Result: serious adverse events select stop; other adverse events select reduce; low adherence or missed doses select maintain; interpretable worsening selects re-optimize. Observed numeric change is not adjusted and no causal effect is claimed. `REAL_WORLD_OUTCOME` is a contract class only; no production or real patient data was used.
- Honest stage: OP-059 and OP-060 are `INTEGRATED` and COMPLETE at their required stage. Production deployment, operation, real-data provenance, and action execution remain unproven.
- Validation: focused `54 passed`; workflow-equivalent `456 passed`; full suite `837 passed`, `77 failed` in the known `73 + 4` groups; frozen 256 evaluation has seven zero deltas and identical weakest slices; full Ruff and service build/lint/typecheck/QA PASS; 13 workflow smokes are stable; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: R&D is published through `b068edac16e889dc6d18e004cf87726eb39e214d`; service through `5ec3adf1f3948e910c1f4498083b43c701eaf557`; R&D Original plan evidence run `29807082270` and service Encoding Guard run `29807015490` succeeded.
- Biggest remaining bottlenecks: required operation evidence for OP-021~030, OP-040, OP-053, and OP-058; qualifying external labels for OP-039; OP-061~120 implementation; missing trusted report archive for 73 tests; four CGM geometry failures.
- Protected user files remain untouched. Existing `etc/` files remain untracked and were not used as canonical evidence.
- Next three loops: OP-061/062; OP-063/064; OP-065/066.

## 2026-07-21 corrected PRO service contract and lineage handoff

- Chosen stage and tasks: `original plan / pre-post outcome quantification and PRO`; OP-057 and OP-058.
- Primary dataset/evidence: frozen eval `256` cases; one synthetic authenticated enrollment, one follow-up creation, and one correction over two strict PRO events. Canonical evidence SHA-256 `67ffac5637d9281cd5b99ae4e435049669842ad2e4abdc54f69b71cbdd90a711`; combined source SHA-256 `10662658664b0ba08112a61582e1a0d22e0d2e3eada875c44bffcf314a016092`.
- Source identity: R&D `86823c364094b275e0e9d41a2b78ed22833b383e`; WellnessBox `9dfc1d0b2034ed15777385802b7283a3ffc78c02`.
- Changed paths: R&D recommendation schema/service, execution ledger, PRO runtime/correction/follow-up services, interim endpoints, contracts, tests, smoke/workflow, manifest/evidence/report; service TIPS PRO UI, authenticated plan/effect routes, existing R&D client/profile adapter, and QA scripts. No new database or duplicate event store was added.
- Result: the service UI persists the R&D execution, plan, and baseline identities. Recommendation and optimization events plus the observed effect share one plan ID; the corrected raw score is `10 -> 8 -> 7`. Duplicate retries are idempotent, while changed baseline or ownership conflicts return HTTP 409 or fail closed.
- Honest stage: OP-057 is `INTEGRATED` and COMPLETE. OP-058 is `INTEGRATED` and PARTIAL below `OPERATED`. Browser rendering behind authenticated login, production operation, real-world outcomes, deployment, and causal effects are not proven.
- Validation: focused `127 passed`; workflow-equivalent `446 passed`; full suite `827 passed`, `77 failed` in the known `73 + 4` groups; frozen 256 evaluation has seven zero deltas and identical weakest slices; full Ruff and service build/lint/typecheck/encoding checks PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: R&D is published through `a431cc448e26155ded2bd694715fa3b541009c53`; service through `9dfc1d0b2034ed15777385802b7283a3ffc78c02`; R&D Original plan evidence run `29805184034` and service Encoding Guard run `29804815958` succeeded.
- Biggest remaining bottlenecks: required operation evidence for OP-021~030, OP-040, OP-053, and OP-058; qualifying external labels for OP-039; OP-059~120 implementation; missing trusted report archive for 73 tests; four CGM geometry failures.
- Protected user files remain untouched. Existing `etc/` files remain untracked and were not used as canonical evidence.
- Next three loops: OP-059/060; OP-061/062; OP-063/064.

## 2026-07-21 personal and group PRO uncertainty handoff

- Chosen stage and tasks: `original plan / pre-post outcome quantification and PRO`; OP-055 and OP-056
- Primary dataset and evidence: `data/frozen_eval/frozen_eval_v1.jsonl` has `256` cases. `data/original_plan/evidence/op055_op056_pro_personal_group_uncertainty_smoke_v1.json` has `100` synthetic personal interpretations plus a separate group estimate and SHA-256 `4a458659b2c44cf35cf4589ac9f09e70ae63de37d7c2891356ce6e9c67fd4eb9`.
- Source identity: commit `56d0542e9506992621c8e356752ee41aec7b09d3`; source bundle SHA-256 `974bc53e20a0ad73308150eacc6218fe11f8182d563d872e6f7112763b619c34`.
- Implementation: `metrics/pro_group_effects.py` retains validated personal effects and derives a separately named group estimate. `metrics/statistics.py` now supplies the same seeded percentile bootstrap used by the existing interim KPI path. Cohorts fail closed on duplicate identities and mixed timepoint, data-class, or scoring identities; derived output mutation is rejected.
- Result: sample size `100`; fully interpretable `100`; mean health-Z change `0.67`, 95% CI `[0.616666, 0.723333]`; mean health-percentile change `25.779542`, 95% CI `[23.82636, 27.745993]`; uncertainty reasons `observational_association_not_causal` and `non_real_world_outcome_data`.
- Files changed: the new group contract, group metrics/statistics modules, deterministic smoke, focused tests, metrics exports, interim KPI helper call, evidence workflow, manifest, generated completion files, and governance tests. Existing OP-051~054 evidence source identities were refreshed because shared metrics files changed. The WellnessBox service repository was unchanged.
- Evidence stage: OP-055 and OP-056 are `IMPLEMENTED` and COMPLETE at their required stage. Counts are complete `43`, partial `12`, pending `64`, external `1`, contradicted `0`. This loop proves only synthetic local implementation; it does not prove real-world outcomes, service integration, operation, deployment, or causal effect.
- Validation: focused `43 passed`; workflow-equivalent `425 passed`; full Ruff PASS; audit PASS with `55` claims and `171` evidence files; report check PASS; full suite `806 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups; frozen eval has seven zero deltas and unchanged weakest slices; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: source commits `5b9dedcc62ff3bcb4c36d882f7f28ebaf2784968` and `56d0542e9506992621c8e356752ee41aec7b09d3`, evidence commit `0a1f102877a09f90195c64fdeeb67a73843f4913`, and Original plan evidence run `29799527985` are published and successful.
- Biggest remaining bottlenecks: OP-021 through OP-030, OP-040, and OP-053 still lack required operation evidence; OP-039 lacks qualifying independent labels; OP-057 through OP-120 contain `64` pending requirements; the trusted archive for `73` report-dependent tests is absent; `4` CGM geometry assertions remain unresolved.
- Protected files remain untouched: `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` and `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`.
- Next three loops: OP-057/058 corrected PRO and plan-linked outcome lineage; OP-059/060 observed-worsening actions and real-outcome data classes; OP-061/062 optimization constraints and the existing service product contract.

## 2026-07-21 PRO follow-up persistence and interpretation handoff

- Chosen stage: `original plan / pre-post outcome quantification and PRO`
- Chosen tasks: OP-053 and OP-054
- Primary dataset and evidence: `data/frozen_eval/frozen_eval_v1.jsonl` has `256` cases; `data/original_plan/evidence/op053_op054_pro_followup_interpretation_smoke_v1.json` has `4` ordered synthetic PRO persistence events and SHA-256 `b57a6ef61310fc70727cb6bca9e3c4addc117d163bf627a72d0fb263d82392fc`.
- Source identity: commit `83997c11684fc482462668865afc843f7cf211ff`; source bundle SHA-256 `6d5829f753148e2c879c4dd546d2a0e5b58fd105f6129653f75147c4cea64e34`.
- Implementation: the existing execution ledger persists strict pre-intake, week-2, week-4, and discontinuation events in order. The interpretation API returns unchanged observed score deltas plus explicit adherence, missed-dose, and adverse-event limitations. It never claims causal effect.
- Fail-closed fixes: strict PRO payloads cannot be stored as conversation events; generic and strict payloads cannot be interconverted by correction; interpretation rejects duplicate assessment IDs, reversed observation time, cross-plan pairs, and cross-distribution pairs.
- Files changed: `src/wellnessbox_rnd/interim/data_lake.py`, `src/wellnessbox_rnd/metrics/pro_followup.py`, `scripts/run_pro_followup_adherence_interpretation_smoke.py`, `tests/test_pro_followup_effects.py`, manifest/evidence/generated completion files, and governance expectation tests. The WellnessBox service was unchanged.
- Evidence stage: OP-053 `IMPLEMENTED` below required `OPERATED`, so it is PARTIAL. OP-054 `IMPLEMENTED`, so it is COMPLETE. Counts are complete `41`, partial `12`, pending `66`, external `1`, contradicted `0`.
- Validation: focused `90 passed`; workflow-equivalent `407 passed`; full Ruff PASS; audit PASS with `53` claims and `165` evidence files; report check PASS; full suite `788 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups; frozen eval has seven zero deltas and unchanged weakest slices; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: commits `83997c11684fc482462668865afc843f7cf211ff`, `706fb4ad22710ab0c5f6d5364ecd5aa3e694fe39`, and `0e7ea31bdf240cab0f4b7a34d35e7722e0a09e2e` are on `origin/main`; Original plan evidence run `29797963682` passed.
- Biggest remaining bottlenecks: OP-053 lacks production operation; OP-021 through OP-030 and OP-040 remain below `OPERATED`; OP-039 lacks qualifying external labels; the trusted archive for `73` report-dependent tests is absent; `4` CGM geometry assertions remain unresolved.
- Protected files remain untouched: `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` and `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`.
- Next three loops: OP-055/056 separate personal and group effects with uncertainty; OP-057/058 recalculate corrected PRO and link outcome lineage; OP-059/060 connect observed worsening to actions and real outcome data classes.

## 2026-07-17 versioned PRO scoring and baseline-percentile handoff

- Chosen stage: `original plan / pre-post outcome quantification and PRO`
- Chosen tasks: OP-051 and OP-052
- Primary evidence: `data/original_plan/evidence/op051_op052_versioned_pro_scoring_smoke_v1.json`; current deterministic SHA-256 `b14d8a69e7e62ca40837dab30552482c638de31452030168afecaf24eb7c5ddf`; source commit `334bd706f72593b7c948785ad2b8630fb65b8911`; source bundle SHA-256 `b9d49513fffb58d6f0a1bcda58741e637fca79c14ab09697492be771b9ba9169`
- Raw scores: the existing R&D PRO module now applies one strict contract to PSQI seven-component sums (`0..21`), ISI seven-item sums (`0..28`), and PSS-10 ten-item sums with items `4, 5, 7, 8` reversed (`0..40`). PSQI 19-item derivation and questionnaire text are intentionally outside this contract.
- Standardization: versioned `BASELINE` observations of one instrument/version produce an order-independent mean and sample standard deviation. Lower problem scores map to higher health Z scores and percentiles. The smoke fixes Z scores `1, 0, -1` to percentiles `84.134475, 50, 15.865525` for all three instruments.
- Fail-closed boundary: public functions revalidate supplied model instances; output models enforce canonical score metadata and ranges; distributions verify source scores, statistics, role, version, and SHA-256; standardized outputs embed the validated distribution. Rounding method and operation order are part of the committed contract.
- Evidence boundary: `SYNTHETIC_OUTCOME_PROXY` only. No service code, authorized questionnaire text, production data, clinical interpretation, deployment, or production operation is claimed.
- Evidence stage: OP-051 and OP-052 are `IMPLEMENTED`. Generated counts: complete `40`, partial `11`, pending `68`, external `1`, contradicted `0`.
- Validation: related scoring tests `38 passed`; CI-equivalent `388 passed`; full Ruff PASS; audit PASS with `51` claims and `160` evidence files; full suite `769 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups; frozen eval has seven zero deltas and no weakest-slice changes; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: commits `fd7e4a3d1d6edb630d6c25cdb0fde11129d98975` and `3bfdfed8d1aabfbfbbcca908bfb17f154aba4e46` are on `origin/main`; Original plan evidence run `29515937856` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-053/054 add follow-up PRO events and adherence/adverse-event interpretation; OP-055/056 separate personal/group effects and return uncertainty; OP-057/058 add user correction and plan-linked outcome lineage.

## 2026-07-17 learned replay and product-candidate handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-049 and OP-050
- Primary evidence: `data/original_plan/evidence/op049_op050_replay_product_candidates_smoke_v1.json`; deterministic SHA-256 `ff3b58d106ac4d8678df1ed6925b01232387880c8d5e6b4064a93d5ef4cdc2e1`; R&D source `584c6c7ca3d053c9ae3430b214eae23f35009b15`; WellnessBox source `a6b8ab1e92a112f6d2e904436bfe44ba688fc4e8`
- Replay result: all `256` frozen requests use paired baseline/learned execution. Learned applies to `12`; `244` are `not_eligible`; true fallback count is `0`; selection changes `4`; rank/score changes `5`; response status, next action, and full safety payload changes are all `0`.
- Service result: the existing ingredient map and `product.catalog` in-stock Prisma path resolve all `8` mapped service ingredients against the captured live-catalog snapshot. The route returns explicit candidates or `NO_MATCH` and fails closed for invalid catalogs and unmapped identifiers. Product and ingredient contract versions must match exactly.
- Boundary: actual R&D HTTP observation is the safety-blocked path only. READY product conversion uses the test-only route seam and captured catalog snapshot. No READY two-process proof, production operation, or deployment is claimed.
- Evidence stage: OP-049 `IMPLEMENTED`; OP-050 `INTEGRATED`. Generated counts: complete `38`, partial `11`, pending `70`, external `1`, contradicted `0`.
- Validation: focused `5 passed`; service QA covers `8/8` mappings; CI-equivalent `350 passed`; full Ruff PASS; audit PASS with `49` claims and `155` evidence files; full suite `751 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups; frozen eval has seven zero deltas and no weakest-slice changes; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: WellnessBox Encoding Guard runs `29511317388` and `29511798649` passed. R&D commits through `3ed17debdbfc0646c819066d4f7a8cbfec36a159` are on `origin/main`; Original plan evidence run `29513104957` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-051/052 version PSQI, ISI, and PSS-10 scoring plus percentile conversion; OP-053/054 add follow-up events and adherence/adverse-event interpretation; OP-055/056 separate personal/group effects and return uncertainty.

## 2026-07-16 decision uncertainty and learned-fallback handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-047 and OP-048
- Primary evidence: `data/original_plan/evidence/op047_op048_decision_uncertainty_learned_fallback_smoke_v1.json`; deterministic SHA-256 `55eae7c9a7a99557fa47ecc687e622bc0a959550b7d629db4e7008e0f5d7d158`; source commit `22aca5e9d64a493562f9d17b302bead2ca02c555`
- Main result: the existing recommendation response now returns versioned numeric uncertainty for missing inputs, review state, candidate availability, and the preselection top-two margin. The score is explicitly not a clinical probability. Every post-safety candidate has a complete ranked score trace with full breakdown, reason, rules, goals, catalog priority, and evidence linkage.
- Fallback result: learned reranking exposes one explicit decision status. Missing, malformed, unsupported, suspicious, or runtime-failing artifacts discard all partial learned results and return the exact deterministic recommendations and `deterministic_baseline_v1` mode. Valid artifacts require explicit model/target identity, supported runtime features, catalog-valid candidate keys, closed-domain values, compatible dimensions, and bounded finite coefficients.
- Fail-closed boundary: response and current-version contract validators reconcile the ranking snapshot and all selected/unselected scores against the post-safety pool, catalog, goal-prior, signal, and safety registries. They reject score/status/selection mutations, partial diagnostics removal, and schema downgrade. Legacy V1 contract validation is available only through explicit compatibility mode.
- Evidence stage: OP-047 and OP-048 are `IMPLEMENTED`. Generated counts are complete `36`, partial `11`, pending `72`, external `1`, contradicted `0`. No WellnessBox service change, deployment, or production operation was performed.
- Validation: focused selection `60 passed`; exact CI-equivalent selection `345 passed`; full Ruff PASS; manifest audit PASS with `47` claims and `145` checked evidence files; completion report check PASS; independent final review Critical `0`, Important `0`, Minor `0`; full suite `746 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: source commit `22aca5e9d64a493562f9d17b302bead2ca02c555` and evidence commit `ae38c36963f00d9c7f0f84cf4cd5597a1e271645` are on `origin/main`; Original plan evidence run `29509159767` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-049/050 compare learned/baseline replay and convert ingredients to service products; OP-051/052 implement versioned PRO scoring and percentile conversion; OP-053/054 implement follow-up state and change calculation.

## 2026-07-16 candidate-pool and structured-reason handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-045 and OP-046
- Primary evidence: `data/original_plan/evidence/op045_op046_candidate_pool_structured_reasons_smoke_v1.json`; current deterministic SHA-256 `86cc00d7662d96a2a350dfabc7b41395987b65db1f418d3bcd7de5741e6d335e`; source identity refreshed to commit `22aca5e9d64a493562f9d17b302bead2ca02c555`
- Main result: the existing optimizer and response now preserve one shared pre-safety/excluded/post-safety candidate partition and selected subset. Global blocking retains the pool for audit but returns no selection. User avoidance, current-regimen overlap, and safety exclusions remain distinguishable.
- Structured reason result: every selected candidate returns goal and applied input signals, all 14 score terms, exact rule/reference/claim IDs, limitations, evidence links, and a total that reconciles to the candidate score. Safety-review scoring preserves the triggering safety rule and scoring-time status. Learned reranking rebuilds the same reason after its bonus is applied.
- Fail-closed boundary: schemas and the recommendation contract reject partition identity drift, duplicate evidence links, incomplete terms, score/component mismatches, forged or empty evidence IDs, wrong ownership, wrong learned markers, and unexpected fields. Candidate selection and trace generation share one partition function instead of duplicating filter logic.
- Evidence stage: OP-045 and OP-046 are `IMPLEMENTED`. Generated counts are complete `34`, partial `11`, pending `74`, external `1`, contradicted `0`. No WellnessBox service change, deployment, or production operation was performed.
- Validation: focused selection `203 passed`; exact local CI-equivalent selection `315 passed`; full Ruff PASS; manifest audit PASS with `45` claims and `140` checked evidence files; completion report check PASS; independent final review Critical `0`, Important `0`, Minor `0`; full suite `716 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: commits `f7479d710e227fe428d96977a91ce2ab66438d06`, `c8c636c61497929a3afb3933236520226c555072`, `92cf53a8f0c2050e7b4ae2368d36b95d2396c9df`, and `0cd4db94c87ac223f7062ae75e6a2ac02267c722` are on `origin/main`; Original plan evidence run `29504825809` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-047/048 quantify uncertainty and enforce learned-artifact fallback; OP-049/050 compare learned/baseline replay and convert to service products; OP-051/052 implement versioned PRO scoring and percentile conversion.

## 2026-07-16 candidate signal scoring handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-043 and OP-044
- Primary evidence: `data/original_plan/evidence/op043_op044_candidate_signal_scoring_smoke_v1.json`; current deterministic SHA-256 `b949483625e5fba4bdbea96afe9cb8ade1f7e45cbc1d5db2955b1e10f6f30052`; source identity refreshed to commit `22aca5e9d64a493562f9d17b302bead2ca02c555`
- Main result: existing candidate scores now expose separate symptom, laboratory, lifestyle, dietary, wearable, CGM, and genetic terms with observed values, bounded points, versioned rule IDs, exact reference/claim IDs, and limitations. The recommendation contract includes every new term in its total.
- Safety boundary: source-specific recommendation consent is explicit for snapshots. CGM TIR scoring requires a verified 70–180 mg/dL range, nonpregnant diabetes context, and a blood-glucose goal. Unknown genetic tags, custom TIR ranges, invalid aliases/bounds, and unscoped tags add zero. The scorer executes only the registry embedded in the validated runtime artifact.
- Evidence stage: OP-043 and OP-044 are `IMPLEMENTED`. Generated counts are complete `32`, partial `11`, pending `76`, external `1`, contradicted `0`. No WellnessBox service change, deployment, or production operation was performed.
- Validation: focused selection `70 passed`; exact CI-equivalent selection `301 passed`; manifest audit PASS with `43` claims and `134` checked evidence files; stored runtime equals fresh; full Ruff PASS; independent final review Critical `0`, Important `0`, Minor `0`; full suite `705 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: source commit `1465db1c153b71b8b636231eb6487c32e469c85b` and evidence commit `64d67eceef2996869c897e9a0bc02b33a549010f` are on `origin/main`; Original plan evidence run `29501666136` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-045/046 preserve pre/post safety candidate sets and return structured reasons; OP-047/048 quantify uncertainty and preserve deterministic fallback; OP-049/050 compare learned/baseline replay and convert candidates to service products.

## 2026-07-16 ingredient identity and goal-prior handoff

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-041 and OP-042
- Primary evidence: `data/original_plan/evidence/op041_op042_ingredient_mapping_goal_prior_smoke_v1.json`; deterministic SHA-256 `fd37111339773f86904cc3d4f6f2b5fda45ff2d51e4f1b8a6a5ff35d5013e8a6`
- Main files: byte-identical service/R&D identifier contracts; service mapping and final-authority modules; R&D goal-prior registry, validator, scorer integration, reference/runtime artifacts, official-source notes, focused tests, two-process smoke, manifest, generated status, and both CI workflows
- Current result: every service and R&D catalog identifier is mapped or explicitly unmapped. Relationship and direction are validated. The actual `/api/tips` export enriches a mapped R&D recommendation with the service ID and returns a service-owned fail-closed block for an unmapped ID.
- Goal-prior result: `24` catalog-supported pairs cover all `9` goals. Registered points preserve the prior `35/18` candidate ordering and are explicitly not efficacy probabilities. Clinical evidence labels are derived from exact scoped claim types; policy-only records cannot be promoted, and unrelated references or forged policy claims are rejected.
- Evidence stage: OP-041 is `INTEGRATED`; OP-042 is `IMPLEMENTED`. Generated counts are complete `30`, partial `11`, pending `78`, external `1`, contradicted `0`. No deployment or production operation was performed.
- Validation: focused selection `48 passed`; exact CI-equivalent selection `283 passed`; manifest audit PASS with `41` claims and `124` checked evidence files; stored runtime equals fresh and fresh builds are deterministic; full Ruff PASS; independent final review Critical `0`, Important `0`; full suite `683 passed`, `77 failed` with only the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Publication: WellnessBox commit `58246f9a086c81bb3a38d4a1f33f5205b388d2b8` is on `origin/main`, and Encoding Guard run `29496255239` passed. R&D source commit `6a1f874b95fadbffbab796eefcbecd71284b6d9e` and evidence commit `da2936206d0ebe8b2ef12d9e0b79f048f2239b10` are on `origin/main`; Original plan evidence run `29496879246` passed.
- Protected files: do not modify or stage `docs/plans/2026-07-14-tips-evaluator-ui-overhaul.md` or `docs/plans/2026-07-15-tips-full-implementation-roadmap.md`. The unrelated dirty WellnessBox UI files remain user-owned and unstaged.
- Next three loops: OP-043/044 candidate filtering and auditable scoring; OP-045/046 post-filter preservation and structured reasons; OP-047/048 uncertainty and deterministic fallback.

## 2026-07-16 external high-risk gate and final safety-authority handoff

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-039 and OP-040
- Primary evidence: `data/original_plan/evidence/op040_final_safety_authority_integration_smoke_v1.json`; actual `POST /api/tips` export and localhost R&D `POST /v1/interim/recommendations`, deterministic SHA-256 `c01eca4f667cfcea00c95f7830ebd8f9711482d81e40e6f4b23629719b9c5183`
- Main files: R&D interim route and safety evaluator; external high-risk evaluator, contracts, empty trust roots, tests, and CLI; service `/api/tips` route, R&D client, final-authority validator, test-only dependency hook, QA scripts, and both repositories' CI workflows
- Current result: stored and current risk facts are conservatively combined before model execution, including multi-key dynamic predicates split across sources. Hard failures do not call the model and return zero recommendations. The service preserves a valid R&D final block and fails closed on transport or contract failure.
- OP-039 boundary: no externally labeled high-risk dataset, detached attestation, independent verification receipt, or repository-approved trust-root entry exists. OP-039 therefore remains unclaimed at `EXTERNAL`; internal synthetic tests are contract verification only.
- Evidence stage: OP-040 is `INTEGRATED`, not `OPERATED`. Generated counts are complete `28`, partial `11`, pending `80`, external `1`, contradicted `0`. The smoke explicitly records `production_operation_proven=false`.
- Validation: focused selection `19 passed`; exact CI-equivalent selection `268 passed`; full Ruff PASS; manifest audit PASS with `39` claims and `113` checked evidence files; completion report check PASS; runtime stored/fresh equality PASS with zero issues; final independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `673 passed`, `77 failed`, matching the known `73` absent-report and `4` CGM-geometry groups. Official frozen eval: `256` cases, seven zero metric deltas, unchanged overall and metric-specific weakest-slice categories.
- Publication: WellnessBox service commit `9609ce804ad06c609b794f455d4f6127b59361ac` is on `origin/main` and Encoding Guard run `29492239202` passed. The R&D implementation source commit is `e830c7debd4b103b756bba494fdbc73d7f0bad3a`; evidence publication and Original plan evidence CI remain the final loop steps.
- Biggest bottlenecks: qualifying independent OP-039 labels and approvals; deployed R&D process; production `WB_RND_*` configuration; durable production storage; observed production final-block behavior.
- Next three loops: OP-041/042 identifier mapping and evidence-backed goal priors; OP-043/044 candidate filtering and auditable scoring; OP-045/046 post-filter preservation and structured recommendation reasons.

## 2026-07-16 dose-limit and rule-metadata handoff

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-037 and OP-038
- Primary dataset path and case count: `data/original_plan/evidence/op037_op038_dose_limit_rule_metadata_smoke_v1.json`; `7` deterministic dose-evaluation cases
- Main files: safety rule DSL and models; runtime knowledge records and stored artifact; recommendation schema and safety service; Data Lake replay projection; focused parser, API, replay, and runtime-boundary tests; smoke runner; manifest, generated reports, CI workflow, and implementation plan
- Current result: complete compatible doses use the existing aggregate and normalized unit for upper-limit comparison. Supplied but partial, non-convertible, compound, ranged, or schedule-qualified legacy evidence excludes the affected ingredient with `dose_evidence_incomplete` and no fabricated total. Optional absent doses do not claim evaluation. Complete above-limit totals retain blocker behavior.
- Parser boundary: comma-grouped amounts parse correctly; multiple amount-unit pairs, single-unit ranges, `twice daily`/`bid`/`N x` schedules, and compound product doses fail closed. Compound segments including modifiers and `plus` are recognized separately. Fuzzy title matching is accepted only when exactly one ingredient remains.
- Metadata result: every runtime safety record has a positive version derived from its rule metadata or knowledge-artifact suffix. Every returned rule includes the same version. `SafetySummary.applied_at` is timezone-aware; smoke injects `2026-07-16T00:00:00Z`. Replay omits that volatile timestamp only from deterministic output comparison.
- Evidence stage: `IMPLEMENTED`. OP-037 and OP-038 are complete at their required stage. Generated counts are complete `28`, partial `10`, pending `81`, external `1`, contradicted `0`. No service code, deployment, or production two-process integration changed.
- Validation: focused selection `240 passed`; exact CI-equivalent selection `252 passed`; full Ruff PASS; deterministic smoke hash `2a34f58b4564b903560341bf0862d1ce12016a0a84f6b4efd298616255347dbb`; manifest audit PASS with `38` claims and `105` checked evidence files; completion report check PASS; runtime stored/fresh equality PASS with zero issues; final independent review Critical `0`, Important `0`, Minor `0`.
- Full suite: `657 passed`, `77 failed`, matching the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval: `256` cases; all seven metric deltas are `0`; overall and metric-specific weakest-slice categories are unchanged.
- Biggest bottlenecks: externally labeled high-risk cases for hard false-negative proof; production final-block authority across the real service/R&D boundary; deployed R&D process; durable production R&D storage; authenticated two-process round trip.
- Next three loops: OP-039/040 high-risk and production blocking evidence; OP-041/042 identifier mapping and evidence-backed goal priors; OP-043/044 candidate filtering and auditable scoring.

## 2026-07-16 interaction evidence and dose aggregation handoff

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-035 and OP-036
- Primary dataset path and case count: `data/original_plan/evidence/op035_op036_interaction_dose_aggregation_smoke_v1.json`; `10` deterministic recommendation/replay cases
- Main files: NIH ODS raw reference and regenerated knowledge artifacts; safety rule DSL and models; runtime knowledge validation; recommendation and interim safety paths; structured safety response; focused tests; smoke runner; manifest, generated reports, CI workflow, and implementation plan
- Current result: every runtime drug-ingredient interaction rule has non-empty, cross-validated reference and claim IDs, and duplicate claim IDs are rejected. The warfarin/omega-3 policy returns the exact NIH ODS citation, while the evidence artifact distinguishes the possible INR effect, mostly negative 3–6 g/day findings, FDA-approved pharmaceutical package-insert monitoring language, and the repository's conservative candidate-exclusion policy. The interim replay finding preserves the same IDs for both warfarin and Coumadin.
- Dose result: the existing extraction path now produces one structured aggregate per recognized current ingredient. The result records product occurrences and names, a cross-product duplicate flag, normalized total and unit when available, observation count, and whether every contributing product supplied a usable dose. The same aggregate amount feeds upper-limit comparison, preventing a separate summation path.
- Evidence stage: `IMPLEMENTED`. OP-035 and OP-036 are complete at their required stage. Generated counts are complete `26`, partial `10`, pending `83`, external `1`, contradicted `0`. No service code, R&D deployment, or production two-process integration changed.
- Validation: focused selection `53 passed`; exact CI-equivalent selection `228 passed`; full Ruff PASS; deterministic smoke hash `9c001cb799b34e65899103f47f959b0d2c9a2125ed8be1bea847fb1daf9f554a`; manifest audit PASS with `36` claims and `102` evidence files; completion report check PASS; independent final review found zero Critical, Important, or Minor issues. Full suite is `635 passed`, `77 failed`, matching the known `73` absent-report and `4` CGM-geometry groups.
- Official frozen eval metric deltas: `256` cases; recommendation coverage `0`, efficacy improvement `0`, next-action accuracy `0`, explanation-quality accuracy `0`, safety-reference accuracy `0`, yearly adverse-event count `0`, sensor/genetic integration rate `0`.
- Replay/slice deltas: every weakest-slice category is unchanged; the interim DDI replay keeps the new reference and claim IDs.
- Biggest bottlenecks: incomplete/non-convertible dose evidence is not yet fail-closed; safety responses lack rule version/application time; external high-risk labels for hard false-negative proof are absent; the production service has no final two-process safety-block proof; no deployed durable R&D service exists.
- Next three loops: OP-037/038 unit and temporal rule metadata; OP-039/040 high-risk and production blocking evidence; OP-041/042 identifier mapping and evidence-backed goal priors.

## 2026-07-16 event idempotency and data-mutation handoff

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-027 and OP-028
- Primary dataset path and case count: `data/original_plan/evidence/op027_op028_event_idempotency_data_mutation_smoke_v1.json`; `3` actual FastAPI route cases
- Main files: schema `8` in `src/wellnessbox_rnd/interim/store.py`; new `src/wellnessbox_rnd/interim/data_mutation.py`; existing execution and behavior record models; authenticated interim routes; focused tests; smoke runner; manifest, generated reports, CI workflow, and execution plan
- Current result: execution and behavior events both return the existing record on an identical replay and reject a changed replay with `409`, even after the effective payload changes. Mutation routes require a configured internal token, verify profile ownership, preserve the immutable ingestion hash, update the effective payload in one immediate transaction, and append an indexed canonical hash-chain record plus audit row.
- Deletion boundary: the event payload becomes `{"deleted":true,"mutation_id":"..."}`. A separate cleanup row remains `PENDING` until SQLite `secure_delete`, WAL truncation, and compaction finish; identical-request retry and store-startup recovery resume interrupted cleanup. Raw-file regressions cover normal deletion, injected cleanup failure, restart recovery, and an active reader. Mutation and audit tables contain identifiers and hashes only. The event ID, execution ID, ingestion fingerprint, and knowledge-lineage foreign keys remain intact.
- Correction boundary: a new correction may follow an earlier correction and extends previous-mutation ID/hash pointers. No new correction may follow deletion. Append-only triggers reject mutation or data-mutation audit updates and deletes. Replaying an accepted mutation returns its original record without adding a row; 16 concurrent identical requests produce one mutation and one audit row.
- Evidence stage: `IMPLEMENTED`. OP-027/028 remain partial because `OPERATED` requires a deployed R&D process, durable production database, and postcondition re-query. No service code, R&D deployment, or production two-process integration changed in this loop.
- Validation: exact CI-equivalent selection `192 passed`; focused persistence regression `46 passed`; new smoke byte-identical across reruns; full Ruff PASS; manifest audit PASS with `30` claims and `81` evidence files; completion-report stale check PASS; independent final review found no findings. Full suite is `602 passed`, `78 failed`, matching the known `74` absent ignored-report and `4` CGM geometry groups.
- Frozen evaluation: `256` cases; zero delta for all seven tracked metrics against `docs/02_eval/05_baseline_gap_report.md`. Replay/slice delta: not applicable.
- Biggest bottlenecks: deployed R&D URL; durable production R&D storage; authenticated service-to-R&D round trip; production mutation postcondition re-query; deterministic whole-session replay and service UI.
- Next three loops: OP-029/030 replay API and service UI; OP-033/034 pregnancy/lactation and condition safety expansion; OP-035/036 evidence-linked interactions and combined-dose calculation.
- Publication: implementation commit `e2cfc54` was pushed to `main`; `Original plan evidence` run `29464603258` passed all steps.
