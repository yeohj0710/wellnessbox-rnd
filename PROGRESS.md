# PROGRESS

## 2026-07-16 ingredient identity and evidence-linked goal-prior loop

- Chosen stage: `original plan / candidate generation and efficacy scoring`
- Chosen tasks: OP-041 version the WellnessBox service/R&D ingredient identifier mapping; OP-042 register evidence-linked candidate priors for every catalog-supported ingredient/goal pair
- Primary evidence: `data/original_plan/evidence/op041_op042_ingredient_mapping_goal_prior_smoke_v1.json`; actual service `/api/tips` export plus localhost R&D HTTP process, byte-identical across reruns (`fd37111339773f86904cc3d4f6f2b5fda45ff2d51e4f1b8a6a5ff35d5013e8a6`)
- Reused both existing ingredient catalogs, the existing `/api/tips` safety-authority path, the R&D candidate scorer, reference ingestion, and runtime knowledge DB. No parallel catalog, recommendation engine, or service route was added.
- The byte-identical mapping contract covers every service identifier and every R&D catalog key as mapped or explicitly unmapped. Equivalent pairs allow both directions; a broader service identifier allows only R&D-to-service conversion. The actual `/api/tips` route returns `ING:MAGNESIUM` for `magnesium_glycinate` and fails closed with HTTP `502` and zero recommendations for an unmapped R&D identifier.
- The versioned goal-prior registry covers all `24` current catalog-supported ingredient/goal pairs and all `9` recommendation goals. It preserves the established candidate-ordering points (`35` for a specific goal and `18` for general wellness); these points are selection policy, not clinical efficacy probabilities. Every record carries the fixed policy claim, and any clinical strength/direction must match a scoped claim type and the exact claim-owned reference set.
- Source scope is conservative: insufficient, mixed, inconclusive, deficiency-dependent, strain-specific, population-dependent, or small-trial evidence remains labeled with its limitation. Forged policy claims, unrelated references, evidence-strength promotion, duplicate IDs, stale runtime artifacts, and nondeterministic fresh builds fail validation.
- Evidence status: OP-041 is complete at required stage `INTEGRATED`; OP-042 is complete at required stage `IMPLEMENTED`. Generated status: complete `30`, partial `11`, pending `78`, external `1`, contradicted `0`. No R&D deployment or production two-process operation is claimed.
- Validation: focused mapping/prior/runtime selection `48 passed`; exact CI-equivalent selection `283 passed`; full Ruff PASS; manifest audit PASS with `41` claims, `124` checked evidence files, and zero issues; completion-report stale check PASS; stored/fresh runtime equality and fresh-build determinism PASS; independent final review Critical `0`, Important `0`.
- Full suite: `683 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and the overall and metric-specific weakest-slice categories are unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication boundary: WellnessBox commit `58246f9a086c81bb3a38d4a1f33f5205b388d2b8` passed Encoding Guard run `29496255239`. R&D source commit `6a1f874b95fadbffbab796eefcbecd71284b6d9e` is pinned in deterministic evidence; evidence publication and Original plan evidence CI are the remaining loop steps.
- Recommended next loops: OP-043/044 candidate filtering and auditable score decomposition; OP-045/046 safe-candidate preservation and structured recommendation reasons; OP-047/048 uncertainty/missing-input quantification and deterministic fallback.

## 2026-07-16 external high-risk gate and final safety-authority loop

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-039 define a fail-closed intake and evaluation contract for an independently labeled high-risk frozen evaluation; OP-040 prove final safety blocking authority across the existing WellnessBox `/api/tips` and R&D interim recommendation paths
- Primary evidence: `data/original_plan/evidence/op040_final_safety_authority_integration_smoke_v1.json`; actual service-route export plus localhost R&D HTTP process, byte-identical across reruns (`c01eca4f667cfcea00c95f7830ebd8f9711482d81e40e6f4b23629719b9c5183`)
- Reused the existing `POST /api/tips` route, interim profile/recommendation client, `POST /v1/interim/recommendations`, deterministic safety evaluator, evidence registry, and original-plan CI workflow. No parallel service route, safety engine, or recommendation system was added.
- The R&D interim route evaluates stored, current, and conservatively merged risk facts before model execution. A hard failure returns `BLOCKED`, no model ID, and zero recommendations. Dynamic multi-key predicates may draw each known risk fact from the stored or current source, so a later request cannot erase or split a blocking condition.
- The service validates the full R&D safety response. A valid R&D block remains authoritative as `rnd_final`; transport, HTTP, decode, or contract failure returns a service-owned `service_fail_closed` block with zero recommendations. The smoke observes `SAFE-EMERGENCY-001`, `STOP_AND_ESCALATE`, `BLOCKED`, and an invalid-contract HTTP `502` through the actual `/api/tips` export.
- OP-039 remains unclaimed at required stage `EXTERNAL`. The evaluator now requires a pre-approved coverage protocol, independently labeled cases, detached attestation, independent verification receipt, repository-pinned trust roots, chronological approvals, complete hazard-stratum coverage, a clean Git tree, and zero hard false negatives. Both trust-root allowlists are intentionally empty because no qualifying external dataset or approval exists.
- Evidence status: OP-040 is `INTEGRATED` and remains partial at required stage `OPERATED`. Generated status: complete `28`, partial `11`, pending `80`, external `1`, contradicted `0`. No R&D deployment, production environment configuration, durable production storage, or production operation is claimed.
- Validation: focused evaluator/interim selection `19 passed`; exact CI-equivalent selection `268 passed`; full Ruff PASS; manifest audit PASS with `39` claims, `113` checked evidence files, and zero issues; completion-report stale check PASS; runtime stored/fresh equality PASS with zero validation issues; independent final review Critical `0`, Important `0`, Minor `0`.
- Full suite: `673 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-039/040 or recommendation-boundary failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, the overall weakest category is unchanged, and every metric-specific weakest category is unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Publication boundary: WellnessBox service commit `9609ce804ad06c609b794f455d4f6127b59361ac` passed Encoding Guard run `29492239202`. R&D source commit `e830c7debd4b103b756bba494fdbc73d7f0bad3a` is pinned by the smoke evidence. The R&D evidence commit and CI result are recorded after publication.
- Recommended next loops: OP-041/042 service/R&D ingredient identity and evidence-backed goal priors; OP-043/044 candidate contraindication filtering and auditable candidate scoring; OP-045/046 post-filter candidate preservation and structured recommendation reasons.

