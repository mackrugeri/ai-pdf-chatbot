from fastapi import APIRouter, Request

from app.api.errors import APIError
from app.schemas.common import HealthResponse
from app.storage.postgres.connection import DatabasePool

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="alive")


@router.get("/ready", response_model=HealthResponse)
async def readiness(request: Request) -> HealthResponse:
    # Readiness is cheap and requires connectivity plus the migration ledger.
    pool: DatabasePool | None = request.app.state.database_pool
    if pool is None or not await pool.is_ready():
        raise APIError(
            503, "NOT_READY", "Required database initialization is unavailable."
        )
    return HealthResponse(status="ready")
