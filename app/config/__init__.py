"""Component settings, composed into one backward-compatible application Settings."""

from app.config.database import DatabaseSettings


class Settings(DatabaseSettings):
    """Validated application configuration. Loading settings performs no service I/O."""
