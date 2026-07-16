# SESSION_HANDOFF

## 2026-07-17 versioned PRO scoring and baseline-percentile handoff

- Chosen stage: `original plan / pre-post outcome quantification and PRO`
- Chosen tasks: OP-051 and OP-052
- Primary evidence: `data/original_plan/evidence/op051_op052_versioned_pro_scoring_smoke_v1.json`; deterministic SHA-256 `17f554025cae2a3410f07b3cd81d27dee7a41b2e1dcd31e370c74a8d8d377bd3`; source commit `fd7e4a3d1d6edb630d6c25cdb0fde11129d98975`; source bundle SHA-256 `7edc4cee9cd2a6dbd8d74be8fc10417d0959e27ddc03fb350218ce143e8a60bf`
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

## 2026-07-15 log separation and execution-identity handoff

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-025 and OP-026
- Primary dataset path and case count: `data/original_plan/evidence/op025_op026_log_separation_identity_smoke_v1.json`; `2` actual FastAPI route cases
- Main files: `src/wellnessbox_rnd/interim/store.py` (schema `8`), new `src/wellnessbox_rnd/interim/behavior_log.py` and `src/wellnessbox_rnd/interim/execution_identity.py`, `src/wellnessbox_rnd/interim/data_lake.py`, `apps/inference_api/routes/interim.py`, smoke runner, manifest, generated reports, CI workflow, and focused tests
- Current result: two disjoint log stores (`execution_events` research vocabulary versus `behavior_events` user-behavior vocabulary, both CHECK-bounded); every persistent recommendation execution stores model ID, engine version, code commit with resolution source, four hashed runtime dataset identities, and one canonical config SHA-256 that identical runs share; the authenticated trace returns the structured identity.
- Consent boundary: behavior events require the profile's active survey persistent-storage consent and fail closed with `403`; unknown profiles return `404`; replays deduplicate; changed payloads return `409`.
- Separation boundary: research event types are rejected by the behavior endpoint and behavior names are rejected by the research event route, both with `422`; `GET /v1/interim/log-classes` reports zero cross-contamination.
- Local artifact note: the ignored local interim database carried sticky `content_changed` quarantines from the audited OP-023/024 artifact update; after checksum verification the three internal reference sources were explicitly reviewed and un-quarantined with a recorded metadata review note. Adapter license quarantines remain. Fresh checkouts and CI never see this state. A committed review workflow is still missing and stays on the bottleneck list.
- Evidence stage: `IMPLEMENTED`. OP-025 and OP-026 remain partial because `OPERATED` requires production persistence and postcondition re-query. No service code, R&D deployment, or production two-process integration changed in this loop.
- Validation: focused CI-equivalent selection `176 passed`; new smoke deterministic; manifest audit passes with `28` valid claims and zero issues; completion-report stale check passes; Ruff passes. Full suite is `586 passed`, `78 failed`, matching the known `74` missing report-artifact and `4` CGM geometry groups.
- Frozen evaluation: `256` cases; zero delta for all seven metrics against the pre-loop report. Replay/slice delta: not applicable.
- Biggest bottlenecks: deployed R&D URL; durable production R&D storage; authenticated service-to-R&D round trip; production re-query evidence; committed quarantine review workflow.
- Next three loops: OP-027/028 idempotency plus deletion/correction audit handling; OP-029/030 replay API plus service UI; OP-033/034 safety-engine group D start.
- Publication: commit `12591d4` is on `origin/main`; Original plan evidence run `29422080597` PASS.

## 2026-07-15 knowledge evidence-lineage handoff

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-023 and OP-024
- Primary dataset path and case count: `data/original_plan/evidence/op023_op024_knowledge_lineage_smoke_v1.json`; `1` actual FastAPI route case
- Main files: schema and registries under `src/wellnessbox_rnd/interim/`, reference ingestion and runtime knowledge models, three raw references, two canonical knowledge artifacts, recommendation route, smoke runner, manifest, generated reports, CI workflow, and focused tests
- Current result: SQLite schema `8`; sources `3`; parsed passages `5`; normalized claims `5`; rules `5`; claim-rule links `5`; execution lineage rows `2` for `safety_rule` and `recommendation_decision`; one claim and output can retain multiple linked rule rows
- Source identity: `source_uri` identifies the actual parsed raw document and `upstream_reference_uri` identifies its upstream note. The warfarin/glucosamine chain preserves lines `13..33`, license `APPROVED_INTERNAL`, local artifact effective date `2026-03-10T00:00:00Z`, null retirement date, and raw-content checksum.
- Consent boundary: derived-result lineage is absent when any used source denies persistent storage. Source registry and normalized knowledge remain non-user reference data.
- Change-control boundary: source checksum changes quarantine the source, and identical re-synchronization no longer clears the quarantine automatically.
- Evidence stage: `IMPLEMENTED`. OP-023 and OP-024 remain partial because `OPERATED` requires production persistence and postcondition re-query. No service code, R&D deployment, or production two-process integration changed in this loop.
- Validation: focused CI-equivalent selection `159 passed`; both lineage smokes pass; manifest audit passes with `26` valid claims and `72` checked evidence references; completion-report stale check passes; Ruff passes. Full suite is `569 passed`, `78 failed`, matching the known `74` missing report-artifact and `4` CGM geometry groups.
- Frozen evaluation: `256` cases; zero delta for all seven metrics; weakest overall category and every metric-specific weakest category are unchanged. Data Lake replay/slice delta: not applicable.
- Biggest bottlenecks: deployed R&D URL; durable production R&D storage; authenticated service-to-R&D round trip; production re-query evidence; source-corpus breadth and upstream supplement-file encoding quality.
- Next three loops: OP-025/026 log and execution identity separation; OP-027/028 idempotency and correction/deletion audit behavior; OP-029/030 replay API and service UI.
- Publication: commits `2ea5e40` and `194db51` are on `origin/main`; Original plan evidence run `29419358491` PASS. The interim recommendation API test now skips explicitly when the ignored local retrained package is absent from a fresh checkout; local behavior and expected values are unchanged.

