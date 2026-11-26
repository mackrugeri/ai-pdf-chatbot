from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import pagination, require_scopes
from app.api.errors import not_implemented
from app.schemas.common import JobAccepted, JobStatus, JobType, Pagination
from app.schemas.jobs import JobList, JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "", response_model=JobList, dependencies=[Depends(require_scopes("pdf:read"))]
)
async def list_jobs(
    page: Annotated[Pagination, Depends(pagination)],
    state: Annotated[JobStatus | None, Query()] = None,
    job_type: Annotated[JobType | None, Query(alias="type")] = None,
) -> JobList:
    not_implemented("Owner-scoped recent job discovery")


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    dependencies=[Depends(require_scopes("pdf:read"))],
)
async def get_job(job_id: UUID) -> JobResponse:
    not_implemented("Authorized job status and result lookup")


@router.post(
    "/{job_id}/cancel",
    response_model=JobAccepted,
    status_code=202,
    dependencies=[Depends(require_scopes("pdf:write"))],
)
async def cancel_job(job_id: UUID) -> JobAccepted:
    not_implemented("Job cancellation")
