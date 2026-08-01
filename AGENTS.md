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

- The KOLAS-accredited lab test (TTA, 와이즈스톤 등) happens AFTER the research is
  finished. It is not a research-phase gate. Do not block or defer research work on it.
  During the research, measure internally and tag results
  `measurement_environment: research_phase_internal_measurement`.
- KPI-6 is satisfied by `scripts/build_adverse_event_report.py`; KPI-7 by
  `scripts/build_sensor_genetic_datasets.py`. Both are done — do not re-litigate them.
- KPI-2 is the only indicator still open. Its 100-person minimum comes from the funded
  plan, so changing the number in this repo changes nothing. See `open_decision` in the
  contract.
- KPI-1/3/4/5 compare the engine against a human-controlled answer key. Keep all 100
  measured cases. To minimize detailed human work, two different provider-family AI
  agents independently answer every case from a blind packet. A named person reviews
  every disagreement, every risk flag, and a deterministic sample of 5 agreements,
  then explicitly approves or rejects the remaining agreement batch. One sampled
  correction expands the sample to 20; two require every agreement. Record detailed
  reviews and batch approvals separately. The named person remains the final decision
  maker, and sealing must happen BEFORE the engine runs. Full per-case human review
  remains a valid fallback.
- KPI-3 starts with scenario-only placeholders. Before cross-AI review, import one
  blind AI response with `import-primary-ai-draft`; a second, different-family AI then
  reviews the same blind packet. Never count the placeholder as an AI answer.
- KPI-4 also requires the primary drafting AI and the dialogue model under test to be
  from different provider families. Record the dialogue model's provider family at
  sealing; same-family provenance is a sealing failure.
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
- Do not introduce human-review / manual-review / handoff actions into the runtime
  recommendation flow. Offline KPI answer-key governance above is the explicit
  exception required for measurement validity.
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