## 2026-07-16 dose-limit fail-closed and rule-metadata loop

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-037 compare unit-normalized upper limits and conservatively exclude ingredients when supplied dose evidence is ambiguous; OP-038 return the applied rule version and one timezone-aware application time
- Primary evidence: `data/original_plan/evidence/op037_op038_dose_limit_rule_metadata_smoke_v1.json`; seven deterministic dose cases, byte-identical across reruns (`2a34f58b4564b903560341bf0862d1ce12016a0a84f6b4efd298616255347dbb`)
- Reused the existing supplement parser, `IngredientDoseAggregate`, runtime knowledge database, deterministic safety service, recommendation response, Data Lake replay projection, and CI evidence workflow. No parallel dose calculator, safety engine, or recommendation path was added.
- Complete compatible doses are converted into the rule unit before comparison. The returned aggregate remains the only compared total. An optional dose that was not supplied has `dose_input_count=0` and does not claim an upper-limit evaluation. A supplied but partial, non-convertible, compound, ranged, or schedule-qualified legacy dose returns `dose_evidence_incomplete`, excludes each affected ingredient, and never invents a total or stops unrelated safe alternatives. Complete above-limit totals remain global blockers.
- Legacy parsing now accepts comma-grouped numbers, rejects multi-dose ranges and schedules, resolves each compound segment independently, and permits a fuzzy catalog title only when the text resolves to exactly one ingredient. Regression coverage includes `plus`/modifier compounds, `twice daily`, `bid`, `N x`, single-unit ranges, and branded single-ingredient titles.
- Every structured safety rule and runtime interaction, contraindication, and dose-limit record has a positive version. Every returned `RuleReference` exposes the applied version and bounded application reason. `SafetySummary.applied_at` is timezone-aware and can be injected for replay/smoke determinism. Session replay excludes only this volatile timestamp from its behavior fingerprint while retaining it in stored and API responses.
- Evidence status: OP-037 and OP-038 are complete at their required `IMPLEMENTED` stage. Generated status: complete `28`, partial `10`, pending `81`, external `1`, contradicted `0`.
- Validation: focused parser/safety/recommendation selection `240 passed`; exact CI-equivalent selection `252 passed`; full Ruff PASS; manifest audit PASS with `38` claims, `105` checked evidence files, and zero issues; completion-report stale check PASS; runtime stored artifact equals a fresh build with zero validation issues; independent final review found zero Critical, Important, or Minor issues.
- Full suite: `657 passed`, `77 failed`; the unchanged failures remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No OP-037/038 or recommendation-baseline failure remains.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, the overall weakest category is unchanged, and every metric-specific weakest category is unchanged against `artifacts/reports/op035_op036_frozen_eval/eval_report.json`.
- Remaining boundary: this R&D-only loop did not change WellnessBox service code, deploy the R&D app, or prove production two-process integration. OP-039 still needs external high-risk labels for hard false-negative proof. OP-040 still needs real production evidence that final safety blocking authority cannot be bypassed.
- Recommended next loops: OP-039/040 high-risk false-negative and production final-block authority; OP-041/042 service/R&D ingredient identity and evidence-backed goal priors; OP-043/044 candidate contraindication filtering and auditable candidate scoring.

## 2026-07-16 evidence-linked interaction and dose-aggregation loop

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-035 connect drug-ingredient interaction rules to evidence IDs; OP-036 calculate duplicate ingredients and cross-product daily-dose totals
- Primary evidence: `data/original_plan/evidence/op035_op036_interaction_dose_aggregation_smoke_v1.json`; ten deterministic recommendation/replay cases, byte-identical across reruns (`9c001cb799b34e65899103f47f959b0d2c9a2125ed8be1bea847fb1daf9f554a`)
- Reused the raw-reference ingestion, runtime knowledge database, normalized `RecommendationRequest`, current supplement dose extraction, deterministic safety service, and interim replay safety path. No parallel interaction engine or dose calculator was added.
- `SAFETY-ANTICOAG-001` now carries `REF-NIH-ODS-OMEGA3-001` and `CLM-NIH-ODS-OMEGA3-WARFARIN-001`; the runtime validator rejects evidence-linked interaction records without valid reference or claim IDs. Recommendation safety returns the exact citation, and interim replay preserves the same stable IDs for both warfarin and its Coumadin alias. The NIH ODS source reports a possible INR effect, notes that most 3–6 g/day studies did not significantly change anticoagulant status, and attributes periodic INR monitoring to FDA-approved omega-3 pharmaceutical package inserts. The omega-3 candidate exclusion remains an explicitly conservative deterministic policy rather than a claim attributed to NIH.
- `SafetySummary` now returns per-ingredient product count and names, cross-product duplicate state, normalized total daily amount and unit, dose-observation count, and completeness. Two vitamin-D products return `4400 IU`; two undosed probiotic products return a duplicate with no invented total; one dosed plus one undosed vitamin-D product returns a partial `2000 IU` total with `dose_complete=false`; repeated lines inside one product do not count as a cross-product duplicate.
- Evidence status: OP-035 and OP-036 are complete at their required `IMPLEMENTED` stage. Generated status: complete `26`, partial `10`, pending `83`, external `1`, contradicted `0`.
- Validation: focused interaction/dose/reference selection `53 passed`; exact CI-equivalent selection `228 passed`; full Ruff PASS; manifest audit PASS with `36` claims, `102` checked evidence files, and zero issues; completion-report stale check PASS; deterministic smoke hash stable across reruns; independent final review found zero Critical, Important, or Minor issues.
- Full suite: `635 passed`, `77 failed`; the unchanged failure groups remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No new interaction, aggregation, lineage, or safety failure remains.
- Frozen evaluation: `256` cases; all seven tracked metric deltas and all weakest-slice category deltas are exactly `0` against `artifacts/reports/op029_op030_frozen_eval/eval_report.json`.
- Remaining boundary: incomplete or non-convertible dose evidence is now visible but is not yet conservatively blocked; OP-037 owns that decision. Rule version and application time remain absent until OP-038. No WellnessBox code, R&D deployment, or two-process production integration changed in this loop.
- Recommended next loops: OP-037/038 unit-normalized upper-limit fail-closed handling and rule version/application time; OP-039/040 high-risk false-negative evidence and production final-blocking authority; OP-041/042 service/R&D ingredient identity and evidence-backed goal priors.

## 2026-07-16 special-population and condition safety loop

