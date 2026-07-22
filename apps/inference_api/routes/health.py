from fastapi import APIRouter, Request

from wellnessbox_rnd.config import get_settings
from wellnessbox_rnd.deployment import build_endpoint_inventory
from wellnessbox_rnd.runtime import validate_runtime_readiness

router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck(request: Request) -> dict[str, object]:
    settings = get_settings()
    runtime_readiness = getattr(request.app.state, "runtime_readiness", None)
    if runtime_readiness is None:
        runtime_readiness = validate_runtime_readiness()
        request.app.state.runtime_readiness = runtime_readiness

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "runtime_status": runtime_readiness["runtime_status"],
        "checks": runtime_readiness,
        "deployment_contract": getattr(
            request.app.state, "deployment_contract_public", None
        ),
        "endpoint_inventory": build_endpoint_inventory(list(request.app.routes)),
    }

