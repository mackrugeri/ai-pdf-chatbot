"""Chroma service configuration; no embedded index or client is created."""

import ipaddress
import re

from pydantic import Field, SecretStr, field_validator, model_validator

from app.config.base import EnvironmentSettings


class ChromaSettings(EnvironmentSettings):
    chroma_host: str | None = None
    chroma_port: int = Field(default=8001, ge=1, le=65535)
    chroma_ssl: bool = False
    chroma_tenant: str = Field(default="default_tenant", min_length=1, max_length=255)
    chroma_database: str = Field(
        default="default_database", min_length=1, max_length=255
    )
    chroma_auth_token: SecretStr | None = None
    chroma_timeout_seconds: float = Field(default=10, gt=0, le=300)

    @field_validator("chroma_host")
    @classmethod
    def validate_chroma_host(cls, value):
        if value is not None:
            try:
                ipaddress.ip_address(value)
            except ValueError:
                if not re.fullmatch(
                    r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", value
                ):
                    raise ValueError(
                        "CHROMA_HOST must be a hostname or IP without a scheme, port or credentials"
                    ) from None
        return value

    @model_validator(mode="after")
    def validate_chroma(self):
        if self.app_env == "production" and not self.chroma_host:
            raise ValueError("CHROMA_HOST is required in production")
        return self
