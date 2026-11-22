from datetime import datetime
from uuid import UUID

from app.schemas.chat import ChatResult
from app.schemas.common import APIModel, ErrorDetail, JobStatus, JobType


class JobSummary(APIModel):
    id: UUID
    type: JobType
    state: JobStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    result_available: bool = False


class JobResponse(JobSummary):
    result: ChatResult | None = None
    error: ErrorDetail | None = None
    poll_after_seconds: int = 2


class JobList(APIModel):
    items: list[JobSummary]
    next_cursor: str | None = None
