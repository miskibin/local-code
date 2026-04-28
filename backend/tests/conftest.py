import json
import os
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlmodel import delete

os.environ.setdefault("APP_DB_URL", "sqlite+aiosqlite:///:memory:")
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


async def reset_task_tables(*models) -> None:
    """init_db + truncate the supplied SQLModel tables in one go."""
    from app.db import async_session, init_db

    await init_db()
    async with async_session() as s:
        for model in models:
            await s.execute(delete(model))
        await s.commit()


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
