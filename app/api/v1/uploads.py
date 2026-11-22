from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import idempotency_key
from app.api.errors import not_implemented
from app.schemas.documents import UploadCompleted, UploadCreated, UploadRequest

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadCreated, status_code=status.HTTP_201_CREATED)
async def initiate_upload(
    body: UploadRequest, key: Annotated[str, Depends(idempotency_key)]
) -> UploadCreated:
    not_implemented("Upload initialization")


@router.post("/{upload_id}/complete", response_model=UploadCompleted, status_code=202)
async def complete_upload(
    upload_id: UUID, key: Annotated[str, Depends(idempotency_key)]
) -> UploadCompleted:
    not_implemented("Immutable upload completion and ingestion scheduling")