- Chosen stage: `original plan / personalized safety engine`
- Chosen tasks: OP-033 separate pregnancy and lactation restrictions; OP-034 expand condition-specific contraindication and review-required rules
- Primary evidence: `data/original_plan/evidence/op033_op034_special_population_condition_safety_smoke_v1.json`; eight real schema-normalization-safety cases plus the interim replay decisions, byte-identical across reruns (`a3689cc0c1d5ad9cb73733ac7aeb42699f12083f26d589dc2ec16c5fd4f71a49`)
- Reused the strict `RecommendationRequest`, normalized intake, data-defined `SafetyRuleSet`, recommendation safety service, interim replay safety path, and runtime knowledge builder. No parallel safety engine or recommendation path was created.
- `UserProfile` now accepts an independent `lactating` flag. The false default remains present in OpenAPI but is omitted from serialized requests, preserving existing request payloads, normalized hashes, and the WellnessBox profile-adapter contract. Pregnancy keeps `SAFETY-PREG-001`; lactation uses `SAFETY-LACT-001`; both active states apply each rule once.
- Condition rules now declare `contraindication` or `review_required`. The data covers chronic kidney review, kidney failure or dialysis blocking, liver failure or cirrhosis blocking pending clinical review, and hemochromatosis exclusions for iron and vitamin C. Contraindication records cannot omit their excluded ingredients.
- Policy bases are scoped per rule and ingredient in the deterministic evidence. NIH NCCIH supports the ashwagandha pregnancy/lactation restriction, the NCBI-hosted MotherToBaby fact sheet supports the berberine pregnancy/lactation restriction, and NIH ODS supports the renal-magnesium and hemochromatosis iron/vitamin-C restrictions. The hepatic blocker is identified separately as the plan's conservative initial high-risk research-scope policy, not as an externally validated clinical rule. OP-035 evidence-ID lineage remains a separate requirement; this loop does not claim that drug-interaction evidence work.
- Evidence status: OP-033 and OP-034 are complete at their required `IMPLEMENTED` stage. Generated status: complete `24`, partial `10`, pending `85`, external `1`, contradicted `0`.
- Validation: exact CI-equivalent selection `208 passed`; focused safety/runtime selection `27 passed`; full Ruff PASS; manifest audit PASS with `34` claims, `99` checked evidence files, and zero issues; completion-report stale check PASS.
- Full suite: `621 passed`, `77 failed`; the unchanged failure groups remain `73` absent ignored report artifacts and `4` CGM geometry assertions. No new safety-rule failure remains.
- Frozen evaluation: `256` cases; all seven tracked metric deltas are exactly `0` against `artifacts/reports/op029_op030_frozen_eval/eval_report.json`.
- Integration boundary: the current WellnessBox stored profile still exposes one combined `pregnantOrBreastfeeding` field. This loop implements distinct R&D inputs and rules but does not claim that the service can identify which state produced the combined source value.
- Recommended next loops: OP-035/036 evidence-linked drug interactions and cross-product aggregate dose; OP-037/038 normalized unit/upper-limit comparison and rule version/application time; OP-039/040 high-risk false-negative evaluation and production final-blocking authority.

## 2026-07-16 deterministic session replay and service UI loop

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-029 deterministic saved-session replay; OP-030 saved-session count and replay-result display in the WellnessBox evaluator UI
- Primary evidence: `data/original_plan/evidence/op029_op030_session_replay_service_ui_smoke_v1.json`; `4` actual FastAPI route cases, SQLite schema `9`, one replay snapshot, one exact-version `MATCH`, one fail-closed `VERSION_MISMATCH`, and two append-only replay-run rows
- Reused the existing recommendation engine, `ExecutionLedger`, execution identity, interim internal-token policy, and WellnessBox `callWbRndInterim` client. No parallel recommendation engine, session store, browser credential path, or local KPI replay substitution was created.
- Replay snapshots retain the exact validated request and a stable output projection only when every represented input source permits persistent storage. Replay checks request and snapshot integrity plus model, engine, code, dataset, and configuration identity before calling the recommendation engine. A version mismatch records the attempt and skips recommendation execution.
- The WellnessBox evaluator now shows the R&D connection state, saved/replayable/run counts, recent replayable sessions, and separate input/version/output checks. The default view does not expose raw health payloads, hashes, execution IDs, model IDs, or internal credentials. Changing the selected session clears the prior result.
- Evidence status: OP-029 and OP-030 are `IMPLEMENTED`, not `OPERATED`. The service production environment has no deployed R&D base URL or `WB_RND_*` configuration, so the two production processes still do not run together and the UI must report `R&D 서버 미연결`. Generated status: complete `22`, partial `10`, pending `87`, external `1`, contradicted `0`.
- Validation: exact CI-equivalent selection `200 passed`; focused runtime-boundary audit `2 passed`; full Ruff PASS; replay smoke byte-identical across reruns (`45e4edfc5d4002853bd722d80e238cba954ca404af5bf687e5a3c79ecb856ded`); manifest audit PASS with `32` claims, `93` checked evidence files, and zero issues; completion-report stale check PASS; final independent review found no Critical, Important, or merge-blocking Minor findings.
- Full suite: `611 passed`, `77 failed`; the unchanged failure groups remain `73` absent ignored report artifacts and `4` CGM geometry assertions. The runtime-boundary audit now inspects the actual `recommend(payload)` call through Python syntax instead of requiring one obsolete return-statement string.
- Frozen evaluation: `256` cases; all seven tracked metric deltas are `0` against the previous 256-case report.
- WellnessBox validation: replay contract QA, web-lab QA, interim QA, Data Lake QA, TypeScript, encoding audit, lint, `git diff --check`, and production build PASS.
- Biggest bottlenecks: no deployed R&D process; no durable production R&D database; no production service-to-R&D internal authentication; no successful production replay round trip or postcondition re-query.
- Recommended next loops: OP-033/034 pregnancy/lactation and condition-specific safety rules; OP-035/036 evidence-linked drug interactions and combined-dose calculation; OP-037/038 allergy normalization and repeated-risk handling.
- Publication: WellnessBox commit `6adf202` and R&D commit `8727853` were pushed to `main`. Encoding Guard run `29467286428` and Original plan evidence run `29467301272` passed. Vercel production deployment `dpl_2exTp3pgV6YsPBqSQkoZFKYgi5w5` is `Ready` and aliased to `wellnessbox.kr`. A headed Chrome check completed password login, the evaluator's default 1→6 stage path, the replay-panel render, and the connection refresh with zero console errors and HTTP 200 lab responses. Because production has no `WB_RND_*` settings, the verified panel correctly shows `R&D 서버 미연결` and dash counts; no production replay was claimed.

## 2026-07-16 event idempotency and data-mutation loop

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-027 idempotency-key duplicate blocking; OP-028 correction and deletion processing with lineage and audit preservation
- Primary evidence: `data/original_plan/evidence/op027_op028_event_idempotency_data_mutation_smoke_v1.json`; `3` actual FastAPI route cases, SQLite schema `8`, one stored conversation replay, one stored behavior replay, two event mutations, two mutation audit rows, and one retained knowledge-lineage row on the mutated event
- Reused `execution_events`, `behavior_events`, `execution_knowledge_lineage`, and `audit_events`. Schema `8` keeps the ingestion hash immutable, adds effective payload state and hash, and adds one indexed `event_mutations` chain; no parallel event store or review queue was created.
- Identical event replays return the existing row and `deduplicated=true`. A changed source, timestamp, operation, or payload under the same scoped idempotency key returns `409`, while SQL unique constraints protect the same invariant under concurrent writes.
- Mutation routes require a configured internal token in every environment and verify profile ownership. A correction changes only the effective payload. A deletion writes a non-sensitive tombstone and a `PENDING` cleanup state, then applies SQLite `secure_delete`, truncates the WAL, and compacts the database before returning success. Failed cleanup resumes on an identical request or the next store startup. Trigger-protected mutation and audit rows store canonical chain hashes and identifiers, not copied raw payloads. The original event ID, ingestion hash, and every `execution_knowledge_lineage` row remain queryable.
- Evidence status: OP-027 and OP-028 are `IMPLEMENTED`, not `OPERATED`. The local `TestClient` plus temporary SQLite does not prove production persistence or a production postcondition re-query. Generated status: complete `22`, partial `8`, pending `89`, external `1`, contradicted `0`.
- Validation: exact CI-equivalent selection `192 passed`; focused persistence regression `46 passed`; full Ruff PASS; new smoke byte-identical across reruns (`9342c871b4084fb09fccfc243ff1898c24e4798a64fb4260b267d817de3bfd48`); manifest audit PASS with `30` claims, `81` checked evidence files, and zero issues; completion-report stale check PASS; independent final review found no Critical, Important, or Minor findings.
- Full suite: `602 passed`, `78 failed`; the unchanged failure groups remain `74` absent ignored report artifacts and `4` CGM geometry assertions.
- Frozen evaluation: `256` cases; all seven tracked metric deltas are `0`. Replay/slice deltas: not applicable to this persistence-only loop.
- Biggest bottlenecks: no deployed R&D process; no durable production R&D database; no authenticated service-to-R&D round trip; no production correction/deletion re-query evidence; no session replay API or service replay UI.
- Recommended next loops: OP-029/030 session replay API and service UI; OP-033/034 pregnancy/lactation and condition-specific safety rules; OP-035/036 evidence-linked drug interactions and combined-dose calculation.
- Publication: implementation commit `e2cfc54` was pushed to `main`; `Original plan evidence` run `29464603258` passed all audit, report, contract-test, and Ruff steps.

