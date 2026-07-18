# OP-053/054 PRO follow-up persistence and interpretation plan

> Extend the existing R&D `execution_events` and `metrics` paths. Do not add a second event store, change the WellnessBox service, or claim deployed operation.

**Goal:** Persist strict versioned PRO assessments at pre-intake, week 2, week 4, and discontinuation, then interpret observed score changes with adherence, missed-dose, and adverse-event context.

**Evidence stages:** OP-053 `IMPLEMENTED` only because local SQLite persistence is not production operation; OP-054 `IMPLEMENTED` at its required stage.

## Task 1: Lock the follow-up payload and interpretation contract with failing tests

- Reuse `PROInstrumentScoreV1` and `PROStandardizedScoreV1` from the existing metrics path.
- Define four timepoints: `pre_intake`, `week_2`, `week_4`, and `discontinuation`.
- Require the committed schema version, plan/assessment identity, timezone-aware observation time, declared `data_class`, exact schedule metadata, canonical instrument-score traces, and the matching standardized scores.
- Require a reconciled dose window after intake: planned count equals taken plus missed, and adherence rate equals taken divided by planned.
- Represent adverse-event context with bounded severity and relatedness values; do not add clinical free-text interpretation or causal claims.
- Reject model-instance mutations, extra fields, duplicate instruments/events, mismatched raw scores or baseline distributions, invalid schedule fields, missing adherence, and invalid discontinuation metadata.

## Task 2: Persist through the existing execution event ledger

- Canonicalize every `followup_evaluation` payload inside `ExecutionLedger.append_event`, not only at the API edge.
- Keep conversation events unchanged.
- Store all four PRO timepoints in the existing `execution_events` table under the recommendation execution ID.
- Enforce one ordered sequence per execution: pre-intake, week 2, week 4, then discontinuation. Preserve existing idempotency and current consent checks.
- Return the same trace and event IDs already used by the session replay and Data Lake paths.

## Task 3: Interpret observed change without inventing an adjusted effect

- Compare events from the same plan, instrument set, scoring versions, and baseline-distribution identities.
- Return per-instrument raw-problem-score change and health-Z change plus the mean health-Z change.
- Keep the numeric observation unchanged. Use adherence, missed doses, and adverse events only to set explicit interpretation status and reason codes.
- Apply priority: serious adverse event, any adverse event, adherence below 80%, missed doses, otherwise observed change interpretable.
- Label the 80% threshold as a conservative internal interpretation policy, not a clinical cutoff or efficacy claim.
- Always state `observed_association_not_causal`; do not claim treatment efficacy, clinical diagnosis, or a production safety action.

## Task 4: Add deterministic evidence and governance

- Prove all four events persist and replay in order in a temporary local SQLite database.
- Cover healthy adherence, missed doses, low adherence, non-serious adverse event, serious adverse event, sequence rejection, schema mutation, and cross-plan/distribution rejection.
- Add a deterministic OP-053/054 smoke report with source commit/hash and explicit local-only boundaries.
- Register only `IMPLEMENTED` evidence, update CI, audit, and generated completion counts.

## Task 5: Verify and publish

- Run focused tests, exact CI selection, full Ruff, frozen eval, and the known full-suite baseline.
- Obtain independent review with zero Critical/Important findings.
- Stage loop-owned files explicitly, push `main`, and require `Original plan evidence` to pass.
- Do not deploy the R&D app or modify the WellnessBox service in this loop.
