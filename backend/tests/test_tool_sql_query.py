import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
async def _chinook_path():
    here = Path(__file__).resolve().parents[1] / "data" / "chinook.db"
    os.environ["CHINOOK_DB_PATH"] = str(here)
    from app.config import get_settings
    from app.db import init_db

    get_settings.cache_clear()
    await init_db()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_sql_query_returns_table_artifact():
    from app.tools.sql_query import sql_query

    msg = await sql_query.ainvoke(
        dict(
            type="tool_call",
            id="s1",
            name="sql_query",
            args={"sql": "SELECT FirstName, LastName FROM Customer LIMIT 3"},
        )
    )
    assert msg.artifact["kind"] == "table"
    assert msg.artifact["source_kind"] == "sql"
    assert (
        msg.artifact["source_code"]
        == "SELECT FirstName, LastName FROM Customer LIMIT 3"
    )
    cols = [c["key"] for c in msg.artifact["payload"]["columns"]]
    assert cols == ["FirstName", "LastName"]
    assert len(msg.artifact["payload"]["rows"]) == 3


@pytest.mark.asyncio
async def test_sql_query_truncates_at_200():
    from app.tools.sql_query import sql_query

    msg = await sql_query.ainvoke(
        dict(
            type="tool_call",
            id="s2",
            name="sql_query",
            args={"sql": "SELECT TrackId FROM Track"},
        )
    )
    assert len(msg.artifact["payload"]["rows"]) == 200
    assert msg.artifact["payload"]["truncated"] is True
    assert "truncated" in msg.content.lower()