## 2026-07-15 Data Lake profile and execution-lineage handoff

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-021 and OP-022
- Primary dataset path and case count: `data/original_plan/evidence/op021_op022_data_lake_lineage_smoke_v1.json`; `3` local runtime cases
- R&D files: `src/wellnessbox_rnd/interim/store.py`, `src/wellnessbox_rnd/interim/data_lake.py`, recommendation and interim API routes, recommendation schemas and orchestration, smoke runner, contracts, manifest, reports, and focused tests
- Service files: profile adapter contract, client type, profile adapter, preview payload builder, and adapter QA
- Current result: current schema `8`; profile versions `[1, 2]`; consent snapshots `2`; denied raw profile rows `0`; recommendation, safety, optimization, conversation, and follow-up events share one response execution ID.
- Consent correction: delayed events use the profile's explicit active consent pointer and store the authorizing `consent_snapshot_id`. Reusing an older immutable denial snapshot moves the pointer back to denial, so `거부 → 허용 → 재거부` blocks writes to an older execution.
- Provenance correction: a replay with the same event key but a different source or payload raises `IdempotencyConflictError`.
- Test isolation correction: all recommendation API tests use a temporary interim database. The reviewer observed that earlier test runs populated the default artifact database; those existing rows remain untouched.
- Evidence stage: `IMPLEMENTED`. OP-021 and OP-022 remain partial because `OPERATED` requires production persistence and postcondition re-query. No R&D deployment or production two-process integration was performed.
- Validation: focused Data Lake/API suites pass; runtime smoke passes; manifest audit passes with `24` valid claims; generated counts are complete `22`, partial `2`, pending `95`, external `1`; R&D Ruff and service QA/TypeScript/encoding/lint/build pass. The full R&D suite has `563` passes and `78` known failures: `74` missing ignored report artifacts and `4` CGM geometry assertions.
- Frozen evaluation: `256` cases and zero delta for recommendation accuracy, efficacy MAE, next-action accuracy, explanation completeness, safety-reference accuracy, adverse-event count, and sensor/genetic processing rate. Replay/slice delta: not applicable.
- Biggest bottlenecks: deployed R&D URL, durable production R&D storage, internal authentication, service environment binding, and production E2E re-query evidence.
- Next three loops: OP-023/024 lineage metadata; OP-025/026 log and execution identity separation; OP-027/028 idempotency and correction/deletion audit behavior.

## 2026-07-15 WellnessBox profile-adapter integration handoff

- Chosen stage: `original plan / personal health inputs`
- Chosen task: OP-019
- Primary dataset path and case count: `data/contracts/wellnessbox_profile_adapter_v1.json`; `1` representative profile containing all `12` service profile properties plus `10` shared boundary cases, `15` R&D contract tests, and `16` service adapter and POST-route checks
- Current requirement count: `120`; valid claims: `22`

Files changed:

- R&D schema and contract: `src/wellnessbox_rnd/schemas/recommendation.py`, `data/contracts/wellnessbox_profile_adapter_v1.json`, `tests/test_wellnessbox_profile_adapter_contract.py`
- Service adapter and route: `wellnessbox/lib/server/wb-rnd-profile-adapter.ts`, `wellnessbox/lib/server/wb-rnd-client.ts`, `wellnessbox/lib/server/wb-rnd-recommend-preview-payload.ts`, `wellnessbox/lib/server/wb-rnd-recommend-preview-route.ts`
- Service contract QA: `wellnessbox/contracts/wb-rnd/profile-adapter-v1.json`, `wellnessbox/scripts/qa/check-rnd-profile-adapter.cts`, service package script and encoding workflow
- R&D evidence: manifest, completion ledger, generated reports, audit/report scripts, original-plan workflow, governance tests, dedicated implementation plan, and handoff documents

Key changes:

- Added a strict runtime adapter for the current `types/chat.UserProfile`. It rejects unknown source properties, invalid values, missing age/sex/goals, absent survey recommendation consent, and unsupported goal aliases with structured field paths.
- Aligned the Zod and Pydantic source limits. Both boundaries now test the same Unicode code-point medication lengths, numeric types, blank text, and list counts. The R&D source trace rejects string, boolean, and fractional ages while accepting integral numeric values such as `42.0`, matching JavaScript number semantics.
- Preserved every current source property under `source_profile.profile` with schema version `wellnessbox.chat.UserProfile.v1`. The operational request maps all compatible health fields; name and caffeine sensitivity remain in the exact trace, while the combined pregnancy-or-breastfeeding flag is mapped conservatively to the existing pregnancy safety flag and also retained verbatim.
- Connected profile-shaped POST bodies to the existing internal recommendation-preview route and preserved the existing raw R&D payload preview path. The same request is forwarded unchanged by `callWbRndRecommendPreview`. Malformed JSON returns `400`, while top-level `null`, arrays, and invalid profiles return structured `422` responses; none are replaced by the sample request.
- Added the strict source envelope to the R&D request and OpenAPI. The envelope is excluded from the normalized clinical-input hash so nonclinical source metadata cannot alter frozen-eval results.
- Registered OP-019 as `INTEGRATED`, not `OPERATED`. The audit now validates tracked implementation, tests, route evidence, and byte-identical contract snapshots in both repositories.
- Current generated status: complete `22`, partial `0`, pending `97`, external `1`, contradicted `0`.

Validation:

- service adapter and POST-route QA: PASS, `16` checks
- existing service preview QA: PASS, `4` checks
- service TypeScript, encoding audit, lint, and production build: PASS
- exact original-plan workflow selection: `114 passed`
- full Ruff and both repositories' `git diff --check`: PASS
- manifest evidence audit: PASS; `22` claims, `55` unique evidence files, source hash matched, zero issues
- generated completion-report stale check: PASS
- full suite: `549 passed`, `77 failed`; failures remain in the known `73` missing report-artifact and `4` CGM geometry groups
- frozen eval: `256` cases; all seven metrics match the previously recorded current values exactly
- independent final code review: zero Critical, Important, and Minor findings
- service commit `485da91`: Encoding Guard run `29414011315` PASS, including the profile-adapter QA
- R&D implementation commit `10ba2a7`: Original plan evidence run `29414033364` PASS, including a fresh checkout of the public service repository

