# OP-045/046 candidate preservation and structured reasons

## Scope

- OP-045: preserve every goal-eligible catalog candidate before safety filtering, every excluded candidate with bounded exclusion categories, every post-safety candidate, and the final selected keys.
- OP-046: return recommendation reasons as separate input signals, score terms, and exact rule/reference/claim IDs.
- Required evidence stage: `IMPLEMENTED` for both requirements.
- Repository boundary: `C:\dev\wellnessbox-rnd` only. Do not change the WellnessBox service or claim deployment or production operation.

## Reuse and invariants

- Reuse `RecommendationRequest`, `NormalizedIntake`, the ingredient catalog, `SafetySummary`, `score_candidate`, `select_recommendations`, goal-prior records, and `RecommendationResponse`.
- Do not add a parallel filter, scorer, optimizer, or response route.
- The preserved pre-safety set must equal the disjoint union of the post-safety and excluded sets. Selected keys must be a subset of the post-safety set.
- Exclusion categories are limited to the existing safety summary, explicit user avoidance, and current-regimen overlap. The trace must not invent a per-ingredient safety-rule relationship that the current safety contract does not expose.
- A global block remains separate from ingredient-level exclusion. It can prevent selection while leaving individually eligible post-safety candidates visible.
- Structured reason totals must reconcile catalog priority plus every visible `CandidateScoreBreakdown` term. Evidence IDs come only from validated goal-prior records and applied score signals.

## Implementation tasks

1. Add strict candidate-pool trace models with unique-key, partition, and selected-subset validation.
2. Build the trace from the same catalog and blocked-key sets used by the existing optimizer, including early blocked responses and cleared-review paths.
3. Add strict structured-reason models for normalized input signals, score terms, optimizer/scoring rule IDs, reference IDs, claim IDs, and limitations.
4. Build reasons from the existing score breakdown, applied signals, and goal-prior registry. Preserve the existing human-readable rationale for compatibility.
5. Rebuild the structured reason after a learned tie-breaker so `learned_effect_bonus`, total, and `OPT-LEARNED-001` remain consistent.
6. Add focused invariants, API/OpenAPI, safety exclusion, global block, learned-rerank, and fail-closed schema tests plus deterministic smoke evidence.
7. Run focused tests, exact Original plan evidence selection, full Ruff, full pytest baseline comparison, stored/fresh artifact checks, official frozen eval, manifest audit, completion-report check, deterministic smoke reruns, diff checks, and independent review.
8. Claim OP-045 and OP-046 only at `IMPLEMENTED`; update status and handoff documents, stage only loop-owned files, commit, push, and wait for CI.
