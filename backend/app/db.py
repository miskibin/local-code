from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from app import models  # noqa: F401  ensure metadata registered
from app.config import get_settings

_db_url = get_settings().app_db_url
# NullPool for file-based SQLite: each session owns its connection so the pool
# never tries to terminate a connection inside a cancelled task scope
# (aiosqlite raises CancelledError / "Connection closed" otherwise).
# In-memory SQLite must NOT use NullPool — each connection would be a fresh DB.
_pool_kwargs = {} if ":memory:" in _db_url else {"poolclass": NullPool}
engine = create_async_engine(_db_url, future=True, **_pool_kwargs)
_sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def async_session() -> AsyncIterator[AsyncSession]:
    async with _sessionmaker() as session:
        yield session


_COLUMN_BACKFILLS = {
    "chatsession": [
        ("is_pinned", "BOOLEAN NOT NULL DEFAULT 0"),
        ("pinned_at", "DATETIME"),
    ],
    "savedartifact": [
        ("pinned", "BOOLEAN NOT NULL DEFAULT 0"),
    ],
    "savedtask": [
        ("tags", "JSON NOT NULL DEFAULT '[]'"),
        ("role", "VARCHAR"),
        ("creator", "VARCHAR"),
    ],
}


async def _backfill_columns(conn) -> None:
    is_postgres = _db_url.startswith("postgresql")
    for table, cols in _COLUMN_BACKFILLS.items():
        if is_postgres:
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
                {"t": table},
            )
            existing = {row[0] for row in result.all()}
        else:
            existing = {
                row[1] for row in (await conn.execute(text(f"PRAGMA table_info({table})"))).all()
            }
        for name, ddl in cols:
            if name not in existing:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await _backfill_columns(conn)
