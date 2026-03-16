# Manual backlog runner for deferred local commands.
# Keep items in the same order as PENDING_USER_ACTIONS.md.
# Each active item should be preceded by comments for:
# - purpose
# - expected artifacts
# - success condition
# - failure hint
# - cautions

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Step 1 purpose:
# - rerun one live OpenAI chat adapter smoke once the local API key is available
# - overwrite the current blocked report that ended with fallback_reason=missing_api_key
# Expected artifacts:
# - artifacts/reports/chat_openai_adapter_smoke_live_v1.json
# - artifacts/reports/chat_openai_adapter_smoke_live_v1.md
# Success condition:
# - the JSON report exists and shows attempted_live_call=true
# - verification_passed=true
# Failure hint:
# - if this step stops before artifact creation, confirm OPENAI_API_KEY is set
# - if the command falls back, inspect fallback_reason in the JSON report
# Cautions:
# - chat-only adapter path; do not wire this into recommendation/safety runtime
# - keep evidence-grounded verifier path enabled
# - requires OPENAI_API_KEY in the environment
if (-not $env:OPENAI_API_KEY) {
    Write-Error "OPENAI_API_KEY is not set. Set the env var first, then rerun scripts/manual_backlog.ps1."
}
python scripts/run_chat_openai_adapter_smoke.py --allow-live-api --report-json artifacts/reports/chat_openai_adapter_smoke_live_v1.json --report-md artifacts/reports/chat_openai_adapter_smoke_live_v1.md
