from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import idempotency_key, pagination, require_scopes
from app.api.errors import not_implemented
from app.schemas.common import JobAccepted, Pagination
from app.schemas.documents import DocumentList, DocumentResponse, DownloadResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get(
    "", response_model=DocumentList, dependencies=[Depends(require_scopes("pdf:read"))]
)
async def list_documents(
    page: Annotated[Pagination, Depends(pagination)],
) -> DocumentList:
    not_implemented("Owner-scoped document listing")


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(require_scopes("pdf:read"))],
)
async def get_document(document_id: UUID) -> DocumentResponse:
    not_implemented("Document lookup")


@router.get(
    "/{document_id}/download",
    response_model=DownloadResponse,
    dependencies=[Depends(require_scopes("pdf:read"))],
)
async def download_document(document_id: UUID) -> DownloadResponse:
    not_implemented("Authorized document download")


@router.post(
    "/{document_id}/retry",
    response_model=JobAccepted,
    status_code=202,
    dependencies=[Depends(require_scopes("pdf:write"))],
)
async def retry_document(
    document_id: UUID, key: Annotated[str, Depends(idempotency_key)]
) -> JobAccepted:
    not_implemented("Ingestion retry")


@router.delete(
    "/{document_id}",
    response_model=JobAccepted,
    status_code=202,
    dependencies=[Depends(require_scopes("pdf:write"))],
)
async def delete_document(document_id: UUID) -> JobAccepted:
    not_implemented("Journal-protected document deletion")
