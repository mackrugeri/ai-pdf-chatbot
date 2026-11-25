"""Explicit lifecycle and bounded asynchronous PostgreSQL connection pool."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg import Error as PsycopgError
from psycopg_pool import AsyncConnectionPool, PoolTimeout

from app.config.database import DatabaseSettings


class DatabasePool:
    """A process-local pool; construct at app startup, never on module import.

    Keep transactions short and database-only. Callers must release a connection
    before invoking Ollama, object storage, Chroma, or broker operations.
    """

    def __init__(self, settings: DatabaseSettings) -> None:
        if settings.database_url is None:
            raise ValueError("DATABASE_URL is required to create the PostgreSQL pool")
        self._settings = settings
        self._pool = AsyncConnectionPool(
            conninfo=settings.database_url.get_secret_value(),
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            timeout=settings.db_pool_timeout_seconds,
            kwargs={
                "connect_timeout": settings.db_connect_timeout_seconds,
                "application_name": "ai-pdf-chatbot-api",
            },
            open=False,
            name="ai-pdf-chatbot-api",
        )
        self._opened = False

    async def open(self) -> None:
        """Open connections and fail startup if the configured database is unavailable."""
        if self._opened:
            return
        try:
            await self._pool.open(
                wait=True, timeout=self._settings.db_pool_timeout_seconds
            )
            self._opened = True
            # A zero-sized warm pool does not connect during open(wait=True).
            async with self.connection() as connection:
                await connection.execute("SELECT 1")
        except BaseException:
            # A timed-out pool open can still own background workers/sockets.
            self._opened = False
            await self._pool.close()
            raise

    async def close(self) -> None:
        """Drain checked-out connections and stop pool workers during shutdown."""
        if self._opened:
            await self._pool.close(timeout=self._settings.db_pool_timeout_seconds)
            self._opened = False

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[AsyncConnection]:
        """Borrow a connection with a bounded acquisition wait."""
        if not self._opened:
            raise RuntimeError("PostgreSQL pool is not open")
        async with self._pool.connection(
            timeout=self._settings.db_pool_timeout_seconds
        ) as connection:
            yield connection

    async def is_ready(self) -> bool:
        """Return readiness only after connectivity and schema migrations exist."""
        if not self._opened:
            return False
        try:
            async with self.connection() as connection:
                cursor = await connection.execute(
                    "SELECT to_regclass('public.schema_migrations') IS NOT NULL"
                )
                row = await cursor.fetchone()
                return bool(row and row[0])
        except (PsycopgError, PoolTimeout):
            return False
