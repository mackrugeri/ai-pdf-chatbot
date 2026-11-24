"""Component settings; loading configuration performs no service I/O."""

from app.config.broker import BrokerSettings
from app.config.database import DatabaseSettings
from app.config.redis import RedisSettings


class Settings(DatabaseSettings, BrokerSettings, RedisSettings):
    """Validated, hardware-neutral application settings."""
