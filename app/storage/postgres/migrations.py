"""Apply ordered SQL migrations under a PostgreSQL advisory transaction lock."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from app.storage.postgres.connection import DatabasePool

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
_MIGRATION_NAME = re.compile(r"^(?P<version>[0-9]{3,})_(?P<name>[a-z0-9_]+)\.sql$")
_MIGRATION_LOCK_ID = 2807984240134


class MigrationError(RuntimeError):
    """A migration is missing, changed after application, or unsafe to apply."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    checksum: str
    sql: str


def discover_migrations(directory: Path = MIGRATIONS_DIR) -> tuple[Migration, ...]:
    """Read migrations in version order and reject ambiguous/empty files."""
    migrations: list[Migration] = []
    seen_versions: set[int] = set()
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename: {path.name}")
        version = int(match.group("version"))
        if version in seen_versions:
            raise MigrationError(f"Duplicate migration version: {version}")
        seen_versions.add(version)
        raw = path.read_bytes()
        if not raw.strip():
            raise MigrationError(f"Empty migration: {path.name}")
        try:
            sql = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise MigrationError(f"Migration is not UTF-8: {path.name}") from None
        migrations.append(
            Migration(
                version=version,
                name=path.stem,
                checksum=hashlib.sha256(raw).hexdigest(),
                sql=sql,
            )
        )

    if not migrations:
        raise MigrationError(f"No SQL migrations found in {directory}")

    for expected, migration in enumerate(migrations, start=1):
        if migration.version != expected:
            raise MigrationError(
                f"Migration sequence has a gap before version {migration.version}"
            )
    return tuple(migrations)


async def apply_migrations(
    pool: DatabasePool, directory: Path = MIGRATIONS_DIR
) -> tuple[str, ...]:
    """Apply unapplied migrations atomically, once at a time across instances.

    Applied migration content is immutable: a changed name or checksum fails
    closed and requires a new forward migration. The database lock is held only
    while schema changes run, never during application/model/storage work.
    """
    migrations = discover_migrations(directory)
    applied_now: list[str] = []

    async with pool.connection() as connection, connection.transaction():
        await connection.execute(
            "SELECT pg_advisory_xact_lock(%s)", (_MIGRATION_LOCK_ID,)
        )
        await connection.execute(
            """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version integer PRIMARY KEY,
                    name text NOT NULL UNIQUE,
                    checksum char(64) NOT NULL,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
        )
        cursor = await connection.execute(
            "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
        )
        applied = {row[0]: (row[1], row[2].strip()) for row in await cursor.fetchall()}
        available = {migration.version: migration for migration in migrations}

        unknown = sorted(set(applied) - set(available))
        if unknown:
            raise MigrationError(
                f"Database has migration versions absent from this release: {unknown}"
            )

        for version, (name, checksum) in applied.items():
            migration = available[version]
            if name != migration.name or checksum != migration.checksum:
                raise MigrationError(
                    f"Applied migration {version} changed; add a new migration instead"
                )

        for migration in migrations:
            if migration.version in applied:
                continue
            # psycopg's simple-query path permits the multi-statement SQL file.
            await connection.execute(migration.sql, prepare=False)
            await connection.execute(
                "INSERT INTO schema_migrations (version, name, checksum) "
                "VALUES (%s, %s, %s)",
                (migration.version, migration.name, migration.checksum),
            )
            applied_now.append(migration.name)

    return tuple(applied_now)
