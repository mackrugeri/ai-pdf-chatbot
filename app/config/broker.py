"""RabbitMQ transport and bounded worker defaults; no Celery app is created."""

from pydantic import Field, SecretStr, field_validator, model_validator

from app.config.base import EnvironmentSettings, require_secret, service_url


class BrokerSettings(EnvironmentSettings):
    broker_url: SecretStr | None = None
    broker_connect_timeout_seconds: float = Field(default=5, gt=0, le=60)
    broker_heartbeat_seconds: int = Field(default=30, ge=1, le=300)
    worker_prefetch_count: int = Field(default=1, ge=1, le=16)
    job_max_retries: int = Field(default=3, ge=0, le=10)
    ingestion_queue: str = Field(default="ingestion", pattern=r"^[A-Za-z0-9_.-]+$")
    answer_queue: str = Field(default="answers", pattern=r"^[A-Za-z0-9_.-]+$")
    cleanup_queue: str = Field(default="cleanup", pattern=r"^[A-Za-z0-9_.-]+$")

    @field_validator("broker_url")
    @classmethod
    def validate_broker_url(cls, value):
        if value is not None:
            service_url(value.get_secret_value(), {"amqp", "amqps"})
        return value

    @model_validator(mode="after")
    def validate_broker(self):
        if len({self.ingestion_queue, self.answer_queue, self.cleanup_queue}) != 3:
            raise ValueError("Worker queue names must be distinct")
        if self.app_env == "production":
            require_secret(self.broker_url, "BROKER_URL")
            url = service_url(self.broker_url.get_secret_value(), {"amqp", "amqps"})
            if not url.username or not url.password or url.username == "guest":
                raise ValueError(
                    "BROKER_URL requires non-guest credentials in production"
                )
        return self
