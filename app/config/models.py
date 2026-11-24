"""Hardware-neutral model endpoints, identity and bounded inference settings."""

from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.config.base import EnvironmentSettings, service_url


class ModelSettings(EnvironmentSettings):
    model_backend: Literal["fake", "ollama"] = "fake"
    generation_model: str = Field(default="qwen3:4b", min_length=1, max_length=200)
    embedding_model: str = Field(
        default="nomic-embed-text", min_length=1, max_length=200
    )
    ollama_generation_url: str = "http://localhost:11434"
    ollama_query_embedding_url: str = "http://localhost:11434"
    ollama_ingestion_embedding_url: str = "http://localhost:11434"
    model_timeout_seconds: float = Field(default=180, gt=0, le=1800)
    model_max_concurrency: int = Field(default=1, ge=1, le=64)
    model_context_tokens: int = Field(default=8192, ge=512, le=131072)
    model_max_output_tokens: int = Field(default=1024, ge=1, le=16384)

    @field_validator(
        "ollama_generation_url",
        "ollama_query_embedding_url",
        "ollama_ingestion_embedding_url",
    )
    @classmethod
    def validate_model_url(cls, value):
        url = service_url(value, {"http", "https"})
        if url.username or url.password or url.query:
            raise ValueError(
                "Model endpoints cannot contain credentials or query strings"
            )
        return value.rstrip("/")

    @field_validator("generation_model", "embedding_model")
    @classmethod
    def validate_model_name(cls, value):
        if (
            not value.strip()
            or any(c.isspace() for c in value)
            or value.endswith(":cloud")
        ):
            raise ValueError("Configure a non-empty self-hosted model identity")
        return value

    @model_validator(mode="after")
    def validate_models(self):
        if self.model_max_output_tokens >= self.model_context_tokens:
            raise ValueError("Model output budget must be smaller than context budget")
        if self.app_env == "production" and self.model_backend != "ollama":
            raise ValueError("Production cannot use fake models")
        return self
