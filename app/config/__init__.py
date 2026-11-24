"""Component settings; loading configuration performs no service I/O."""

from app.config.auth import AuthSettings
from app.config.broker import BrokerSettings
from app.config.chroma import ChromaSettings
from app.config.database import DatabaseSettings
from app.config.models import ModelSettings
from app.config.object_storage import ObjectStorageSettings
from app.config.redis import RedisSettings


class Settings(
    DatabaseSettings,
    BrokerSettings,
    RedisSettings,
    ModelSettings,
    AuthSettings,
    ChromaSettings,
    ObjectStorageSettings,
):
    """Validated, hardware-neutral application settings."""