## 2026-07-15 log separation and execution-identity loop

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-025 user-behavior versus research-evaluation log separation; OP-026 model, dataset, code-commit, and config identity per recommendation execution
- Primary evidence: `data/original_plan/evidence/op025_op026_log_separation_identity_smoke_v1.json`; `2` actual FastAPI route cases, SQLite schema `8`, two execution identities, six research events, one behavior event, deterministic across reruns
- Schema `6` added `behavior_events` with a bounded user-behavior vocabulary that is disjoint from the research event vocabulary at the SQL CHECK level, plus `execution_identities` keyed by execution ID. Schema `7` corrects the execution-knowledge-lineage unique key so one claim and output can retain multiple linked rules. Existing v5 and v6 databases migrate in place with all rows preserved.
- The actual `/v1/recommend` route now records model ID `deterministic_baseline_v1`, engine version, code commit (environment override first, local git HEAD second, explicit `unresolved` fallback), four hashed runtime dataset identities (runtime knowledge DB, reference knowledge base, safety rules, ingredient catalog), and a canonical config SHA-256 inside the same persistence transaction. The authenticated execution trace returns the structured identity, and identical runs share one config hash.
- `POST /v1/interim/behavior-events` writes only to the behavior store: research event types return `422` there, behavior names return `422` on the research event route, identical replays deduplicate, changed payloads return `409`, and missing survey storage consent returns `403`. `GET /v1/interim/log-classes` reports per-class counts and zero cross-contamination.
- Local artifact maintenance: the ignored local interim database still carried sticky `content_changed` quarantines caused by the audited OP-023/024 knowledge-artifact update. After confirming the stored checksums already match the current committed artifacts, the three internal reference sources were explicitly reviewed and un-quarantined with a recorded review note in their metadata; the eight external adapter `license_not_approved` quarantines remain untouched. Fresh checkouts never see this state, so CI was unaffected.
- Evidence status: OP-025 and OP-026 are `IMPLEMENTED`, not `INTEGRATED` or `OPERATED`, because a local `TestClient` plus temporary SQLite proves neither a production round trip nor a production re-query. Generated status: complete `22`, partial `6`, pending `91`, external `1`, contradicted `0`.
- Validation: focused CI-equivalent selection `176 passed`; full Ruff PASS; new smoke byte-identical across reruns; manifest audit PASS with `28` claims and zero issues; completion-report stale check PASS.
- Frozen evaluation: `256` cases; all seven metric deltas are `0` against the pre-loop report. Replay/slice deltas: not applicable to this persistence-only loop.
- Biggest bottlenecks: no deployed R&D process; no durable production R&D database; no authenticated service-to-R&D round trip; no production storage re-query evidence; no explicit committed review workflow for quarantined sources yet.
- Recommended next loops: OP-027/028 idempotency plus deletion/correction audit handling; OP-029/030 replay API plus service UI; OP-033/034 safety-engine group D start.
- Publication: implementation commit `12591d4` passed Original plan evidence run `29422080597` on the first attempt.

