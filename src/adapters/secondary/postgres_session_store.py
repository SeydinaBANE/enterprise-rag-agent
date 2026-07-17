from __future__ import annotations

from psycopg_pool import AsyncConnectionPool

from src.domain.config import settings
from src.domain.exceptions import VectorStoreError
from src.domain.models import ChatMessage
from src.ports.outbound import ISessionStore

MAX_TURNS = 10

_SCHEMA = """
CREATE TABLE IF NOT EXISTS rag_sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES rag_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rag_messages_session_idx
    ON rag_messages (session_id, created_at);
"""


class PostgresSessionStore(ISessionStore):
    def __init__(self, dsn: str, max_turns: int = MAX_TURNS) -> None:
        self._dsn = dsn
        self._max_turns = max_turns
        self._pool: AsyncConnectionPool | None = None

    async def _get_pool(self) -> AsyncConnectionPool:
        if self._pool is None:
            self._pool = AsyncConnectionPool(
                self._dsn,
                open=False,
                min_size=settings.postgres_pool_min,
                max_size=settings.postgres_pool_max,
            )
            await self._pool.open()
            async with self._pool.connection() as conn:
                await conn.execute(_SCHEMA)
        return self._pool

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        try:
            pool = await self._get_pool()
            async with pool.connection() as conn:
                rows = await conn.execute(
                    """
                    SELECT role, content FROM rag_messages
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (session_id, self._max_turns * 2),
                )
                return [
                    ChatMessage(role=row[0], content=row[1])
                    for row in reversed(await rows.fetchall())
                ]
        except Exception as exc:
            raise VectorStoreError(f"Postgres get_history failed: {exc}") from exc

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        try:
            pool = await self._get_pool()
            async with pool.connection() as conn:
                await conn.execute(
                    "INSERT INTO rag_sessions (id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (session_id,),
                )
                await conn.execute(
                    "INSERT INTO rag_messages (session_id, role, content) VALUES (%s, %s, %s)",
                    (session_id, message.role, message.content),
                )
        except Exception as exc:
            raise VectorStoreError(f"Postgres add_message failed: {exc}") from exc

    async def count(self) -> int:
        try:
            pool = await self._get_pool()
            async with pool.connection() as conn:
                row = await (await conn.execute("SELECT COUNT(*) FROM rag_sessions")).fetchone()
                return int(row[0]) if row else 0
        except Exception:
            return 0

    async def is_healthy(self) -> bool:
        try:
            pool = await self._get_pool()
            async with pool.connection() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
