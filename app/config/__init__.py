"""Component settings; loading configuration performs no service I/O."""

from app.config.broker import BrokerSettings
from app.config.database import DatabaseSettings


class Settings(DatabaseSettings, BrokerSettings):
    """Validated, hardware-neutral application settings."""
