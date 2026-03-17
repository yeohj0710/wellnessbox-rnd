# PENDING_USER_ACTIONS

This file is the running backlog for commands or checks that should stay outside the current Codex loop.

Working rules:

- Read this file before starting future loops.
- Add manual items here instead of stopping to ask the user to run something immediately.
- Keep optional chat work below runtime/core KPI-path work.
- Move completed or obsolete items to the final section instead of silently deleting history.

## Must do

- None currently.

## Optional

### Optional item 1: If chat-path diagnosis is still needed later, rerun the latest OpenAI live smoke

- Type: `chat adapter smoke test`
- Current priority:
  - optional only
  - lower than replay-only evidence, synthetic validity, weakest-slice residual proof, PRO, and `cgm` work
- Why run it:
  - current audit still says `rerun_needed_now = false`
  - latest compare/reject state still says baseline remains held
  - the only remaining reason to rerun is to capture richer provider-failure detail in-artifact
- Command:
  - `python scripts/run_chat_openai_adapter_smoke.py --allow-live-api --report-json artifacts/reports/chat_openai_adapter_smoke_live_v1.json --report-md artifacts/reports/chat_openai_adapter_smoke_live_v1.md`
- Success condition:
  - either `provider = openai_responses_api`
  - or fallback still occurs but `live_failure` is populated with `exception_class` and `failure_stage`

## Required env vars

- `OPENAI_API_KEY`
- `WELLNESSBOX_CHAT_OPENAI_MODEL` optional, default `gpt-5-mini`
- `WELLNESSBOX_CHAT_OPENAI_BASE_URL` optional, default `https://api.openai.com/v1`
- `WELLNESSBOX_CHAT_OPENAI_TIMEOUT_SECONDS` optional, default `20.0`

## Expected artifacts

- `artifacts/reports/chat_openai_adapter_smoke_live_v1.json`
- `artifacts/reports/chat_openai_adapter_smoke_live_v1.md`

## Blocked-by-user items

- The optional enriched live smoke rerun still requires the shell/session where `OPENAI_API_KEY` is visible.

## Done / obsolete items

- `2026-03-16`: previous local replay, dataset, retrieval, verifier, parser, eval-helper, and API contract loops completed without deferred user commands.
- `2026-03-16`: prompt 13 catch-up loop materialized `chat_openai_adapter_smoke_live_v1` artifacts with `fallback_reason = missing_api_key`, so the remaining manual item became a rerun with a real key, not a first-time build.
- `2026-03-16`: live OpenAI smoke rerun completed with `attempted_live_call = true`, `verification_passed = true`, `provider = deterministic_template_fallback`, `fallback_reason = openai_call_failed`, and `live_failure = null`; the remaining item is now only a richer diagnostic rerun, not a missing first rerun.
