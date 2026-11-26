"""PostgreSQL identity mapping for verified OIDC issuer/subject pairs."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.storage.postgres.connection import DatabasePool


@dataclass(frozen=True)
class UserIdentity:
    user_id: UUID
    is_active: bool


class UserRepository:
    def __init__(self, pool: DatabasePool) -> None:
        self._pool = pool

    async def resolve(self, issuer: str, subject: str) -> UserIdentity:
        """Create a first-seen user or return its active state without reactivation."""
        async with self._pool.connection() as connection, connection.transaction():
            await connection.execute(
                """
                INSERT INTO users (id, issuer, subject)
                VALUES (%s, %s, %s)
                ON CONFLICT (issuer, subject) DO NOTHING
                """,
                (uuid4(), issuer, subject),
            )
            cursor = await connection.execute(
                """
                SELECT id, is_active
                FROM users
                WHERE issuer = %s AND subject = %s
                FOR SHARE
                """,
                (issuer, subject),
            )
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError("Identity upsert did not return a user")
            return UserIdentity(user_id=row[0], is_active=row[1])
