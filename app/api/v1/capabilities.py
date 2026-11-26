from fastapi import APIRouter, Depends

from app.api.dependencies import require_scopes
from app.api.errors import not_implemented
from app.schemas.capabilities import CapabilitiesResponse

router = APIRouter(tags=["capabilities"])


@router.get(
    "/capabilities",
    response_model=CapabilitiesResponse,
    dependencies=[Depends(require_scopes("pdf:read"))],
)
async def capabilities() -> CapabilitiesResponse:
    not_implemented("Service capability discovery")
