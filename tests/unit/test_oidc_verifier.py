import base64
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.verifier import (
    IdentityProviderUnavailable,
    InvalidAccessToken,
    OIDCTokenVerifier,
)
from app.config.auth import AuthSettings

ISSUER = "http://localhost:8080/realms/ai-pdf-chatbot"
AUDIENCE = "pdf-api"
JWKS_URL = "http://keycloak.test/realms/ai-pdf-chatbot/certs"


def b64url_int(value):
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def make_signer(kid="key-1"):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": b64url_int(numbers.n),
        "e": b64url_int(numbers.e),
    }
    return private, jwk


def make_token(private, *, kid="key-1", **overrides):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "sub": "local-user-123",
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 300,
        "scope": "openid profile",
        "realm_access": {"roles": ["pdf:read", "pdf:write"]},
    }
    claims.update(overrides)
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": kid})


def configured_settings():
    return AuthSettings(
        _env_file=None,
        oidc_issuer=ISSUER,
        oidc_audience=AUDIENCE,
        oidc_jwks_url=JWKS_URL,
        oidc_jwks_cache_ttl_seconds=60,
    )


@pytest.mark.asyncio
async def test_verifies_signature_issuer_audience_and_extracts_role_scopes():
    private, jwk = make_signer()

    async def handler(request):
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = OIDCTokenVerifier(
        configured_settings(), transport=httpx.MockTransport(handler)
    )
    await verifier.open()
    try:
        identity = await verifier.verify_access_token(make_token(private))
    finally:
        await verifier.close()

    assert identity.issuer == ISSUER
    assert identity.subject == "local-user-123"
    assert identity.scopes == frozenset({"openid", "profile", "pdf:read", "pdf:write"})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "some-other-api"},
        {"iss": "http://attacker.invalid"},
        {"exp": int(time.time()) - 600},
    ],
)
async def test_rejects_wrong_audience_issuer_and_expired_tokens(claims):
    private, jwk = make_signer()

    async def handler(request):
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = OIDCTokenVerifier(
        configured_settings(), transport=httpx.MockTransport(handler)
    )
    await verifier.open()
    try:
        with pytest.raises(InvalidAccessToken):
            await verifier.verify_access_token(make_token(private, **claims))
    finally:
        await verifier.close()


@pytest.mark.asyncio
async def test_rejects_bad_signature_and_disallowed_algorithm():
    _, jwk = make_signer()
    attacker, _ = make_signer()

    async def handler(request):
        return httpx.Response(200, json={"keys": [jwk]})

    verifier = OIDCTokenVerifier(
        configured_settings(), transport=httpx.MockTransport(handler)
    )
    await verifier.open()
    try:
        with pytest.raises(InvalidAccessToken):
            await verifier.verify_access_token(make_token(attacker))
        unsigned = jwt.encode(
            {"iss": ISSUER, "sub": "x", "aud": AUDIENCE, "iat": 1, "exp": 9},
            key="",
            algorithm="none",
            headers={"kid": "key-1"},
        )
        with pytest.raises(InvalidAccessToken):
            await verifier.verify_access_token(unsigned)
    finally:
        await verifier.close()


@pytest.mark.asyncio
async def test_refreshes_jwks_when_a_rotated_kid_appears():
    old_private, old_jwk = make_signer("old-key")
    new_private, new_jwk = make_signer("new-key")
    current = {"keys": [old_jwk]}
    fetches = 0

    async def handler(request):
        nonlocal fetches
        fetches += 1
        return httpx.Response(200, json=current)

    verifier = OIDCTokenVerifier(
        configured_settings(), transport=httpx.MockTransport(handler)
    )
    await verifier.open()
    try:
        await verifier.verify_access_token(make_token(old_private, kid="old-key"))
        current["keys"] = [new_jwk]
        identity = await verifier.verify_access_token(
            make_token(new_private, kid="new-key")
        )
    finally:
        await verifier.close()

    assert identity.subject == "local-user-123"
    assert fetches == 2


@pytest.mark.asyncio
async def test_jwks_outage_fails_closed_and_oversized_token_is_rejected():
    private, _ = make_signer()

    async def handler(request):
        return httpx.Response(503)

    verifier = OIDCTokenVerifier(
        configured_settings(), transport=httpx.MockTransport(handler)
    )
    await verifier.open()
    try:
        with pytest.raises(IdentityProviderUnavailable):
            await verifier.verify_access_token(make_token(private))
        with pytest.raises(InvalidAccessToken):
            await verifier.verify_access_token("a" * 17000)
    finally:
        await verifier.close()
