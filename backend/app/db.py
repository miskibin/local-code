from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app import models  # noqa: F401  ensure metadata registered
from app.config import get_settings

engine = create_async_engine(get_settings().app_db_url, future=True)
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
}


async def _backfill_columns(conn) -> None:
    for table, cols in _COLUMN_BACKFILLS.items():
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


async def get_session() -> AsyncIterator[AsyncSession]:
    async with _sessionmaker() as session:
        yield session
