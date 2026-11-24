import pytest
from pydantic import ValidationError

from app.config import Settings
from app.config.broker import BrokerSettings

VALID = {"broker_url": "amqp://owner:private-password@queue:5672/library"}


@pytest.mark.parametrize(
    "invalid",
    [
        {"broker_url": "https://queue/library"},
        {"broker_url": "amqp://queue:0/library"},
        {"worker_prefetch_count": 0},
        {"ingestion_queue": "same", "answer_queue": "same"},
        {"cleanup_queue": "bad queue"},
    ],
)
def test_invalid_configuration_is_rejected(invalid):
    with pytest.raises(ValidationError):
        BrokerSettings(_env_file=None, **invalid)


def test_valid_component_configuration_and_production_guards():
    BrokerSettings(_env_file=None, **VALID)
    BrokerSettings(_env_file=None, app_env="production", **VALID)
    with pytest.raises(ValidationError):
        BrokerSettings(
            _env_file=None,
            app_env="production",
            **{**VALID, "broker_url": "amqp://guest:guest@queue/library"},
        )


def test_settings_composition_keeps_component_validation():
    Settings(_env_file=None, **VALID)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, broker_url="https://queue/library")


def test_broker_environment_and_redaction(monkeypatch):
    monkeypatch.setenv("BROKER_URL", VALID["broker_url"])
    settings = BrokerSettings(_env_file=None)
    assert settings.broker_url.get_secret_value() == VALID["broker_url"]
    assert "private-password" not in repr(settings) + settings.model_dump_json()