Official frozen-eval metric deltas: recommendation coverage `0`, efficacy improvement `0`, next-action accuracy `0`, explanation-quality accuracy `0`, safety-reference accuracy `0`, yearly adverse-event count `0`, sensor/genetic integration rate `0`.

Replay/slice deltas: not applicable. This loop changed a cross-repository input adapter and did not produce a replay candidate.

Biggest remaining bottlenecks:

1. Versioned profile and consent snapshots are not persisted.
2. Conversation, recommendation, safety, optimization, and follow-up events lack one shared execution ID.
3. Source passages, claims, rules, and recommendation outputs lack a complete lineage chain.
4. Knowledge effective dates, expiration dates, source types, and licenses are incomplete.
5. No deployed R&D FastAPI process or production `WB_RND_*` configuration exists; the legacy suite also retains 77 known failures.

Recommended next loops:

1. OP-021 and OP-022 profile/consent persistence plus shared execution IDs.
2. OP-023 and OP-024 source-to-recommendation lineage plus knowledge validity metadata.
3. OP-025 and OP-026 log separation plus reproducible execution identity metadata.

Production status: `wellnessbox` and `wellnessbox-rnd` still do not run together in production. This loop adds and verifies the adapter contract only; it does not satisfy OP-101 through OP-105.

## 2026-07-15 unsupported-input rejection handoff

- Chosen stage: `original plan / personal health inputs`
- Chosen task: OP-020
- Primary dataset path and case count: `data/samples/api_recommend_consent_hash_request_v1.json`; `1` representative API request plus `18` focused contract cases
- Current requirement count: `120`; valid claims: `21`

Files changed:

- `src/wellnessbox_rnd/schemas/recommendation.py`
- `tests/test_unsupported_input_contracts.py`
- `docs/superpowers/plans/2026-07-15-op020-unsupported-input-rejection.md`
- manifest, generated completion reports, workflow, completion ledger, and handoff documents

Key changes:

- Added one strict base model for every `RecommendationRequest` input container. Unknown top-level or nested fields now fail with API 422 instead of being discarded.
- Limited structured laboratory units to the existing canonical unit set and explicit aliases. Unsupported units fail at both model and API boundaries.
- Added semantic signatures for duplicate medications, supplement products, and supplement ingredients. NFKC, case folding, whitespace normalization, exact ingredient aliases, and ingredient multiplicity participate in conflict detection.
- Preserved exact medication and supplement product duplicates for compatibility, while rejecting duplicate identities with different classification, dose, ingredient dose, or ingredient counts.
- Registered OP-020 as `INTEGRATED` because the actual FastAPI `/v1/recommend` route enforces the contract. OP-019 remains pending: `wellnessbox/types/chat.ts` and `lib/server/wb-rnd-client.ts` still have different profile shapes and no production adapter.
- Current generated status: complete `21`, partial `0`, pending `98`, external `1`, contradicted `0`.

Validation:

- focused OP-020 contracts: `18 passed`
- exact original-plan workflow selection: `99 passed`
- recommendation and safety core regressions: `206 passed`
- full Ruff: PASS
- manifest evidence audit: PASS; `21` claims, `47` unique evidence files, source hash matched, zero issues
- generated completion-report stale check: PASS
- independent code review: no Critical or Important issues after fixes
- full suite: `534 passed`, `77 failed`; failures remain in the known `73` missing report-artifact and `4` CGM geometry groups
- frozen eval: `256` cases; all seven metrics match the previously recorded current values exactly

Official frozen-eval metric deltas: all `0`.

Replay/slice deltas: not applicable. This loop changed request validation and did not produce a replay candidate.

Biggest remaining bottlenecks:

1. The current `wellnessbox` stored `UserProfile` has no lossless adapter to `RecommendationRequest`; OP-019 remains pending.
2. Versioned profile and consent snapshots are not persisted.
3. Conversation, recommendation, safety, optimization, and follow-up events lack one shared execution ID.
4. Source passages, claims, rules, and recommendation outputs lack a complete lineage chain with validity and license metadata.
5. No deployed R&D FastAPI process or production `WB_RND_*` configuration exists; the legacy suite also retains 77 known failures.

Recommended next loops:

1. OP-019 cross-repository `wellnessbox` profile adapter and dual-repository contract proof.
2. OP-021 and OP-022 profile/consent persistence plus shared execution IDs.
3. OP-023 and OP-024 source-to-recommendation lineage plus knowledge validity metadata.

## 2026-07-15 consent and deterministic input-hash handoff

- Chosen stage: `original plan / personal health inputs`
- Chosen tasks: OP-017 and OP-018
- Primary dataset path and case count: `data/samples/api_recommend_consent_hash_request_v1.json`; `1` representative API request plus `13` focused contract cases
- Current requirement count: `120`; valid claims: `20`

Files changed:

- `src/wellnessbox_rnd/schemas/recommendation.py`
- `src/wellnessbox_rnd/domain/intake.py`
- `apps/inference_api/routes/recommend.py`
- `data/samples/api_recommend_consent_hash_request_v1.json`
- `tests/test_consent_and_input_hash_contracts.py`
- `docs/superpowers/plans/2026-07-15-op017-op018-consent-input-hash.md`
- manifest, generated completion reports, workflow, completion ledger, and handoff documents

Key changes:

- Added separate recommendation-use and persistent-storage consent fields for survey, National Health Insurance Service, wearable, CGM, and genetic sources.
- A wholly omitted consent block retains legacy use behavior but never grants storage. In a supplied block, every omitted source is denied. Survey-use denial fails closed because the recommendation request requires survey-derived profile and goals.
- `normalize_request` combines declared availability with source consent. Existing downstream safety, efficacy, and recommendation code receives the consent-gated request rather than raw availability flags.
- Laboratory observations now identify their source. A denied-source observation is removed before missing-context, safety, feature, and recommendation computation. Tests vary denied NHIS values and prove identical snapshots, hashes, and recommendations.
- The normalized input snapshot excludes request IDs and sorts semantically unordered collections, including nested supplement ingredients. Compact sorted-key UTF-8 JSON produces a stable SHA-256; `0.0` and `-0.0` share one representation.
- The API OpenAPI example and representative JSON fixture exercise all five source scopes through the real recommendation endpoint.
- Current generated status: complete `20`, partial `0`, pending `99`, external `1`, contradicted `0`.

