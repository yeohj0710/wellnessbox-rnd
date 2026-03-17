import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request

from apps.inference_api.routes.health import router as health_router
from apps.inference_api.routes.recommend import router as recommend_router
from wellnessbox_rnd.config import get_settings
from wellnessbox_rnd.logging import configure_logging
from wellnessbox_rnd.runtime import validate_runtime_readiness

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger("wellnessbox_rnd.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime_readiness = validate_runtime_readiness()
    app.state.runtime_readiness = runtime_readiness
    logger.info(
        "api_startup_complete service=%s env=%s host=%s port=%s workers=%s knowledge_source=%s",
        settings.app_name,
        settings.app_env,
        settings.host,
        settings.port,
        settings.workers,
        runtime_readiness["knowledge_source"],
    )
    yield
    logger.info("api_shutdown_complete service=%s env=%s", settings.app_name, settings.app_env)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="WellnessBox R&D inference API scaffold",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    started_at = perf_counter()
    response = await call_next(request)
    duration_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "request_complete method=%s path=%s status_code=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(health_router)
app.include_router(recommend_router, prefix=settings.api_prefix)

