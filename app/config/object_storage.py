"""Private S3-compatible objects and independent deletion-journal settings."""

import ipaddress
import re

from pydantic import Field, SecretStr, field_validator, model_validator

from app.config.base import EnvironmentSettings, require_secret, service_url


class ObjectStorageSettings(EnvironmentSettings):
    object_storage_endpoint: str | None = None
    object_storage_bucket: str | None = None
    object_storage_region: str = Field(default="us-east-1", min_length=1)
    object_storage_access_key: SecretStr | None = None
    object_storage_secret_key: SecretStr | None = None
    object_storage_timeout_seconds: float = Field(default=10, gt=0, le=300)
    object_storage_signed_url_ttl_seconds: int = Field(default=300, ge=1, le=900)
    deletion_journal_endpoint: str | None = None
    deletion_journal_bucket: str | None = None
    deletion_journal_access_key: SecretStr | None = None
    deletion_journal_secret_key: SecretStr | None = None
    deletion_journal_independent: bool = False

    @field_validator("object_storage_endpoint", "deletion_journal_endpoint")
    @classmethod
    def validate_object_endpoint(cls, value):
        if value is not None:
            url = service_url(value, {"http", "https"})
            if url.username or url.password or url.query:
                raise ValueError(
                    "Storage endpoints cannot contain credentials or query strings"
                )
        return value.rstrip("/") if value is not None else None

    @field_validator("object_storage_bucket", "deletion_journal_bucket")
    @classmethod
    def validate_bucket(cls, value):
        if value is not None and not re.fullmatch(
            r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", value
        ):
            raise ValueError(
                "Configure a 3-63 character lowercase S3-compatible bucket name"
            )
        if value is not None:
            if any(marker in value for marker in ("..", ".-", "-.")):
                raise ValueError(
                    "Bucket labels cannot contain adjacent dots or dot/hyphen boundaries"
                )
            try:
                ipaddress.ip_address(value)
            except ValueError:
                pass
            else:
                raise ValueError("Bucket names cannot be IP addresses")
        return value

    @model_validator(mode="after")
    def validate_object_storage(self):
        for access, secret, label in [
            (
                self.object_storage_access_key,
                self.object_storage_secret_key,
                "Object storage",
            ),
            (
                self.deletion_journal_access_key,
                self.deletion_journal_secret_key,
                "Deletion journal",
            ),
        ]:
            if (access is None) != (secret is None):
                raise ValueError(
                    f"{label} access and secret keys must be configured together"
                )
            if access is not None:
                require_secret(access, f"{label} access key")
                require_secret(secret, f"{label} secret key")
        for endpoint, bucket, label in [
            (
                self.object_storage_endpoint,
                self.object_storage_bucket,
                "Object storage",
            ),
            (
                self.deletion_journal_endpoint,
                self.deletion_journal_bucket,
                "Deletion journal",
            ),
        ]:
            if (endpoint is None) != (bucket is None):
                raise ValueError(
                    f"{label} endpoint and bucket must be configured together"
                )
        if self.object_storage_endpoint and (
            self.object_storage_endpoint,
            self.object_storage_bucket,
        ) == (self.deletion_journal_endpoint, self.deletion_journal_bucket):
            raise ValueError("Deletion journal must not share the application bucket")
        if self.app_env == "production":
            if not all(
                [
                    self.object_storage_endpoint,
                    self.object_storage_bucket,
                    self.deletion_journal_endpoint,
                    self.deletion_journal_bucket,
                    self.deletion_journal_independent,
                ]
            ):
                raise ValueError(
                    "Production needs configured storage and an independently protected journal"
                )
            for value in [self.object_storage_endpoint, self.deletion_journal_endpoint]:
                if service_url(value, {"http", "https"}).scheme != "https":
                    raise ValueError(
                        "Production object/journal endpoints require HTTPS"
                    )
        return self
