"""Shared wire contracts. Request data is never echoed in error responses."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(APIModel):
    code: str
    message: str
    retryable: bool = False


class ErrorResponse(APIModel):
    error: ErrorDetail
    request_id: UUID


class HealthResponse(APIModel):
    status: str


class Pagination(APIModel):
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=2048)


class DocumentStatus(StrEnum):
    UPLOADING = "uploading"
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYING = "retrying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class JobType(StrEnum):
    INGESTION = "ingestion"
    ANSWER = "answer"
    CLEANUP = "cleanup"


class JobAccepted(APIModel):
    job_id: UUID
    document_id: UUID | None = None
