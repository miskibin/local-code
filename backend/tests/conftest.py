import os
from pathlib import Path

import pytest

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
