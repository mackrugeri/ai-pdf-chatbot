from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AnyHttpUrl, Field, StringConstraints

from app.schemas.common import APIModel, DocumentStatus, ErrorDetail

Filename = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
]


class UploadRequest(APIModel):
    filename: Filename
    size_bytes: int = Field(gt=0, le=20 * 1024 * 1024)


class UploadCreated(APIModel):
    upload_id: UUID
    document_id: UUID
    upload_url: AnyHttpUrl
    expires_at: datetime


class UploadCompleted(APIModel):
    document_id: UUID
    job_id: UUID | None = None
    duplicate: bool = False


class DocumentResponse(APIModel):
    id: UUID
    original_filename: str
    status: DocumentStatus
    page_count: int | None = Field(default=None, ge=0)
    textless_page_count: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    error: ErrorDetail | None = None
    created_at: datetime
    updated_at: datetime


class DocumentList(APIModel):
    items: list[DocumentResponse]
    next_cursor: str | None = None


class DownloadResponse(APIModel):
    download_url: AnyHttpUrl
    expires_at: datetime