Validation:

- focused original-plan workflow contracts: `81 passed`
- recommendation and safety core regressions: `206 passed`
- full Ruff: PASS
- manifest evidence audit: PASS; `20` claims, `46` unique evidence files, source hash matched, zero issues
- generated completion-report stale check: PASS
- full suite: `516 passed`, `77 failed`; failures remain in the known `73` missing report-artifact and `4` CGM geometry groups
- frozen eval: `256` cases; all seven metrics match the previously recorded current values exactly

Official frozen-eval metric deltas: all `0`.

Replay/slice deltas: not applicable. This loop changed the input contract and did not produce a replay candidate.

Biggest remaining bottlenecks:

1. No lossless `wellnessbox` profile-to-R&D adapter has been proven across both repositories.
2. Unsupported or ambiguous service fields do not yet fail through a shared cross-repository contract.
3. Versioned profile and consent snapshots are not persisted.
4. Conversation, recommendation, safety, optimization, and follow-up events lack one shared execution ID.
5. No deployed R&D FastAPI process or production `WB_RND_*` configuration exists; the legacy suite also retains 77 known failures.

Recommended next loops:

1. OP-019 and OP-020 lossless service adapter plus ambiguous-input rejection.
2. OP-021 and OP-022 profile/consent persistence plus shared execution IDs.
3. OP-023 and OP-024 source-to-recommendation lineage plus knowledge validity metadata.

## 2026-07-15 diet, lifestyle, and laboratory input-contract handoff

- Chosen stage: `original plan / personal health inputs`
- Chosen tasks: OP-015 and OP-016
- Primary dataset path and case count: `data/samples/api_recommend_diet_lifestyle_lab_request_v1.json`; `1` representative API case with `2` timestamped laboratory observations plus focused validation and compatibility cases
- Current requirement count: `120`; valid claims: `18`

Files changed:

- `src/wellnessbox_rnd/schemas/recommendation.py`
- `src/wellnessbox_rnd/domain/intake.py`
- `src/wellnessbox_rnd/models/efficacy_model_v0.py`
- `src/wellnessbox_rnd/models/policy_model_v0.py`
- `apps/inference_api/routes/recommend.py`
- `data/samples/api_recommend_diet_lifestyle_lab_request_v1.json`
- `tests/test_diet_lifestyle_lab_input_contracts.py`
- manifest, generated completion reports, workflow, completion ledger, and handoff documents

Key changes:

- Allergy strings share one sorted lowercase-whitespace normalization path and retain a normalized list plus lookup set.
- Dietary patterns accept legacy strings or strict objects, deduplicate by normalized code, and preserve the richer display name when a duplicate structured record exists.
- Lifestyle input adds bounded `exercise_minutes_per_week` and `caffeine_mg_per_day` fields without changing existing defaults.
- Laboratory observations require code, finite non-boolean value, unit, at least one reference-range bound, and a timezone-aware measurement time. New exercise and caffeine fields also reject boolean coercion. Invalid ranges, naive times, and non-finite values fail validation.
- Normalization canonicalizes common laboratory units and ASCII/Unicode micro prefixes, converts timestamps to UTC, retains the full observation list, selects the latest value per code, and records low/within-range/high status. Conflicting records at the same normalized code and UTC time fail request validation and return API `422`.
- Allergy, diet, exercise, caffeine, laboratory code/unit/status features reach both existing learned-model feature dictionaries. Existing artifacts ignore unknown new feature names, preserving current replay behavior.
- Relevant glucose and lipid observations satisfy existing missing-context checks. Frozen requests without the new fields keep their previous outputs.
- Current generated status: complete `18`, partial `0`, pending `101`, external `1`, contradicted `0`.

Validation:

- focused original-plan workflow contracts: `68 passed`
- expanded core regressions: `311 passed`, `2 failed`; both failures are documented legacy cases, one missing ignored report and one CGM geometry assertion
- full Ruff: PASS
- manifest evidence audit: PASS; `18` claims, `44` unique evidence files, source hash matched, zero issues
- generated completion-report stale check: PASS
- full suite: `503 passed`, `77 failed`; failures remain in the known `73` missing report-artifact and `4` CGM geometry groups
- frozen eval: `256` cases; all seven metrics match the previously recorded current values exactly

Official frozen-eval metric deltas: all `0`.

Biggest remaining bottlenecks:

1. Consent scopes and deterministic normalized-input hashing are incomplete.
2. No lossless service profile adapter has been proven across both repositories.
3. Versioned profile/consent snapshots and shared execution IDs are not persisted.
4. No deployed R&D FastAPI runtime or production `WB_RND_*` configuration exists.
5. Missing ignored reports and stale CGM geometry keep the legacy full suite red.

Recommended next loops:

1. OP-017 and OP-018 consent scopes and deterministic normalized-input hashing.
2. OP-019 and OP-020 service adapter plus ambiguous-input rejection.
3. OP-021 and OP-022 profile/consent persistence and shared execution IDs.

## 2026-07-15 medication and supplement input-contract handoff

- Chosen stage: `original plan / personal health inputs`
- Chosen tasks: OP-013 and OP-014
- Primary dataset path and case count: `data/samples/api_recommend_structured_safety_block_request_v1.json`; `1` representative API case plus focused compatibility, aggregation, conversion, ambiguity, and feature-path cases
- Current requirement count: `120`; valid claims: `16`

Files changed:

- `src/wellnessbox_rnd/schemas/recommendation.py`
- `src/wellnessbox_rnd/domain/intake.py`
- `src/wellnessbox_rnd/safety/service.py`
- `src/wellnessbox_rnd/models/efficacy_model_v0.py`
- `src/wellnessbox_rnd/models/policy_model_v0.py`
- `apps/inference_api/routes/recommend.py`
- `data/samples/api_recommend_structured_safety_block_request_v1.json`
- `tests/test_medication_supplement_input_contracts.py`
- `tests/test_inference_api.py`
- manifest, generated completion reports, workflow, completion ledger, and handoff documents

Key changes:

