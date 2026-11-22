"""Environment configuration for the API shell; service settings come later."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "AI PDF Chatbot"
    app_env: Literal["development", "test", "production"] = "development"
