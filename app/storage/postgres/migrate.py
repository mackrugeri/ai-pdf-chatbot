"""Command line entry point: python -m app.storage.postgres.migrate."""

from __future__ import annotations

import asyncio

from app.config.database import DatabaseSettings
from app.storage.postgres.connection import DatabasePool
from app.storage.postgres.migrations import apply_migrations


async def _run() -> None:
    settings = DatabaseSettings()
    if settings.database_url is None:
        raise SystemExit("DATABASE_URL must be configured before running migrations")

    pool = DatabasePool(settings)
    await pool.open()
    try:
        applied = await apply_migrations(pool)
    finally:
        await pool.close()

    if applied:
        print(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        print("Database schema is already up to date.")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
