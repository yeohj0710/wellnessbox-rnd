# Optional manual backlog runner for deferred local commands.
# Keep items in the same order as PENDING_USER_ACTIONS.md.
# Each active item should be preceded by comments for:
# - purpose
# - expected artifacts
# - success condition
# - failure hint
# - cautions

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Optional Step 1 purpose:
# - rerun the enriched OpenAI live smoke only if chat-path diagnosis is still needed
# - confirm either provider=openai_responses_api or live_failure is populated
# Expected artifacts:
# - artifacts/reports/chat_openai_adapter_smoke_live_v1.json
# - artifacts/reports/chat_openai_adapter_smoke_live_v1.md
# Success condition:
# - the JSON report exists
# - if fallback occurs, live_failure is populated with exception details
# - if live succeeds, provider=openai_responses_api
# Failure hint:
# - if this shell still cannot see the key, rerun from the original env context that produced attempted_live_call=true
# - if attempted_live_call=true but live_failure is still null, confirm the rerun used the latest repo code path
# Cautions:
# - optional chat-only adapter path
# - do not wire this into recommendation/safety runtime
# - keep evidence-grounded verifier path enabled
# - keep this below synthetic/PRO/parser/cgm KPI-path work
if (-not $env:OPENAI_API_KEY) {
    Write-Error "OPENAI_API_KEY is not visible in this shell. Rerun from the shell/session that actually inherited the key."
}
python scripts/run_chat_openai_adapter_smoke.py --allow-live-api --report-json artifacts/reports/chat_openai_adapter_smoke_live_v1.json --report-md artifacts/reports/chat_openai_adapter_smoke_live_v1.md
