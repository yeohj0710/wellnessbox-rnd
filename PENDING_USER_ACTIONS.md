# PENDING_USER_ACTIONS

This file is the running backlog for any command or verification that cannot or should not be completed inside the current Codex loop.

Working rules:

- Read this file before starting future loops.
- Add new manual items here instead of stopping to ask the user to run something immediately.
- Keep command order aligned with `scripts/manual_backlog.ps1`.
- Move completed or obsolete items to the final section instead of deleting history silently.

## Must do

- None currently.

## Optional

### Optional item 1: Rerun OpenAI chat adapter live smoke after key injection

- Type: `chat adapter smoke test`
- Why run it:
  - replace the current blocked live-smoke report that ended with `fallback_reason = missing_api_key`
  - validate the real OpenAI adapter path once a real API key is available
  - confirm verifier-gated output still passes with a real response
- Command:
  - `python scripts/run_chat_openai_adapter_smoke.py --allow-live-api --report-json artifacts/reports/chat_openai_adapter_smoke_live_v1.json --report-md artifacts/reports/chat_openai_adapter_smoke_live_v1.md`
- Expected artifacts:
  - overwrite `artifacts/reports/chat_openai_adapter_smoke_live_v1.json`
  - overwrite `artifacts/reports/chat_openai_adapter_smoke_live_v1.md`
- Success condition:
  - report exists
  - `preflight.readiness_status = ready_for_live_smoke` or a completed live-call state
  - `attempted_live_call = true`
  - `verification_passed = true`
  - `provider = openai_responses_api` or safe fallback with explicit reason
- Failure hint:
  - if the command fails before response generation, first check `OPENAI_API_KEY`
  - if the report shows fallback after a live call, inspect `fallback_reason`

## Required env vars

- `OPENAI_API_KEY`
- `WELLNESSBOX_CHAT_OPENAI_MODEL` optional, default `gpt-5-mini`
- `WELLNESSBOX_CHAT_OPENAI_BASE_URL` optional, default `https://api.openai.com/v1`
- `WELLNESSBOX_CHAT_OPENAI_TIMEOUT_SECONDS` optional, default `20.0`

## Execution order

1. Set or confirm the required env vars.
2. Run `scripts/manual_backlog.ps1` once.
3. Confirm the expected artifact paths exist.
4. Feed the resulting artifact summary back into the next Codex loop.

## Training / eval / server smoke test

### Training

- None currently.

### Eval

- None currently.

### Server smoke test

- None currently.

### Chat adapter smoke test

- `python scripts/run_chat_openai_adapter_smoke.py --allow-live-api --report-json artifacts/reports/chat_openai_adapter_smoke_live_v1.json --report-md artifacts/reports/chat_openai_adapter_smoke_live_v1.md`

## Expected artifacts

- `artifacts/reports/chat_openai_adapter_smoke_live_v1.json`
- `artifacts/reports/chat_openai_adapter_smoke_live_v1.md`

## Blocked-by-user items

- Live OpenAI Responses API smoke is blocked until `OPENAI_API_KEY` is available in the local environment.

## Done / obsolete items

- `2026-03-16`: previous local replay, dataset, retrieval, and verifier prep loops completed without deferred user commands.
- `2026-03-16`: prompt 13 catch-up loop materialized `chat_openai_adapter_smoke_live_v1` artifacts with `fallback_reason = missing_api_key`, so the remaining manual item is now a rerun with a real key, not a first-time missing artifact build.
