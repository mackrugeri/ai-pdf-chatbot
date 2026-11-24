"""PostgreSQL connection and bounded pool configuration, without I/O."""

from pydantic import Field, SecretStr, field_validator, model_validator

from app.config.base import EnvironmentSettings, require_secret, service_url


class DatabaseSettings(EnvironmentSettings):
    database_url: SecretStr | None = None
    db_pool_min_size: int = Field(default=0, ge=0, le=100)
    db_pool_max_size: int = Field(default=5, ge=1, le=100)
    db_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    db_pool_timeout_seconds: float = Field(default=10, gt=0, le=300)

    @field_validator("database_url")
    @classmethod
    def validate_url(cls, value: SecretStr | None):
        if value is not None:
            service_url(
                value.get_secret_value(), {"postgresql", "postgres"}, database=True
            )
        return value

    @model_validator(mode="after")
    def validate_database(self):
        if self.db_pool_min_size > self.db_pool_max_size:
            raise ValueError("DB_POOL_MIN_SIZE cannot exceed DB_POOL_MAX_SIZE")
        if self.app_env == "production":
            require_secret(self.database_url, "DATABASE_URL")
            url = service_url(
                self.database_url.get_secret_value(),
                {"postgresql", "postgres"},
                database=True,
            )
            if not url.username or not url.password:
                raise ValueError("DATABASE_URL requires credentials in production")
        return self
