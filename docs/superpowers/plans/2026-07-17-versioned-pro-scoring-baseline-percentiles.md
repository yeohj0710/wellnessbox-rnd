# OP-051/052 versioned PRO scoring and baseline-percentile plan

> Extend the existing R&D PRO scoring path. Do not create a second metrics package or change the WellnessBox service implementation in this R&D-owned loop.

**Goal:** Fix PSQI, ISI, and PSS-10 raw-score algorithms to one versioned contract, then calculate health-oriented Z scores and percentiles only from a declared baseline cohort distribution.

**Evidence stages:** OP-051 `IMPLEMENTED`; OP-052 `IMPLEMENTED`. This loop does not claim service integration, production data, clinical interpretation, or instrument licensing beyond the recorded source metadata.

## Task 1: Lock the instrument contract with failing tests

- Add a versioned JSON contract beside the existing R&D data contracts.
- Represent PSQI input as seven already-derived component scores from 0 through 3; do not reproduce or reimplement the licensed 19-item component derivation.
- Represent ISI as seven item scores from 0 through 4.
- Represent PSS-10 as ten item scores from 0 through 4 and reverse one-based positions 4, 5, 7, and 8 before summing.
- Reject booleans, floats, missing/extra items, out-of-range values, unknown instruments, contract drift, and unexpected fields instead of clamping.

## Task 2: Extend the existing `metrics/pro_scoring.py` path

- Load and fail-closed validate the committed contract.
- Return original item scores, scored item values, reversed positions, raw total, valid range, orientation, scoring version, and source IDs.
- Keep the existing generic domain PRO path unchanged for backward compatibility.

## Task 3: Fix baseline-distribution standardization

- Require every distribution input to use the versioned baseline-observation wrapper, then build one distribution from observations of the same instrument and scoring version.
- Use sample mean and sample standard deviation (`ddof=1`), require at least two observations and nonzero finite spread, and bind the sorted source scores to a SHA-256 digest.
- Define `health_z = (baseline_mean - raw_problem_score) / baseline_sample_std` because all three instruments are lower-is-better problem scores.
- Define health percentile as `100 * Φ(health_z)` and return the distribution identity with every transformed score.
- Fix six-decimal half-even rounding and the statistics, Z-score, and percentile operation order in the versioned contract.
- Reject cross-instrument, cross-version, non-baseline, nonfinite, or forged distribution inputs.

## Task 4: Add deterministic evidence

- Cover canonical raw-score examples, boundary scores, PSS reversal, strict invalid inputs, cohort order independence, exact sample statistics, monotonic health percentile, and schema forgery.
- Add a deterministic OP-051/052 smoke report with the complete calculator and data-class dependency bundle hash and no production claims.
- Run the smoke twice and require byte identity.

## Task 5: Close governance and publish

- Add the new paths to Original plan evidence CI and register only `IMPLEMENTED` evidence in the manifest.
- Regenerate and check the completion report, run focused and CI-equivalent tests, full Ruff, frozen eval, and the known full-suite baseline.
- Obtain independent review with zero Critical/Important findings.
- Stage only loop-owned files, push `main`, and require Original plan evidence to pass.
