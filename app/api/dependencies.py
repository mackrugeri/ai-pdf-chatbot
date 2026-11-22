"""Dependency boundaries. No token is treated as verified by this scaffold."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Header, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.errors import APIError
from app.schemas.common import Pagination

bearer = HTTPBearer(
    auto_error=False,
    description="API-audience access token. Token verification is not wired yet.",
)


@dataclass(frozen=True)
class Principal:
    owner_id: UUID
    scopes: frozenset[str] = frozenset()


async def require_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)],
) -> Principal:
    if credentials is None:
        raise APIError(
            401,
            "AUTHENTICATION_REQUIRED",
            "A Bearer access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Replace with the real issuer/audience/signature/expiry/active-user checks.
    # Never accept an arbitrary Bearer string or trust an owner ID from the client.
    raise APIError(503, "AUTH_NOT_CONFIGURED", "Token verification is not configured.")


def pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=2048)] = None,
) -> Pagination:
    return Pagination(limit=limit, cursor=cursor)


def idempotency_key(
    key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
) -> str:
    if not key.strip():
        raise APIError(422, "VALIDATION_ERROR", "An idempotency key is required.")
    return key
