"""Redis cache/admission connection settings, without opening a client."""

from pydantic import Field, SecretStr, field_validator, model_validator

from app.config.base import EnvironmentSettings, require_secret, service_url


class RedisSettings(EnvironmentSettings):
    redis_url: SecretStr | None = None
    redis_max_connections: int = Field(default=20, ge=1, le=500)
    redis_connect_timeout_seconds: float = Field(default=5, gt=0, le=60)
    redis_socket_timeout_seconds: float = Field(default=5, gt=0, le=60)

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value):
        if value is not None:
            url = service_url(value.get_secret_value(), {"redis", "rediss"})
            path = url.path.removeprefix("/")
            if path and (not path.isdecimal()):
                raise ValueError(
                    "REDIS_URL database index must be a non-negative integer"
                )
        return value

    @model_validator(mode="after")
    def validate_redis(self):
        if self.app_env == "production":
            require_secret(self.redis_url, "REDIS_URL")
            url = service_url(self.redis_url.get_secret_value(), {"redis", "rediss"})
            if not url.password:
                raise ValueError("REDIS_URL requires credentials in production")
        return self
