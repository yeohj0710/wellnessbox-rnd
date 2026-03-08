from fastapi import FastAPI

from apps.inference_api.routes.health import router as health_router
from apps.inference_api.routes.recommend import router as recommend_router
from wellnessbox_rnd.config import get_settings
from wellnessbox_rnd.logging import configure_logging

settings = get_settings()
configure_logging(settings)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="WellnessBox R&D inference API scaffold",
)
app.include_router(health_router)
app.include_router(recommend_router, prefix=settings.api_prefix)

