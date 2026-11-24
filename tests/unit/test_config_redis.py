import pytest
from pydantic import ValidationError

from app.config import Settings
from app.config.redis import RedisSettings

VALID = {"redis_url": "rediss://:private-password@cache:6379/0"}


@pytest.mark.parametrize(
    "invalid",
    [
        {"redis_url": "http://cache/0"},
        {"redis_url": "redis://cache/-1"},
        {"redis_url": "redis://cache/not-a-db"},
        {"redis_max_connections": 0},
        {"redis_socket_timeout_seconds": 0},
    ],
)
def test_invalid_configuration_is_rejected(invalid):
    with pytest.raises(ValidationError):
        RedisSettings(_env_file=None, **invalid)


def test_valid_component_configuration_and_production_guards():
    RedisSettings(_env_file=None, **VALID)
    RedisSettings(_env_file=None, app_env="production", **VALID)
    with pytest.raises(ValidationError):
        RedisSettings(
            _env_file=None,
            app_env="production",
            **{**VALID, "redis_url": "redis://cache/0"},
        )


def test_settings_composition_keeps_component_validation():
    Settings(_env_file=None, **VALID)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, redis_url="http://cache/0")


def test_redis_redaction_and_environment(monkeypatch):
    monkeypatch.setenv("REDIS_URL", VALID["redis_url"])
    settings = RedisSettings(_env_file=None)
    assert settings.redis_url.get_secret_value() == VALID["redis_url"]
    assert "private-password" not in repr(settings) + settings.model_dump_json()