- Medication records carry a structured classification plus a bounded numeric dose and explicit unit; legacy dose strings still validate through the same request field.
- Supplement records carry a product name, structured ingredients, ingredient-specific daily doses, and an optional product daily dose; legacy strings remain accepted.
- Normalization retains canonical structured records and lookup sets without dropping uncatalogued terms used by the runtime knowledge DB.
- Deterministic safety sums ingredient daily doses across products and converts `g`, `mg`, `mcg`, and vitamin D `IU` where the conversion is defined.
- A product-level dose is assigned only when the input declares exactly one ingredient through an exact catalog alias. Fuzzy and compound text cannot assign a product dose to one ingredient. Supplying both the legacy product dose and structured product daily dose is rejected as ambiguous.
- Existing medication-interaction rules and learned-model feature builders consume canonical values rather than Pydantic object representations.
- Current generated status: complete `16`, partial `0`, pending `103`, external `1`, contradicted `0`.

Validation:

- focused original-plan workflow contracts: `58 passed`
- broader requirement, knowledge, safety, and recommendation regressions: `258 passed`
- full Ruff: PASS
- manifest evidence audit: PASS; `16` claims, `42` unique evidence files, source hash matched, zero issues
- generated completion-report stale check: PASS
- full suite: `493 passed`, `77 failed`; failures remain in the known `73` missing report-artifact and `4` CGM geometry groups

Official frozen-eval metric deltas: none.

Biggest remaining bottlenecks:

1. Dietary pattern and laboratory observation contracts are still incomplete.
2. Consent scopes and deterministic normalized-input hashing are still incomplete.
3. No lossless service profile adapter has been proven across both repositories.
4. No deployed R&D FastAPI runtime or production `WB_RND_*` configuration exists.
5. Missing ignored reports and stale CGM geometry keep the legacy full suite red.

Recommended next loops:

1. OP-015 and OP-016 dietary/lifestyle normalization and laboratory observations.
2. OP-017 and OP-018 consent scopes and deterministic normalized-input hashing.
3. OP-019 and OP-020 service adapter plus ambiguous-input rejection.

## 2026-07-15 structured health-input contract handoff

- Chosen stage: `original plan / personal health inputs`
- Chosen tasks: OP-011 and OP-012
- Primary fixture: `data/samples/api_recommend_structured_health_input_request_v1.json`
- Current requirement count: `120`; valid claims: `14`

Files changed:

- `src/wellnessbox_rnd/schemas/recommendation.py`
- `src/wellnessbox_rnd/domain/intake.py`
- `src/wellnessbox_rnd/models/efficacy_model_v0.py`
- `src/wellnessbox_rnd/models/policy_model_v0.py`
- `src/wellnessbox_rnd/synthetic/rich_longitudinal_v2.py`
- `apps/inference_api/routes/recommend.py`
- `data/samples/api_recommend_structured_health_input_request_v1.json`
- `tests/test_health_input_contracts.py`
- manifest, generated completion reports, workflow, completion ledger, and handoff documents

Key changes:

- `UserProfile` now carries optional bounded `height_cm` and `weight_kg` alongside the existing age, biological sex, and pregnancy state.
- Conditions, symptoms, and urgent-risk flags retain the existing field names and legacy string compatibility while also accepting strict structured objects.
- Normalized intake contains canonical detail records as well as code maps. It retains condition display name and status, symptom severity and duration, and urgent-signal presence and source without rereading the heterogeneous request.
- Resolved conditions and absent urgent signals do not become active safety codes, risk labels, model features, synthetic penalties, or learned-model guard reasons.
- Existing model feature paths consume canonical codes rather than Python object representations and omit resolved conditions.
- The structured urgent signal executes the existing safety rule and returns a blocked response with no recommendations.
- CI runs both the focused contract test and inference API regression test for this claim.

Current generated status:

- complete `14`
- partial `0`
- pending `105`
- external `1`
- contradicted `0`

Validation:

- original-plan, health-input, and inference API contracts: `42 passed`
- broader recommendation and safety regressions: `199 passed`
- downstream model and synthetic compatibility tests: `30 passed`
- full Ruff, manifest audit, and generated-report stale check: PASS
- full suite: `477 passed`, `77 failed`; failures remain in the known `73` missing report-artifact and `4` CGM geometry groups

Official frozen-eval metric deltas: none.

Recommended next loops:

1. OP-013 and OP-014 medication and supplement dose/unit contracts.
2. OP-015 and OP-016 dietary/lifestyle normalization and laboratory observations.
3. OP-017 and OP-018 consent scopes and deterministic normalized-input hashing.

## 2026-07-15 original plan completion-report handoff

- Chosen stage: `original plan / evidence governance`
- Chosen task: OP-010
- Primary dataset path and case count: `data/original_plan/requirements_manifest_v1.json`; `120` requirements, `12` claimed

Files changed:

- `src/wellnessbox_rnd/governance/original_plan_report.py`
- `scripts/build_original_plan_completion_report.py`
- `tests/test_original_plan_completion_report.py`
- `docs/original_plan/completion_status_v1.json`
- `docs/original_plan/COMPLETION_STATUS.md`
- workflow, manifest, completion ledger, and handoff documents

Key changes:

- The report builder consumes the validated manifest plus the real evidence audit and emits all 120 requirements.
- Statuses are complete, partial, pending, external, and contradicted; missing claims never become complete.
- Broken evidence downgrades a claim to contradicted, and a common source/manifest audit failure invalidates current completion claims.
- A canonical manifest SHA-256 binds each report to the exact manifest content that the audit checked; stale audit objects are rejected.
- `--check` compares normalized text content exactly so CI rejects stale committed reports across LF and CRLF checkouts.
- OP-010 is the twelfth valid claim. Current counts are complete `12`, partial `0`, pending `107`, external `1`, contradicted `0`.

Validation:

- manifest, audit, CLI, and completion-report tests: `25 passed`
- full Ruff: PASS
- normal generation and stale-output check: PASS
- full suite: `470 passed`, `77 failed`; all failures remain in the known `73` missing report-artifact and `4` CGM geometry groups

Official frozen-eval metric deltas: none.

Biggest remaining bottlenecks:

