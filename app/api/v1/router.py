from fastapi import APIRouter, Depends

from app.api.dependencies import require_principal
from app.api.v1 import capabilities, chat, documents, jobs, uploads
from app.schemas.common import ErrorResponse

router = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(require_principal)],
    responses={
        401: {"model": ErrorResponse, "description": "Authentication required"},
        422: {"model": ErrorResponse, "description": "Invalid request"},
        501: {"model": ErrorResponse, "description": "Operation not implemented"},
        503: {"model": ErrorResponse, "description": "Required service not configured"},
    },
)
for feature_router in (
    capabilities.router,
    uploads.router,
    documents.router,
    chat.router,
    jobs.router,
):
    router.include_router(feature_router)
