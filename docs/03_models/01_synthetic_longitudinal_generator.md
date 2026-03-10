# Synthetic Longitudinal Generator v1

## Scope

This loop introduces the first reproducible synthetic data pipeline for the
closed-loop roadmap.

- stage: `P0`
- task: `synthetic longitudinal cohort generator`
- source-of-truth alignment:
  - synthetic-first development is explicitly allowed in
    [master_context.md](/c:/dev/wellnessbox-rnd/docs/context/master_context.md)
  - the closed-loop states mirror the baseline questionnaire, safety review,
    recommendation ready, intake active, follow-up due, re-evaluation,
    adjust-plan, and stop-or-escalate flow described in the source-of-truth

## Artifacts

- dataset: [synthetic_longitudinal_v1.jsonl](/c:/dev/wellnessbox-rnd/data/synthetic/synthetic_longitudinal_v1.jsonl)
- summary JSON: [synthetic_longitudinal_v1_summary.json](/c:/dev/wellnessbox-rnd/artifacts/reports/synthetic_longitudinal_v1_summary.json)
- summary Markdown: [synthetic_longitudinal_v1_summary.md](/c:/dev/wellnessbox-rnd/artifacts/reports/synthetic_longitudinal_v1_summary.md)

## Record schema

Each record contains:

- deterministic `user_id` and `record_id`
- `RecommendationRequest` payload
- `follow_up_step` and `day_index`
- `expected_effect_proxy`
- `adherence_proxy`
- baseline recommendations snapshot
- labels:
  - `next_action`
  - `reason_code`
  - `safety_status`
  - `risk_tier`
  - `adverse_event`
  - `closed_loop_state`

## Generator design

- archetype-driven request synthesis
- fixed RNG seed support
- longitudinal step progression over 3 checkpoints: day 0, day 14, day 28
- deterministic follow-up updates:
  - `start_plan` users carry forward current supplements from recommendations
  - `collect_more_input` users fill one missing symptom first, then current
    supplement context later
- labels are derived by running the existing deterministic baseline, not by
  bypassing it

## Guardrails

- safety rules stay in front of the synthetic labels
- deterministic baseline remains the labeler and comparison target
- no external data and no actual user data are used
