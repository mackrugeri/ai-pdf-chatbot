import pytest
from pydantic import ValidationError

from app.config import Settings
from app.config.object_storage import ObjectStorageSettings

VALID = {
    "object_storage_endpoint": "https://objects.internal",
    "object_storage_bucket": "pdf-objects",
    "deletion_journal_endpoint": "https://journal.internal",
    "deletion_journal_bucket": "pdf-journal",
    "deletion_journal_independent": True,
}


@pytest.mark.parametrize(
    "invalid",
    [
        {"object_storage_endpoint": "http://objects"},
        {"object_storage_bucket": "UPPERCASE"},
        {"object_storage_access_key": "access-without-secret"},
        {"object_storage_signed_url_ttl_seconds": 901},
        {
            "object_storage_endpoint": "http://store",
            "object_storage_bucket": "same-bucket",
            "deletion_journal_endpoint": "http://store",
            "deletion_journal_bucket": "same-bucket",
        },
    ],
)
def test_invalid_configuration_is_rejected(invalid):
    with pytest.raises(ValidationError):
        ObjectStorageSettings(_env_file=None, **invalid)


def test_valid_component_configuration_and_production_guards():
    ObjectStorageSettings(_env_file=None, **VALID)
    ObjectStorageSettings(_env_file=None, app_env="production", **VALID)
    with pytest.raises(ValidationError):
        ObjectStorageSettings(
            _env_file=None,
            app_env="production",
            **{**VALID, "deletion_journal_independent": False},
        )


def test_settings_composition_keeps_component_validation():
    Settings(_env_file=None, **VALID)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, object_storage_endpoint="http://objects")


def test_storage_keys_are_paired_and_redacted():
    settings = ObjectStorageSettings(
        _env_file=None,
        object_storage_access_key="private-access-key",
        object_storage_secret_key="private-secret-key",
    )
    assert "private-access-key" not in repr(settings) + settings.model_dump_json()
    assert "private-secret-key" not in repr(settings) + settings.model_dump_json()
    # Missing explicit keys is allowed for a future SDK workload-identity chain.
    ObjectStorageSettings(_env_file=None, app_env="production", **VALID)


@pytest.mark.parametrize("bucket", ["a..bucket", "127.0.0.1", "bucket.-name"])
def test_storage_rejects_invalid_bucket_labels(bucket):
    with pytest.raises(ValidationError):
        ObjectStorageSettings(
            _env_file=None,
            object_storage_endpoint="http://store",
            object_storage_bucket=bucket,
        )


def test_combined_production_settings_remain_strict_and_redact_secrets():
    settings = Settings(
        _env_file=None,
        app_env="production",
        database_url="postgresql://owner:db-private-password@db/library",
        broker_url="amqps://owner:broker-private-password@queue/library",
        redis_url="rediss://:redis-private-password@cache/0",
        model_backend="ollama",
        oidc_issuer="https://identity.internal/realm",
        oidc_audience="pdf-api",
        oidc_jwks_url="https://identity.internal/certs",
        chroma_host="vectors.internal",
        **VALID,
    )
    encoded = repr(settings) + settings.model_dump_json()
    for secret in [
        "db-private-password",
        "broker-private-password",
        "redis-private-password",
    ]:
        assert secret not in encoded
    with pytest.raises(ValidationError):
        Settings(
            **{**settings.model_dump(), "db_pool_min_size": 99, "db_pool_max_size": 1},
            _env_file=None,
        )
