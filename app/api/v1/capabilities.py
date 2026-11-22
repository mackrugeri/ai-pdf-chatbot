from fastapi import APIRouter

from app.api.errors import not_implemented
from app.schemas.capabilities import CapabilitiesResponse

router = APIRouter(tags=["capabilities"])


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities() -> CapabilitiesResponse:
    not_implemented("Service capability discovery")
