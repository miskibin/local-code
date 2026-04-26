import pytest


@pytest.mark.asyncio
async def test_sql_query_returns_table_artifact(chinook_path):
    from app.db import init_db
    from app.tools.sql_query import sql_query

    await init_db()
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
async def test_sql_query_truncates_at_200(chinook_path):
    from app.db import init_db
    from app.tools.sql_query import sql_query

    await init_db()
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
