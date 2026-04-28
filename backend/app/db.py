import asyncio as _asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
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


def _alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    # Alembic is sync — strip async driver prefix so it doesn't deadlock in a thread
    sync_url = _db_url.replace("sqlite+aiosqlite", "sqlite")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg


async def init_db() -> None:
    cfg = _alembic_config()
    # alembic uses sync engines internally; run on a worker thread so we don't
    # block the event loop and don't double-open the async engine's pool.
    await _asyncio.to_thread(command.upgrade, cfg, "head")