## 2026-07-15 knowledge evidence-lineage loop

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-023 source-to-result lineage; OP-024 source lifecycle, type, and license metadata
- Primary evidence: `data/original_plan/evidence/op023_op024_knowledge_lineage_smoke_v1.json`; `1` actual FastAPI route case, SQLite schema `8`, three sources, five parsed passages, five normalized claims, five rules, five claim-rule links, and two execution-result lineage rows
- Reused the existing reference knowledge artifact and `InterimStore`. No parallel knowledge base was created. The schema now stores parsed source URI, upstream reference URI, page or section, line span, normalized claim, rule, source lifecycle, source type, license, and raw-content checksum.
- The actual `/v1/recommend` route synchronizes the versioned local knowledge artifact and persists safety-rule and final-decision lineage under the response execution ID. The authenticated execution trace returns structured lineage without returning full raw source documents.
- Recommendation-result lineage is skipped when used-source storage consent is denied. A changed source remains quarantined across identical re-synchronizations until a future explicit review workflow clears it.
- Parsed source identity and upstream reference identity are separate. Citation lines `13..33` and their checksum point to `data/raw_references/supplement_warfarin_interaction.md`; the upstream supplement note remains recorded separately.
- Evidence status: OP-023 and OP-024 are `IMPLEMENTED`, not `INTEGRATED` or `OPERATED`. Local `TestClient` plus temporary SQLite does not prove a real two-process round trip or production re-query. Generated status: complete `22`, partial `4`, pending `93`, external `1`, contradicted `0`.
- Focused CI-equivalent selection: `159 passed`. Full suite: `569 passed`, `78 failed`; the unchanged failures are `74` absent ignored report artifacts and `4` CGM geometry assertions.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`, and every weakest-slice category is unchanged. Data Lake replay delta: not applicable to this persistence-only loop.
- Biggest bottlenecks: no deployed R&D process; no durable production R&D database; no authenticated service-to-R&D process round trip; no production storage re-query evidence; only three normalized local source documents, with the upstream supplement file still requiring encoding/source-quality remediation.
- Recommended next loops: OP-025/026 log separation and execution identities; OP-027/028 broader idempotency plus deletion/correction audit handling; OP-029/030 replay API plus service UI.
- Publication: implementation commit `2ea5e40` plus CI-compatibility commit `194db51` passed Original plan evidence run `29419358491`. The first push run `29419151688` failed only because the newly CI-selected `tests/test_interim_api.py` recommendation test requires the ignored local `artifacts/tips/interim/retrained` package, which fresh CI checkouts do not have; the fix adds an explicit artifact-absence skip guard to that one test and changes no expected values. Local rerun before publication: focused selection PASS, full Ruff PASS, knowledge-lineage smoke deterministic PASS, manifest audit PASS with zero issues, completion-report stale check PASS, and the official `256`-case frozen evaluation exactly matches all seven recorded current metric values.

## 2026-07-15 Data Lake profile and execution-lineage loop

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-021 versioned profile and consent snapshots; OP-022 common execution IDs for recommendation, safety, optimization, conversation, and follow-up events
- Primary evidence: `data/original_plan/evidence/op021_op022_data_lake_lineage_smoke_v1.json`; `3` local runtime cases, current SQLite schema `8`, two authorized profile versions, two consent versions, and five linked event types
- Added profile snapshots, immutable consent snapshots, execution records, and event records to the existing `InterimStore`. The actual recommendation route writes the three stages that ran; authenticated internal routes append conversation and follow-up events.
- Every event now records the consent snapshot that authorized the write. A profile-level active consent pointer preserves decision order even when an old immutable snapshot is reused, so `거부 → 허용 → 재거부` blocks writes to the older allowed execution. Replays with a changed source or payload fail closed.
- Added an autouse temporary database fixture to recommendation API tests. Test runs no longer write to the default interim artifact database; pre-existing rows were not deleted.
- The service adapter forwards one stable `usr_<hex>` subject ID without exposing a raw service database ID. Both repository contracts remain byte-identical.
- Evidence status: OP-021 and OP-022 are `IMPLEMENTED`, not `INTEGRATED` or `OPERATED`. The local `TestClient` and temporary SQLite smoke does not prove a real two-process round trip or production re-query. Generated status: complete `22`, partial `2`, pending `95`, external `1`, contradicted `0`.
- Frozen evaluation: `256` cases; all seven metric deltas are `0`. Replay/slice deltas: not applicable to this persistence-only loop.
- Focused Data Lake and API tests pass. The current full suite has `563` passes and `78` known failures: `74` missing ignored report artifacts and `4` CGM geometry assertions.
- Biggest bottlenecks: no deployed R&D process; no persistent production R&D database; no service-to-R&D process round trip; no authenticated production recommendation write path; no production storage re-query evidence.
- Recommended next loops: OP-023/024 source-to-recommendation lineage; OP-025/026 log separation and execution identities; OP-027/028 broader idempotency plus deletion/correction audit handling.

## 2026-07-15 WellnessBox profile-adapter integration loop

- Chosen stage: `original plan / personal health inputs`
- Chosen task: OP-019 lossless `wellnessbox` stored-profile adapter
- Primary contract: `data/contracts/wellnessbox_profile_adapter_v1.json`; `1` representative profile containing all `12` current `types/chat.UserProfile` properties plus `10` shared boundary cases, `15` R&D contract tests, and `16` service adapter and POST-route checks
- Added a strict Zod adapter in `wellnessbox` and connected it to the existing internal recommendation-preview route. The adapter requires age, sex, at least one supported goal, and explicit survey recommendation-use consent; unknown fields and unsupported goals return structured errors instead of disappearing.
- The adapter preserves the complete source object under versioned `source_profile.profile`. It also maps age, sex, height, weight, conditions, medication names, allergies, goals, dietary restrictions, and the conservative pregnancy-or-breastfeeding flag into the existing R&D request fields. Name and caffeine sensitivity remain available in the exact source trace rather than being invented as unrelated clinical fields.
- Added the matching strict Pydantic source-profile envelope to `RecommendationRequest`. The trace is exposed in OpenAPI but excluded from the established normalized clinical-input hash, so frozen-eval comparability is preserved.
- Aligned source validation at both boundaries: medication and other source list items are capped at `128` Unicode code points, list counts match, blank text is rejected, and R&D no longer coerces string, boolean, or fractional ages. Integral numeric ages such as `42.0` remain compatible with JavaScript number semantics. Malformed JSON returns `400`; top-level `null` or arrays return structured `422` responses instead of silently running the sample request.
- The contract snapshot is byte-identical in both repositories. The R&D evidence workflow now checks out the public `wellnessbox` repository and audits tracked evidence from both owners; the service encoding workflow runs the adapter contract QA.
- Current audited disposition after regeneration: complete `22`, partial `0`, pending `97`, external `1`, contradicted `0`.
- Validation: exact original-plan workflow selection `114 passed`; full Ruff PASS; manifest audit (`22` claims, `55` evidence files) and generated-report stale check PASS.
- `wellnessbox` validation: adapter and POST-route QA PASS (`16` checks), existing preview QA PASS (`4` checks), TypeScript PASS, encoding PASS, lint PASS, production build PASS.
- Full R&D suite: `549 passed`, `77 failed`. The failure count remains the known `73` absent ignored report artifacts and `4` CGM geometry assertions.
- Official frozen eval: `256` cases rerun; all seven metrics exactly match the previously recorded current values, so every metric delta is `0`.
- Publication: service commit `485da91` passed Encoding Guard run `29414011315`; R&D implementation commit `10ba2a7` passed Original plan evidence run `29414033364`. Independent final review reported zero Critical, Important, and Minor findings.
- This loop did not deploy the R&D process or enable production `WB_RND_*` settings. The two production processes still do not run together; OP-101 through OP-105 remain open.

## 2026-07-15 unsupported-input rejection loop

- Chosen stage: `original plan / personal health inputs`
- Chosen task: OP-020 unsupported or ambiguous recommendation input rejection
- Primary fixture: `data/samples/api_recommend_consent_hash_request_v1.json`; `1` representative API request plus `18` focused field, unit, duplicate, Unicode, alias, multiplicity, and compatibility cases
- Reused `RecommendationRequest` and the existing `/v1/recommend` route. No parallel validation endpoint or duplicate request schema was added.
- Every recommendation request container now rejects unknown fields through one `extra="forbid"` base model. Unsupported top-level, profile, lifestyle, source-availability, preference, and nested fields return FastAPI 422 instead of disappearing during Pydantic parsing.
- Structured medication dose units continue to use the bounded `DoseUnit` enum. Laboratory observations now accept only the existing canonical unit set and its explicit aliases; arbitrary units such as `bananas` return 422.
- Medication, supplement product, and supplement ingredient identities use NFKC, case folding, and collapsed whitespace. Ingredient identity also uses exact catalog aliases, so `vitamin c` and `ascorbic acid` cannot bypass conflict detection. Fuzzy catalog matching is not used for rejection.
- Same-name inputs with different classifications, doses, ingredient doses, or ingredient multiplicity return 422. Completely identical medication and supplement product duplicates remain compatible.
- Current audited disposition after regeneration: complete `21`, partial `0`, pending `98`, external `1`, contradicted `0`. OP-019 remains pending because `wellnessbox` still lacks a real profile-to-R&D adapter.
- Validation: exact original-plan workflow selection `99 passed`; recommendation and safety core regressions `206 passed`; full Ruff PASS; manifest audit and generated-report stale check PASS.
- Full suite: `534 passed`, `77 failed`. The failure count remains the known `73` absent ignored report artifacts and `4` CGM geometry assertions.
- Official frozen eval: `256` cases rerun; all seven metrics exactly match the previously recorded current values, so every metric delta is `0`.
- This loop did not deploy or connect the R&D process to production `wellnessbox`.

## 2026-07-15 consent and deterministic input-hash loop

- Chosen stage: `original plan / personal health inputs`
- Chosen tasks: OP-017 source-specific consent scopes; OP-018 deterministic normalized-input snapshot and SHA-256
- Primary fixture: `data/samples/api_recommend_consent_hash_request_v1.json`; `1` representative API request plus `13` focused consent, gating, normalization, hashing, API, and compatibility cases
- Reused `RecommendationRequest`, `normalize_request`, the existing recommendation service, and the inference route instead of adding a parallel consent API or hash path.
- Survey, National Health Insurance Service, wearable, CGM, and genetic sources now have independent `use_for_recommendation` and `allow_persistent_storage` scopes. Effective recommendation availability and storage-authorized source sets are calculated separately.
- Omitting the whole consent block preserves legacy recommendation behavior without granting persistent storage. Once a caller supplies the consent block, omitted sources default to denied. Survey-use denial rejects the recommendation request at both the model and API boundaries.
- Laboratory observations carry source provenance. Observations whose source lacks recommendation-use consent are removed before missing-information, safety, model-feature, and recommendation consumers run. Denied NHIS laboratory values cannot change the normalized snapshot, hash, or recommendation result.
- The normalized snapshot excludes random request IDs, sorts unordered top-level records and nested supplement ingredients, canonicalizes existing health-input values, and normalizes `-0.0` to `0.0`. SHA-256 is calculated from compact UTF-8 JSON with sorted object keys.
- Current audited disposition after regeneration: complete `20`, partial `0`, pending `99`, external `1`, contradicted `0`.
- Validation: focused original-plan workflow contracts `81 passed`; recommendation and safety core regressions `206 passed`; full Ruff PASS; manifest audit and generated-report stale check PASS.
- Full suite: `516 passed`, `77 failed`. The failure count remains the known `73` absent ignored report artifacts and `4` CGM geometry assertions.
- Official frozen eval: `256` cases rerun; all seven metrics exactly match the previously recorded current values, so every metric delta is `0`.
- This loop did not deploy or integrate the R&D process with `wellnessbox`; two-process integration remains open.

## 2026-07-15 diet, lifestyle, and laboratory input-contract loop

- Chosen stage: `original plan / personal health inputs`
- Chosen tasks: OP-015 allergy, dietary-pattern, and lifestyle normalization; OP-016 structured laboratory observations
- Primary fixture: `data/samples/api_recommend_diet_lifestyle_lab_request_v1.json`; `1` representative API case with `2` laboratory observations
- Reused `RecommendationRequest`, `normalize_request`, the efficacy/policy feature builders, missing-information decisions, and the existing inference route instead of adding a parallel intake API.
- Allergy strings are now exposed as a stable sorted normalized list and set. Dietary patterns accept legacy strings or strict code/display-name objects, deduplicate by normalized code, and retain structured display names.
- Lifestyle input retains the existing sleep, stress, activity, smoking, and alcohol fields and adds bounded weekly exercise minutes and daily caffeine milligrams.
- Laboratory observations require a code, finite non-boolean value, explicit unit, bounded reference range, and timezone-aware measurement time. Normalization canonicalizes codes and common unit spellings, including ASCII and Unicode micro prefixes, converts times to UTC, retains every observation, selects the latest observation per code, and classifies it as low, within range, or high. Conflicting values at the same normalized code and UTC time are rejected.
- Normalized allergy, diet, lifestyle, and laboratory context reaches both existing model feature dictionaries. Relevant glucose or lipid observations also satisfy the corresponding missing-context check without changing frozen requests that have no laboratory observations.
- Current audited disposition after regeneration: complete `18`, partial `0`, pending `101`, external `1`, contradicted `0`.
- Validation: focused original-plan workflow contracts `68 passed`; expanded core regressions `311 passed` with `2` documented legacy failures; full Ruff PASS; manifest audit and generated-report stale check PASS.
- Full suite: `503 passed`, `77 failed`. The failure count remains the known `73` absent ignored report artifacts and `4` CGM geometry assertions.
- Official frozen eval: `256` cases rerun; all seven metrics exactly match the previously recorded current values, so every metric delta is `0`.

## 2026-07-15 medication and supplement input-contract loop

- Chosen stage: `original plan / personal health inputs`
- Chosen tasks: OP-013 medication classification and dose/unit contract; OP-014 current-supplement product, ingredient, and daily-dose contract
- Primary fixture: `data/samples/api_recommend_structured_safety_block_request_v1.json`
- Reused the existing `medications`, `current_supplements`, normalization, model-feature, and deterministic safety paths instead of adding a parallel intake API.
- Medication input now accepts a strict classification object and either the existing legacy dose string or a numeric dose-unit object.
- Supplement input now accepts a numeric product daily dose and ingredient objects with ingredient-specific daily doses while retaining the legacy product dose string and ingredient strings.
- Normalized intake preserves canonical medication detail, classification codes, supplement products, ingredients, and typed doses. Existing unknown product and ingredient strings remain available for runtime knowledge matching.
- The safety engine consumes normalized typed ingredient doses, sums the same ingredient across products, converts compatible mass and vitamin D IU units, and compares the total with the existing deterministic upper-limit rules.
- Product-level doses are used only when the input declares exactly one ingredient through an exact catalog alias. Fuzzy matches and compound ingredient text cannot assign one product dose to a single ingredient.
- Existing warfarin-glucosamine knowledge-rule behavior and legacy string dose requests remain compatible.
- Current audited disposition after regeneration: complete `16`, partial `0`, pending `103`, external `1`, contradicted `0`.
- Validation: focused original-plan workflow contracts `58 passed`; broader requirement, knowledge, safety, and recommendation regressions `258 passed`; full Ruff PASS; manifest audit and generated-report stale check PASS.
- Full suite: `493 passed`, `77 failed`. The failure count remains the known `73` absent ignored report artifacts and `4` CGM geometry assertions.
- Official frozen-eval metric deltas: none. No model artifact, dataset, runtime deployment, or production service changed.

## 2026-07-15 structured health-input contract loop

- Chosen stage: `original plan / personal health inputs`
- Chosen tasks: OP-011 biometric profile and OP-012 condition, symptom-severity, and urgent-risk contracts
- Primary fixture: `data/samples/api_recommend_structured_health_input_request_v1.json`
- Reused the existing age, biological-sex, pregnancy boolean, condition/symptom arrays, urgent-risk rules, and safety engine instead of creating a parallel request path.
- Added bounded optional height and weight fields to `UserProfile`.
- The existing `conditions`, `symptoms`, and `risk_flags` fields now accept either legacy strings or strict structured objects. Structured inputs retain condition status, symptom severity and duration, and urgent-signal presence and source.
- One normalization path converts both formats into canonical detail records plus deterministic code sets and status maps. Symptom duration, condition display name, and explicitly absent risk-signal metadata remain available without rereading the heterogeneous request. Resolved conditions and absent risk signals do not activate safety, risk labels, model features, or learned-model guards.
- The existing urgent chest-pain rule consumes a structured risk signal and stops recommendation generation with `trigger_safety_recheck`.
- The original-plan CI now runs the health-input contract and inference API tests when their schemas, normalization, fixtures, or route examples change.
- Current audited disposition after regeneration: complete `14`, partial `0`, pending `105`, external `1`, contradicted `0`.
- Validation: original-plan and API contracts `42 passed`; broader recommendation and safety regressions `199 passed`; downstream model and synthetic compatibility tests `30 passed`; full Ruff, audit, and generated-report checks PASS.
- Full suite: `477 passed`, `77 failed`. The failure set remains the known `73` absent ignored report artifacts and `4` CGM geometry assertions.
- Official frozen-eval metric deltas: none. No model artifact, runtime deployment, or production service changed.

## 2026-07-15 original plan completion-report loop

- Chosen stage: `original plan / evidence governance`
- Chosen task: OP-010 generate the full requirement-status report from audited evidence
- Primary dataset: `data/original_plan/requirements_manifest_v1.json`
- Case count: `120` requirements; `12` valid completion claims
- Added deterministic JSON and Korean Markdown reports covering every OP-001 through OP-120 requirement.
- The generator classifies requirements as complete, partial, pending, external, or contradicted. A broken requirement-level evidence claim becomes contradicted; a common source or manifest audit failure invalidates every existing completion claim. The audit embeds a canonical manifest SHA-256, and the report rejects an audit produced from different manifest content.
- CI now checks that both committed report artifacts exactly match the current manifest and evidence audit.
- Current audited disposition: complete `12`, partial `0`, pending `107`, external `1`, contradicted `0`.
- Focused validation: `25 passed`; full Ruff PASS; generator and stale-output checks PASS.
- Full suite: `470 passed`, `77 failed`. The unchanged failures are `73` absent ignored report-artifact checks and `4` existing CGM geometry assertions; no OP-010 test failed.
- Official frozen-eval metric deltas: none. No runtime or production deployment changed.

## 2026-07-15 original plan audit-command and CI loop

- Chosen stage: `original plan / evidence governance`
- Chosen task: OP-009 expose the audit as one deterministic command and CI gate
- Primary dataset: `data/original_plan/requirements_manifest_v1.json`
- Case count: `120` requirements; `11` current claims
- Added `python scripts/audit_original_plan_requirements.py` with JSON output and strict PASS=`0`, FAIL=`1` exit codes.
- Relative manifest paths resolve from the R&D repository root. The sibling service repository is optional until a claimed evidence file requires it.
- Added a Python 3.11 GitHub Actions workflow that runs the CLI, manifest/audit/CLI tests, and focused Ruff checks on relevant changes.
- Added CLI tests for a valid manifest, a deliberately corrupted hash, and workflow command coverage.
- OP-009 is the eleventh claimed requirement. The remaining `109` requirements stay unclaimed.
- Validation: `16 passed`; full Ruff PASS; CLI audit PASS with `20` unique evidence files, zero issues, and PDF hash match.
- GitHub Actions run `29402915435` passed after replacing hard-coded Windows test roots with checkout-relative roots. The workflow now uses current `actions/checkout@v7` and `actions/setup-python@v6` releases.
- Official frozen-eval metric deltas: none. No runtime or production deployment changed.

## 2026-07-15 original plan evidence-audit loop

- Chosen stage: `original plan / evidence governance`
- Chosen task: OP-008 verify completion claims against current repositories
- Primary dataset: `data/original_plan/requirements_manifest_v1.json`
- Case count: `120` requirements; `10` current claims
- Added a deterministic audit report with PASS/FAIL status, claimed-stage counts, checked evidence count, source-hash result, and structured issue codes.
- The audit verifies repository ownership, path containment, file existence, Git tracking, original PDF SHA-256, completion-program presence, and stage-specific evidence requirements.
- Added negative tests for missing evidence, ownership mismatch, repository path escape, untracked evidence, and source hash mismatch.
- Current claim count advances from `9/120` to `10/120` only because OP-008 now has tracked implementation and test evidence. The other `110` requirements remain unclaimed.
- Focused result: manifest and audit tests `13 passed`; full Ruff PASS; live audit PASS with `17` unique evidence files and zero issues.
- Official frozen-eval metric deltas: none. No runtime recommendation, model, dataset, order path, or production deployment changed.

## 2026-07-15 original plan evidence-manifest loop

- Chosen stage: `original plan / evidence governance`
- Chosen task: OP-006 machine-readable requirement manifest and OP-007 evidence-stage schema
- Primary dataset: `data/original_plan/requirements_manifest_v1.json`
- Case count: `120` requirements in `12` groups
- Added exact OP-001 through OP-120 coverage with original-plan page references, repository ownership, required evidence stage, current claim, and six evidence collections.
- Added strict Pydantic models for `IMPLEMENTED`, `INTEGRATED`, `OPERATED`, and `EXTERNAL` claims.
- `IMPLEMENTED` requires implementation and test files; `INTEGRATED` additionally requires integration evidence; `OPERATED` additionally requires operational evidence; `EXTERNAL` requires an external dependency and replacement contract.
- Unknown fields, unknown completion wording, duplicate or missing IDs, wrong group order, and non-ten-item groups are rejected.
- Current conservative claim count: `9/120`; claimed IDs are OP-001 through OP-007, OP-031, and OP-032. The remaining `111` requirements stay unclaimed even when partial code exists.
- Focused result: manifest and recommendation API tests `17 passed`; focused Ruff PASS.
- Full suite: `529` collected, `452 passed`, `77 failed`; the same 73 missing-report and four CGM baseline failures remain, with no new failure introduced by this loop.
- Official frozen-eval metric deltas: none. No training, model promotion, KPI substitution, service mutation, or deployment occurred.

## 2026-07-15 original plan completion loop 1

- Chosen stage: `original plan / safety input contract`
- Chosen task: implement deterministic allergy exclusion and urgent-risk blocking across the R&D and service request contracts
- Primary rule dataset: `data/rules/safety_rules.json`
- Case count: `2` new deterministic API scenarios
- Production topology finding: `wellnessbox` and `wellnessbox-rnd` do not currently run together. The production `/tips` page uses the service repository's TypeScript lab runtime, and the R&D FastAPI proxy remains disabled and undeployed.
- Added `allergies` and `risk_flags` to `RecommendationRequest`, normalized both inputs, and added version-controlled rule models.
- A fish allergy now excludes `omega3` before recommendation output.
- Chest pain and severe abdominal pain flags now block recommendation and return `trigger_safety_recheck`.
- The `wellnessbox` preview client forwards both fields without changing the existing fallback contract.
- Fixed one pre-existing Python 3.11 compatibility defect in the sensor/genetic audit Markdown renderer.
- Focused R&D result: `10 passed` for `tests/test_inference_api.py`; sensor/genetic audit `2 passed`; full Ruff PASS.
- Service result: preview-route QA PASS, TypeScript PASS, encoding audit PASS, production build PASS.
- Full legacy R&D suite: `445 passed, 77 failed, 68 warnings`.
- Full-suite failure root causes: `73` tests require absent ignored `artifacts/reports/**` files; `4` tests assert stale CGM geometry. Disabling the new safety rules produced the same CGM distribution, so the safety contract did not cause that drift.
- Official frozen-eval metric deltas: none. No training, learned-model promotion, KPI substitution, or production R&D deployment occurred.

## 2026-07-14 verified replay-input restoration loop

- Chosen stage: `P3/P4 replay evidence reproducibility`
- Chosen task: add a fail-closed restoration path for the five missing `large_drop` replay inputs
- Primary dataset: `data/synthetic/synthetic_longitudinal_v4.jsonl`
- Case count: `480` trajectory records, `96` users; target slice remains `3` cases
- Human approvals received: research-loop start, pharmacist safety/recommendation basis, validation result
- The approvals authorize the bounded evidence loop; they do not authorize retraining or fabricated artifacts.
- Added manifest-driven archive restoration with SHA-256 verification, allowed-root checks, and atomic file replacement.
- Restore remains blocked until the exact trusted archive and its hash manifest are supplied.
- No training, runtime promotion, safety change, optimizer change, or frozen-eval change.

## 2026-07-13 large-drop replay prerequisite audit

- Chosen stage: `P3/P4 replay evidence reproducibility`
- Chosen task: preflight the next `threshold_duration_sensitive / mid_margin / large_drop` replay-only attribution
- Primary dataset: `data/synthetic/synthetic_longitudinal_v4.jsonl`
- Case count: `480` trajectory records, `96` users; expected target slice count `3`
- Classification: shared reproducibility-contract defect, not a new model defect
- Required inputs: `8`; present: `3`; missing: `5`
- Present: dataset, `policy_model_v1`, reference `effect_model_v3`
- Missing: held candidate artifact, family diagnostic, subgroup diagnostic, mid-margin diagnostic,
  and prior small-drop attribution
- Added a deterministic prerequisite audit with file size and SHA-256 evidence.
- The replay command now writes a structured blocked report before attempting evidence loads.
- No retraining, candidate creation, attribution fabrication, runtime promotion, safety change, or frozen-eval change.
- Result: `artifacts/reports/large_drop_replay_prerequisite_audit_v1.json`

## 2026-07-13 Cloud GPU bulk-inference testbed

- Chosen stage: `P3/P4 infrastructure validation`
- Chosen task: reusable CPU/CUDA bulk-inference testbed for the held `effect_model_v3` artifact
- Primary dataset: `data/synthetic/synthetic_longitudinal_v4.jsonl`
- Case count: `480` trajectory records, `96` users
- Implemented equivalent PyTorch `Linear` inference, CPU/CUDA benchmarking, numerical parity checks,
  structured logs, TorchScript export, prediction samples, metrics, and SHA-256 manifest verification.
- Real Cloud run: Kakao `gn1i.xlarge`, Tesla T4, PyTorch `2.6.0+cu124`.
- Same-workload result: CPU `33,263,663.619 rows/s`; CUDA `347,441,184.227 rows/s`; `10.4451x` speedup.
- CPU/CUDA maximum absolute difference: `0.0`.
- Task cost: `138.171818083333 KRW` excluding VAT; GPU time: `746.077 s` including retries.
- Postflight resources: instances `0`, public IPs `0`; instance-owned temporary disk released.
- No training, runtime promotion, safety change, optimizer change, or frozen-eval change.
- Result: `artifacts/gpu_testbed/cloud_kakao/`.

## 2026-07-10 TIPS interim end-to-end override

- Mode: `PROXY_GOLD_SIMULATION`
- Source manifest SHA-256: `2a430ac5899544885d4be923213b50d526ffd0df016b2b34bf57a077d4c650a4`
- Retrained model SHA-256: `f6b053ee0eb39d16e12e102723f9435a03e71068b70502f6ca702c80e82a7612`
- Imported: 150,000 cases, 240 PRO, 3 ADR, 180 W/C/G sessions, 10,000 eval cases.
- Implemented: manifest verification, SQLite lineage, corrected KPI formulas, retraining and registry,
  evidence/license gates, 14-category safety, 12-state bounded Agent, 10 typed tools, operational API,
  PRO/ADR/WCG paths, reports, release manifest, and thin authenticated WellnessBox UI/API.
- Proxy KPI: `7/7` passed. Real research completion: `false`.
- Release manifest: 13/13 files valid.
- Verification: 29 interim tests, ruff, service QA, encoding/route audit, TypeScript, ESLint,
  production build, desktop/mobile browser snapshots, console 0, role APIs unauthenticated 401.
- Independent code review Critical findings were fixed and covered by added regression tests.
- Full legacy pytest remains red from pre-existing missing ignored `artifacts/reports/**` inputs and
  existing CGM geometry baseline drift; the TIPS interim test selection is green.
- `npm audit --omit=dev`: 2 moderate advisories remain in Next.js's bundled PostCSS; critical/high
  advisories are 0. The audit's forced fix incorrectly proposes a Next.js 9 downgrade, so it was rejected.
- Upgraded Next.js/React and direct production dependencies; service QA, typecheck, lint, and production
  build pass. Keep the feature flag off until the external research, legal, and certification gates pass.
- The older strict effect-training `NO-GO` below remains unchanged and applies to the legacy learned
  effect-model promotion path. This proxy override did not promote that model into runtime.

## Current loop

- Chosen stage: `P3/P4`
- Chosen task: `one deliberately narrow effect-model training rerun targeting the authorized residual family only`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
  - `case_count = 480`

## What changed

- No new training artifact was created in this loop.
- Updated only the handoff docs to record why the requested effect-training loop must not proceed:
  - `PROGRESS.md`
  - `NEXT_STEPS.md`
  - `SESSION_HANDOFF.md`

## Why this loop was chosen

- The user explicitly requested one bounded effect-training loop.
- But the loop included a hard precondition:
  - run only if `training_readiness_gate_v2` is `GO`
- The latest gate remains:
  - `authorized_now = false`
  - `decision = no_go_keep_training_blocked`
  - `first_blocking_criterion = dominant_replay_residual_explained_tightly_enough`
- So the correct bounded action was to stop and document the block rather than run unauthorized training.

## Result in this loop

- Training did not run.
- The following requested artifacts were intentionally not created because the gate is `NO-GO`:
  - `artifacts/models/effect_model_v4_authorized_candidate.json`
  - `artifacts/reports/effect_model_v4_authorized_candidate_compare_v1.json`
  - `artifacts/reports/effect_model_v4_authorized_candidate_compare_v1.md`
- The blocking chain remains:
  - replay residual is still not gate-ready
  - chosen synthetic-validity item is still risky
  - reopened `cgm` blocker is not closed or proven non-blocking
  - no safe narrow rerun target is available now
- The single next non-training loop remains:
  - `replay_only_attribution_for_threshold_duration_sensitive_mid_margin_large_drop`

## Interpretation

- Running training here would violate the current strict gate.
- The correct next step is still:
  - do not train
  - do not create a new candidate artifact
  - take the `large_drop` replay-only loop first

## Behavior boundary

- No runtime recommendation change
- No safety logic change
- No optimizer change
- No inference API change
- No training run
- No learned-artifact promotion into runtime
- No chat/OpenAI change
- Frozen-eval comparability preserved

## Deterministic baseline status

Official frozen eval baseline remains unchanged:

- `recommendation_coverage_pct = 100.0`
- `efficacy_improvement_pp = 9.90291632090153`
- `next_action_accuracy_pct = 99.21875`
- `explanation_quality_accuracy_pct = 99.47916666666667`
- `safety_reference_accuracy_pct = 99.86979166666667`
- `adverse_event_count_yearly = 0.0`
- `sensor_genetic_integration_rate_pct = 90.40247678018576`

## Validation

- `git diff --check -- PROGRESS.md NEXT_STEPS.md SESSION_HANDOFF.md`