1. Structured biometric, symptom-severity, medication-dose, supplement-dose, laboratory, and consent contracts remain incomplete.
2. No deployed R&D FastAPI runtime or production `WB_RND_*` configuration exists.
3. The current audited report proves only `12/120` requirements complete; it does not claim the original plan is fully implemented.
4. Missing ignored reports and stale CGM geometry keep the full R&D suite red.

Recommended next loops:

1. OP-011 and OP-012 biometric profile and symptom-severity contracts.
2. OP-013 and OP-014 medication and supplement dose/unit contracts.
3. OP-015 and OP-016 dietary/lifestyle normalization and laboratory observations.

## 2026-07-15 original plan audit-command and CI handoff

- Chosen stage: `original plan / evidence governance`
- Chosen task: OP-009
- Primary dataset path and case count: `data/original_plan/requirements_manifest_v1.json`; `120` requirements, `11` claimed

Files changed:

- `scripts/audit_original_plan_requirements.py`
- `.github/workflows/original-plan-evidence.yml`
- `tests/test_original_plan_audit_cli.py`
- manifest, completion ledger, and handoff documents

Key changes:

- Developers and CI now run the same audit function through one command.
- The command emits machine-readable JSON and fails the process for any audit issue.
- CI uses Python 3.11 and runs the audit command, contract tests, and Ruff.
- OP-009 is claimed only with command, workflow, and CLI-test evidence.

Validation:

- manifest, audit, and CLI tests: `16 passed`
- full Ruff: PASS
- audit command: PASS; `120` requirements, `11` claims, `20` unique evidence files, zero issues, PDF hash match
- `git diff --check`: PASS
- GitHub Actions run `29402915435`: PASS after fixing checkout-relative test roots

Official frozen-eval metric deltas: none.

Biggest remaining bottlenecks:

1. No Korean completion report is generated from the audited manifest.
2. No deployed R&D FastAPI runtime or production `WB_RND_*` configuration exists.
3. Full profile, consent, product, order, pharmacy, and delivery contracts remain incomplete.
4. The service repository is not checked out in the standalone R&D CI job, so future cross-repository claims will need a second-checkout or signed evidence bundle.
5. Missing ignored reports and stale CGM geometry keep the full R&D suite red.

Recommended next loops:

1. OP-010 generated completion report.
2. OP-011 and OP-012 biometric profile and symptom-severity contracts.
3. OP-013 and OP-014 medication and supplement dose/unit contracts.

## 2026-07-15 original plan evidence-audit handoff

- Chosen stage: `original plan / evidence governance`
- Chosen task: OP-008
- Primary dataset path and case count: `data/original_plan/requirements_manifest_v1.json`; `120` requirements, `10` claimed

Files changed:

- `src/wellnessbox_rnd/governance/original_plan_audit.py`
- `src/wellnessbox_rnd/governance/__init__.py`
- `tests/test_original_plan_audit.py`
- requirement manifest, completion ledger, and handoff documents

Key changes:

- Completion evidence is resolved against explicit `wellnessbox-rnd` and `wellnessbox` roots.
- Evidence outside the declared owner repository, outside the repository root, absent from disk, or absent from `git ls-files` fails the audit.
- The stored original-plan hash is recomputed from `docs/context/original_plan.pdf`.
- OP-008 is the tenth claimed requirement; no partial feature was promoted.

Validation:

- manifest and audit tests: `13 passed`
- full Ruff: PASS
- `git diff --check`: PASS
- live manifest audit: PASS; `120` requirements, `10` claims, `17` unique evidence files, zero issues, PDF hash match

Official frozen-eval metric deltas: none.

Biggest remaining bottlenecks:

1. The audit is not yet exposed as a repository command or CI gate.
2. The completion report is not generated from the audited manifest.
3. No deployed R&D FastAPI runtime or production `WB_RND_*` configuration exists.
4. Full profile, consent, product, order, pharmacy, and delivery contracts remain incomplete.
5. Missing ignored reports and stale CGM geometry keep the full R&D suite red.

Recommended next loops:

1. OP-009 deterministic audit command and CI gate.
2. OP-010 generated Korean completion report.
3. OP-011 and OP-012 biometric profile and symptom-severity contracts.

## 2026-07-15 original plan evidence-manifest handoff

- Chosen stage: `original plan / evidence governance`
- Chosen task: OP-006 and OP-007
- Primary dataset path and case count: `data/original_plan/requirements_manifest_v1.json`; `120` requirements across `12` groups

Files changed:

- `data/original_plan/requirements_manifest_v1.json`
- `src/wellnessbox_rnd/schemas/original_plan_manifest.py`
- `src/wellnessbox_rnd/schemas/__init__.py`
- `tests/test_original_plan_manifest.py`
- `docs/plans/2026-07-15-original-plan-completion-program.md`
- `PROGRESS.md`, `NEXT_STEPS.md`, `SESSION_HANDOFF.md`

Key changes:

- Every OP-001 through OP-120 requirement now resolves to one record with source pages, repository owners, required stage, current claim, and evidence fields.
- Completion wording is restricted to `IMPLEMENTED`, `INTEGRATED`, `OPERATED`, and `EXTERNAL`.
- Stage-specific evidence is mandatory, and unknown manifest fields are rejected.
- Only nine requirements currently carry an evidence claim. The other 111 remain unclaimed.
- No model, training dataset, runtime recommendation, order path, or production deployment changed.

Validation:

- manifest tests plus recommendation API tests: `17 passed`
- focused Ruff: PASS
- full pytest: `529` collected, `452 passed`, `77 failed`; failure set unchanged from the existing 73 missing-report and four CGM baseline failures
- original PDF SHA-256 in manifest: `31291e6f93977fa2d5d083d0161743c49debef25caf12dccf6edc7fa1c2197d4`

Official frozen-eval metric deltas: none. Replay and slice metrics were not changed.

Biggest remaining bottlenecks:

1. Manifest evidence references are not yet checked against actual files, hashes, or runtime state.
2. No deployed R&D FastAPI runtime or production `WB_RND_*` configuration exists.
3. Full profile, medication, supplement, laboratory, and consent contracts remain incomplete.
4. Actual product catalog, stock, order, pharmacy, dispensing, and delivery feedback remain disconnected.
5. Missing ignored reports and stale CGM geometry keep the full R&D suite red.

