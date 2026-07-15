# SESSION_HANDOFF

## 2026-07-15 log separation and execution-identity handoff

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-025 and OP-026
- Primary dataset path and case count: `data/original_plan/evidence/op025_op026_log_separation_identity_smoke_v1.json`; `2` actual FastAPI route cases
- Main files: `src/wellnessbox_rnd/interim/store.py` (schema `6`), new `src/wellnessbox_rnd/interim/behavior_log.py` and `src/wellnessbox_rnd/interim/execution_identity.py`, `src/wellnessbox_rnd/interim/data_lake.py`, `apps/inference_api/routes/interim.py`, smoke runner, manifest, generated reports, CI workflow, and focused tests
- Current result: two disjoint log stores (`execution_events` research vocabulary versus `behavior_events` user-behavior vocabulary, both CHECK-bounded); every persistent recommendation execution stores model ID, engine version, code commit with resolution source, four hashed runtime dataset identities, and one canonical config SHA-256 that identical runs share; the authenticated trace returns the structured identity.
- Consent boundary: behavior events require the profile's active survey persistent-storage consent and fail closed with `403`; unknown profiles return `404`; replays deduplicate; changed payloads return `409`.
- Separation boundary: research event types are rejected by the behavior endpoint and behavior names are rejected by the research event route, both with `422`; `GET /v1/interim/log-classes` reports zero cross-contamination.
- Local artifact note: the ignored local interim database carried sticky `content_changed` quarantines from the audited OP-023/024 artifact update; after checksum verification the three internal reference sources were explicitly reviewed and un-quarantined with a recorded metadata review note. Adapter license quarantines remain. Fresh checkouts and CI never see this state. A committed review workflow is still missing and stays on the bottleneck list.
- Evidence stage: `IMPLEMENTED`. OP-025 and OP-026 remain partial because `OPERATED` requires production persistence and postcondition re-query. No service code, R&D deployment, or production two-process integration changed in this loop.
- Validation: focused CI-equivalent selection `176 passed`; new smoke deterministic; manifest audit passes with `28` valid claims and zero issues; completion-report stale check passes; Ruff passes. Full suite is `586 passed`, `78 failed`, matching the known `74` missing report-artifact and `4` CGM geometry groups.
- Frozen evaluation: `256` cases; zero delta for all seven metrics against the pre-loop report. Replay/slice delta: not applicable.
- Biggest bottlenecks: deployed R&D URL; durable production R&D storage; authenticated service-to-R&D round trip; production re-query evidence; committed quarantine review workflow.
- Next three loops: OP-027/028 idempotency plus deletion/correction audit handling; OP-029/030 replay API plus service UI; OP-033/034 safety-engine group D start.

## 2026-07-15 knowledge evidence-lineage handoff

- Chosen stage: `original plan / Data Lake evidence lineage`
- Chosen tasks: OP-023 and OP-024
- Primary dataset path and case count: `data/original_plan/evidence/op023_op024_knowledge_lineage_smoke_v1.json`; `1` actual FastAPI route case
- Main files: schema and registries under `src/wellnessbox_rnd/interim/`, reference ingestion and runtime knowledge models, three raw references, two canonical knowledge artifacts, recommendation route, smoke runner, manifest, generated reports, CI workflow, and focused tests
- Current result: SQLite schema `5`; sources `3`; parsed passages `5`; normalized claims `5`; rules `5`; claim-rule links `5`; execution lineage rows `2` for `safety_rule` and `recommendation_decision`
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
- Current result: current schema `5`; profile versions `[1, 2]`; consent snapshots `2`; denied raw profile rows `0`; recommendation, safety, optimization, conversation, and follow-up events share one response execution ID.
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
