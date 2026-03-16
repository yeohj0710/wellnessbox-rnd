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

### Optional item 1: If chat-path diagnosis is still needed, rerun the latest OpenAI live smoke and confirm `live_failure` is populated

- Type: `chat adapter smoke test`
- Why run it:
  - the latest live rerun already confirmed `api_key_present = true` and `attempted_live_call = true`
  - however, the resulting artifact still has `provider = deterministic_template_fallback`, `fallback_reason = openai_call_failed`, and `live_failure = null`
  - run it again only if you want the exact failure family captured in-artifact
- Command:
  - `python scripts/run_chat_openai_adapter_smoke.py --allow-live-api --report-json artifacts/reports/chat_openai_adapter_smoke_live_v1.json --report-md artifacts/reports/chat_openai_adapter_smoke_live_v1.md`
- Expected artifacts:
  - overwrite `artifacts/reports/chat_openai_adapter_smoke_live_v1.json`
  - overwrite `artifacts/reports/chat_openai_adapter_smoke_live_v1.md`
- Success condition:
  - report exists
  - if fallback still occurs, `live_failure` is populated with `exception_class` and `failure_stage`
  - if live succeeds, `provider = openai_responses_api`
- Failure hint:
  - if the rerun again shows `missing_api_key`, make sure the command is run from the shell/session that actually inherited the key
  - if `attempted_live_call = true` but `live_failure` is still null, confirm the rerun used the latest repo code path
- Priority note:
  - this remains optional and lower priority than the core KPI path
  - do not let this chat-only item outrank synthetic pre/post quality, `PRO scoring`, weakest-slice audit, or `cgm` score-geometry work

## Required env vars

- Reference for the current optional OpenAI rerun:
  - `OPENAI_API_KEY`
  - `WELLNESSBOX_CHAT_OPENAI_MODEL` optional, default `gpt-5-mini`
  - `WELLNESSBOX_CHAT_OPENAI_BASE_URL` optional, default `https://api.openai.com/v1`
  - `WELLNESSBOX_CHAT_OPENAI_TIMEOUT_SECONDS` optional, default `20.0`

## Execution order

1. Only if chat-path diagnosis is still needed, run the enriched OpenAI live smoke from the shell/session that actually has the key.
2. Confirm the smoke artifact now includes either `live_failure` details or `provider = openai_responses_api`.
3. Feed the resulting artifact back into the next Codex loop.

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

- The enriched live smoke rerun still requires the shell/session where `OPENAI_API_KEY` is actually visible.

## Done / obsolete items

- `2026-03-16`: previous local replay, dataset, retrieval, verifier, parser, eval-helper, and API contract loops completed without deferred user commands.
- `2026-03-16`: prompt 13 catch-up loop materialized `chat_openai_adapter_smoke_live_v1` artifacts with `fallback_reason = missing_api_key`, so the remaining manual item became a rerun with a real key, not a first-time build.
- `2026-03-16`: live OpenAI smoke rerun completed with `attempted_live_call = true`, `verification_passed = true`, `provider = deterministic_template_fallback`, `fallback_reason = openai_call_failed`, and `live_failure = null`; the remaining item is now only a richer diagnostic rerun, not a missing first rerun.
