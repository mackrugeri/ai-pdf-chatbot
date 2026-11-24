import pytest
from pydantic import ValidationError

from app.config import Settings
from app.config.auth import AuthSettings

VALID = {
    "oidc_issuer": "https://identity.internal/realms/app",
    "oidc_audience": "pdf-api",
    "oidc_jwks_url": "https://identity.internal/realms/app/certs",
}


@pytest.mark.parametrize(
    "invalid",
    [
        {"oidc_allowed_algorithms": ["none"]},
        {"oidc_allowed_algorithms": ["HS256"]},
        {"oidc_allowed_algorithms": []},
        {"oidc_issuer": "http://identity"},
        {"oidc_audience": " "},
        {"oidc_clock_skew_seconds": 121},
    ],
)
def test_invalid_configuration_is_rejected(invalid):
    with pytest.raises(ValidationError):
        AuthSettings(_env_file=None, **invalid)


def test_valid_component_configuration_and_production_guards():
    AuthSettings(_env_file=None, **VALID)
    AuthSettings(_env_file=None, app_env="production", **VALID)
    with pytest.raises(ValidationError):
        AuthSettings(
            _env_file=None,
            app_env="production",
            **{
                **VALID,
                "oidc_issuer": "http://identity",
                "oidc_audience": "pdf-api",
                "oidc_jwks_url": "http://identity/certs",
            },
        )


def test_settings_composition_keeps_component_validation():
    Settings(_env_file=None, **VALID)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, oidc_allowed_algorithms=["none"])


def test_oidc_json_allowlist_and_local_http_configuration(monkeypatch):
    monkeypatch.setenv("OIDC_ALLOWED_ALGORITHMS", '["RS256", "ES256"]')
    settings = AuthSettings(
        _env_file=None,
        oidc_issuer="http://localhost:8080/realm/",
        oidc_audience="pdf-api",
        oidc_jwks_url="http://localhost:8080/certs",
    )
    assert settings.oidc_allowed_algorithms == ["RS256", "ES256"]
    assert settings.oidc_issuer.endswith("/")
