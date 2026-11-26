"""Authentication and authorization dependencies for protected API routes."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg import Error as PsycopgError
from psycopg_pool import PoolTimeout

from app.api.errors import APIError
from app.auth.verifier import IdentityProviderUnavailable, InvalidAccessToken
from app.schemas.common import Pagination
from app.storage.postgres.connection import DatabasePool
from app.storage.postgres.users import UserRepository

bearer = HTTPBearer(
    auto_error=False,
    description="Verified OIDC access token issued for the PDF chatbot API.",
)


@dataclass(frozen=True)
class Principal:
    owner_id: UUID
    scopes: frozenset[str] = frozenset()


async def require_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)],
) -> Principal:
    if credentials is None:
        raise APIError(
            401,
            "AUTHENTICATION_REQUIRED",
            "A Bearer access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    verifier = getattr(request.app.state, "oidc_verifier", None)
    if verifier is None:
        raise APIError(
            503, "AUTH_NOT_CONFIGURED", "Token verification is not configured."
        )
    try:
        identity = await verifier.verify_access_token(credentials.credentials)
    except InvalidAccessToken:
        raise APIError(
            401,
            "INVALID_ACCESS_TOKEN",
            "The access token is invalid or expired.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        ) from None
    except IdentityProviderUnavailable:
        raise APIError(
            503,
            "IDENTITY_PROVIDER_UNAVAILABLE",
            "Token verification is temporarily unavailable.",
            retryable=True,
        ) from None

    pool: DatabasePool | None = getattr(request.app.state, "database_pool", None)
    if pool is None:
        raise APIError(
            503, "DATABASE_UNAVAILABLE", "User identity storage is unavailable."
        )
    try:
        user = await UserRepository(pool).resolve(identity.issuer, identity.subject)
    except (PsycopgError, PoolTimeout):
        raise APIError(
            503,
            "DATABASE_UNAVAILABLE",
            "User identity storage is temporarily unavailable.",
            retryable=True,
        ) from None
    if not user.is_active:
        raise APIError(403, "USER_INACTIVE", "This account is disabled.")
    return Principal(owner_id=user.user_id, scopes=identity.scopes)


def require_scopes(*required_scopes: str):
    required = frozenset(required_scopes)
    if not required or any(not scope or scope.strip() != scope for scope in required):
        raise ValueError("At least one non-empty scope is required")

    async def check_scopes(
        principal: Annotated[Principal, Depends(require_principal)],
    ) -> Principal:
        missing = required - principal.scopes
        if missing:
            scope_text = " ".join(sorted(required))
            raise APIError(
                403,
                "INSUFFICIENT_SCOPE",
                "The access token does not grant this operation.",
                headers={
                    "WWW-Authenticate": (
                        f'Bearer error="insufficient_scope", scope="{scope_text}"'
                    )
                },
            )
        return principal

    return check_scopes


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
