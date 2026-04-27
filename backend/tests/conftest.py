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


@pytest.fixture(scope="session")
def python_sandbox():
    """Shared Pyodide sandbox for tests that exercise `python_exec`.

    Skipped when Deno isn't installed so unrelated test runs stay green.
    Cold cost ~30 s on first call; subsequent calls reuse Deno's HTTP cache.
    Also installs the sandbox on `app.runtime.set_sandbox` so tool-level tests
    that go through the `python_exec` tool (which reads from runtime, not from
    a fixture) work the same as the lifespan-wired production path.
    """
    import shutil as _shutil
    import tempfile

    if not _shutil.which("deno"):
        pytest.skip("deno not installed; python sandbox tests need Deno")

    from langchain_sandbox import PyodideSandbox

    from app.python_sandbox import _deno_cache_dir
    from app.runtime import set_sandbox

    tmp = tempfile.mkdtemp(prefix="lc_test_sb_", dir=Path.cwd())
    sb = PyodideSandbox(
        sessions_dir=tmp,
        allow_net=["cdn.jsdelivr.net", "pypi.org", "files.pythonhosted.org"],
        allow_read=[tmp, _deno_cache_dir(), "node_modules", str(Path.cwd())],
        allow_write=[tmp],
    )
    set_sandbox(sb)
    yield sb
    _shutil.rmtree(tmp, ignore_errors=True)


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
