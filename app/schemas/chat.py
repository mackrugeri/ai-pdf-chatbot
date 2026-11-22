from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints, field_validator

from app.schemas.common import APIModel

Question = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]


class ChatRequest(APIModel):
    question: Question
    document_ids: list[UUID] = Field(min_length=1, max_length=10)

    @field_validator("document_ids")
    @classmethod
    def reject_duplicate_documents(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Document selection must contain unique IDs")
        return value


class SourceResponse(APIModel):
    source_id: str
    chunk_id: str
    document_id: UUID
    document_version: str
    filename: str
    page_number: int = Field(ge=1)
    excerpt: str


class ChatResult(APIModel):
    answer: str
    insufficient_evidence: bool
    sources: list[SourceResponse]
