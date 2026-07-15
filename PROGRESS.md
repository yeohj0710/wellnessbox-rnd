# PROGRESS

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
