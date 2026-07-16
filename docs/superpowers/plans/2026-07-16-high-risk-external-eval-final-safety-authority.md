# OP-039/040 External Safety Evaluation and Final Authority Plan

> **Execution rule:** Complete this bounded loop without claiming external validation or production operation from local, mocked, synthetic, or CI-only evidence.

**Goal:** Prevent internal frozen data from being presented as independent high-risk validation, and prove that the existing WellnessBox service client preserves the R&D safety engine's final block decision across a real two-process boundary.

**Architecture:** Reuse `wellnessbox-rnd` `/v1/recommend` and the existing WellnessBox `lib/server/wb-rnd-client.ts`. Add a strict external-evaluation intake contract in R&D and a fail-closed response boundary in the service. A deterministic smoke runner starts the R&D FastAPI process and invokes the service TypeScript client over HTTP. This is integration evidence only; production deployment and external clinical attestation remain separate human gates.

**Evidence boundary:**

- OP-039 required stage: `EXTERNAL`. This loop may implement and test the evaluator, but must leave OP-039 unclaimed until an independent reviewer supplies a frozen dataset and matching attestation.
- OP-040 required stage: `OPERATED`. A repeatable local/CI two-process result may claim `INTEGRATED`, but must not claim `OPERATED` without production deployment, production environment configuration, and production-path evidence.

## Task 1: Add the external high-risk evaluation contract

**Files:**

- Create: `src/wellnessbox_rnd/evals/external_high_risk_safety.py`
- Create: `scripts/run_external_high_risk_safety_eval.py`
- Create: `tests/test_external_high_risk_safety_eval.py`
- Create: `docs/original_plan/OP039_EXTERNAL_HIGH_RISK_EVAL_CONTRACT.md`

**Requirements:**

1. Accept a frozen JSONL dataset and a detached JSON attestation whose dataset SHA-256 values match.
2. Require independent-review provenance, high-risk labels, and an expected final disposition of `blocked` for every evaluated case.
3. Reject repository synthetic/internal datasets, placeholder attestations, hash mismatches, duplicate case IDs, and malformed recommendation requests before evaluation.
4. Count a hard false negative whenever an expected-block case returns a non-blocked status, a non-blocked safety summary, or any recommendation.
5. Write a deterministic report with dataset and attestation hashes, case count, false-negative case IDs, and pass/fail status.
6. Use temporary fixtures only in tests. Do not check in a fabricated external dataset or attestation and do not register an OP-039 completion claim.

## Task 2: Make the existing service client fail closed

**Files:**

- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-client.ts`
- Modify: `C:/dev/wellnessbox/lib/server/wb-rnd-interim-route.ts`
- Create: `C:/dev/wellnessbox/lib/server/wb-rnd-interim-safety-authority.ts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-recommend-preview.cts`
- Modify: `C:/dev/wellnessbox/scripts/qa/check-rnd-profile-adapter.cts`
- Create: `C:/dev/wellnessbox/scripts/qa/check-rnd-final-safety-authority.cts`
- Modify: `C:/dev/wellnessbox/package.json`
- Modify: `C:/dev/wellnessbox/.github/workflows/encoding-guard.yml`

**Requirements:**

1. Validate the minimum `/v1/recommend` response contract before returning an upstream result.
2. Preserve a valid R&D blocked response without changing status, safety status, reasons, rule references, or recommendation list.
3. Reject inconsistent responses, including blocked responses with recommendations or disagreement between top-level and safety status.
4. Convert missing configuration, timeout, network, HTTP, decode, and contract failures into a service-owned blocked response with zero recommendations.
5. Return explicit authority metadata distinguishing `rnd_final` from `service_fail_closed`.
6. Keep the client disabled in production under the existing preview gate. Do not add production environment values or deploy.
7. Apply the same final-authority invariant to the actual `POST /api/tips` handler and its existing `/v1/interim/recommendations` upstream path.
8. Run safety before loading the interim recommendation model so urgent blockers still return a valid blocked response when no model is registered.

## Task 3: Prove the real two-process boundary

**Files:**

- Create: `scripts/run_wellnessbox_final_safety_authority_smoke.py`
- Create: `data/original_plan/evidence/op040_final_safety_authority_integration_smoke_v1.json`
- Modify: `.github/workflows/original-plan-evidence.yml`
- Add focused R&D tests if the smoke orchestration needs unit coverage.

**Requirements:**

1. Start the R&D FastAPI app on an ephemeral localhost port.
2. Wait for `/health`, create the required interim profile, then run the existing WellnessBox `POST /api/tips` handler against `/v1/interim/recommendations` with an urgent high-risk request.
3. Require the expected emergency rule, `safety_authority.mode=rnd_final`, top-level `BLOCKED`, `STOP_AND_ESCALATE`, and zero recommendations.
4. Stop the child process reliably and emit a deterministic artifact.
5. Run the same smoke in `Original plan evidence` after checking out and installing the WellnessBox service dependencies.

## Task 4: Register only the proven stage

**Files:**

- Modify: `data/original_plan/requirements_manifest_v1.json`
- Modify: `docs/original_plan/COMPLETION_STATUS.md`
- Modify: `PROGRESS.md`
- Modify: `NEXT_STEPS.md`
- Modify: `SESSION_HANDOFF.md`

**Requirements:**

1. Leave OP-039 without a claimed stage and document the exact external dataset/attestation replacement contract.
2. Claim at most `INTEGRATED` for OP-040 after the real two-process smoke succeeds.
3. State that production operation remains unproved and list deployment/environment evidence still required.

## Task 5: Review, verify, and publish the bounded loop

1. Run focused tests and service QA first.
2. Run the two-process smoke twice and confirm identical normalized output.
3. Run the R&D CI-equivalent suite, Ruff, manifest audit, completion report check, runtime artifact validation, frozen eval regression comparison, and both repositories' diff checks.
4. Request an independent code review and resolve all Critical and Important findings.
5. Stage only loop-owned files. Never use `git add .` and never stage the two protected untracked roadmap files.
6. Commit and push the WellnessBox service changes first; wait for its CI.
7. Commit and push the R&D changes second; wait for `Original plan evidence`.
8. Do not deploy. Record OP-039 external validation and OP-040 production operation as explicit remaining gates.
