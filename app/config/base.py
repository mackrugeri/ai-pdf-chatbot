"""Shared environment loading and safe URL validation; never connects to services."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
        hide_input_in_errors=True,
    )
    app_name: str = "AI PDF Chatbot"
    app_env: Literal["development", "test", "production"] = "development"


def service_url(value: str, schemes: set[str], *, database: bool = False):
    try:
        url = urlsplit(value)
        if (
            url.scheme not in schemes
            or not url.hostname
            or any(c.isspace() for c in value)
            or url.fragment
            or (url.port is not None and not 1 <= url.port <= 65535)
            or (database and url.path in {"", "/"})
        ):
            raise ValueError
        return url
    except ValueError:
        raise ValueError(
            "Invalid service URL; check scheme, host, port and path"
        ) from None


def require_secret(value: SecretStr | None, name: str) -> None:
    if value is None or not value.get_secret_value().strip():
        raise ValueError(f"{name} must be configured in production")
    raw = value.get_secret_value().lower()
    if any(marker in raw for marker in ("replace_with", "changeme", "change_me")):
        raise ValueError(f"{name} cannot contain example credentials in production")
