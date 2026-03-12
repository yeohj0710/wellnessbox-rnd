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
