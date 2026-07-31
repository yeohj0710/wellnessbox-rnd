# AGENTS.md

## Purpose

This file is the short execution contract for Codex/AI agents.
Do not treat this file as the full project context document.
The canonical long-form context is:

- `docs/context/master_context.md`

## Source hierarchy

When there is any ambiguity, prefer sources in this order:

1. `docs/context/master_context.md`
2. `PROGRESS.md`
3. `NEXT_STEPS.md`
4. `SESSION_HANDOFF.md`
5. `README.md` (commands/layout only)

## PDF rule

- Do NOT globally parse, OCR, or summarize `docs/context/original_plan.pdf` during routine loops.
- Treat `docs/context/master_context.md` as the text reconstruction and operational context.
- Consult `original_plan.pdf` only when:
  - KPI definitions/measurement semantics are in doubt
  - `master_context.md` is ambiguous or contradictory
  - a page-level audit is explicitly needed
- When consulting the PDF, inspect only the relevant pages first, especially p.25~26.

## KPI measurement rules (read before touching any metric)

Binding source: original plan p.25~26. Machine-readable contract:
`data/original_plan/contracts/kpi_measurement_contract_v1.json`.
Rationale and approved internal-only routes: `docs/original_plan/KPI_COMPLIANCE_STRATEGY.md`.

- All seven indicators are measured at a KOLAS-accredited lab (TTA, 와이즈스톤 등).
  Internal numbers are pre-checks. Tag them `measurement_environment: internal_pre_check_only`
  and never report them as final performance.
- KPI-1/3/4/5 compare the engine against a human answer key. Seal the answer key
  BEFORE running the engine (`scripts/seal_reference_standard.py`). Never derive an
  answer key from engine output — the score becomes self-referential.
- Synthetic data is allowed as training input. It is NOT allowed as a KPI answer key
  (KPI-1/3/4/5) or as the measured values for KPI-2 and KPI-6.
- KPI-2 needs pre/post PRO from at least 100 real people. KPI-6 needs 12 months of real
  operation. Neither can be satisfied internally.
- Distribution similarity of generated data does not substitute for a real effect claim.
- Year-2 outputs are by pharmacist candidates, not licensed pharmacists. Follow
  `docs/original_plan/REVIEWER_QUALIFICATION_POLICY.md`.

## Hard constraints

- Optimize for the KPI set defined in original plan p.25~26.
- Implementation details from the original plan are non-binding.
- Single-founder + single-computer assumption only.
- Runtime safety must remain deterministic and rule / structured-knowledge based.
- Deterministic fallback must remain when learned output is missing, unsafe, or suspicious.
- Keep system-owned action space only.
- Do not introduce human-review / manual-review / handoff actions.
- Prefer simple, testable, reproducible systems over ambitious architecture.

## Repo boundary

Work only inside:

- `C:/dev/wellnessbox-rnd`

Do not read or modify these unless explicitly required by a future scope change:

- `wellnessbox/`
- `docs/03_integration/`
- `docs/00_discovery/`
- `docs/00_migration/`
- `docs/legacy_from_wellnessbox/`

## Preferred technical direction

- Safety: deterministic structured rules
- Recommendation: constrained candidate generation + lightweight scoring
- Optimization: explicit solver / constrained search
- Closed-loop: explicit state machine
- Chat: bounded RAG + verifier
- Data: synthetic / rule-generated / frozen-eval driven
- Evaluation and reproducibility come before UI polish

## Loop policy

- Complete exactly one bounded R&D loop per run.
- Choose the highest-priority task from `NEXT_STEPS.md` that can produce measurable output in one loop.
- If a task is too broad, choose the smallest measurable subtask.
- Preserve frozen-eval comparability.
- Avoid broad refactors, framework churn, and unnecessary new abstractions.
- Prefer editing existing modules/tests/docs over introducing new systems.

## Before stopping, always do all of the following

1. Run relevant validation commands.
2. Update `PROGRESS.md`.
3. Update `NEXT_STEPS.md`.
4. Update `SESSION_HANDOFF.md`.

## Standard validation expectation

Use the narrowest relevant checks, and run broader guardrail checks when core behavior changed.
Typical commands include:

- `python -m ruff check .`
- `python -m pytest`
- dataset validation / summary scripts
- eval scripts
- training or simulation scripts when the loop changes those areas

## Required handoff format

Your final response must contain:

- Chosen stage
- Chosen task
- Primary dataset path and case_count
- Files changed
- Key code/data/training/simulation changes
- Validation commands and results
- Official frozen eval metric deltas
- Replay/slice deltas if applicable
- Biggest remaining bottlenecks 5
- Recommended next loop 3