Recommended next loops:

1. OP-008 evidence-path, hash, ownership, and claim audit.
2. OP-009 deterministic audit command plus pytest and CI gate.
3. OP-010 generated requirement-completion report.

## 2026-07-15 original plan completion handoff

- Chosen stage: `original plan / safety input contract`
- Chosen task: OP-031 allergy exclusion and OP-032 urgent-risk blocking
- Primary dataset path and case count: `data/rules/safety_rules.json`; `2` new deterministic API cases
- Repository topology: production does not run `C:/dev/wellnessbox` and `C:/dev/wellnessbox-rnd` together. `/tips` currently executes the service repository's local TypeScript lab runtime.

Files changed:

- R&D request, intake, rule, safety, and orchestration modules
- R&D inference API tests and safety rule data
- R&D Python 3.11-compatible sensor/genetic audit renderer
- service R&D preview request type and forwarding QA
- 120-step completion ledger and the three handoff documents

Key changes:

- `allergies` and `risk_flags` survive request parsing and normalization.
- Fish allergy excludes `omega3` before candidates are returned.
- Urgent symptom flags block all recommendations and select `trigger_safety_recheck`.
- Service preview forwarding preserves both fields.
- No data training, simulation regeneration, model promotion, order mutation, or deployment occurred.

Validation:

- `.venv-interim/Scripts/python.exe -m pytest tests/test_inference_api.py -q`: `10 passed`
- sensor/genetic audit tests: `2 passed`
- `.venv-interim/Scripts/python.exe -m ruff check .`: PASS
- `npm run qa:rnd:preview-route`: PASS
- `npx tsc --noEmit`: PASS
- `npm run audit:encoding`: PASS
- `git diff --check`: PASS in both repositories
- `npm run build`: PASS
- full R&D pytest: `445 passed, 77 failed, 68 warnings`; 73 missing ignored reports and 4 existing CGM geometry mismatches

Official frozen-eval metric deltas: none. Replay and slice metrics were not changed.

Biggest remaining bottlenecks:

1. No deployed R&D FastAPI runtime or production `WB_RND_*` configuration exists.
2. The original-plan ledger is not yet a machine-readable evidence manifest.
3. The full profile, medication, supplement, laboratory, and consent contracts remain incomplete.
4. Actual product catalog, stock, order, pharmacy, dispensing, and delivery feedback are not connected to the R&D runtime.
5. Missing ignored reports and stale CGM geometry keep the full R&D suite red.

Recommended next loops:

1. OP-006 and OP-007 machine-readable requirement/evidence manifest.
2. OP-008 through OP-010 evidence audit and generated completion report.
3. OP-011 through OP-020 structured profile/consent contract and cross-repository adapter.

## 2026-07-14 verified replay-input restoration handoff

- Stage: `P3/P4 replay evidence reproducibility`
- Dataset: `data/synthetic/synthetic_longitudinal_v4.jsonl`, `case_count = 480`
- Target: `threshold_duration_sensitive / mid_margin / large_drop`, expected `3` cases
- Human checkpoint sequence: `3/3 APPROVED`
- Added `scripts/restore_large_drop_replay_prerequisites.py` and fail-closed restore logic.
- Current state: blocked until the exact archive and SHA-256 manifest are available.
- After verified restore: rerun prerequisite audit, then run the three-case attribution.
- Training and runtime promotion remain prohibited.

## 2026-07-13 large-drop replay prerequisite handoff

- Chosen stage: `P3/P4 replay evidence reproducibility`
- Chosen task: make the next large-drop replay loop fail safely and explainably when evidence is absent
- Primary dataset: `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
- Case count: `480` records, `96` users; expected large-drop target `3` cases
- Audit: `artifacts/reports/large_drop_replay_prerequisite_audit_v1.json`
- Status: `blocked_missing_prerequisites`
- Required/present/missing: `8 / 3 / 5`
- Missing roles:
  - `held_candidate_effect_artifact`
  - `family_diagnostic`
  - `subgroup_diagnostic`
  - `mid_margin_diagnostic`
  - `prior_small_drop_attribution`
- Root cause: replay evidence required by code/tests lives under ignored `artifacts/` and is absent from this checkout.
- Narrow fix: added reusable preflight metadata and integrated it before all evidence loads.
- Rejected broad work: no `.gitignore` redesign, no regeneration training, no hardcoded reconstruction from docs.
- Boundary: no model creation, runtime promotion, deterministic safety change, or frozen-eval change.

Next loops:

1. restore and hash-verify the exact held candidate plus four prior reports;
2. run the three-case `large_drop` replay-only attribution;
3. run the single `medium_drop` replay-only attribution after large-drop closes or stalls cleanly.

## 2026-07-13 Cloud GPU bulk-inference handoff

- Chosen stage: `P3/P4 infrastructure validation`
- Chosen task: production-shaped CPU/CUDA bulk inference using the held `effect_model_v3`
- Primary dataset: `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
- Case count: `480` records, `96` users
- Entry point: `scripts/run_gpu_inference_testbed.py`
- Focused tests: `tests/test_gpu_inference_testbed.py`
- Operational guide: `docs/cloud_gpu_inference_testbed.md`
- Cloud result: `artifacts/gpu_testbed/cloud_kakao/`
- Successful job: `abe1d1b1-4e77-47a4-a4fe-9d1fcc96f1ef`
- Runtime: Python `3.11.15`, PyTorch `2.6.0+cu124`, Tesla T4
- Workload per device: `10,485,760` rows
- CPU: `0.315231663 s`, `33,263,663.619 rows/s`
- CUDA: `0.030179957 s`, `347,441,184.227 rows/s`
- Speedup: `10.4451x`; max absolute difference: `0.0`
- Total task cost: `138.171818083333 KRW` excluding VAT
- Total billed GPU time: `746.077 s`
- Closing balances: NAVER `5,299,999.835918042 KRW`; Kakao `9,999,498.635506416 KRW`
- Cleanup: instances `0`, public IPs `0`, instance-owned temporary disk released

