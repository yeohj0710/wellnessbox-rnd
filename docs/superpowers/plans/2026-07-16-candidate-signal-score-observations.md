# OP-043/044 Candidate Signal Scoring Implementation Plan

## Scope

- OP-043: make normalized symptoms, user-supplied laboratory ranges, lifestyle facts, and dietary patterns affect candidate scores.
- OP-044: convert consent-authorized wearable, CGM, and genetic observations into bounded numeric score terms.
- Required evidence stage: `IMPLEMENTED` for both requirements.
- Repository boundary: `C:\dev\wellnessbox-rnd` only. Do not change or claim a WellnessBox service deployment.
- Reuse the existing `RecommendationRequest`, `NormalizedIntake`, `NormalizedSensorGeneticSnapshot`, ingredient catalog, goal-prior registry, `score_candidate`, optimizer, and `CandidateScoreBreakdown`.

## Evidence and interpretation boundaries

- Candidate points are deterministic ordering terms, not diagnoses, treatment targets, efficacy probabilities, or dose advice.
- Laboratory rules use the reference range supplied with the observation. They do not invent universal laboratory cutoffs.
- Adult wearable sleep scoring may use the official seven-hour short-sleep boundary, only for sleep-oriented candidate ordering.
- CGM time-in-range scoring requires explicit diabetes context, a blood-glucose goal, a nonpregnant adult profile, and a verified 70–180 mg/dL range. The value is not used to change medication, diagnose diabetes, or set an individualized treatment target.
- Genetic tags use only the adjustment directions already listed in `master_context.md`; unknown tags add zero points.
- Every applied numeric term must expose the observed value/tag, rule/version, bounded points, and reference/claim IDs.

## Implementation tasks

1. Add raw evidence notes for the master-context candidate-signal policy, CDC adult sleep duration, ADA CGM time-in-range, and NIH ODS vegetarian/vegan B12 risk. Regenerate parsed references and knowledge artifacts.
2. Add a strict, versioned candidate-signal scoring registry. Validate unique rule IDs, known catalog ingredients/goals, bounded points, supported operators, exact reference/claim ownership, limitation text, input allowlists, and domain/ingredient scope. Execute only the validated registry embedded in the runtime artifact.
3. Extend the existing recommendation request with the existing normalized sensor/genetic snapshot contract. Require an explicit consent object for snapshot inputs, apply recommendation-consent gates per source, and include only authorized values in normalized hashes and persisted request projections.
4. Extend `CandidateScoreBreakdown` with separate laboratory, dietary, wearable, CGM, and genetic terms plus structured applied-signal details. Preserve existing symptom/lifestyle components and total-score arithmetic.
5. Update `score_candidate` to evaluate the versioned rules after the current goal prior and safety filter. Unknown, absent, out-of-scope, or unauthorized observations contribute zero.
6. Add focused schema, consent, hashing, rule-validation, scoring, API, replay, and runtime regression tests. Include negative tests for forged claims, unrelated references, duplicate rules, invalid bounds/operators, and unauthorized sensor values.
7. Add a deterministic OP-043/044 smoke artifact covering symptom, lab, lifestyle, diet, wearable, CGM, genetic, consent denial, and score-sum reconciliation.
8. Run focused tests, exact Original plan evidence selection, full Ruff, full pytest baseline comparison, stored/fresh artifact checks, official 256-case frozen eval, manifest audit, completion-report check, deterministic smoke reruns, diff checks, and independent review.
9. Claim OP-043 and OP-044 only at `IMPLEMENTED`. Update progress/handoff/next steps, stage only loop-owned files, commit, push, and wait for Original plan evidence CI.

## Non-goals

- No learned-model training or promotion.
- No supplement dose recommendation from sensor, laboratory, or genetic values.
- No production WellnessBox integration or deployment claim.
- No change to the known absent-report or CGM-geometry baseline failures.
