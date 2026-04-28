import atexit
import json
import os
import shutil
import tempfile
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlmodel import delete

# A tempfile-backed test DB instead of `:memory:`. Alembic's env.py spins up
# its own async engine to run migrations; with `:memory:` that engine sees a
# private DB, creates the schema, then disposes — leaving `app.db.engine`'s
# connections looking at a fresh empty DB. A real file is shared across
# engines and avoids the connection-isolation surprise.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="lc_test_db_")
_TEST_DB_PATH = os.path.join(_TEST_DB_DIR, "test.db")
os.environ.setdefault(
    "APP_DB_URL",
    f"sqlite+aiosqlite:///{_TEST_DB_PATH.replace(os.sep, '/')}",
)
atexit.register(lambda: shutil.rmtree(_TEST_DB_DIR, ignore_errors=True))

os.environ.setdefault("CHECKPOINT_DB_PATH", ":memory:")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_MODEL", "gemma4:e4b")


@pytest.fixture
def chinook_path():
    here = Path(__file__).resolve().parents[1] / "data" / "chinook.db"
    os.environ["CHINOOK_DB_PATH"] = str(here)
    from app.config import get_settings

    get_settings.cache_clear()
    yield str(here)
    get_settings.cache_clear()


@pytest.fixture
def stub_state():
    """Minimal app.state stand-in for runner tests (mcp_registry.tools = [])."""
    return SimpleNamespace(mcp_registry=SimpleNamespace(tools=[]))


TEST_OWNER_ID = "usr_test"
TEST_OWNER_EMAIL = "test@example.com"


async def ensure_test_user() -> str:
    """Insert (or no-op) the shared test user. Returns its id."""
    from app.db import async_session
    from app.models import User
    from app.utils import now_utc

    async with async_session() as s:
        existing = await s.get(User, TEST_OWNER_ID)
        if existing is None:
            s.add(User(id=TEST_OWNER_ID, email=TEST_OWNER_EMAIL, created_at=now_utc()))
            await s.commit()
    return TEST_OWNER_ID


@pytest.fixture(autouse=True)
def _patch_owner_id_for_tests(monkeypatch):
    """Tests rarely pass through the `/chat` route that injects owner_id into the
    runnable config. Default any missing owner_id to the shared test user so
    `create_artifact` (called from tools / runners) doesn't blow up."""
    from app import artifact_store

    real = artifact_store.owner_id_from_config

    def _safe(config):
        try:
            return real(config)
        except RuntimeError:
            return TEST_OWNER_ID

    monkeypatch.setattr(artifact_store, "owner_id_from_config", _safe)


async def reset_task_tables(*models) -> None:
    """init_db + truncate the supplied SQLModel tables in one go.

    Recreates the shared test user after truncation so foreign keys hold.
    """
    from app.db import async_session, init_db

    await init_db()
    async with async_session() as s:
        for model in models:
            await s.execute(delete(model))
        await s.commit()
    await ensure_test_user()


def parse_sse_events(lines: Iterable[str]) -> list[dict]:
    """Parse `data: {...}` lines from an SSE stream into dicts (skip [DONE])."""
    out: list[dict] = []
    for line in lines:
        if not line.startswith("data: "):
            continue
        body = line.removeprefix("data: ").strip()
        if not body or body == "[DONE]":
            continue
        try:
            out.append(json.loads(body))
        except json.JSONDecodeError:
            continue
    return out
