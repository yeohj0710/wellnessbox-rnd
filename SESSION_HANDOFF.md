# SESSION_HANDOFF

Older handoff entries are archived in `docs/archive/SESSION_HANDOFF-archive-1.md`.

## 2026-07-21 corrected PRO service contract and lineage handoff

- Chosen stage and tasks: `original plan / pre-post outcome quantification and PRO`; OP-057 and OP-058.
- Primary dataset/evidence: frozen eval `256` cases; one synthetic authenticated service correction over two strict PRO events. Canonical evidence SHA-256 `d1f72dd209650097184f97b406573758f642ed331877f0e47a2c2f5786a60dbe`; combined source SHA-256 `bf05dd7ba5ca72d405463fb254387990168216e6473be6fc52702ab2801dfdbf`.
- Source identity: R&D `c8c07679aa1a311a3831859c8c82f35aacc855c3`; WellnessBox `b0a7af921ddce08fb51323f4f6f10ad666f9a372`.
- Changed paths: R&D correction service, interim endpoint, metric exports, focused tests, deterministic smoke/workflow, manifest/evidence/report/governance tests; service authenticated route helper, `/api/tips/pro/effects`, QA/client scripts, and package command. No new database or duplicate event store was added.
- Result: user-contract raw score `8 -> 7`; immediate recalculation true; mutation audit recorded; recommendation selected ingredient keys retained in the response lineage. Precondition failures commit no correction.
- Honest stage: OP-057 and OP-058 are `IMPLEMENTED` and PARTIAL. The actual UI still uses local PRO calculation, and recommendation events do not persist `plan_id`; production operation and real-world outcomes are not proven.
- Validation: focused `48 passed`; workflow-equivalent `428 passed`; full suite `809 passed`, `77 failed` in the known `73 + 4` groups; frozen 256 evaluation has seven zero deltas and unchanged weakest slices; full Ruff and service build/lint/typecheck/encoding checks PASS; independent review Critical `0`, Important `0`, Minor `0`.
- Publication: R&D is published through `dc0febec22a717e85fc6ca34c91436cfc1d2636e`; service commit `b0a7af921ddce08fb51323f4f6f10ad666f9a372`; Original plan evidence run `29801874180` succeeded.
- Biggest remaining bottlenecks: actual UI integration for OP-057; persisted recommendation `plan_id` for OP-058; required operation evidence for OP-021~030, OP-040, OP-053, and OP-058; qualifying external labels for OP-039; missing trusted report archive plus four CGM geometry failures.
- Protected user files remain untouched. Existing `etc/` files remain untracked and were not used as canonical evidence.
- Next three loops: complete OP-057/058 integration; OP-059/060; OP-061/062.

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
