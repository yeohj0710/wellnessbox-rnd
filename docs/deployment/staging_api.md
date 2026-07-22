# Staging Inference API Deployment

This deployment path is intentionally narrow:

- deterministic baseline only
- no training
- no learned-artifact promotion into runtime
- no chat/OpenAI widening
- one small always-on CPU instance

## Runtime contract

- ASGI app: `apps.inference_api.main:app`
- Production startup command: `python scripts/start_inference_api.py`
- Default listen address: `0.0.0.0:8000`
- Provider-compatible port alias: `PORT`
- Provider-compatible worker alias: `WEB_CONCURRENCY`

## Required runtime files

The deployed image/server must include:

- `data/catalog/ingredients.json`
- `data/rules/safety_rules.json`
- `data/knowledge/runtime_knowledge_db_v1.json`

If `data/knowledge/runtime_knowledge_db_v1.json` is absent, runtime can rebuild from:

- `data/knowledge/reference_knowledge_base_v1.json`
- `data/rules/safety_rules.json`
- `data/catalog/ingredients.json`

## Environment variables

- `WB_RND_APP_ENV`
  - recommended value for staging: `staging`
- `WB_RND_APP_NAME`
  - default: `wellnessbox-rnd`
- `WB_RND_API_PREFIX`
  - default: `/v1`
- `WB_RND_HOST`
  - default: `0.0.0.0`
- `WB_RND_PORT`
  - default: `8000`
- `PORT`
  - optional provider alias for `WB_RND_PORT`
- `WB_RND_LOG_LEVEL`
  - default: `INFO`
- `WB_RND_WORKERS`
  - default: `1`
- `WEB_CONCURRENCY`
  - optional provider alias for `WB_RND_WORKERS`

## Enforced interim deployment contract

Set `WB_RND_DEPLOYMENT_CONTRACT_ENFORCED=1` for an interim staging or production
deployment. Startup then fails before serving traffic unless all fields below are valid.

- `WB_RND_INTERIM_ENABLED=1`
- `WB_RND_DEPLOYMENT_TARGET`: provider service name
- `WB_RND_DEPLOYMENT_ID`: immutable provider deployment identifier
- `WB_RND_CODE_COMMIT`: full 40-character Git SHA
- `WB_RND_INTERIM_DATABASE`: absolute SQLite path on the mounted persistent volume
- `WB_RND_DATABASE_DURABILITY=provider_persistent_volume`
- `WB_RND_INTERNAL_AUTH_SCHEME=shared_header_hmac_sha256_v1`
- `WB_RND_INTERIM_INTERNAL_TOKEN`: provider-managed secret of at least 32 UTF-8 bytes
- `WB_RND_WORKERS=1`: required while SQLite is the deployment database

Never commit the token or pass it as a command-line argument. The health response exposes
only a 12-character SHA-256 prefix so operators can distinguish secret rotations without
recovering the secret.

`GET /health` derives the required endpoint inventory from the mounted FastAPI routes. It
fails if any required family is absent: health, recommendation, state machine, device, or
counseling. `deployment_contract` is null when enforcement is disabled.

This contract proves readiness and local restart persistence. It is not proof that a
provider deployment exists or that production traffic has been served.

## Local container flow

```bash
docker build -t wellnessbox-rnd-staging .
docker run --rm -p 8000:8000 -e WB_RND_APP_ENV=staging wellnessbox-rnd-staging
```

## Local non-container flow

```bash
pip install -e ".[dev]"
python scripts/start_inference_api.py
```

## Smoke test

Use the bounded deterministic request fixture already covered by API tests:

```bash
python scripts/run_staging_api_smoke.py --base-url http://127.0.0.1:8000
```

The smoke checks:

- `GET /health`
- `POST /v1/recommend`
- `status = ok`
- `next_action = start_plan`
- `metadata.mode = deterministic_baseline_v1`

## Provider notes

- Keep the deployment provider-agnostic: deploy the container or run the same startup command on any always-on CPU host.
- Do not rely on provider-specific background jobs, managed queues, or private service bindings for the deterministic baseline path.
- One worker is the default recommendation for staging because the current goal is stable 24/7 availability, not throughput tuning.
