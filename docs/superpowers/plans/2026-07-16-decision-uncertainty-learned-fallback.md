# OP-047/048 decision uncertainty and learned fallback plan

## Scope

- Reuse `NormalizedIntake.missing_information`, the existing candidate scores, safety result, optional learned reranker, and `RecommendationResponse`.
- Add a deterministic, versioned uncertainty report whose numeric components reconcile exactly to one bounded total. The score describes unresolved recommendation-input and ranking uncertainty, not clinical probability or diagnosis.
- Convert each existing missing-information item into an explicit additional-input condition with a fixed importance weight. Preserve the original code, question, reason, and importance.
- Add an observable learned-reranking decision that distinguishes not requested, ineligible, applied, missing path/file, invalid artifact, suspicious artifact, and runtime-error fallback.
- Validate learned artifacts before prediction: expected model/target identity, non-empty unique feature names, matching feature/weight dimensions, finite numeric values, and positive finite regularization.
- Build learned candidates off the untouched deterministic list and return the original list if artifact loading, validation, or prediction fails. Never return a partially reranked list.

## Fail-closed invariants

- Uncertainty component points must be nonnegative, unique by code, and sum to the returned total after the documented cap.
- Additional-input condition points must match their declared importance and must appear in the uncertainty components.
- The uncertainty band must match the numeric thresholds and the response must state the score scope.
- A non-applied learned decision cannot leave `OPT-LEARNED-001`, a learned bonus, or learned engine mode in the response.
- An applied learned decision must correspond to a validated artifact and rebuilt structured reasons.
- Malformed JSON, extra artifact fields, duplicate features, dimension mismatch, non-finite values, wrong model/target identity, and prediction exceptions fall back to the byte-equivalent deterministic selection.

## Evidence and verification

- Add focused schema, API, uncertainty, artifact-validation, and optimizer fallback tests.
- Add a deterministic OP-047/048 smoke with normal, missing-input, close-ranking, missing-file, malformed, suspicious, runtime-error, and valid-artifact cases.
- Add the smoke and focused tests to `Original plan evidence` CI.
- Claim OP-047 and OP-048 only at `IMPLEMENTED`; do not claim deployment, production learned-model use, or service integration.
- Run focused tests, exact CI selection, full Ruff, frozen eval comparison, full pytest baseline classification, independent review, audit, completion-report check, deterministic smoke reruns, explicit staging, push, and CI observation.
