import pytest
from pydantic import ValidationError

from app.config import Settings
from app.config.database import DatabaseSettings


def test_database_defaults_and_pool_bounds():
    settings = DatabaseSettings(_env_file=None)
    assert settings.database_url is None
    assert settings.db_pool_max_size == 5
    with pytest.raises(ValidationError):
        DatabaseSettings(_env_file=None, db_pool_min_size=6, db_pool_max_size=5)
    with pytest.raises(ValidationError):
        DatabaseSettings(_env_file=None, db_connect_timeout_seconds=0)


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///tmp.db",
        "postgresql://host",
        "postgresql://host:0/db",
        "postgresql://host:bad/db",
    ],
)
def test_database_rejects_invalid_urls(url):
    with pytest.raises(ValidationError):
        DatabaseSettings(_env_file=None, database_url=url)


def test_database_secret_redaction_and_loading(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text(
        "DATABASE_URL=postgresql://owner:private-password@db:5432/library\nDB_POOL_MAX_SIZE=8\n"
    )
    settings = Settings(_env_file=path)
    assert settings.db_pool_max_size == 8
    assert "private-password" not in repr(settings) + settings.model_dump_json()
    monkeypatch.setenv("DB_POOL_MAX_SIZE", "9")
    assert Settings(_env_file=path).db_pool_max_size == 9
    with pytest.raises(ValidationError) as exc:
        DatabaseSettings(
            _env_file=None, database_url="wrong://owner:private-password@db/name"
        )
    assert "private-password" not in str(exc.value)


def test_database_production_requires_real_configuration():
    for value in [
        None,
        "postgresql://owner:replace_with_password@db/library",
        "postgresql://db/library",
    ]:
        with pytest.raises(ValidationError):
            DatabaseSettings(_env_file=None, app_env="production", database_url=value)
    DatabaseSettings(
        _env_file=None,
        app_env="production",
        database_url="postgresql://owner:private-password@db/library",
    )