Frozen-eval deltas: none. Official baseline values remain unchanged. No training or learned runtime promotion
occurred. Deterministic recommendation and structured safety paths remain unchanged.

Biggest remaining bottlenecks:

1. unresolved `non_cgm_continue_to_monitor_threshold_cross` replay residual;
2. synthetic-data circularity and generator contamination;
3. incomplete weakest-slice lineage closure;
4. unresolved `cgm` final-step geometry overlap;
5. strict training gate remains `NO-GO` because evidence quality, not infrastructure, is insufficient.

Recommended next loops:

1. `threshold_duration_sensitive / mid_margin / large_drop` replay-only attribution;
2. the single `mid_margin / medium_drop` replay-only attribution;
3. `generator_contamination` single-item synthetic-validity follow-up.

## 2026-07-10 TIPS interim handoff

- Run environment: `.venv-interim` (Python 3.12) with `.[dev,interim]`.
- Final pipeline: `python scripts/run_interim_pipeline.py all --verify`.
- Database: `artifacts/tips/interim/interim.sqlite3` (ignored local artifact).
- Retrain package: `artifacts/tips/interim/retrained` (ignored local artifact).
- Tracked evidence: `docs/tips/CURRENT_REPO_AUDIT.md` and `docs/tips/interim/*.md`.
- Service integration: `C:/dev/wellnessbox` under `/tips`, `/pharm/tips`, `/admin/tips` and their
  authenticated API routes. Existing user-modified service files were preserved.
- Truth boundary: proxy 7/7 passed; real pharmacist labels, real outcomes, 12-month ADR,
  production devices, external testing/certification and legal review remain external.
- Legacy effect-training gate remains `NO-GO`; no legacy candidate was promoted.

## Scope guardrails

- Work only inside `C:/dev/wellnessbox-rnd`
- Do not read or reference:
  - `wellnessbox/`
  - `docs/03_integration/`
  - `docs/00_discovery/`
  - `docs/00_migration/`
  - `docs/legacy_from_wellnessbox/`

## Source of truth

- `C:/dev/wellnessbox-rnd/docs/context/master_context.md`
- `C:/dev/wellnessbox-rnd/docs/context/original_plan.pdf` p.25~26 only for KPI ambiguity

## What this loop did

- Chosen stage: `P3/P4`
- Chosen task: `one deliberately narrow effect-model training rerun targeting the authorized residual family only`
- Primary dataset:
  - `C:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v4.jsonl`
  - `case_count = 480`

## Files changed

- `C:/dev/wellnessbox-rnd/PROGRESS.md`
- `C:/dev/wellnessbox-rnd/NEXT_STEPS.md`
- `C:/dev/wellnessbox-rnd/SESSION_HANDOFF.md`

## What changed technically

- No training code, model artifact, or compare artifact was created.
- This loop only checked the required precondition against:
  - `artifacts/reports/training_readiness_gate_v2.json`
  - current handoff docs
- The result is a documented stop:
  - effect-training must not proceed while the gate remains `NO-GO`

## Outcome this loop

- Precondition result:
  - `do_not_proceed_now = true`
- Why:
  - `training_readiness_gate_v2` is strict `NO-GO`
  - `first_blocking_criterion = dominant_replay_residual_explained_tightly_enough`
  - next required non-training loop is still
    `replay_only_attribution_for_threshold_duration_sensitive_mid_margin_large_drop`
- The requested training outputs were intentionally not created:
  - `artifacts/models/effect_model_v4_authorized_candidate.json`
  - `artifacts/reports/effect_model_v4_authorized_candidate_compare_v1.json`
  - `artifacts/reports/effect_model_v4_authorized_candidate_compare_v1.md`

## Why it matters

- This prevents an unauthorized training rerun.
- It keeps the repo aligned with the current gate contract:
  - no hidden training
  - no replay-only artifact promotion
  - no scope widening beyond the next required pre-training loop

## Key evidence snapshot

- gate evidence:
  - `authorized_now = false`
  - `decision = no_go_keep_training_blocked`
  - `first_blocking_criterion = dominant_replay_residual_explained_tightly_enough`
- operational consequence:
  - no effect-model rerun may proceed now
  - no `v4_authorized_candidate` artifact should exist yet
  - next non-training loop remains `large_drop` only

## Runtime boundary

- Recommendation runtime unchanged
- Safety runtime unchanged
- Optimizer runtime unchanged
- Inference API unchanged
- No training rerun
- No learned runtime promotion
- No chat/OpenAI widening
- Frozen eval remains comparable

## Interface contract for next loop

- Highest-ROI next loop:
  - replay-only attribution for `threshold_duration_sensitive / mid_margin / large_drop` only
  - keep the same deterministic baseline and replay artifacts
  - do not reopen the already-closed `small_drop` slice
- Second:
  - if loop 1 completes or stalls cleanly, take the single `mid_margin / medium_drop` case as its own bounded replay-only attribution
- Third:
  - take one narrow synthetic-validity follow-up on `generator_contamination` only
- Do not run training yet.
- Do not run `cgm outside-band final-step geometry` yet unless replay and synthetic-first blockers move enough to change the gate.

## Guard boundary

- runtime recommendation remains deterministic
- runtime safety remains deterministic and structured-rule first
- frozen eval remains comparable
- learned artifacts remain replay-only
- do not widen `dataset_f_effect_training_view_v1`
- do not reintroduce forbidden outcome-side or leakage-prone feature families
- optional chat/OpenAI stays below replay-first KPI-path work

## Deterministic baseline status

- current reference baseline remains:
  - `recommendation_coverage_pct = 100.0`
  - `efficacy_improvement_pp = 9.90291632090153`
  - `next_action_accuracy_pct = 99.21875`
  - `explanation_quality_accuracy_pct = 99.47916666666667`
  - `safety_reference_accuracy_pct = 99.86979166666667`
  - `adverse_event_count_yearly = 0.0`
  - `sensor_genetic_integration_rate_pct = 90.40247678018576`

## Validation snapshot

- `git diff --check -- PROGRESS.md NEXT_STEPS.md SESSION_HANDOFF.md`

## Optional chat-path note

- No optional chat/OpenAI work was touched in this loop.
