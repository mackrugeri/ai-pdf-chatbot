"""OIDC access-token verification with bounded, rotation-aware JWKS caching."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt import PyJWK
from jwt.exceptions import PyJWTError

from app.config.auth import AuthSettings

_MAX_JWKS_BYTES = 512 * 1024


class InvalidAccessToken(Exception):
    """The presented bearer token is invalid or not intended for this API."""


class IdentityProviderUnavailable(Exception):
    """The configured JWKS endpoint cannot currently validate tokens safely."""


@dataclass(frozen=True)
class AccessTokenIdentity:
    issuer: str
    subject: str
    scopes: frozenset[str]


class OIDCTokenVerifier:
    """Validate API access tokens against one explicitly configured OIDC issuer."""

    def __init__(
        self,
        settings: AuthSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if (
            not settings.oidc_issuer
            or not settings.oidc_audience
            or not settings.oidc_jwks_url
        ):
            raise ValueError(
                "Complete OIDC issuer, audience, and JWKS configuration is required"
            )
        self._settings = settings
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._owns_client = True
        self._jwks: tuple[dict[str, Any], ...] = ()
        self._expires_at = 0.0
        self._last_unknown_refresh_at = -settings.oidc_unknown_kid_refresh_seconds
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._settings.oidc_http_timeout_seconds),
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
                headers={"Accept": "application/json"},
            )

    async def close(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
        self._client = None

    async def verify_access_token(self, token: str) -> AccessTokenIdentity:
        if (
            not isinstance(token, str)
            or not token
            or len(token) > self._settings.oidc_max_token_bytes
        ):
            raise InvalidAccessToken("Malformed bearer token")
        try:
            token.encode("ascii")
        except UnicodeEncodeError:
            raise InvalidAccessToken("Malformed bearer token") from None
        try:
            header = jwt.get_unverified_header(token)
        except (PyJWTError, TypeError, ValueError):
            raise InvalidAccessToken("Malformed bearer token") from None

        algorithm = header.get("alg")
        key_id = header.get("kid")
        if (
            algorithm not in self._settings.oidc_allowed_algorithms
            or not isinstance(key_id, str)
            or not key_id
        ):
            raise InvalidAccessToken("Unsupported bearer token header")

        key = await self._get_signing_key(key_id, algorithm)
        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                audience=self._settings.oidc_audience,
                issuer=self._settings.oidc_issuer,
                leeway=self._settings.oidc_clock_skew_seconds,
                options={"require": ["iss", "sub", "aud", "exp", "iat"]},
            )
        except PyJWTError:
            raise InvalidAccessToken("Bearer token validation failed") from None

        subject = claims.get("sub")
        issuer = claims.get("iss")
        if not isinstance(subject, str) or not subject.strip() or len(subject) > 512:
            raise InvalidAccessToken("Bearer token subject is invalid")
        if issuer != self._settings.oidc_issuer:
            raise InvalidAccessToken("Bearer token issuer is invalid")
        return AccessTokenIdentity(
            issuer=issuer,
            subject=subject,
            scopes=frozenset(self._extract_scopes(claims)),
        )

    async def _get_signing_key(self, key_id: str, algorithm: str) -> Any:
        if self._client is None:
            raise IdentityProviderUnavailable("OIDC verifier is not initialized")
        async with self._lock:
            now = time.monotonic()
            if not self._jwks or now >= self._expires_at:
                await self._refresh_jwks(now)

            matching = self._matching_keys(key_id, algorithm)
            if (
                not matching
                and now - self._last_unknown_refresh_at
                >= self._settings.oidc_unknown_kid_refresh_seconds
            ):
                self._last_unknown_refresh_at = now
                await self._refresh_jwks(time.monotonic())
                matching = self._matching_keys(key_id, algorithm)

            if len(matching) != 1:
                raise InvalidAccessToken(
                    "No unique signing key matches the bearer token"
                )
            try:
                return PyJWK.from_dict(matching[0], algorithm=algorithm).key
            except (PyJWTError, TypeError, ValueError):
                raise IdentityProviderUnavailable(
                    "OIDC signing key is malformed"
                ) from None

    def _matching_keys(self, key_id: str, algorithm: str) -> list[dict[str, Any]]:
        return [
            key
            for key in self._jwks
            if key.get("kid") == key_id
            and key.get("use", "sig") == "sig"
            and key.get("alg", algorithm) == algorithm
        ]

    async def _refresh_jwks(self, now: float) -> None:
        assert self._client is not None
        try:
            async with self._client.stream(
                "GET", self._settings.oidc_jwks_url
            ) as response:
                if response.status_code != 200:
                    raise IdentityProviderUnavailable(
                        "OIDC JWKS endpoint returned an error"
                    )
                raw = await response.aread()
            if len(raw) > _MAX_JWKS_BYTES:
                raise IdentityProviderUnavailable("OIDC JWKS document is too large")
            document = json.loads(raw)
            keys = document.get("keys") if isinstance(document, Mapping) else None
            if (
                not isinstance(keys, list)
                or not keys
                or len(keys) > self._settings.oidc_jwks_max_keys
            ):
                raise IdentityProviderUnavailable("OIDC JWKS document is invalid")
            if any(not isinstance(key, dict) for key in keys):
                raise IdentityProviderUnavailable("OIDC JWKS document is invalid")
            self._jwks = tuple(keys)
            self._expires_at = now + self._settings.oidc_jwks_cache_ttl_seconds
        except IdentityProviderUnavailable:
            raise
        except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError):
            raise IdentityProviderUnavailable(
                "OIDC JWKS endpoint is unavailable"
            ) from None

    @staticmethod
    def _extract_scopes(claims: Mapping[str, Any]) -> set[str]:
        scopes: set[str] = set()
        raw_scope = claims.get("scope", "")
        if isinstance(raw_scope, str):
            scopes.update(item for item in raw_scope.split() if item)
        elif isinstance(raw_scope, list):
            scopes.update(item for item in raw_scope if isinstance(item, str) and item)

        realm_access = claims.get("realm_access")
        if isinstance(realm_access, Mapping):
            roles = realm_access.get("roles", [])
            if isinstance(roles, list):
                scopes.update(item for item in roles if isinstance(item, str) and item)
        resource_access = claims.get("resource_access")
        if isinstance(resource_access, Mapping):
            for client in resource_access.values():
                if isinstance(client, Mapping) and isinstance(
                    client.get("roles"), list
                ):
                    scopes.update(
                        item
                        for item in client["roles"]
                        if isinstance(item, str) and item
                    )
        return scopes
