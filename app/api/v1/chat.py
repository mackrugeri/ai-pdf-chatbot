from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import idempotency_key
from app.api.errors import not_implemented
from app.schemas.chat import ChatRequest
from app.schemas.common import JobAccepted

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=JobAccepted, status_code=202)
async def submit_question(
    body: ChatRequest, key: Annotated[str, Depends(idempotency_key)]
) -> JobAccepted:
    not_implemented("Durable question answering")
