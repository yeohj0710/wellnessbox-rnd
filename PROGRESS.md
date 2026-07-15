# PROGRESS

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
