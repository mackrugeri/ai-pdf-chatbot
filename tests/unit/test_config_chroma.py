import pytest
from pydantic import ValidationError

from app.config import Settings
from app.config.chroma import ChromaSettings

VALID = {"chroma_host": "vectors.internal"}


@pytest.mark.parametrize(
    "invalid",
    [
        {"chroma_host": "http://vectors"},
        {"chroma_port": 0},
        {"chroma_port": 65536},
        {"chroma_timeout_seconds": 0},
        {"chroma_host": "bad host"},
    ],
)
def test_invalid_configuration_is_rejected(invalid):
    with pytest.raises(ValidationError):
        ChromaSettings(_env_file=None, **invalid)


def test_valid_component_configuration_and_production_guards():
    ChromaSettings(_env_file=None, **VALID)
    ChromaSettings(_env_file=None, app_env="production", **VALID)
    with pytest.raises(ValidationError):
        ChromaSettings(
            _env_file=None, app_env="production", **{**VALID, "chroma_host": None}
        )


def test_settings_composition_keeps_component_validation():
    Settings(_env_file=None, **VALID)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, chroma_host="http://vectors")


def test_chroma_env_and_optional_gateway_token_redaction(monkeypatch):
    monkeypatch.setenv("CHROMA_PORT", "8000")
    settings = ChromaSettings(
        _env_file=None, chroma_host="chroma", chroma_auth_token="private-gateway-token"
    )
    assert settings.chroma_port == 8000
    assert "private-gateway-token" not in repr(settings) + settings.model_dump_json()


@pytest.mark.parametrize("host", ["chroma:8000", "user@chroma", "chroma/path"])
def test_chroma_host_excludes_ports_and_credentials(host):
    with pytest.raises(ValidationError):
        ChromaSettings(_env_file=None, chroma_host=host)


def test_chroma_ipv6_host():
    assert ChromaSettings(_env_file=None, chroma_host="::1").chroma_host == "::1"
