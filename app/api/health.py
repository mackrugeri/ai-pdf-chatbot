from fastapi import APIRouter

from app.api.errors import APIError
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="alive")


@router.get("/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    # Do not report ready until real storage/schema/service initialization exists.
    # This public response is intentionally minimal; no dependency details are exposed.
    raise APIError(503, "NOT_READY", "Service initialization is not implemented yet.")
