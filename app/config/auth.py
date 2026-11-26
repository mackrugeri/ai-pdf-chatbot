"""Validated issuer, audience, JWKS and JWT verification settings."""

from pydantic import Field, field_validator, model_validator

from app.config.base import EnvironmentSettings, service_url


class AuthSettings(EnvironmentSettings):
    oidc_issuer: str | None = None
    oidc_audience: str | None = Field(default=None, min_length=1, max_length=255)
    oidc_jwks_url: str | None = None
    oidc_allowed_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    oidc_clock_skew_seconds: int = Field(default=30, ge=0, le=120)
    oidc_jwks_cache_ttl_seconds: int = Field(default=300, ge=1, le=3600)
    oidc_http_timeout_seconds: float = Field(default=5, gt=0, le=60)
    oidc_max_token_bytes: int = Field(default=16384, ge=1024, le=65536)
    oidc_jwks_max_keys: int = Field(default=100, ge=1, le=256)
    oidc_unknown_kid_refresh_seconds: float = Field(default=5, ge=1, le=60)

    @field_validator("oidc_issuer", "oidc_jwks_url")
    @classmethod
    def validate_oidc_url(cls, value):
        if value is not None:
            url = service_url(value, {"http", "https"})
            if url.username or url.password or url.query:
                raise ValueError(
                    "OIDC URLs cannot contain credentials or query strings"
                )
        return value  # Preserve issuer spelling exactly for future token comparison.

    @field_validator("oidc_audience")
    @classmethod
    def validate_audience(cls, value):
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError(
                "OIDC_AUDIENCE must be non-empty without surrounding whitespace"
            )
        return value

    @field_validator("oidc_allowed_algorithms")
    @classmethod
    def validate_algorithms(cls, value):
        allowed = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "EdDSA"}
        if not value or len(set(value)) != len(value) or not set(value) <= allowed:
            raise ValueError(
                "Configure a non-empty distinct asymmetric JWT algorithm allowlist"
            )
        return value

    @model_validator(mode="after")
    def validate_auth(self):
        configured = [self.oidc_issuer, self.oidc_audience, self.oidc_jwks_url]
        if any(configured) and not all(configured):
            raise ValueError(
                "OIDC issuer, audience and JWKS URL must be configured together"
            )
        if self.app_env == "production":
            if not all(configured):
                raise ValueError("OIDC configuration is required in production")
            if any(
                service_url(value, {"http", "https"}).scheme != "https"
                for value in [self.oidc_issuer, self.oidc_jwks_url]
            ):
                raise ValueError("Production OIDC endpoints require HTTPS")
        return self
